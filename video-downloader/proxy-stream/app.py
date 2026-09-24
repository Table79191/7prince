from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests
import yt_dlp
from flask import Flask, Response, jsonify, request, send_from_directory, stream_with_context

app = Flask(__name__, static_folder=None)
ROOT = Path(__file__).resolve().parent
SESSION = requests.Session()
CACHE_TTL = 15 * 60
CACHE_LOCK = threading.Lock()


@dataclass
class StreamEntry:
    url: str
    headers: dict[str, str]
    content_type: str
    title: str
    expires_at: float


STREAMS: dict[str, StreamEntry] = {}


def is_youtube_url(raw: str) -> bool:
    try:
        parsed = urlparse(raw)
    except ValueError:
        return False
    host = (parsed.hostname or "").lower().removeprefix("www.")
    return parsed.scheme in {"http", "https"} and (
        host == "youtu.be" or host == "youtube.com" or host.endswith(".youtube.com")
    )


def purge_expired() -> None:
    now = time.time()
    with CACHE_LOCK:
        expired = [token for token, item in STREAMS.items() if item.expires_at <= now]
        for token in expired:
            STREAMS.pop(token, None)


def choose_progressive_format(info: dict) -> dict:
    formats = info.get("formats") or []
    progressive = [
        f for f in formats
        if f.get("url")
        and f.get("vcodec") not in {None, "none"}
        and f.get("acodec") not in {None, "none"}
        and str(f.get("protocol", "")).startswith("http")
    ]
    if not progressive:
        raise RuntimeError("브라우저에서 바로 재생 가능한 영상+음성 통합 스트림을 찾지 못했습니다.")

    def score(fmt: dict):
        ext_score = 1 if fmt.get("ext") == "mp4" else 0
        height = int(fmt.get("height") or 0)
        # Progressive MP4 is typically the most browser-compatible option.
        return (ext_score, height, float(fmt.get("tbr") or 0))

    return max(progressive, key=score)


def extract_stream(raw_url: str) -> tuple[dict, dict]:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "cachedir": False,
    }
    cookiefile = ROOT / "cookies.txt"
    if cookiefile.is_file():
        opts["cookiefile"] = str(cookiefile)

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(raw_url, download=False)

    if info.get("_type") == "playlist":
        entries = [e for e in info.get("entries", []) if e]
        if not entries:
            raise RuntimeError("재생 가능한 항목을 찾지 못했습니다.")
        info = entries[0]

    fmt = choose_progressive_format(info)
    return info, fmt


@app.get("/")
def index():
    return send_from_directory(ROOT, "index.html")


@app.get("/health")
def health():
    return jsonify({"ok": True})


@app.post("/api/resolve")
def resolve():
    purge_expired()
    payload = request.get_json(silent=True) or {}
    raw_url = str(payload.get("url") or "").strip()

    if not is_youtube_url(raw_url):
        return jsonify({"error": "현재는 YouTube URL만 지원합니다."}), 400

    try:
        info, fmt = extract_stream(raw_url)
    except Exception as exc:
        message = str(exc)
        if "Sign in" in message or "age" in message.lower() or "confirm your age" in message.lower():
            message = "이 영상은 YouTube 로그인/연령 확인이 필요한 제한 영상입니다."
        return jsonify({"error": message}), 422

    token = secrets.token_urlsafe(24)
    headers = {
        str(k): str(v)
        for k, v in (fmt.get("http_headers") or info.get("http_headers") or {}).items()
        if k and v
    }
    content_type = fmt.get("mime_type") or (
        "video/mp4" if fmt.get("ext") == "mp4" else "video/webm"
    )

    with CACHE_LOCK:
        STREAMS[token] = StreamEntry(
            url=fmt["url"],
            headers=headers,
            content_type=content_type,
            title=str(info.get("title") or "Video"),
            expires_at=time.time() + CACHE_TTL,
        )

    return jsonify({
        "title": info.get("title"),
        "duration": info.get("duration"),
        "thumbnail": info.get("thumbnail"),
        "format": {
            "height": fmt.get("height"),
            "width": fmt.get("width"),
            "ext": fmt.get("ext"),
            "format_id": fmt.get("format_id"),
        },
        "stream": f"/stream/{token}",
    })


@app.route("/stream/<token>", methods=["GET", "HEAD"])
def stream(token: str):
    purge_expired()
    with CACHE_LOCK:
        entry = STREAMS.get(token)

    if entry is None:
        return jsonify({"error": "스트림 주소가 만료되었습니다. 다시 불러오세요."}), 404

    upstream_headers = dict(entry.headers)
    range_header = request.headers.get("Range")
    if range_header:
        upstream_headers["Range"] = range_header

    try:
        upstream = SESSION.request(
            request.method,
            entry.url,
            headers=upstream_headers,
            stream=True,
            timeout=(10, 30),
            allow_redirects=True,
        )
    except requests.RequestException as exc:
        return jsonify({"error": f"원본 스트림 연결 실패: {exc}"}), 502

    passthrough_headers = {}
    for name in (
        "Content-Type",
        "Content-Length",
        "Content-Range",
        "Accept-Ranges",
        "ETag",
        "Last-Modified",
    ):
        if name in upstream.headers:
            passthrough_headers[name] = upstream.headers[name]

    passthrough_headers.setdefault("Content-Type", entry.content_type)
    passthrough_headers.setdefault("Accept-Ranges", "bytes")
    passthrough_headers["Cache-Control"] = "private, no-store"

    if request.method == "HEAD":
        upstream.close()
        return Response(status=upstream.status_code, headers=passthrough_headers)

    @stream_with_context
    def generate():
        try:
            for chunk in upstream.iter_content(chunk_size=256 * 1024):
                if chunk:
                    yield chunk
        finally:
            upstream.close()

    return Response(
        generate(),
        status=upstream.status_code,
        headers=passthrough_headers,
        direct_passthrough=True,
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8765, threaded=True)
