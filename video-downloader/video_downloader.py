#!/usr/bin/env python3
"""One-click video downloader for media you own or are authorized to download."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg


def default_output_dir() -> Path:
    downloads = Path.home() / "Downloads"
    return downloads if downloads.exists() else Path.cwd() / "downloads"


def find_cookies(explicit: str | None) -> Path | None:
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"cookies.txt not found: {path}")
        return path

    local = Path(__file__).resolve().with_name("cookies.txt")
    return local if local.is_file() else None


def build_command(url: str, output_dir: Path, cookies: Path | None, playlist: bool) -> list[str]:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--newline",
        "--ffmpeg-location",
        ffmpeg,
        "--merge-output-format",
        "mp4",
        "--remux-video",
        "mp4",
        "--windows-filenames",
        "-f",
        "bv*+ba/b",
        "-o",
        str(output_dir / "%(title).180B [%(id)s].%(ext)s"),
    ]

    if not playlist:
        cmd.append("--no-playlist")

    # Newer YouTube extraction is more reliable when Node is available.
    if shutil.which("node"):
        cmd.extend(["--js-runtimes", "node", "--remote-components", "ejs:github"])

    if cookies is not None:
        cmd.extend(["--cookies", str(cookies)])

    cmd.append(url)
    return cmd


def self_test() -> int:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    print(f"Python: {sys.version.split()[0]}")
    print(f"ffmpeg: {ffmpeg}")
    print(f"Node: {shutil.which('node') or 'not found (optional)'}")
    subprocess.run([sys.executable, "-m", "yt_dlp", "--version"], check=True)
    subprocess.run([ffmpeg, "-version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("SELF-TEST OK")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download an authorized video URL as MP4."
    )
    parser.add_argument("url", nargs="?", help="Video URL. If omitted, you will be prompted.")
    parser.add_argument(
        "-o",
        "--output-dir",
        default=str(default_output_dir()),
        help="Destination folder (default: your Downloads folder)",
    )
    parser.add_argument("--cookies", help="Path to Netscape-format cookies.txt")
    parser.add_argument("--playlist", action="store_true", help="Allow playlist downloads")
    parser.add_argument("--self-test", action="store_true", help="Check local dependencies and exit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.self_test:
        return self_test()

    url = (args.url or input("Video URL: ")).strip()
    if not url:
        print("ERROR: URL is empty.", file=sys.stderr)
        return 2

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        cookies = find_cookies(args.cookies)
        cmd = build_command(url, output_dir, cookies, args.playlist)
        print(f"Saving to: {output_dir}")
        if cookies:
            print(f"Using cookies: {cookies}")
        subprocess.run(cmd, check=True)
        print("\nDONE")
        return 0
    except (FileNotFoundError, subprocess.CalledProcessError, OSError) as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        print(
            "If YouTube asks you to sign in, export a Netscape-format cookies.txt "
            "next to this script and run again.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
