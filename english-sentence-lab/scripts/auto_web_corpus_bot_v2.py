#!/usr/bin/env python3
"""SentenceLab incremental corpus collector v2.

Operational guarantees:
- authenticated GitHub API discovery via GITHUB_TOKEN/GH_TOKEN
- append-only collection of unseen sentences
- no per-source storage ceiling by default
- a global per-run collection budget that is redistributed when a source is exhausted
- lightweight HEAD checks for exhausted sources
- stable provenance, hashes, manifest, and report totals
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
USER_AGENT = "SentenceLab-AutoWebCorpusBot/2.2 (+https://github.com/Table79191/7prince)"
REPO_COMMIT_API = "https://api.github.com/repos/UniversalDependencies/{repo}/commits/master"
REPO_SEARCH_API = (
    "https://api.github.com/search/repositories"
    "?q=org%3AUniversalDependencies+UD_English-&per_page=100&page={page}"
)
DYNAMIC_ALLOWED_LICENSES = {"CC-BY-SA-4.0", "CC-BY-SA-3.0", "CC-BY-4.0"}


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


def fetch_json(url: str):
    return json.loads(authenticated_fetch_bytes(url).decode("utf-8"))


def source_key_from_repo(repo: str) -> str:
    prefix = "UD_English-"
    suffix = repo[len(prefix):] if repo.startswith(prefix) else repo
    return "".join(ch.lower() for ch in suffix if ch.isalnum())


def fetch_license_text(repo: str) -> str:
    last = None
    for name in ("LICENSE.txt", "LICENSE", "LICENSE.md"):
        url = f"https://raw.githubusercontent.com/UniversalDependencies/{repo}/master/{name}"
        try:
            return authenticated_fetch_bytes(url, retries=2).decode("utf-8", errors="replace")
        except Exception as exc:
            last = exc
    raise RuntimeError(f"could not read license for {repo}: {last}")


def classify_license(repo: str, text: str) -> tuple[str, bool, str]:
    low = text.lower()
    if "ldc99t42" in low or "valid license for treebank 3" in low:
        return "RESTRICTED-LDC", False, "requires_external_LDC_text_license"
    if "noncommercial" in low or "by-nc" in low:
        return "CC-BY-NC-SA-4.0", False, "noncommercial_license_excluded"
    if "annotations are licensed" in low and "underlying texts" in low:
        return "CC-BY-4.0-ANNOTATIONS", False, "underlying_text_rights_not_clear"
    if "attribution-sharealike 4.0" in low or "/by-sa/4.0/" in low:
        return "CC-BY-SA-4.0", True, ""
    if "attribution-sharealike 3.0" in low or "/by-sa/3.0/" in low:
        return "CC-BY-SA-3.0", True, ""
    if (
        "attribution 4.0 international" in low
        or "/by/4.0/" in low
        or "cc-by 4.0" in low
    ):
        return "CC-BY-4.0", True, ""
    return "UNKNOWN", False, "license_not_auto_allowlisted"


def discover_english_sources() -> tuple[dict[str, dict], list[dict]]:
    """Discover every current UD_English-* repository with reusable text terms."""
    known_by_repo = {v["repo"]: (k, v) for k, v in legacy.SOURCES.items()}
    accepted: dict[str, dict] = {}
    skipped: list[dict] = []
    page = 1
    seen_repos: set[str] = set()

    while True:
        payload = fetch_json(REPO_SEARCH_API.format(page=page))
        items = payload.get("items", []) if isinstance(payload, dict) else []
        if not items:
            break
        for item in items:
            repo = str(item.get("name", ""))
            if not repo.startswith("UD_English-") or repo in seen_repos:
                continue
            seen_repos.add(repo)
            if item.get("archived"):
                skipped.append({"repo": repo, "reason": "archived"})
                continue

            if repo in known_by_repo:
                key, source = known_by_repo[repo]
                accepted[key] = dict(source)
                continue

            try:
                license_text = fetch_license_text(repo)
                license_name, allowed, reason = classify_license(repo, license_text)
            except Exception as exc:
                skipped.append(
                    {"repo": repo, "reason": "license_probe_failed", "detail": str(exc)}
                )
                continue

            if not allowed or license_name not in DYNAMIC_ALLOWED_LICENSES:
                skipped.append(
                    {"repo": repo, "license": license_name, "reason": reason}
                )
                continue

            try:
                conllu_files = legacy.discover_conllu_files(repo)
            except Exception as exc:
                skipped.append(
                    {
                        "repo": repo,
                        "license": license_name,
                        "reason": "no_released_conllu_files",
                        "detail": str(exc),
                    }
                )
                continue
            if not conllu_files:
                skipped.append(
                    {
                        "repo": repo,
                        "license": license_name,
                        "reason": "no_released_conllu_files",
                    }
                )
                continue

            key = source_key_from_repo(repo)
            accepted[key] = {"repo": repo, "license": license_name}

        if len(items) < 100:
            break
        page += 1
        if page > 10:
            break

    return accepted, skipped


def repo_head_sha(repo: str) -> str:
    payload = fetch_json(REPO_COMMIT_API.format(repo=repo))
    sha = payload.get("sha") if isinstance(payload, dict) else None
    if not sha:
        raise RuntimeError(f"could not resolve upstream HEAD for {repo}")
    return str(sha)


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


def fair_quota(
    remaining_budget: int | None,
    active_sources_left: int,
    per_source_limit: int,
) -> int:
    """Allocate this source a fair share; unused share rolls to later sources."""
    if remaining_budget is None:
        return per_source_limit
    if remaining_budget <= 0:
        return 0
    share = (remaining_budget + max(1, active_sources_left) - 1) // max(
        1, active_sources_left
    )
    if per_source_limit > 0:
        share = min(share, per_source_limit)
    return share


def row_status_counts(rows: list[dict]) -> tuple[int, int]:
    auto_pass = sum(row["analysis"]["status"] == "auto_pass" for row in rows)
    return auto_pass, len(rows) - auto_pass


def should_skip_download(
    existing_count: int,
    previous_stats: dict,
    current_head: str,
    max_total: int,
) -> tuple[bool, str]:
    # max_total=0 means unlimited. The cap remains as an emergency CLI option only.
    if max_total > 0 and existing_count >= max_total:
        return True, "emergency_total_cap_reached"
    previous_head = str(previous_stats.get("upstream_head_sha", ""))
    remaining = previous_stats.get("remaining_unseen")
    if previous_head and previous_head == current_head and remaining == 0:
        return True, "upstream_unchanged_and_exhausted"
    return False, ""


def reused_source_stats(
    key: str,
    source: dict,
    previous: dict,
    existing: list[dict],
    current_head: str,
    reason: str,
) -> dict:
    auto_pass, needs_review = row_status_counts(existing)
    stats = dict(previous)
    stats.update(
        {
            "source": key,
            "repo": source["repo"],
            "license": source["license"],
            "sentences_written": len(existing),
            "new_items_added": 0,
            "auto_pass": auto_pass,
            "needs_review": needs_review,
            "upstream_head_sha": current_head,
            "download_skipped": True,
            "skip_reason": reason,
        }
    )
    return stats


def source_stats(
    key: str,
    source: dict,
    upstream_stats: dict,
    merged: list[dict],
    added: list[dict],
    remaining: int,
    upstream_head: str,
    quota: int,
) -> dict:
    auto_pass, needs_review = row_status_counts(merged)
    return {
        "source": key,
        "repo": source["repo"],
        "license": source["license"],
        "discovered_files": upstream_stats["discovered_files"],
        "raw_files": upstream_stats["raw_files"],
        "sentences_after_dedupe_upstream": upstream_stats["sentences_after_dedupe"],
        "sentences_written": len(merged),
        "new_items_added": len(added),
        "allocated_run_quota": quota,
        "remaining_unseen": remaining,
        "auto_pass": auto_pass,
        "needs_review": needs_review,
        "upstream_head_sha": upstream_head,
        "download_skipped": False,
        "skip_reason": "",
    }


def recompute_totals(out: Path, manifest: dict) -> None:
    totals = {
        "sentences_written": 0,
        "auto_pass": 0,
        "needs_review": 0,
        "new_items_added_this_run": 0,
        "sources_downloaded_this_run": 0,
        "sources_skipped_this_run": 0,
    }
    for key in sorted(manifest.get("sources", {})):
        rows = read_jsonl(out / f"{key}.jsonl")
        if not rows:
            continue
        legacy.validate_output(rows)
        auto_pass, needs_review = row_status_counts(rows)
        totals["sentences_written"] += len(rows)
        totals["auto_pass"] += auto_pass
        totals["needs_review"] += needs_review
        stats = manifest.get("sources", {}).get(key, {})
        totals["new_items_added_this_run"] += int(stats.get("new_items_added", 0))
        if stats.get("download_skipped"):
            totals["sources_skipped_this_run"] += 1
        else:
            totals["sources_downloaded_this_run"] += 1
    manifest["totals"] = totals


def build_report(manifest: dict) -> str:
    lines = [
        "# Auto Web Corpus Bot report",
        "",
        f"Upstream snapshot: `{manifest['upstream_snapshot_sha256']}`",
        "",
        "Incremental allowlisted Universal Dependencies English corpus.",
        "Existing records are retained; only unseen sentences are appended.",
        "Per-source storage is unlimited by default. When a source is exhausted, its unused run budget is redistributed to other active sources.",
        "Exhausted unchanged sources are checked by upstream HEAD and skip large raw downloads.",
        "",
        "| Source | License | Stored | Added | Quota | Remaining | Download | Auto-pass | Review |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for key, stats in sorted(manifest["sources"].items()):
        download = "skipped" if stats.get("download_skipped") else "fetched"
        lines.append(
            f"| {key} | {stats.get('license', '')} | "
            f"{stats.get('sentences_written', 0)} | "
            f"{stats.get('new_items_added', 0)} | "
            f"{stats.get('allocated_run_quota', 0)} | "
            f"{stats.get('remaining_unseen', '?')} | {download} | "
            f"{stats.get('auto_pass', 0)} | {stats.get('needs_review', 0)} |"
        )
    totals = manifest["totals"]
    lines += [
        "",
        f"**Total analyzed sentences:** {totals['sentences_written']}",
        f"**New items added this run:** {totals['new_items_added_this_run']}",
        f"**Raw sources fetched/skipped this run:** {totals['sources_downloaded_this_run']}/{totals['sources_skipped_this_run']}",
        "",
        "Every record retains its original UD provenance/license and canonical role analysis.",
        "",
    ]
    return "\n".join(lines)


def self_test() -> None:
    demo = {
        "id": "a",
        "text": "Hello world",
        "analysis": {
            "status": "auto_pass",
            "tokens": [{"role": "S", "deprel": "root", "head": 0}],
        },
    }
    merged, added, remaining = merge_incremental([], [demo], 10, 0)
    assert len(merged) == 1 and len(added) == 1 and remaining == 0
    merged2, added2, remaining2 = merge_incremental(merged, [demo], 10, 0)
    assert len(merged2) == 1 and not added2 and remaining2 == 0
    assert fair_quota(1000, 3, 0) == 334
    assert fair_quota(666, 2, 0) == 333
    assert fair_quota(333, 1, 0) == 333
    assert "Authorization" not in headers_for("https://raw.githubusercontent.com/x/y")
    skip, reason = should_skip_download(
        50, {"remaining_unseen": 0, "upstream_head_sha": "same"}, "same", 0
    )
    assert skip and reason == "upstream_unchanged_and_exhausted"
    skip, _ = should_skip_download(
        50, {"remaining_unseen": 0, "upstream_head_sha": "old"}, "new", 0
    )
    assert not skip
    print("collector-v2 self-test: ok")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT))
    ap.add_argument(
        "--max-new-per-run",
        type=int,
        default=1000,
        help="global run budget; unused quota is redistributed to other active sources; 0=unlimited",
    )
    ap.add_argument(
        "--max-new-per-source",
        type=int,
        default=0,
        help="optional per-source safety limit; 0=unlimited",
    )
    ap.add_argument(
        "--max-total-per-source",
        type=int,
        default=0,
        help="emergency per-source storage cap; 0=unlimited",
    )
    ap.add_argument(
        "--source",
        action="append",
        help="optional source key; omit to auto-discover all reusable UD_English-* treebanks",
    )
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return
    if (
        args.max_new_per_run < 0
        or args.max_new_per_source < 0
        or args.max_total_per_source < 0
    ):
        raise SystemExit("collection limits must be >= 0")

    legacy.fetch_bytes = authenticated_fetch_bytes
    legacy.ALLOWED_LICENSES.update(DYNAMIC_ALLOWED_LICENSES)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        manifest = {}

    manifest["version"] = "AUTO-WEB-CORPUS-2-INCREMENTAL"
    manifest["policy"] = {
        "source_type": "auto-discovered reusable Universal Dependencies UD_English-* treebanks",
        "arbitrary_web_scraping": False,
        "append_only": True,
        "max_new_per_run": args.max_new_per_run,
        "max_new_per_source_per_run": args.max_new_per_source,
        "max_total_per_source": args.max_total_per_source,
        "per_source_storage_unlimited": args.max_total_per_source == 0,
        "redistribute_unused_run_budget": True,
        "authenticated_github_api": bool(
            os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        ),
        "skip_exhausted_unchanged_sources": True,
        "auto_discover_english_treebanks": True,
        "license_policy": "CC-BY/CC-BY-SA reusable text only; NC/restricted/unclear-text-rights sources excluded",
        "role_analyzer": "english-sentence-lab/scripts/canonical_roles.py",
    }
    manifest.setdefault("sources", {})

    discovery_error = ""
    try:
        discovered_sources, skipped_repositories = discover_english_sources()
    except Exception as exc:
        discovered_sources = dict(legacy.SOURCES)
        skipped_repositories = []
        discovery_error = f"{type(exc).__name__}: {exc}"
        print(f"WARNING: dynamic source discovery failed; using known sources: {discovery_error}")

    legacy.SOURCES.update(discovered_sources)
    manifest["discovery"] = {
        "matching_repositories_seen": len(discovered_sources) + len(skipped_repositories),
        "accepted_source_count": len(discovered_sources),
        "accepted_sources": sorted(
            [
                {"key": key, "repo": src["repo"], "license": src["license"]}
                for key, src in discovered_sources.items()
            ],
            key=lambda x: x["key"],
        ),
        "skipped_repositories": skipped_repositories,
        "discovery_error": discovery_error,
    }

    if args.source:
        selected = []
        for requested in args.source:
            if requested not in legacy.SOURCES:
                raise SystemExit(
                    f"unknown/unusable source {requested!r}; available={sorted(legacy.SOURCES)}"
                )
            selected.append(requested)
    else:
        selected = sorted(legacy.SOURCES)

    plans = []
    for key in selected:
        source = legacy.SOURCES[key]
        existing = read_jsonl(out / f"{key}.jsonl")
        legacy.validate_output(existing)
        previous_stats = dict(manifest["sources"].get(key, {}))
        current_head = repo_head_sha(source["repo"])
        skip, reason = should_skip_download(
            len(existing), previous_stats, current_head, args.max_total_per_source
        )
        plans.append(
            {
                "key": key,
                "source": source,
                "existing": existing,
                "previous": previous_stats,
                "head": current_head,
                "skip": skip,
                "reason": reason,
            }
        )

    active_left = sum(not plan["skip"] for plan in plans)
    remaining_budget: int | None = (
        args.max_new_per_run if args.max_new_per_run > 0 else None
    )

    for plan in plans:
        key = plan["key"]
        source = plan["source"]
        existing = plan["existing"]
        previous_stats = plan["previous"]
        current_head = plan["head"]

        if plan["skip"]:
            stats = reused_source_stats(
                key,
                source,
                previous_stats,
                existing,
                current_head,
                plan["reason"],
            )
            stats["allocated_run_quota"] = 0
            manifest["sources"][key] = stats
            print(
                f"{key:14s}: stored={len(existing):5d} added={0:4d} "
                f"remaining={stats.get('remaining_unseen', '?')} SKIP={plan['reason']}"
            )
            continue

        if remaining_budget is not None and remaining_budget <= 0:
            stats = reused_source_stats(
                key,
                source,
                previous_stats,
                existing,
                current_head,
                "run_budget_exhausted",
            )
            stats["allocated_run_quota"] = 0
            manifest["sources"][key] = stats
            active_left -= 1
            print(f"{key:14s}: stored={len(existing):5d} added={0:4d} SKIP=run_budget_exhausted")
            continue

        quota = fair_quota(
            remaining_budget,
            active_left,
            args.max_new_per_source,
        )
        try:
            upstream, upstream_stats = legacy.collect_source(key, source, 0)
        except Exception as exc:
            manifest.setdefault("discovery", {}).setdefault("runtime_skips", []).append(
                {
                    "key": key,
                    "repo": source["repo"],
                    "reason": "source_collection_failed",
                    "detail": f"{type(exc).__name__}: {exc}",
                }
            )
            if existing:
                stats = reused_source_stats(
                    key,
                    source,
                    previous_stats,
                    existing,
                    current_head,
                    "source_collection_failed_preserved_existing",
                )
                stats["allocated_run_quota"] = 0
                manifest["sources"][key] = stats
            else:
                manifest["sources"].pop(key, None)
            active_left -= 1
            print(
                f"{key:14s}: collection failed but run continues: "
                f"{type(exc).__name__}: {exc}"
            )
            continue

        merged, added, remaining = merge_incremental(
            existing,
            upstream,
            quota,
            args.max_total_per_source,
        )
        legacy.write_jsonl(out / f"{key}.jsonl", merged)
        manifest["sources"][key] = source_stats(
            key,
            source,
            upstream_stats,
            merged,
            added,
            remaining,
            current_head,
            quota,
        )
        if remaining_budget is not None:
            remaining_budget = max(0, remaining_budget - len(added))
        active_left -= 1
        print(
            f"{key:14s}: stored={len(merged):5d} added={len(added):4d} "
            f"quota={quota:4d} remaining={remaining:5d} "
            f"run_budget_left={remaining_budget if remaining_budget is not None else 'unlimited'}"
        )

    recompute_totals(out, manifest)

    snapshot_parts = []
    for key, stats in sorted(manifest["sources"].items()):
        snapshot_parts.append(f"{key}:HEAD:{stats.get('upstream_head_sha', '')}")
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
