from __future__ import annotations

import app as target


class FakeUpstream:
    def __init__(self, status_code=206):
        self.status_code = status_code
        self.headers = {
            "Content-Type": "video/mp4",
            "Content-Length": "4",
            "Content-Range": "bytes 0-3/10",
            "Accept-Ranges": "bytes",
        }
        self.closed = False

    def iter_content(self, chunk_size=262144):
        yield b"TEST"

    def close(self):
        self.closed = True


def test_health():
    client = target.app.test_client()
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json() == {"ok": True}


def test_rejects_non_youtube_url():
    client = target.app.test_client()
    res = client.post("/api/resolve", json={"url": "http://127.0.0.1:9000/private"})
    assert res.status_code == 400


def test_resolve_returns_stream_token(monkeypatch):
    info = {
        "title": "Example video",
        "duration": 12,
        "thumbnail": "https://example.invalid/thumb.jpg",
        "http_headers": {"User-Agent": "test-agent"},
    }
    fmt = {
        "url": "https://media.example.invalid/video.mp4",
        "http_headers": {"User-Agent": "test-agent"},
        "ext": "mp4",
        "height": 360,
        "width": 640,
        "format_id": "18",
        "mime_type": "video/mp4",
        "vcodec": "avc1",
        "acodec": "mp4a",
        "protocol": "https",
    }

    monkeypatch.setattr(target, "extract_stream", lambda raw: (info, fmt))

    client = target.app.test_client()
    res = client.post("/api/resolve", json={"url": "https://youtu.be/example123"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["title"] == "Example video"
    assert data["format"]["height"] == 360
    assert data["stream"].startswith("/stream/")


def test_range_is_forwarded_and_partial_content_returned(monkeypatch):
    token = "range-test"
    target.STREAMS[token] = target.StreamEntry(
        url="https://media.example.invalid/video.mp4",
        headers={"User-Agent": "test-agent"},
        content_type="video/mp4",
        title="Example",
        expires_at=target.time.time() + 60,
    )

    seen = {}

    def fake_request(method, url, headers, stream, timeout, allow_redirects):
        seen["method"] = method
        seen["url"] = url
        seen["headers"] = dict(headers)
        return FakeUpstream()

    monkeypatch.setattr(target.SESSION, "request", fake_request)

    client = target.app.test_client()
    res = client.get(f"/stream/{token}", headers={"Range": "bytes=0-3"})

    assert res.status_code == 206
    assert res.data == b"TEST"
    assert res.headers["Content-Range"] == "bytes 0-3/10"
    assert res.headers["Accept-Ranges"] == "bytes"
    assert seen["headers"]["Range"] == "bytes=0-3"


def test_choose_progressive_prefers_mp4_and_higher_resolution():
    info = {
        "formats": [
            {
                "url": "https://example.invalid/360.webm",
                "vcodec": "vp9",
                "acodec": "opus",
                "protocol": "https",
                "ext": "webm",
                "height": 360,
                "tbr": 500,
            },
            {
                "url": "https://example.invalid/360.mp4",
                "vcodec": "avc1",
                "acodec": "mp4a",
                "protocol": "https",
                "ext": "mp4",
                "height": 360,
                "tbr": 600,
            },
            {
                "url": "https://example.invalid/720.mp4",
                "vcodec": "avc1",
                "acodec": "mp4a",
                "protocol": "https",
                "ext": "mp4",
                "height": 720,
                "tbr": 1200,
            },
        ]
    }
    chosen = target.choose_progressive_format(info)
    assert chosen["url"].endswith("720.mp4")
