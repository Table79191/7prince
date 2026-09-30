#!/usr/bin/env python3
"""One-click video downloader for media you own or are authorized to download."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import imageio_ffmpeg


BROWSER_CHOICES = ("auto", "none", "edge", "chrome", "brave", "firefox")


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


def is_youtube_url(raw: str) -> bool:
    try:
        parsed = urlparse(raw)
    except ValueError:
        return False
    host = (parsed.hostname or "").lower().removeprefix("www.")
    return parsed.scheme in {"http", "https"} and (
        host == "youtu.be" or host == "youtube.com" or host.endswith(".youtube.com")
    )


def browser_candidates(mode: str) -> list[str]:
    if mode == "none":
        return []
    if mode != "auto":
        return [mode]

    if sys.platform.startswith("win"):
        return ["edge", "chrome", "brave", "firefox"]
    if sys.platform == "darwin":
        return ["chrome", "brave", "firefox"]
    return ["chrome", "brave", "firefox", "edge"]


def build_command(
    url: str,
    output_dir: Path,
    cookies: Path | None,
    playlist: bool,
    browser_cookies: str | None = None,
    youtube_client: str | None = None,
) -> list[str]:
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
        "--retries",
        "5",
        "--fragment-retries",
        "5",
        "-f",
        "bv*+ba/b",
        "-o",
        str(output_dir / "%(title).180B [%(id)s].%(ext)s"),
    ]

    if not playlist:
        cmd.append("--no-playlist")

    # Current YouTube extraction is more reliable when a JS runtime is available.
    if shutil.which("node"):
        cmd.extend(["--js-runtimes", "node", "--remote-components", "ejs:github"])

    if cookies is not None:
        cmd.extend(["--cookies", str(cookies)])
    elif browser_cookies:
        cmd.extend(["--cookies-from-browser", browser_cookies])

    if youtube_client:
        cmd.extend(["--extractor-args", f"youtube:player_client={youtube_client}"])

    cmd.append(url)
    return cmd


def run_attempt(
    label: str,
    *,
    url: str,
    output_dir: Path,
    cookies: Path | None,
    playlist: bool,
    browser_cookies: str | None = None,
    youtube_client: str | None = None,
) -> bool:
    print(f"\n=== {label} ===", flush=True)
    cmd = build_command(
        url,
        output_dir,
        cookies,
        playlist,
        browser_cookies=browser_cookies,
        youtube_client=youtube_client,
    )
    completed = subprocess.run(cmd, check=False)
    if completed.returncode == 0:
        print(f"SUCCESS: {label}", flush=True)
        return True

    print(f"FAILED ({completed.returncode}): {label}", file=sys.stderr, flush=True)
    return False


def self_test() -> int:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    print(f"Python: {sys.version.split()[0]}")
    print(f"ffmpeg: {ffmpeg}")
    print(f"Node: {shutil.which('node') or 'not found (optional)'}")
    subprocess.run([sys.executable, "-m", "yt_dlp", "--version"], check=True)
    subprocess.run([ffmpeg, "-version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    probe = build_command(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        Path.cwd(),
        None,
        False,
        browser_cookies="edge",
        youtube_client="web_safari",
    )
    assert "--cookies-from-browser" in probe
    assert "edge" in probe
    assert "--extractor-args" in probe
    assert "youtube:player_client=web_safari" in probe
    assert "--no-playlist" in probe
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
    parser.add_argument(
        "--browser-cookies",
        choices=BROWSER_CHOICES,
        default="auto",
        help=(
            "On YouTube failure, retry with cookies from a local browser. "
            "Default: auto (Edge/Chrome/Brave/Firefox). Use 'none' to disable."
        ),
    )
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
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Saving to: {output_dir}")
    if cookies:
        print(f"Using cookies file first: {cookies}")

    # First attempt is intentionally anonymous unless a cookies.txt was supplied.
    if run_attempt(
        "cookies.txt" if cookies else "anonymous",
        url=url,
        output_dir=output_dir,
        cookies=cookies,
        playlist=args.playlist,
    ):
        print("\nDONE")
        return 0

    if not is_youtube_url(url):
        print("\nERROR: download failed.", file=sys.stderr)
        return 1

    candidates = browser_candidates(args.browser_cookies)
    if not candidates:
        print(
            "\nERROR: YouTube rejected the anonymous request. "
            "Browser-cookie retry is disabled.",
            file=sys.stderr,
        )
        return 1

    print(
        "\nYouTube rejected the first request. "
        "Retrying with local browser cookies; nothing is exported or committed.",
        flush=True,
    )

    # Retry with browser cookies. This is the most reliable local fallback for
    # YouTube's 'Sign in to confirm you're not a bot' response.
    for browser in candidates:
        if run_attempt(
            f"{browser} cookies",
            url=url,
            output_dir=output_dir,
            cookies=None,
            playlist=args.playlist,
            browser_cookies=browser,
        ):
            print("\nDONE")
            return 0

    # Some 2026 YouTube rollouts behave better through the web_safari client,
    # whose HLS path may avoid GVS PO-token requirements for some formats.
    for browser in candidates:
        if run_attempt(
            f"{browser} cookies + web_safari client",
            url=url,
            output_dir=output_dir,
            cookies=None,
            playlist=args.playlist,
            browser_cookies=browser,
            youtube_client="web_safari",
        ):
            print("\nDONE")
            return 0

    print(
        "\nERROR: All download attempts failed. "
        "Close the browser and retry, or export a fresh Netscape cookies.txt "
        "and pass it with --cookies.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
