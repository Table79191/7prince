#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "eval"
MANIFEST = EVAL / "chaos50_tracks.json"


def decode_b64_json(path: Path):
    text = path.read_text(encoding="ascii")
    raw = gzip.decompress(base64.b64decode(text.strip()))
    return json.loads(raw.decode("utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def score_baseline(sentences, gold):
    gold_by_id = {row["id"]: row for row in gold}
    total = pos_ok = role_ok = both_ok = exact = 0
    for sent in sentences:
        row = gold_by_id[sent["id"]]
        sent_exact = True
        for idx, word, exp_pos, exp_role in row["f"]:
            tok = sent["tokens"][idx]
            if tok["text"].lower() != word.lower():
                raise RuntimeError(
                    f"indexed gold mismatch sentence={sent['id']} idx={idx}: "
                    f"{tok['text']!r} != {word!r}"
                )
            p = tok["pos"] == exp_pos
            r = tok["role"] == exp_role
            total += 1
            pos_ok += int(p)
            role_ok += int(r)
            both_ok += int(p and r)
            sent_exact = sent_exact and p and r
        exact += int(sent_exact)
    return {
        "focus_checks": total,
        "pos_correct": pos_ok,
        "role_correct": role_ok,
        "both_correct": both_ok,
        "exact_sentences": exact,
        "pos_accuracy": pos_ok / total,
        "role_accuracy": role_ok / total,
        "both_accuracy": both_ok / total,
        "exact_sentence_accuracy": exact / len(sentences),
    }


def main():
    ap = argparse.ArgumentParser(
        description="Verify one explicitly named sealed Chaos50 evaluation track."
    )
    ap.add_argument(
        "--track",
        required=True,
        choices=["historical-v153", "production-v155"],
        help="Track name is mandatory so historical and production scores cannot be mixed.",
    )
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    track = manifest["tracks"][args.track]
    gold_meta = manifest["gold"]
    input_path = EVAL / track["input_path"]
    gold_path = EVAL / gold_meta["path"]

    for path, expected in [
        (input_path, track["sha256_encoded_file"]),
        (gold_path, gold_meta["sha256_encoded_file"]),
    ]:
        actual = sha256_file(path)
        if actual != expected:
            raise RuntimeError(f"asset hash mismatch for {path.name}: {actual} != {expected}")

    data = decode_b64_json(input_path)
    gold = decode_b64_json(gold_path)
    sentences = data["sentences"]
    if len(sentences) != gold_meta["sentences"] or len(gold) != gold_meta["sentences"]:
        raise RuntimeError("Chaos50 sentence cardinality mismatch")

    result = score_baseline(sentences, gold)
    if result["focus_checks"] != gold_meta["focus_checks"]:
        raise RuntimeError("Chaos50 focus-check cardinality mismatch")

    for key, expected in track["expected_baseline"].items():
        if result[key] != expected:
            raise RuntimeError(
                f"{args.track} baseline mismatch {key}: {result[key]} != {expected}"
            )

    payload = {
        "track": args.track,
        "sealed_holdout": manifest["sealed_holdout"],
        "input_path": track["input_path"],
        "gold_path": gold_meta["path"],
        "selection_policy": manifest["selection_policy"],
        "baseline": result,
        "integrity": "PASS",
    }
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    print(text, end="")
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
