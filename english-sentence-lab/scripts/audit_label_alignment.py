#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "train"))
sys.path.insert(0, str(ROOT / "scripts"))

import train_ud_role as ud_legacy
import train_gold_ewt_masc_replay as masc_legacy
from canonical_roles import canonicalize_ud, canonicalize_masc


def compare_roles(tokens, legacy_roles, decisions, source, stats, examples, sent_name):
    for i, (tok, legacy, decision) in enumerate(zip(tokens, legacy_roles, decisions)):
        canon = decision.role
        stats["tokens"] += 1
        stats["legacy"][str(legacy)] += 1
        stats["canonical"][str(canon)] += 1
        stats["rules"][decision.rule_id] += 1
        stats["review"][decision.review_status] += 1
        if canon == "AMBIG":
            stats["ambig"] += 1
        if legacy != canon:
            stats["disagreements"] += 1
            stats["matrix"][f"{legacy}->{canon}"] += 1
            if len(examples) < 200:
                examples.append({
                    "source": source,
                    "sentence": sent_name,
                    "index": i,
                    "token": tok.get("text"),
                    "pos": tok.get("pos"),
                    "relation": tok.get("deprel"),
                    "legacy": legacy,
                    "canonical": canon,
                    "rule_id": decision.rule_id,
                    "review_status": decision.review_status,
                })


def audit_ud(root: Path, limit: int, stats, examples):
    seen = 0
    for path in sorted(root.rglob("*.conllu")):
        for meta, toks in ud_legacy.parse_conllu(path):
            if not (2 <= len(toks) <= 160):
                continue
            legacy = ud_legacy.phrase_roles(toks)
            canon = canonicalize_ud(toks)
            compare_roles(
                toks, legacy, canon, "ud", stats, examples,
                meta.get("sent_id") or meta.get("text") or path.name,
            )
            seen += 1
            if limit and seen >= limit:
                return seen
    return seen


def iter_masc_sentences(root: Path):
    for path in sorted(root.rglob("*.conll")):
        if "__MACOSX" in path.parts:
            continue
        text = masc_legacy.decode_bytes(path.read_bytes())
        lines = []
        for raw in text.splitlines() + [""]:
            if raw.strip():
                lines.append(raw.rstrip("\r"))
            elif lines:
                toks, reason = masc_legacy.parse_masc_sentence(lines)
                lines = []
                if toks is not None:
                    yield path, toks


def audit_masc(root: Path, limit: int, stats, examples):
    seen = 0
    for path, toks in iter_masc_sentences(root):
        legacy = masc_legacy.masc_roles(toks)
        canon = canonicalize_masc(toks)
        compare_roles(toks, legacy, canon, "masc", stats, examples, path.name)
        seen += 1
        if limit and seen >= limit:
            break
    return seen


def empty_stats():
    return {
        "tokens": 0,
        "disagreements": 0,
        "ambig": 0,
        "legacy": Counter(),
        "canonical": Counter(),
        "matrix": Counter(),
        "rules": Counter(),
        "review": Counter(),
    }


def jsonable(stats):
    return {
        "tokens": stats["tokens"],
        "disagreements": stats["disagreements"],
        "disagreement_rate": stats["disagreements"] / stats["tokens"] if stats["tokens"] else 0.0,
        "ambig": stats["ambig"],
        "ambig_rate": stats["ambig"] / stats["tokens"] if stats["tokens"] else 0.0,
        "legacy": dict(stats["legacy"]),
        "canonical": dict(stats["canonical"]),
        "matrix": dict(stats["matrix"].most_common()),
        "rules": dict(stats["rules"].most_common()),
        "review": dict(stats["review"].most_common()),
    }


def main():
    ap = argparse.ArgumentParser(description="Audit legacy vs canonical S/V/O/C/M label alignment.")
    ap.add_argument("--ud", default=str(ROOT / "data" / "ud"))
    ap.add_argument("--masc", default=str(ROOT / "data" / "gold_external" / "masc_conll" / "extracted" / "masc-conll" / "data"))
    ap.add_argument("--limit-per-source", type=int, default=0, help="0 means all accepted sentences")
    ap.add_argument("--out", default=str(ROOT / "artifacts" / "label_alignment_audit.json"))
    args = ap.parse_args()

    ud_stats = empty_stats(); masc_stats = empty_stats(); examples = []
    ud_sentences = audit_ud(Path(args.ud), args.limit_per_source, ud_stats, examples) if Path(args.ud).exists() else 0
    masc_sentences = audit_masc(Path(args.masc), args.limit_per_source, masc_stats, examples) if Path(args.masc).exists() else 0

    payload = {
        "spec": "docs/role_label_spec_v1.md",
        "training_changed": False,
        "purpose": "diagnose label convention drift before canonical labels are allowed into training",
        "sources": {
            "ud": {"sentences": ud_sentences, **jsonable(ud_stats)},
            "masc": {"sentences": masc_sentences, **jsonable(masc_stats)},
        },
        "sample_disagreements": examples,
    }
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "ud_sentences": ud_sentences,
        "ud_disagreement_rate": payload["sources"]["ud"]["disagreement_rate"],
        "masc_sentences": masc_sentences,
        "masc_disagreement_rate": payload["sources"]["masc"]["disagreement_rate"],
        "out": str(out),
    }, indent=2))


if __name__ == "__main__":
    main()
