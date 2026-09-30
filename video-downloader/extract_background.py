#!/usr/bin/env python3
"""Recover static video backgrounds from multiple frames without generative fill.

The extractor samples frames, detects hard cuts, aligns frames inside each shot,
and reconstructs each pixel from the closest *observed* sample to the temporal
median. This keeps output pixels tied to real source frames instead of inventing
new image content.
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path

import cv2
import numpy as np


@dataclass
class ShotInfo:
    index: int
    start_seconds: float
    end_seconds: float
    sampled_frames: int
    aligned_frames: int
    alignment_failures: int
    mean_consensus: float
    output: str


def _video_meta(path: Path) -> tuple[float, int, int, int, float]:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {path}")
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    cap.release()
    if fps <= 0 or total <= 0 or width <= 0 or height <= 0:
        raise RuntimeError(f"Invalid video metadata: fps={fps}, frames={total}, size={width}x{height}")
    return fps, total, width, height, total / fps


def _read_frame_at(cap: cv2.VideoCapture, frame_index: int) -> np.ndarray | None:
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(frame_index))
    ok, frame = cap.read()
    return frame if ok else None


def _signature(frame: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    small = cv2.resize(frame, (160, 90), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [24, 24], [0, 180, 0, 256])
    hist = cv2.normalize(hist, None).flatten().astype(np.float32)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    return hist, gray


def _is_cut(prev_sig: tuple[np.ndarray, np.ndarray], cur_sig: tuple[np.ndarray, np.ndarray]) -> bool:
    prev_hist, prev_gray = prev_sig
    cur_hist, cur_gray = cur_sig
    corr = float(cv2.compareHist(prev_hist, cur_hist, cv2.HISTCMP_CORREL))
    mad = float(np.mean(cv2.absdiff(prev_gray, cur_gray)))
    return (corr < 0.42 and mad > 32.0) or mad > 58.0


def sample_video(path: Path, sample_interval: float, max_samples: int) -> tuple[list[np.ndarray], list[float], list[tuple[int, int]]]:
    fps, total, _, _, duration = _video_meta(path)
    n_target = max(2, min(max_samples, int(math.ceil(duration / max(sample_interval, 0.05))) + 1))
    indices = np.linspace(0, max(total - 1, 0), n_target, dtype=np.int64)
    cap = cv2.VideoCapture(str(path))
    frames: list[np.ndarray] = []
    times: list[float] = []
    sigs: list[tuple[np.ndarray, np.ndarray]] = []
    for idx in indices:
        frame = _read_frame_at(cap, int(idx))
        if frame is None:
            continue
        frames.append(frame)
        times.append(float(idx) / fps)
        sigs.append(_signature(frame))
    cap.release()
    if len(frames) < 2:
        raise RuntimeError("Not enough decodable frames")

    boundaries = [0]
    for i in range(1, len(frames)):
        if _is_cut(sigs[i - 1], sigs[i]):
            boundaries.append(i)
    boundaries.append(len(frames))

    raw = [(boundaries[i], boundaries[i + 1]) for i in range(len(boundaries) - 1)]
    shots: list[tuple[int, int]] = []
    for start, end in raw:
        if shots and end - start < 4:
            ps, _ = shots[-1]
            shots[-1] = (ps, end)
        else:
            shots.append((start, end))
    if len(shots) > 1 and shots[-1][1] - shots[-1][0] < 4:
        ps, _ = shots[-2]
        shots[-2] = (ps, shots[-1][1])
        shots.pop()
    return frames, times, shots


def _orb_affine(reference: np.ndarray, frame: np.ndarray) -> tuple[np.ndarray, bool]:
    h, w = reference.shape[:2]
    scale = min(1.0, 900.0 / max(h, w))
    if scale < 1.0:
        size = (max(32, int(w * scale)), max(32, int(h * scale)))
        ref_s = cv2.resize(reference, size, interpolation=cv2.INTER_AREA)
        frm_s = cv2.resize(frame, size, interpolation=cv2.INTER_AREA)
    else:
        ref_s, frm_s = reference, frame

    ref_g = cv2.cvtColor(ref_s, cv2.COLOR_BGR2GRAY)
    frm_g = cv2.cvtColor(frm_s, cv2.COLOR_BGR2GRAY)
    orb = cv2.ORB_create(nfeatures=2200, fastThreshold=12)
    kp_ref, des_ref = orb.detectAndCompute(ref_g, None)
    kp_frm, des_frm = orb.detectAndCompute(frm_g, None)
    if des_ref is None or des_frm is None or len(kp_ref) < 12 or len(kp_frm) < 12:
        return np.eye(2, 3, dtype=np.float32), False

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
    pairs = matcher.knnMatch(des_frm, des_ref, k=2)
    good = [a for a, b in pairs if a.distance < 0.74 * b.distance]
    if len(good) < 12:
        return np.eye(2, 3, dtype=np.float32), False

    src = np.float32([kp_frm[m.queryIdx].pt for m in good])
    dst = np.float32([kp_ref[m.trainIdx].pt for m in good])
    mat, inliers = cv2.estimateAffinePartial2D(
        src, dst, method=cv2.RANSAC, ransacReprojThreshold=3.0, maxIters=3000, confidence=0.995
    )
    if mat is None or inliers is None or int(inliers.sum()) < 8:
        return np.eye(2, 3, dtype=np.float32), False

    a, b, tx = mat[0]
    c, d, ty = mat[1]
    zoom = math.sqrt(max(1e-8, a * a + c * c))
    angle = abs(math.degrees(math.atan2(c, a)))
    if not (0.92 <= zoom <= 1.08) or angle > 5.0:
        return np.eye(2, 3, dtype=np.float32), False
    if abs(tx) > ref_s.shape[1] * 0.18 or abs(ty) > ref_s.shape[0] * 0.18:
        return np.eye(2, 3, dtype=np.float32), False

    mat = mat.astype(np.float32)
    if scale < 1.0:
        mat[0, 2] /= scale
        mat[1, 2] /= scale
    return mat, True


def _align(reference: np.ndarray, frame: np.ndarray) -> tuple[np.ndarray, np.ndarray, bool]:
    h, w = reference.shape[:2]
    mat, ok = _orb_affine(reference, frame)
    aligned = cv2.warpAffine(
        frame, mat, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0)
    )
    mask = np.full(frame.shape[:2], 255, np.uint8)
    valid = cv2.warpAffine(mask, mat, (w, h), flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    return aligned, valid > 0, ok


def _reference_index(frames: list[np.ndarray]) -> int:
    thumbs = []
    for f in frames:
        t = cv2.resize(f, (128, 72), interpolation=cv2.INTER_AREA)
        thumbs.append(cv2.cvtColor(t, cv2.COLOR_BGR2GRAY).astype(np.float32))
    arr = np.stack(thumbs)
    flat = arr.reshape(arr.shape[0], -1)
    scores = []
    for i in range(len(frames)):
        scores.append(float(np.mean(np.abs(flat - flat[i]), axis=1).mean()))
    return int(np.argmin(scores))


def reconstruct(frames: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray, float, int]:
    ref_i = _reference_index(frames)
    reference = frames[ref_i]
    aligned: list[np.ndarray] = []
    valid_masks: list[np.ndarray] = []
    failures = 0
    for i, f in enumerate(frames):
        if i == ref_i:
            aligned.append(f.copy())
            valid_masks.append(np.ones(f.shape[:2], dtype=bool))
            continue
        af, vm, ok = _align(reference, f)
        aligned.append(af)
        valid_masks.append(vm)
        if not ok:
            failures += 1

    h, w = reference.shape[:2]
    output = np.empty_like(reference)
    confidence = np.zeros((h, w), dtype=np.uint8)
    consensus_accum = []

    for y0 in range(0, h, 96):
        y1 = min(h, y0 + 96)
        stack = np.stack([f[y0:y1] for f in aligned], axis=0).astype(np.float32)
        masks = np.stack([m[y0:y1] for m in valid_masks], axis=0)
        work = stack.copy()
        work[~masks[..., None].repeat(3, axis=3)] = np.nan
        median = np.nanmedian(work, axis=0)
        fallback = reference[y0:y1].astype(np.float32)
        median = np.where(np.isnan(median), fallback, median)

        dist = np.sum((stack - median[None, ...]) ** 2, axis=3)
        dist[~masks] = np.inf
        best = np.argmin(dist, axis=0)
        yy, xx = np.indices((y1 - y0, w))
        chosen = stack[best, yy, xx]
        no_valid = ~np.any(masks, axis=0)
        chosen[no_valid] = fallback[no_valid]
        output[y0:y1] = np.clip(chosen, 0, 255).astype(np.uint8)

        color_delta = np.sqrt(np.sum((stack - median[None, ...]) ** 2, axis=3))
        close = (color_delta < 24.0) & masks
        valid_count = np.maximum(1, masks.sum(axis=0))
        ratio = close.sum(axis=0) / valid_count
        consensus_accum.append(float(np.mean(ratio)))
        confidence[y0:y1] = np.clip(ratio * 255.0, 0, 255).astype(np.uint8)

    return output, confidence, float(np.mean(consensus_accum)), failures


def _contact_sheet(frames: list[np.ndarray], out: Path, cols: int = 4) -> None:
    if not frames:
        return
    thumbs = []
    for f in frames[:16]:
        h, w = f.shape[:2]
        tw = 320
        th = max(1, int(h * tw / w))
        thumbs.append(cv2.resize(f, (tw, th), interpolation=cv2.INTER_AREA))
    cell_h = max(x.shape[0] for x in thumbs)
    rows = math.ceil(len(thumbs) / cols)
    sheet = np.zeros((rows * cell_h, cols * 320, 3), np.uint8)
    for i, im in enumerate(thumbs):
        r, c = divmod(i, cols)
        sheet[r * cell_h:r * cell_h + im.shape[0], c * 320:(c + 1) * 320] = im
    cv2.imwrite(str(out), sheet, [cv2.IMWRITE_JPEG_QUALITY, 88])


def extract_video(path: Path, out_dir: Path, sample_interval: float, max_samples: int, max_frames_per_shot: int, max_shots: int) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    fps, total, width, height, duration = _video_meta(path)
    sampled, times, shots = sample_video(path, sample_interval, max_samples)

    ranked = sorted(shots, key=lambda p: p[1] - p[0], reverse=True)[:max_shots]
    ranked = sorted(ranked, key=lambda p: p[0])
    reports: list[ShotInfo] = []
    longest_len = -1
    best_path: Path | None = None

    for out_idx, (start, end) in enumerate(ranked, 1):
        idxs = np.linspace(start, end - 1, min(max_frames_per_shot, end - start), dtype=int)
        shot_frames = [sampled[int(i)] for i in idxs]
        bg, conf, consensus, failures = reconstruct(shot_frames)
        bg_name = f"background_{out_idx:03d}.png"
        conf_name = f"confidence_{out_idx:03d}.png"
        contact_name = f"samples_{out_idx:03d}.jpg"
        cv2.imwrite(str(out_dir / bg_name), bg, [cv2.IMWRITE_PNG_COMPRESSION, 3])
        cv2.imwrite(str(out_dir / conf_name), conf)
        _contact_sheet(shot_frames, out_dir / contact_name)
        reports.append(
            ShotInfo(
                index=out_idx,
                start_seconds=times[start],
                end_seconds=times[end - 1],
                sampled_frames=len(shot_frames),
                aligned_frames=len(shot_frames),
                alignment_failures=failures,
                mean_consensus=consensus,
                output=bg_name,
            )
        )
        if end - start > longest_len:
            longest_len = end - start
            best_path = out_dir / bg_name

    if best_path is not None:
        best = cv2.imread(str(best_path), cv2.IMREAD_COLOR)
        cv2.imwrite(str(out_dir / "best_background.png"), best, [cv2.IMWRITE_PNG_COMPRESSION, 3])

    report = {
        "input": str(path),
        "width": width,
        "height": height,
        "fps": fps,
        "frame_count": total,
        "duration_seconds": duration,
        "sample_interval_seconds": sample_interval,
        "total_sampled_frames": len(sampled),
        "detected_shots": len(shots),
        "exported_shots": len(reports),
        "method": "shot detection + ORB/RANSAC affine alignment + temporal median + observed-pixel medoid selection",
        "note": "No generative fill is used. Regions never visible in any sampled frame cannot be truly recovered.",
        "shots": [asdict(x) for x in reports],
    }
    (out_dir / "diagnostics.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def self_test() -> int:
    rng = np.random.default_rng(7)
    h, w = 360, 640
    base = np.zeros((h, w, 3), np.uint8)
    xg = np.linspace(0, 255, w, dtype=np.uint8)
    yg = np.linspace(0, 255, h, dtype=np.uint8)[:, None]
    base[..., 0] = xg[None, :]
    base[..., 1] = yg
    base[..., 2] = ((xg[None, :].astype(np.uint16) + yg.astype(np.uint16)) // 2).astype(np.uint8)
    for x in range(30, w, 70):
        cv2.line(base, (x, 0), (x, h - 1), (230, 230, 230), 1)
    for y in range(25, h, 55):
        cv2.line(base, (0, y), (w - 1, y), (20, 20, 20), 1)
    cv2.putText(base, "BACKGROUND TEST", (125, 185), cv2.FONT_HERSHEY_SIMPLEX, 1.15, (250, 240, 30), 3, cv2.LINE_AA)

    frames = []
    for i in range(36):
        dx = int(round(3.0 * math.sin(i * 0.33)))
        dy = int(round(2.0 * math.cos(i * 0.29)))
        mat = np.float32([[1, 0, dx], [0, 1, dy]])
        f = cv2.warpAffine(base, mat, (w, h), borderMode=cv2.BORDER_REFLECT)
        cx = 40 + (i * 17) % (w - 80)
        cy = 110 + int(60 * math.sin(i * 0.45))
        cv2.circle(f, (cx, cy), 54, (5, 25, 245), -1, cv2.LINE_AA)
        cv2.rectangle(f, (max(0, cx - 35), 245), (min(w - 1, cx + 70), 335), (20, 245, 30), -1)
        noise = rng.normal(0, 1.2, f.shape).astype(np.float32)
        f = np.clip(f.astype(np.float32) + noise, 0, 255).astype(np.uint8)
        frames.append(f)

    bg, conf, consensus, failures = reconstruct(frames)
    crop = (slice(12, -12), slice(12, -12))
    mae = float(np.mean(np.abs(bg[crop].astype(np.int16) - base[crop].astype(np.int16))))
    conf_mean = float(np.mean(conf[crop]))
    print(json.dumps({"mae": mae, "confidence_mean": conf_mean, "consensus": consensus, "alignment_failures": failures}, indent=2))
    if mae > 18.0 or consensus < 0.45:
        raise SystemExit("SELF-TEST FAILED")
    print("SELF-TEST OK")
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Recover source-observed video backgrounds from multiple frames.")
    p.add_argument("video", nargs="?", help="Input video file")
    p.add_argument("-o", "--output-dir", default="background-output")
    p.add_argument("--sample-interval", type=float, default=0.25)
    p.add_argument("--max-samples", type=int, default=240)
    p.add_argument("--max-frames-per-shot", type=int, default=32)
    p.add_argument("--max-shots", type=int, default=12)
    p.add_argument("--self-test", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.self_test:
        return self_test()
    if not args.video:
        raise SystemExit("video path is required")
    report = extract_video(
        Path(args.video).resolve(), Path(args.output_dir).resolve(),
        max(0.05, args.sample_interval), max(8, args.max_samples),
        max(4, args.max_frames_per_shot), max(1, args.max_shots),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
