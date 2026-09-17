#!/usr/bin/env python3
"""SentenceLab incremental corpus collector v2.

This wrapper reuses the proven UD parsing/canonical-role logic from
auto_web_corpus_bot.py, but fixes the operational problems in v1:
- authenticated GitHub API discovery via GITHUB_TOKEN/GH_TOKEN
- append-only collection of unseen sentences
- bounded new additions per source/run
- stable provenance and manifest/report totals
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import auto_web_corpus_bot as legacy

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data" / "web_corpus_bot"
USER_AGENT = "SentenceLab-AutoWebCorpusBot/2.0 (+https://github.com/Table79191/7prince)"


def headers_for(url: str) -> dict[str, str]:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/vnd.github+json",
    }
    if urllib.parse.urlparse(url).hostname == "api.github.com":
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
            headers["X-GitHub-Api-Version"] = "2022-11-28"
    return headers


def authenticated_fetch_bytes(url: str, retries: int = 5) -> bytes:
    last: Exception | None = None
    for attempt in range(retries):
        request = urllib.request.Request(url, headers=headers_for(url))
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            last = exc
            retryable = exc.code in {403, 408, 429, 500, 502, 503, 504}
            if not retryable or attempt + 1 >= retries:
                remaining = exc.headers.get("X-RateLimit-Remaining", "?")
                reset = exc.headers.get("X-RateLimit-Reset", "?")
                raise RuntimeError(
                    f"HTTP {exc.code} fetching {url}; "
                    f"rate_remaining={remaining} rate_reset={reset}"
                ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
            if attempt + 1 >= retries:
                break
        time.sleep(min(30, 2 ** attempt))
    raise RuntimeError(f"failed to fetch {url}: {last}")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def merge_incremental(
    existing: list[dict],
    upstream: list[dict],
    max_new: int,
    max_total: int,
) -> tuple[list[dict], list[dict], int]:
    existing_ids = {str(row.get("id", "")) for row in existing}
    existing_texts = {
        legacy.normalized_text(str(row.get("text", ""))) for row in existing
    }
    unseen = [
        row
        for row in upstream
        if str(row.get("id", "")) not in existing_ids
        and legacy.normalized_text(str(row.get("text", ""))) not in existing_texts
    ]

    take = len(unseen)
    if max_total > 0:
        take = max(0, min(take, max_total - len(existing)))
    if max_new > 0:
        take = min(take, max_new)

    added = unseen[:take]
    merged = existing + added
    legacy.validate_output(merged)
    return merged, added, max(0, len(unseen) - len(added))


def source_stats(
    key: str,
    source: dict,
    upstream_stats: dict,
    merged: list[dict],
    added: list[dict],
    remaining: int,
) -> dict:
    return {
        "source": key,
        "repo": source["repo"],
        "license": source["license"],
        "discovered_files": upstream_stats["discovered_files"],
        "raw_files": upstream_stats["raw_files"],
        "sentences_after_dedupe_upstream": upstream_stats["sentences_after_dedupe"],
        "sentences_written": len(merged),
        "new_items_added": len(added),
        "remaining_unseen": remaining,
        "auto_pass": sum(
            row["analysis"]["status"] == "auto_pass" for row in merged
        ),
        "needs_review": sum(
            row["analysis"]["status"] == "needs_review" for row in merged
        ),
    }


def recompute_totals(out: Path, manifest: dict) -> None:
    totals = {
        "sentences_written": 0,
        "auto_pass": 0,
        "needs_review": 0,
        "new_items_added_this_run": 0,
    }
    for key in legacy.SOURCES:
        rows = read_jsonl(out / f"{key}.jsonl")
        if not rows:
            continue
        legacy.validate_output(rows)
        totals["sentences_written"] += len(rows)
        totals["auto_pass"] += sum(
            row["analysis"]["status"] == "auto_pass" for row in rows
        )
        totals["needs_review"] += sum(
            row["analysis"]["status"] == "needs_review" for row in rows
        )
        totals["new_items_added_this_run"] += int(
            manifest.get("sources", {}).get(key, {}).get("new_items_added", 0)
        )
    manifest["totals"] = totals


def build_report(manifest: dict) -> str:
    lines = [
        "# Auto Web Corpus Bot report",
        "",
        f"Upstream snapshot: `{manifest['upstream_snapshot_sha256']}`",
        "",
        "Incremental allowlisted Universal Dependencies English corpus.",
        "Existing records are retained; only unseen sentences are appended.",
        "",
        "| Source | License | Stored | Added this run | Remaining unseen | Auto-pass | Needs review |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for key, stats in sorted(manifest["sources"].items()):
        lines.append(
            f"| {key} | {stats.get('license', '')} | "
            f"{stats.get('sentences_written', 0)} | "
            f"{stats.get('new_items_added', 0)} | "
            f"{stats.get('remaining_unseen', '?')} | "
            f"{stats.get('auto_pass', 0)} | "
            f"{stats.get('needs_review', 0)} |"
        )
    lines += [
        "",
        f"**Total analyzed sentences:** {manifest['totals']['sentences_written']}",
        f"**New items added this run:** {manifest['totals']['new_items_added_this_run']}",
        "",
        "Every record retains its original UD provenance/license and canonical role analysis.",
        "",
    ]
    return "\n".join(lines)


def self_test() -> None:
    demo = {
        "id": "a",
        "text": "Hello world",
        "analysis": {"status": "auto_pass", "tokens": [{"role": "S", "deprel": "root", "head": 0}]},
    }
    merged, added, remaining = merge_incremental([], [demo], 10, 100)
    assert len(merged) == 1 and len(added) == 1 and remaining == 0
    merged2, added2, remaining2 = merge_incremental(merged, [demo], 10, 100)
    assert len(merged2) == 1 and not added2 and remaining2 == 0
    assert "Authorization" not in headers_for("https://raw.githubusercontent.com/x/y")
    print("collector-v2 self-test: ok")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT))
    ap.add_argument("--max-new-per-source", type=int, default=250)
    ap.add_argument("--max-total-per-source", type=int, default=10000)
    ap.add_argument("--source", action="append", choices=sorted(legacy.SOURCES))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return
    if args.max_new_per_source < 0 or args.max_total_per_source < 0:
        raise SystemExit("collection limits must be >= 0")

    legacy.fetch_bytes = authenticated_fetch_bytes

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        manifest = {}

    manifest["version"] = "AUTO-WEB-CORPUS-2-INCREMENTAL"
    manifest["policy"] = {
        "source_type": "allowlisted public Universal Dependencies English treebanks",
        "arbitrary_web_scraping": False,
        "append_only": True,
        "max_new_per_source_per_run": args.max_new_per_source,
        "max_total_per_source": args.max_total_per_source,
        "authenticated_github_api": bool(
            os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        ),
        "role_analyzer": "english-sentence-lab/scripts/canonical_roles.py",
    }
    manifest.setdefault("sources", {})

    selected = args.source or list(legacy.SOURCES)
    for key in selected:
        source = legacy.SOURCES[key]
        existing = read_jsonl(out / f"{key}.jsonl")
        legacy.validate_output(existing)

        upstream, upstream_stats = legacy.collect_source(key, source, 0)
        merged, added, remaining = merge_incremental(
            existing,
            upstream,
            args.max_new_per_source,
            args.max_total_per_source,
        )
        legacy.write_jsonl(out / f"{key}.jsonl", merged)
        manifest["sources"][key] = source_stats(
            key, source, upstream_stats, merged, added, remaining
        )
        print(
            f"{key:14s}: stored={len(merged):5d} "
            f"added={len(added):4d} remaining={remaining:5d}"
        )

    recompute_totals(out, manifest)

    snapshot_parts = []
    for key, stats in sorted(manifest["sources"].items()):
        for raw in stats.get("raw_files", []):
            snapshot_parts.append(
                f"{key}:{raw.get('filename', '')}:{raw.get('sha256', '')}"
            )
    manifest["upstream_snapshot_sha256"] = hashlib.sha256(
        "\n".join(snapshot_parts).encode("utf-8")
    ).hexdigest()

    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out / "REPORT.md").write_text(build_report(manifest), encoding="utf-8")
    print(json.dumps(manifest["totals"], ensure_ascii=False))


if __name__ == "__main__":
    main()
