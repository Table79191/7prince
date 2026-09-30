#!/usr/bin/env python3
"""Download a public YouTube video's video-only stream through public Piped/Invidious APIs.

This is used as a fallback when YouTube blocks datacenter IPs used by CI runners.
Only the video stream is needed for multi-frame background recovery.
"""
from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


PIPED_INSTANCES = [
    "https://pipedapi.kavin.rocks",
    "https://pipedapi.leptons.xyz",
    "https://pipedapi.nosebs.ru",
    "https://pipedapi-libre.kavin.rocks",
    "https://piped-api.privacy.com.de",
    "https://pipedapi.adminforge.de",
    "https://api.piped.yt",
    "https://pipedapi.drgns.space",
    "https://pipedapi.owo.si",
    "https://pipedapi.ducks.party",
    "https://piped-api.codespace.cz",
    "https://pipedapi.reallyaweso.me",
    "https://api.piped.private.coffee",
    "https://pipedapi.darkness.services",
    "https://pipedapi.orangenet.cc",
]

INVIDIOUS_INSTANCES = [
    "https://inv.nadeko.net",
    "https://invidious.nerdvpn.de",
    "https://yt.chocolatemoo53.com",
    "https://invidious.tiekoetter.com",
]

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/154 Safari/537.36"


def video_id_from_url(url: str) -> str:
    p = urllib.parse.urlparse(url)
    if p.hostname in {"youtu.be", "www.youtu.be"}:
        vid = p.path.strip("/").split("/")[0]
    else:
        vid = urllib.parse.parse_qs(p.query).get("v", [""])[0]
        if not vid and "/shorts/" in p.path:
            vid = p.path.split("/shorts/", 1)[1].split("/", 1)[0]
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", vid or ""):
        raise ValueError(f"Could not parse YouTube video id from: {url}")
    return vid


def get_json(url: str, timeout: float = 18.0) -> dict:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": UA, "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as r:
        raw = r.read()
    return json.loads(raw.decode("utf-8"))


def quality_score(item: dict) -> tuple[int, int, int]:
    text = " ".join(
        str(item.get(k, "")) for k in ("quality", "qualityLabel", "format", "mimeType", "type")
    )
    nums = [int(x) for x in re.findall(r"(?<!\d)(\d{3,4})p?", text)]
    height = max([x for x in nums if x <= 4320], default=0)
    if height > 1080:
        height = 1080 - (height - 1080)
    mp4 = 1 if ("mp4" in text.lower() or "mpeg_4" in text.lower()) else 0
    bitrate = int(item.get("bitrate") or 0)
    return height, mp4, bitrate


def pick_piped_stream(data: dict) -> str | None:
    streams = data.get("videoStreams") or []
    candidates = [s for s in streams if isinstance(s, dict) and s.get("url")]
    if not candidates:
        return None
    candidates.sort(key=quality_score, reverse=True)
    return str(candidates[0]["url"])


def pick_invidious_stream(data: dict) -> str | None:
    streams = []
    streams.extend(data.get("formatStreams") or [])
    streams.extend(data.get("adaptiveFormats") or [])
    candidates = []
    for s in streams:
        if not isinstance(s, dict) or not s.get("url"):
            continue
        kind = str(s.get("type") or s.get("mimeType") or "").lower()
        if kind and "video" not in kind:
            continue
        candidates.append(s)
    if not candidates:
        return None
    candidates.sort(key=quality_score, reverse=True)
    return str(candidates[0]["url"])


def download(url: str, dest: Path, timeout: float = 30.0) -> int:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "*/*",
            "Referer": "https://www.youtube.com/",
        },
    )
    total = 0
    with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as r, dest.open("wb") as f:
        while True:
            chunk = r.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
            total += len(chunk)
            if total and total % (25 * 1024 * 1024) < len(chunk):
                print(f"downloaded {total / (1024*1024):.1f} MiB", flush=True)
    return total


def try_sources(source_url: str, dest: Path) -> tuple[str, str, int]:
    vid = video_id_from_url(source_url)
    errors: list[str] = []

    for base in PIPED_INSTANCES:
        endpoint = f"{base.rstrip('/')}/streams/{vid}"
        try:
            print(f"Trying Piped: {base}", flush=True)
            data = get_json(endpoint)
            stream = pick_piped_stream(data)
            if not stream:
                raise RuntimeError("no usable videoStreams")
            dest.unlink(missing_ok=True)
            size = download(stream, dest)
            if size < 100_000:
                raise RuntimeError(f"download suspiciously small: {size} bytes")
            return "piped", base, size
        except Exception as exc:
            errors.append(f"Piped {base}: {type(exc).__name__}: {exc}")
            dest.unlink(missing_ok=True)

    for base in INVIDIOUS_INSTANCES:
        endpoint = f"{base.rstrip('/')}/api/v1/videos/{vid}"
        try:
            print(f"Trying Invidious: {base}", flush=True)
            data = get_json(endpoint)
            stream = pick_invidious_stream(data)
            if not stream:
                raise RuntimeError("no usable video format URL")
            dest.unlink(missing_ok=True)
            size = download(stream, dest)
            if size < 100_000:
                raise RuntimeError(f"download suspiciously small: {size} bytes")
            return "invidious", base, size
        except Exception as exc:
            errors.append(f"Invidious {base}: {type(exc).__name__}: {exc}")
            dest.unlink(missing_ok=True)

    print("\n".join(errors), file=sys.stderr)
    raise RuntimeError("All Piped/Invidious fallback instances failed")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("url")
    p.add_argument("-o", "--output", required=True)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    source_type, instance, size = try_sources(args.url, out)
    print(json.dumps({
        "source_type": source_type,
        "instance": instance,
        "output": str(out),
        "bytes": size,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
