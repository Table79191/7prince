#!/usr/bin/env python3
"""Snapshot corpus state and append robust per-run history records."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

KST = timezone(timedelta(hours=9))


def scan(root: Path) -> dict:
    sources = {}
    total = 0
    for path in sorted(root.glob("*.jsonl")):
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        sources[path.stem] = rows
        total += len(rows)
    return {"sources": sources, "total": total}


def snapshot(root: Path, output: Path) -> None:
    state = scan(root)
    compact = {
        "total": state["total"],
        "sources": {
            key: [str(row.get("id", "")) for row in rows]
            for key, rows in state["sources"].items()
        },
    }
    output.write_text(json.dumps(compact, ensure_ascii=False), encoding="utf-8")
    print(f"snapshot: {compact['total']} records")


def record(root: Path, snapshot_path: Path, status: str, details: str) -> None:
    before = (
        json.loads(snapshot_path.read_text(encoding="utf-8"))
        if snapshot_path.exists()
        else {"total": 0, "sources": {}}
    )
    current = scan(root)
    new_rows = []
    removed = 0
    source_changes = []

    for key, rows in current["sources"].items():
        before_ids = set(before.get("sources", {}).get(key, []))
        current_ids = {str(row.get("id", "")) for row in rows}
        added_ids = current_ids - before_ids
        removed_ids = before_ids - current_ids
        removed += len(removed_ids)
        if added_ids or removed_ids:
            source_changes.append(f"{key}: +{len(added_ids)} / -{len(removed_ids)}")
        for row in rows:
            if str(row.get("id", "")) in added_ids:
                src = row.get("source", {})
                new_rows.append(
                    {
                        "key": key,
                        "id": str(row.get("id", "")),
                        "text": str(row.get("text", "")).replace("\n", " ").strip(),
                        "provenance": src.get("repo")
                        or src.get("raw_file")
                        or src.get("filename")
                        or "unknown-source",
                    }
                )

    now = datetime.now(timezone.utc).replace(microsecond=0)
    kst = now.astimezone(KST)
    before_total = int(before.get("total", 0))
    after_total = int(current["total"])
    history = root / "RUN_HISTORY.txt"
    lines = [
        f"=== {kst.isoformat()} / {now.isoformat()} ===",
        f"status: {status}",
        f"event: {os.environ.get('GITHUB_EVENT_NAME', 'local')}",
        f"run_id: {os.environ.get('GITHUB_RUN_ID', '-')}",
        f"run_attempt: {os.environ.get('GITHUB_RUN_ATTEMPT', '-')}",
        f"head_sha: {os.environ.get('GITHUB_SHA', '-')}",
        f"details: {details or '-'}",
        f"before_total: {before_total}",
        f"after_total: {after_total}",
        f"net_total_change: {after_total - before_total:+d}",
        f"new_items_added: {len(new_rows)}",
        f"items_removed: {removed}",
        "source_changes: " + (", ".join(source_changes) if source_changes else "none"),
        "new_items_sample:",
    ]
    if new_rows:
        for item in new_rows[:30]:
            lines.append(
                f"- [{item['key']}] {item['id']} | "
                f"{item['text'][:220]} | {item['provenance']}"
            )
        if len(new_rows) > 30:
            lines.append(f"- ... {len(new_rows) - 30} more new items")
    else:
        lines.append("- none")
    lines.append("")

    previous = (
        history.read_text(encoding="utf-8")
        if history.exists()
        else "# SentenceLab corpus run history\n\n"
    )
    history.write_text(previous + "\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"history: status={status} before={before_total} after={after_total} "
        f"added={len(new_rows)} removed={removed}"
    )


def self_test() -> None:
    assert KST.utcoffset(None).total_seconds() == 9 * 3600
    print("corpus-run-history self-test: ok")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="english-sentence-lab/data/web_corpus_bot")
    ap.add_argument("--snapshot-file", default="/tmp/sentence_lab_before.json")
    ap.add_argument("--self-test", action="store_true")
    sub = ap.add_subparsers(dest="command")
    sub.add_parser("snapshot")
    rec = sub.add_parser("record")
    rec.add_argument("--status", required=True, choices=["success", "failure"])
    rec.add_argument("--details", default="")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return
    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    snap = Path(args.snapshot_file)
    if args.command == "snapshot":
        snapshot(root, snap)
    elif args.command == "record":
        record(root, snap, args.status, args.details)
    else:
        ap.error("command required: snapshot or record")


if __name__ == "__main__":
    main()
