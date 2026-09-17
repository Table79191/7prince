#!/usr/bin/env python3
"""Persist first-seen collection timestamps for generated corpus rows.

The collector regenerates JSONL deterministically. This post-processor reads the
previously committed version with `git show HEAD:<path>`, reuses each record's
original first-collected timestamp, and stamps only genuinely new records.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "data" / "web_corpus_bot"
KST = timezone(timedelta(hours=9))


def iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def previous_rows(repo_root: Path, path: Path) -> dict[str, dict]:
    try:
        rel = path.resolve().relative_to(repo_root.resolve()).as_posix()
        proc = subprocess.run(
            ["git", "show", f"HEAD:{rel}"],
            cwd=repo_root,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            return {}
        out: dict[str, dict] = {}
        for line in proc.stdout.splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("id"):
                out[row["id"]] = row.get("collection", {})
        return out
    except Exception:
        return {}


def stamp_file(repo_root: Path, path: Path, now: datetime) -> tuple[int, int]:
    old = previous_rows(repo_root, path)
    rows = []
    new_count = 0
    preserved = 0
    utc = iso(now.astimezone(timezone.utc))
    kst = iso(now.astimezone(KST))

    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        prior = old.get(row.get("id", ""), {})
        prior_utc = prior.get("first_collected_at_utc")
        prior_kst = prior.get("first_collected_at_kst")
        if prior_utc and prior_kst:
            row["collection"] = {
                "first_collected_at_utc": prior_utc,
                "first_collected_at_kst": prior_kst,
            }
            preserved += 1
        else:
            row["collection"] = {
                "first_collected_at_utc": utc,
                "first_collected_at_kst": kst,
            }
            new_count += 1
        rows.append(row)

    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    return new_count, preserved


def update_manifest(data_dir: Path) -> None:
    path = data_dir / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    newest_utc = None
    newest_kst = None
    stamped = 0
    for jsonl in sorted(data_dir.glob("*.jsonl")):
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            collection = row.get("collection", {})
            u = collection.get("first_collected_at_utc")
            k = collection.get("first_collected_at_kst")
            if u and k:
                stamped += 1
                if newest_utc is None or u > newest_utc:
                    newest_utc, newest_kst = u, k
    manifest["collection_time"] = {
        "meaning": "first time each record was collected by this repository bot",
        "timezone_fields": ["UTC", "Asia/Seoul (+09:00)"],
        "records_with_timestamp": stamped,
        "latest_first_collected_at_utc": newest_utc,
        "latest_first_collected_at_kst": newest_kst,
    }
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def self_test() -> None:
    now = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)
    assert iso(now.astimezone(KST)) == "2026-09-17T21:00:00+09:00"
    print("collection-time self-test: ok")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=str(DEFAULT_DATA))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return

    data_dir = Path(args.data_dir)
    now = datetime.now(timezone.utc)
    total_new = total_preserved = 0
    for path in sorted(data_dir.glob("*.jsonl")):
        new, preserved = stamp_file(ROOT.parent, path, now)
        total_new += new
        total_preserved += preserved
        print(f"{path.name}: new={new} preserved={preserved}")
    update_manifest(data_dir)
    print(f"timestamps: new={total_new} preserved={total_preserved}")


if __name__ == "__main__":
    main()
