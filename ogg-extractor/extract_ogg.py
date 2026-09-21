#!/usr/bin/env python3
"""Extract/convert audio to OGG Vorbis from a local media file or an authorized URL."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


def require_binary(name: str) -> None:
    if shutil.which(name) is None:
        raise RuntimeError(f"Required executable not found: {name}")


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def convert_local(source: Path, output: Path, quality: int) -> Path:
    if not source.is_file():
        raise FileNotFoundError(f"Input file does not exist: {source}")
    require_binary("ffmpeg")
    output.parent.mkdir(parents=True, exist_ok=True)
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(source), "-vn", "-c:a", "libvorbis", "-q:a", str(quality),
        str(output),
    ])
    return output


def extract_url(source_url: str, output: Path) -> Path:
    require_binary("yt-dlp")
    require_binary("ffmpeg")
    output.parent.mkdir(parents=True, exist_ok=True)
    template = str(output.with_suffix("")) + ".%(ext)s"
    run([
        "yt-dlp", "--no-playlist", "-x", "--audio-format", "vorbis",
        "--audio-quality", "0", "-o", template, source_url,
    ])
    expected = output.with_suffix(".ogg")
    if expected.is_file():
        return expected
    candidates = sorted(output.parent.glob(output.with_suffix("").name + ".*"))
    if not candidates:
        raise RuntimeError("yt-dlp completed but no output file was found")
    if candidates[0].suffix.lower() != ".ogg":
        return convert_local(candidates[0], output, quality=7)
    return candidates[0]


def validate_ogg(path: Path) -> None:
    require_binary("ffprobe")
    probe = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "a:0",
            "-show_entries", "stream=codec_name", "-of", "default=nw=1:nk=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    codec = probe.stdout.strip()
    if codec != "vorbis":
        raise RuntimeError(f"Unexpected output codec: {codec or 'none'}")
    print(f"OK: {path} (codec=vorbis, bytes={path.stat().st_size})")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract/convert audio to OGG Vorbis. Use only with media you own or are authorized to process."
    )
    parser.add_argument("source", help="Local media path or authorized http(s) URL")
    parser.add_argument("--output", "-o", default="output.ogg", help="Output .ogg path")
    parser.add_argument(
        "--quality", type=int, default=7, choices=range(0, 11), metavar="0-10",
        help="Vorbis quality for local-file conversion (default: 7)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = Path(args.output).expanduser().resolve()
    if output.suffix.lower() != ".ogg":
        output = output.with_suffix(".ogg")

    try:
        if is_url(args.source):
            result = extract_url(args.source, output)
        else:
            result = convert_local(Path(args.source).expanduser().resolve(), output, args.quality)
        validate_ogg(result)
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
