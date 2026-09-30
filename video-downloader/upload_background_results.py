#!/usr/bin/env python3
"""Upload recovered background outputs to the current GitHub repository branch."""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def request_json(url: str, *, token: str, data: dict | None = None, method: str = "GET") -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "video-background-extractor",
    }
    body = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def remote_sha(api: str, *, token: str, branch: str) -> str | None:
    try:
        result = request_json(
            api + "?ref=" + urllib.parse.quote(branch, safe=""),
            token=token,
        )
        return result.get("sha")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def main() -> int:
    token = os.environ["GH_TOKEN"]
    repo = os.environ["REPO"]
    branch = os.environ["BRANCH"]
    video_id = os.environ["VIDEO_ID"]
    root = Path("video-downloader/background-results") / video_id

    files = [root / "best_background.png", root / "diagnostics.json"]
    files.extend(sorted(root.glob("background_*.png")))

    uploaded = 0
    for path in files:
        if not path.is_file():
            continue

        repo_path = path.as_posix()
        api = (
            f"https://api.github.com/repos/{repo}/contents/"
            + urllib.parse.quote(repo_path, safe="/")
        )
        sha = remote_sha(api, token=token, branch=branch)

        payload: dict[str, str] = {
            "message": f"artifacts: update extracted background {path.name} [skip ci]",
            "content": base64.b64encode(path.read_bytes()).decode("ascii"),
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha

        result = request_json(api, token=token, data=payload, method="PUT")
        print(f"{repo_path}: {result['commit']['sha']}")
        uploaded += 1

    if uploaded == 0:
        raise SystemExit("No recovered background files found to upload")
    print(f"Uploaded {uploaded} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
