#!/usr/bin/env python3
"""SentenceLab external corpus collector: Tatoeba English.

This collector is intentionally separate from the UD gold corpus.

Source:
  https://downloads.tatoeba.org/exports/per_language/eng/eng_sentences.tsv.bz2
License:
  CC BY 2.0 FR (text exports; attribution to Tatoeba required)

Behavior:
- no sentence-count or total-corpus cap
- scans the official weekly English export directly from Tatoeba, not GitHub
- uses sentence id as an append-only high-water mark
- converts raw English sentences to UD-style dependencies with Stanza
- converts dependencies to SentenceLab S/V/O/C/M roles
- writes append-only JSONL shards so individual files do not grow without bound
- checkpoints before the Actions job timeout; the corpus itself remains unlimited
"""
from __future__ import annotations

import argparse
import bz2
from collections import Counter
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import tempfile
import time
import urllib.request

import auto_web_corpus_bot as legacy
from canonical_roles import canonicalize_ud

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "external_corpus_bot" / "tatoeba"
SHARDS = OUT / "shards"
STATE = OUT / "state.json"
MANIFEST = OUT / "manifest.json"
REPORT = OUT / "REPORT.md"

SOURCE_URL = "https://downloads.tatoeba.org/exports/per_language/eng/eng_sentences.tsv.bz2"
SOURCE_PAGE = "https://tatoeba.org/en/downloads"
PROVIDER = "Tatoeba"
LICENSE = "CC-BY-2.0-FR"
LICENSE_URL = "https://creativecommons.org/licenses/by/2.0/fr/"
SHARD_SIZE = 2000
USER_AGENT = "SentenceLab-ExternalCorpusBot/1.0 (+https://github.com/Table79191/7prince)"


def now_pair() -> tuple[str, str]:
    utc = datetime.now(timezone.utc).replace(microsecond=0)
    kst = utc.astimezone(timezone(timedelta(hours=9)))
    return utc.isoformat(), kst.isoformat()


def load_json(path: Path, default: dict) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return dict(default)


def dump_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def fetch_archive() -> tuple[Path, str, int]:
    req = urllib.request.Request(
        SOURCE_URL,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/octet-stream,*/*;q=0.8",
        },
    )
    fd, name = tempfile.mkstemp(prefix="tatoeba-eng-", suffix=".tsv.bz2")
    path = Path(name)
    h = hashlib.sha256()
    size = 0
    try:
        import os
        with os.fdopen(fd, "wb") as out, urllib.request.urlopen(req, timeout=120) as r:
            while True:
                chunk = r.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
                h.update(chunk)
                size += len(chunk)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path, h.hexdigest(), size


def stanza_tokens(nlp, text: str) -> list[dict]:
    doc = nlp(text)
    words = []
    for sent in doc.sentences:
        words.extend(sent.words)
    tokens = []
    for i, w in enumerate(words, start=1):
        # Stanza word ids are sentence-local. Rebase ids/heads when the parser
        # unexpectedly returns more than one sentence.
        tokens.append(
            {
                "id": i,
                "text": w.text,
                "lemma": w.lemma or "",
                "pos": w.upos or "",
                "xpos": w.xpos or "",
                "feats": w.feats or "",
                "head": int(w.head or 0),
                "deprel": w.deprel or "dep",
                "deps": "",
                "misc": "",
            }
        )

    # tokenize_no_ssplit should keep one sentence. If Stanza nevertheless emitted
    # multiple sentences, reject rather than preserve invalid cross-sentence heads.
    if len(doc.sentences) != 1:
        return []
    return tokens


def make_record(sentence_id: int, text: str, tokens: list[dict]) -> dict:
    decisions = canonicalize_ud(tokens)
    role_counts = Counter(d.role for d in decisions if d.role)
    needs_review = any(
        d.role == "AMBIG" or d.review_status != "auto_pass" for d in decisions
    )
    analyzed_tokens = []
    for token, decision in zip(tokens, decisions):
        row = dict(token)
        row["role"] = decision.role
        row["role_rule"] = decision.rule_id
        row["review_status"] = decision.review_status
        analyzed_tokens.append(row)

    stable_basis = f"tatoeba\n{sentence_id}\n{legacy.normalized_text(text)}"
    record_id = hashlib.sha256(stable_basis.encode("utf-8")).hexdigest()
    content_hash = hashlib.sha256(
        json.dumps(
            analyzed_tokens,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    utc, kst = now_pair()
    return {
        "id": record_id,
        "text": text,
        "analysis": {
            "format": "Stanza-UD + SentenceLab-canonical-roles",
            "label_quality": "weak_parser_generated",
            "status": "needs_review" if needs_review else "auto_pass",
            "role_counts": dict(sorted(role_counts.items())),
            "grammar_features": legacy.grammar_features(tokens),
            "tokens": analyzed_tokens,
        },
        "source": {
            "key": "tatoeba",
            "provider": PROVIDER,
            "sentence_id": sentence_id,
            "upstream": f"https://tatoeba.org/en/sentences/show/{sentence_id}",
            "raw_export": SOURCE_URL,
            "download_page": SOURCE_PAGE,
            "license": LICENSE,
            "license_url": LICENSE_URL,
        },
        "collection": {
            "first_collected_at_utc": utc,
            "first_collected_at_kst": kst,
        },
        "content_sha256": content_hash,
    }


class ShardWriter:
    def __init__(self, state: dict):
        SHARDS.mkdir(parents=True, exist_ok=True)
        self.index = int(state.get("current_shard", 1))
        self.count = int(state.get("current_shard_records", 0))
        if self.index < 1:
            self.index = 1
        if self.count < 0 or self.count > SHARD_SIZE:
            self.count = 0

    def _path(self) -> Path:
        return SHARDS / f"tatoeba-{self.index:06d}.jsonl"

    def write(self, row: dict) -> None:
        if self.count >= SHARD_SIZE:
            self.index += 1
            self.count = 0
        with self._path().open("a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        self.count += 1


def iter_new_sentences(archive: Path, high_watermark: int):
    previous_id = -1
    with bz2.open(archive, "rt", encoding="utf-8", errors="replace") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("\t", 2)
            if len(parts) != 3:
                continue
            sid_raw, lang, text = parts
            try:
                sid = int(sid_raw)
            except ValueError:
                continue
            if sid < previous_id:
                raise RuntimeError(
                    f"Tatoeba export is not sorted by sentence id at line {line_no}: "
                    f"{sid} < {previous_id}; refusing unsafe high-watermark update"
                )
            previous_id = sid
            if lang != "eng" or sid <= high_watermark:
                continue
            yield sid, text.strip()


def build_report(manifest: dict) -> str:
    return "\n".join(
        [
            "# SentenceLab external corpus — Tatoeba",
            "",
            "This is a weakly labeled external corpus and is kept separate from the UD gold corpus.",
            "",
            f"- Source: {SOURCE_URL}",
            f"- License: {LICENSE}",
            f"- Total analyzed records: {manifest.get('total_records', 0)}",
            f"- Auto-pass: {manifest.get('auto_pass', 0)}",
            f"- Needs review: {manifest.get('needs_review', 0)}",
            f"- Last processed Tatoeba sentence id: {manifest.get('last_processed_sentence_id', 0)}",
            f"- Added this run: {manifest.get('added_this_run', 0)}",
            f"- Shards: {manifest.get('shard_count', 0)}",
            "",
            "No sentence-count or total-corpus cap is configured. Runs checkpoint by wall-clock time so GitHub Actions can commit progress before its job timeout.",
            "",
        ]
    )


def self_test() -> None:
    tokens = [
        {"id": 1, "text": "Students", "lemma": "student", "pos": "NOUN", "head": 2, "deprel": "nsubj"},
        {"id": 2, "text": "learn", "lemma": "learn", "pos": "VERB", "head": 0, "deprel": "root"},
        {"id": 3, "text": "English", "lemma": "English", "pos": "PROPN", "head": 2, "deprel": "obj"},
        {"id": 4, "text": ".", "lemma": ".", "pos": "PUNCT", "head": 2, "deprel": "punct"},
    ]
    row = make_record(123, "Students learn English.", tokens)
    roles = [t["role"] for t in row["analysis"]["tokens"]]
    assert roles[:3] == ["S", "V", "O"], roles
    assert row["source"]["license"] == LICENSE
    print("tatoeba external collector self-test: ok")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--runtime-seconds",
        type=int,
        default=1500,
        help="checkpoint wall-clock budget for one run; 0 means process until source exhaustion",
    )
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return
    if args.runtime_seconds < 0:
        raise SystemExit("--runtime-seconds must be >= 0")

    try:
        import stanza
    except ImportError as exc:
        raise SystemExit("stanza is required for external parsing") from exc

    OUT.mkdir(parents=True, exist_ok=True)
    state = load_json(
        STATE,
        {
            "last_processed_sentence_id": 0,
            "total_records": 0,
            "auto_pass": 0,
            "needs_review": 0,
            "current_shard": 1,
            "current_shard_records": 0,
        },
    )
    high_watermark = int(state.get("last_processed_sentence_id", 0))
    archive, archive_sha256, archive_bytes = fetch_archive()

    nlp = stanza.Pipeline(
        "en",
        processors="tokenize,pos,lemma,depparse",
        tokenize_no_ssplit=True,
        use_gpu=False,
        verbose=False,
    )
    writer = ShardWriter(state)

    started = time.monotonic()
    added = 0
    skipped = 0
    run_auto = 0
    run_review = 0
    last_processed = high_watermark
    source_exhausted = True

    try:
        for sid, text in iter_new_sentences(archive, high_watermark):
            if args.runtime_seconds and time.monotonic() - started >= args.runtime_seconds:
                source_exhausted = False
                break

            last_processed = sid
            if not text or len(text) > 4000:
                skipped += 1
                continue
            try:
                tokens = stanza_tokens(nlp, text)
            except Exception:
                skipped += 1
                continue
            if not (2 <= len(tokens) <= 180):
                skipped += 1
                continue

            row = make_record(sid, text, tokens)
            writer.write(row)
            added += 1
            if row["analysis"]["status"] == "auto_pass":
                run_auto += 1
            else:
                run_review += 1
    finally:
        archive.unlink(missing_ok=True)

    state.update(
        {
            "last_processed_sentence_id": last_processed,
            "total_records": int(state.get("total_records", 0)) + added,
            "auto_pass": int(state.get("auto_pass", 0)) + run_auto,
            "needs_review": int(state.get("needs_review", 0)) + run_review,
            "current_shard": writer.index,
            "current_shard_records": writer.count,
            "source_exhausted_at_last_run": source_exhausted,
        }
    )
    dump_json(STATE, state)

    manifest = {
        "version": "SENTENCELAB-EXTERNAL-TATOEBA-1",
        "provider": PROVIDER,
        "source_url": SOURCE_URL,
        "source_page": SOURCE_PAGE,
        "license": LICENSE,
        "license_url": LICENSE_URL,
        "label_quality": "weak_parser_generated",
        "parser": "stanza tokenize,pos,lemma,depparse -> SentenceLab canonical roles",
        "policy": {
            "total_corpus_limit": 0,
            "per_run_sentence_limit": 0,
            "append_only": True,
            "shard_size": SHARD_SIZE,
            "separate_from_gold_ud_corpus": True,
            "runtime_checkpoint_seconds": args.runtime_seconds,
        },
        "archive_sha256": archive_sha256,
        "archive_bytes": archive_bytes,
        "last_processed_sentence_id": state["last_processed_sentence_id"],
        "total_records": state["total_records"],
        "auto_pass": state["auto_pass"],
        "needs_review": state["needs_review"],
        "added_this_run": added,
        "skipped_this_run": skipped,
        "source_exhausted_at_last_run": source_exhausted,
        "shard_count": writer.index,
    }
    dump_json(MANIFEST, manifest)
    REPORT.write_text(build_report(manifest), encoding="utf-8")
    print(
        json.dumps(
            {
                "provider": PROVIDER,
                "added": added,
                "total": state["total_records"],
                "last_sentence_id": state["last_processed_sentence_id"],
                "source_exhausted": source_exhausted,
                "shard_count": writer.index,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
