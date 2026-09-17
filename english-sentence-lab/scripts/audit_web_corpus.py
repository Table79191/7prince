#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "web_corpus_bot"
ALLOWED_LICENSES = {"CC-BY-SA-4.0", "CC-BY-SA-3.0"}
ALLOWED_ROLES = {"S", "V", "O", "C", "M", "AMBIG", None}


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).lower()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main() -> None:
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    errors: list[str] = []
    warnings: list[str] = []
    global_ids: set[str] = set()
    text_owners: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    total = 0
    status_counts = Counter()
    source_counts: dict[str, int] = {}

    for key, meta in sorted(manifest.get("sources", {}).items()):
        path = DATA / f"{key}.jsonl"
        if not path.exists():
            errors.append(f"missing source file: {path.name}")
            continue
        count = 0
        local_ids: set[str] = set()
        for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not raw.strip():
                continue
            count += 1
            total += 1
            try:
                row = json.loads(raw)
            except Exception as exc:
                errors.append(f"{path.name}:{lineno}: invalid JSON: {exc}")
                continue

            rid = str(row.get("id", ""))
            text = str(row.get("text", ""))
            source = row.get("source") or {}
            analysis = row.get("analysis") or {}
            tokens = analysis.get("tokens") or []
            collection = row.get("collection") or {}

            if not rid or not text:
                errors.append(f"{path.name}:{lineno}: missing id/text")
                continue
            if rid in local_ids:
                errors.append(f"{path.name}:{lineno}: duplicate id within source {rid}")
            local_ids.add(rid)
            if rid in global_ids:
                errors.append(f"{path.name}:{lineno}: duplicate id across corpus {rid}")
            global_ids.add(rid)

            if source.get("key") != key:
                errors.append(f"{path.name}:{lineno}: source key mismatch {source.get('key')!r}")
            if source.get("repo") != meta.get("repo"):
                errors.append(f"{path.name}:{lineno}: repo mismatch")
            if source.get("license") != meta.get("license"):
                errors.append(f"{path.name}:{lineno}: license mismatch")
            if source.get("license") not in ALLOWED_LICENSES:
                errors.append(f"{path.name}:{lineno}: non-allowlisted license {source.get('license')}")

            raw_file = str(source.get("raw_file", ""))
            filename = str(source.get("filename", ""))
            sent_id = str(source.get("sent_id", ""))
            repo = str(source.get("repo", ""))
            if not raw_file.startswith("https://raw.githubusercontent.com/UniversalDependencies/"):
                errors.append(f"{path.name}:{lineno}: unexpected raw_file URL")
            if repo and f"/{repo}/" not in raw_file:
                errors.append(f"{path.name}:{lineno}: raw_file/repo mismatch")
            if filename and not raw_file.endswith("/" + filename):
                errors.append(f"{path.name}:{lineno}: raw_file/filename mismatch")

            expected_id = sha256_text(f"{repo}\n{filename}\n{sent_id}\n{norm(text)}")
            if rid != expected_id:
                errors.append(f"{path.name}:{lineno}: record id hash mismatch")

            if not tokens:
                errors.append(f"{path.name}:{lineno}: empty token list")
            else:
                token_ids = [t.get("id") for t in tokens]
                valid_ids = {x for x in token_ids if isinstance(x, int)}
                if len(valid_ids) != len(tokens):
                    errors.append(f"{path.name}:{lineno}: invalid/duplicate token ids")
                roots = 0
                token_needs_review = False
                for token in tokens:
                    head = token.get("head")
                    if head == 0:
                        roots += 1
                    elif head not in valid_ids:
                        errors.append(f"{path.name}:{lineno}: dangling head {head}")
                    if token.get("role") not in ALLOWED_ROLES:
                        errors.append(f"{path.name}:{lineno}: unexpected role {token.get('role')!r}")
                    if token.get("role") == "AMBIG" or token.get("review_status") != "auto_pass":
                        token_needs_review = True
                if roots < 1:
                    errors.append(f"{path.name}:{lineno}: no dependency root")

                expected_status = "needs_review" if token_needs_review else "auto_pass"
                if analysis.get("status") != expected_status:
                    errors.append(f"{path.name}:{lineno}: analysis status mismatch")
                status_counts[analysis.get("status", "missing")] += 1

                expected_content_hash = hashlib.sha256(
                    json.dumps(tokens, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                ).hexdigest()
                if row.get("content_sha256") != expected_content_hash:
                    errors.append(f"{path.name}:{lineno}: content_sha256 mismatch")

            utc = str(collection.get("first_collected_at_utc", ""))
            kst = str(collection.get("first_collected_at_kst", ""))
            try:
                du = datetime.fromisoformat(utc)
                dk = datetime.fromisoformat(kst)
                if du.utcoffset() is None or du.utcoffset().total_seconds() != 0:
                    raise ValueError("UTC offset is not +00:00")
                if dk.utcoffset() is None or dk.utcoffset().total_seconds() != 9 * 3600:
                    raise ValueError("KST offset is not +09:00")
                if du.timestamp() != dk.timestamp():
                    raise ValueError("UTC/KST timestamps refer to different instants")
            except Exception as exc:
                errors.append(f"{path.name}:{lineno}: invalid collection timestamp: {exc}")

            text_owners[norm(text)].append((key, rid, text))

        source_counts[key] = count
        if count != int(meta.get("sentences_written", -1)):
            errors.append(
                f"{key}: file count {count} != manifest sentences_written {meta.get('sentences_written')}"
            )

    manifest_total = int(manifest.get("totals", {}).get("sentences_written", -1))
    if total != manifest_total:
        errors.append(f"total rows {total} != manifest total {manifest_total}")
    stamped = int(manifest.get("collection_time", {}).get("records_with_timestamp", -1))
    if total != stamped:
        errors.append(f"total rows {total} != records_with_timestamp {stamped}")

    duplicates = {k: v for k, v in text_owners.items() if len(v) > 1}
    cross_source_duplicates = {
        k: v for k, v in duplicates.items() if len({x[0] for x in v}) > 1
    }
    duplicate_extra_rows = sum(len(v) - 1 for v in duplicates.values())
    cross_extra_rows = sum(len(v) - 1 for v in cross_source_duplicates.values())
    if cross_source_duplicates:
        warnings.append(
            f"normalized-text duplicates across sources: {len(cross_source_duplicates)} groups / {cross_extra_rows} extra rows"
        )

    report = {
        "status": "PASS" if not errors else "FAIL",
        "total_rows": total,
        "manifest_total": manifest_total,
        "source_counts": source_counts,
        "analysis_status_counts": dict(status_counts),
        "global_unique_ids": len(global_ids),
        "normalized_unique_texts": len(text_owners),
        "duplicate_text_groups_anywhere": len(duplicates),
        "duplicate_extra_rows_anywhere": duplicate_extra_rows,
        "cross_source_duplicate_groups": len(cross_source_duplicates),
        "cross_source_duplicate_extra_rows": cross_extra_rows,
        "errors": errors[:100],
        "warnings": warnings,
        "cross_source_duplicate_examples": [
            {
                "text": vals[0][2],
                "sources": sorted({x[0] for x in vals}),
                "count": len(vals),
            }
            for vals in list(cross_source_duplicates.values())[:20]
        ],
    }
    out = ROOT / "artifacts" / "web_corpus_audit.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
