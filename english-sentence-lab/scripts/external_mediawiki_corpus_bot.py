#!/usr/bin/env python3
"""SentenceLab external MediaWiki corpus collector.

Default enabled sources:
- English Wikipedia
- Simple English Wikipedia
- English Wikibooks

All text is fetched from the sites' MediaWiki APIs, not GitHub. Each source is
kept separate from the UD gold corpus and labeled as parser-generated weak data.

The collector is intentionally generic: add a source to MEDIAWIKI_SOURCES to
support another compatible MediaWiki project after its reuse terms are verified.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import time
import urllib.parse
import urllib.request

import auto_web_corpus_bot as legacy
from canonical_roles import canonicalize_ud

ROOT = Path(__file__).resolve().parents[1]
BASE_OUT = ROOT / "data" / "external_corpus_bot" / "mediawiki"
USER_AGENT = "SentenceLab-MediaWikiCorpusBot/1.0 (+https://github.com/Table79191/7prince)"
SHARD_SIZE = 2000

MEDIAWIKI_SOURCES = {
    "enwiki": {
        "name": "English Wikipedia",
        "api": "https://en.wikipedia.org/w/api.php",
        "license": "CC-BY-SA-4.0",
        "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
        "project_url": "https://en.wikipedia.org/",
        "enabled": True,
    },
    "simplewiki": {
        "name": "Simple English Wikipedia",
        "api": "https://simple.wikipedia.org/w/api.php",
        "license": "CC-BY-SA-4.0",
        "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
        "project_url": "https://simple.wikipedia.org/",
        "enabled": True,
    },
    "enwikibooks": {
        "name": "English Wikibooks",
        "api": "https://en.wikibooks.org/w/api.php",
        "license": "CC-BY-SA-4.0",
        "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
        "project_url": "https://en.wikibooks.org/",
        "enabled": True,
    },
    # Adapter slots are intentionally present but disabled until the exact
    # project-specific reuse terms are reviewed.
    "enwikiversity": {
        "name": "English Wikiversity",
        "api": "https://en.wikiversity.org/w/api.php",
        "license": "VERIFY-BEFORE-ENABLE",
        "license_url": "",
        "project_url": "https://en.wikiversity.org/",
        "enabled": False,
    },
    "enwikisource": {
        "name": "English Wikisource",
        "api": "https://en.wikisource.org/w/api.php",
        "license": "VERIFY-BEFORE-ENABLE",
        "license_url": "",
        "project_url": "https://en.wikisource.org/",
        "enabled": False,
    },
}


def now_pair() -> tuple[str, str]:
    utc = datetime.now(timezone.utc).replace(microsecond=0)
    kst = utc.astimezone(timezone(timedelta(hours=9)))
    return utc.isoformat(), kst.isoformat()


def request_json(api: str, params: dict[str, str | int], retries: int = 7) -> dict:
    q = dict(params)
    q["format"] = "json"
    q["formatversion"] = "2"
    url = api + "?" + urllib.parse.urlencode(q)
    last = None
    for attempt in range(retries):
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as exc:
            last = exc
            if attempt + 1 >= retries:
                break
            code = getattr(exc, "code", None)
            if code == 429:
                headers = getattr(exc, "headers", None)
                retry_after = None
                if headers is not None:
                    try:
                        retry_after = int(headers.get("Retry-After", "0") or 0)
                    except (TypeError, ValueError):
                        retry_after = None
                delay = max(retry_after or 0, min(180, 30 * (2 ** attempt)))
            else:
                delay = min(30, 2 ** attempt)
            time.sleep(delay)
    raise RuntimeError(f"MediaWiki API failed: {url}: {last}")


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


def source_root(key: str) -> Path:
    return BASE_OUT / key


class ShardWriter:
    def __init__(self, key: str, state: dict):
        self.key = key
        self.root = source_root(key) / "shards"
        self.root.mkdir(parents=True, exist_ok=True)
        self.index = max(1, int(state.get("current_shard", 1)))
        self.count = max(0, int(state.get("current_shard_records", 0)))
        if self.count > SHARD_SIZE:
            self.count = 0

    def path(self) -> Path:
        return self.root / f"{self.key}-{self.index:06d}.jsonl"

    def write(self, row: dict) -> None:
        if self.count >= SHARD_SIZE:
            self.index += 1
            self.count = 0
        with self.path().open("a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        self.count += 1


def stanza_sentence_tokens(sentence) -> list[dict]:
    tokens = []
    for w in sentence.words:
        tokens.append(
            {
                "id": int(w.id),
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
    return tokens


def page_sentence_record(
    key: str,
    cfg: dict,
    page: dict,
    sentence_index: int,
    text: str,
    tokens: list[dict],
) -> dict:
    decisions = canonicalize_ud(tokens)
    role_counts = Counter(d.role for d in decisions if d.role)
    needs_review = any(
        d.role == "AMBIG" or d.review_status != "auto_pass" for d in decisions
    )
    analyzed = []
    for token, decision in zip(tokens, decisions):
        row = dict(token)
        row["role"] = decision.role
        row["role_rule"] = decision.rule_id
        row["review_status"] = decision.review_status
        analyzed.append(row)

    pageid = int(page["pageid"])
    revisions = page.get("revisions") or []
    revision = revisions[0] if revisions else {}
    revid = int(revision.get("revid", 0) or 0)
    page_url = page.get("fullurl") or (
        cfg["project_url"] + "wiki/" + urllib.parse.quote(str(page.get("title", "")))
    )
    basis = (
        f"{key}\n{pageid}\n{revid}\n{sentence_index}\n"
        f"{legacy.normalized_text(text)}"
    )
    record_id = hashlib.sha256(basis.encode("utf-8")).hexdigest()
    content_hash = hashlib.sha256(
        json.dumps(
            analyzed,
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
            "tokens": analyzed,
        },
        "source": {
            "key": key,
            "provider": cfg["name"],
            "pageid": pageid,
            "revision_id": revid,
            "revision_timestamp": revision.get("timestamp", ""),
            "page_title": page.get("title", ""),
            "page_url": page_url,
            "history_url": page_url + ("&" if "?" in page_url else "?") + "action=history",
            "api": cfg["api"],
            "license": cfg["license"],
            "license_url": cfg["license_url"],
        },
        "collection": {
            "first_collected_at_utc": utc,
            "first_collected_at_kst": kst,
        },
        "content_sha256": content_hash,
    }


def list_page_ids(key: str, cfg: dict, state: dict, limit: int = 50):
    params: dict[str, str | int] = {
        "action": "query",
        "list": "allpages",
        "apnamespace": 0,
        "aplimit": limit,
        "apfilterredir": "nonredirects",
    }
    if state.get("apcontinue"):
        params["apcontinue"] = str(state["apcontinue"])
    payload = request_json(cfg["api"], params)
    pages = payload.get("query", {}).get("allpages", [])
    pageids = [str(x["pageid"]) for x in pages if x.get("pageid")]
    continuation = payload.get("continue", {}).get("apcontinue")
    return pageids, continuation


def fetch_pages(cfg: dict, pageids: list[str]) -> list[dict]:
    if not pageids:
        return []
    payload = request_json(
        cfg["api"],
        {
            "action": "query",
            "pageids": "|".join(pageids),
            "prop": "extracts|revisions|info",
            "explaintext": 1,
            "exsectionformat": "plain",
            "rvprop": "ids|timestamp",
            "rvlimit": 1,
            "inprop": "url",
        },
    )
    return payload.get("query", {}).get("pages", [])


def write_manifest(key: str, cfg: dict, state: dict, added: int, skipped: int):
    root = source_root(key)
    manifest = {
        "version": "SENTENCELAB-EXTERNAL-MEDIAWIKI-1",
        "source_key": key,
        "provider": cfg["name"],
        "api": cfg["api"],
        "project_url": cfg["project_url"],
        "license": cfg["license"],
        "license_url": cfg["license_url"],
        "label_quality": "weak_parser_generated",
        "parser": "stanza tokenize,pos,lemma,depparse -> SentenceLab canonical roles",
        "policy": {
            "total_corpus_limit": 0,
            "per_run_sentence_limit": 0,
            "append_only": True,
            "shard_size": SHARD_SIZE,
            "separate_from_gold_ud_corpus": True,
            "crawl_order": "MediaWiki allpages namespace 0",
            "attribution": "page URL + revision id + history URL retained per record",
        },
        "total_pages_processed": state.get("total_pages_processed", 0),
        "total_records": state.get("total_records", 0),
        "auto_pass": state.get("auto_pass", 0),
        "needs_review": state.get("needs_review", 0),
        "added_this_run": added,
        "skipped_this_run": skipped,
        "apcontinue": state.get("apcontinue"),
        "source_exhausted": state.get("source_exhausted", False),
        "shard_count": state.get("current_shard", 1),
    }
    dump_json(root / "manifest.json", manifest)
    (root / "REPORT.md").write_text(
        "\n".join(
            [
                f"# SentenceLab external corpus — {cfg['name']}",
                "",
                "Parser-generated weak corpus, separate from the UD gold corpus.",
                "",
                f"- API: {cfg['api']}",
                f"- License: {cfg['license']}",
                f"- Pages processed: {manifest['total_pages_processed']}",
                f"- Analyzed sentences: {manifest['total_records']}",
                f"- Auto-pass: {manifest['auto_pass']}",
                f"- Needs review: {manifest['needs_review']}",
                f"- Added this run: {added}",
                f"- Source exhausted: {manifest['source_exhausted']}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def process_batch(key: str, cfg: dict, nlp) -> tuple[int, int, bool]:
    root = source_root(key)
    state_path = root / "state.json"
    state = load_json(
        state_path,
        {
            "apcontinue": None,
            "total_pages_processed": 0,
            "total_records": 0,
            "auto_pass": 0,
            "needs_review": 0,
            "current_shard": 1,
            "current_shard_records": 0,
            "source_exhausted": False,
        },
    )
    if state.get("source_exhausted"):
        write_manifest(key, cfg, state, 0, 0)
        return 0, 0, True

    pageids, next_continue = list_page_ids(key, cfg, state, limit=50)
    pages = fetch_pages(cfg, pageids)
    writer = ShardWriter(key, state)
    added = 0
    skipped = 0
    run_auto = 0
    run_review = 0

    for page in pages:
        extract = (page.get("extract") or "").strip()
        if not extract:
            skipped += 1
            continue
        # Keep API calls bounded and avoid huge list/index pages.
        if len(extract) > 250_000:
            extract = extract[:250_000]
        try:
            doc = nlp(extract)
        except Exception:
            skipped += 1
            continue

        sentence_index = 0
        for sentence in doc.sentences:
            sentence_index += 1
            tokens = stanza_sentence_tokens(sentence)
            text = " ".join(w.text for w in sentence.words).strip()
            if not text or not (2 <= len(tokens) <= 180):
                skipped += 1
                continue
            row = page_sentence_record(
                key, cfg, page, sentence_index, text, tokens
            )
            writer.write(row)
            added += 1
            if row["analysis"]["status"] == "auto_pass":
                run_auto += 1
            else:
                run_review += 1

    state.update(
        {
            "apcontinue": next_continue,
            "total_pages_processed": int(state.get("total_pages_processed", 0))
            + len(pageids),
            "total_records": int(state.get("total_records", 0)) + added,
            "auto_pass": int(state.get("auto_pass", 0)) + run_auto,
            "needs_review": int(state.get("needs_review", 0)) + run_review,
            "current_shard": writer.index,
            "current_shard_records": writer.count,
            "source_exhausted": not bool(next_continue),
        }
    )
    dump_json(state_path, state)
    write_manifest(key, cfg, state, added, skipped)
    return added, skipped, state["source_exhausted"]


def validate_source(key: str) -> dict:
    root = source_root(key)
    manifest = load_json(root / "manifest.json", {})
    if not manifest:
        return {}
    total = 0
    for path in sorted((root / "shards").glob(f"{key}-*.jsonl")):
        with path.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                row = json.loads(line)
                assert row["source"]["key"] == key
                assert row["source"]["page_url"]
                assert row["source"]["revision_id"] >= 0
                assert row["analysis"]["tokens"]
                total += 1
    assert total == manifest["total_records"], (key, total, manifest["total_records"])
    return {"key": key, "total": total, "provider": manifest["provider"]}


def self_test() -> None:
    for key in ("enwiki", "simplewiki", "enwikibooks"):
        assert MEDIAWIKI_SOURCES[key]["enabled"]
        assert MEDIAWIKI_SOURCES[key]["license"] == "CC-BY-SA-4.0"
    assert not MEDIAWIKI_SOURCES["enwikiversity"]["enabled"]
    print("MediaWiki external collector self-test: ok")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runtime-seconds", type=int, default=1200)
    ap.add_argument("--site", action="append", choices=sorted(MEDIAWIKI_SOURCES))
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--validate-only", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return

    selected = args.site or [
        key for key, cfg in MEDIAWIKI_SOURCES.items() if cfg.get("enabled")
    ]
    for key in selected:
        if not MEDIAWIKI_SOURCES[key].get("enabled"):
            raise SystemExit(
                f"{key} is adapter-ready but disabled until license/reuse terms are verified"
            )

    if args.validate_only:
        print(json.dumps([validate_source(k) for k in selected], ensure_ascii=False))
        return

    try:
        import stanza
    except ImportError as exc:
        raise SystemExit("stanza is required") from exc

    nlp = stanza.Pipeline(
        "en",
        processors="tokenize,pos,lemma,depparse",
        use_gpu=False,
        verbose=False,
    )

    started = time.monotonic()
    stats = {k: {"added": 0, "skipped": 0, "exhausted": False} for k in selected}
    active = list(selected)

    while active:
        next_active = []
        for key in active:
            if args.runtime_seconds and time.monotonic() - started >= args.runtime_seconds:
                next_active.extend([x for x in active if x not in next_active])
                active = []
                break
            cfg = MEDIAWIKI_SOURCES[key]
            try:
                added, skipped, exhausted = process_batch(key, cfg, nlp)
            except RuntimeError as exc:
                # One rate-limited/unavailable project must not kill collection
                # from every other MediaWiki source in the same run.
                stats[key]["error"] = str(exc)
                stats[key]["deferred"] = True
                print(f"{key}: deferred after source error: {exc}")
                continue
            stats[key]["added"] += added
            stats[key]["skipped"] += skipped
            stats[key]["exhausted"] = exhausted
            print(f"{key}: added={added} skipped={skipped} exhausted={exhausted}")
            if not exhausted:
                next_active.append(key)
        if not active:
            break
        active = next_active

    results = [validate_source(k) for k in selected if (source_root(k) / "manifest.json").exists()]
    print(json.dumps({"run": stats, "validated": results}, ensure_ascii=False))


if __name__ == "__main__":
    main()
