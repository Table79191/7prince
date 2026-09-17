#!/usr/bin/env python3
"""Continuously collect *already syntactically annotated* English data from the web.

The bot intentionally does not scrape arbitrary pages. It follows an allowlist of
public Universal Dependencies (UD) English treebanks, discovers their current
CoNLL-U files, preserves provenance/license metadata, and converts each sentence
into SentenceLab's canonical S/V/O/C/M roles using canonical_roles.py.

Generated files live under data/web_corpus_bot and are safe to regenerate. Git
history acts as the audit log for upstream changes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Iterable

from canonical_roles import canonicalize_ud

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data" / "web_corpus_bot"
GITHUB_API = "https://api.github.com/repos/UniversalDependencies/{repo}/contents?ref=master"
RAW = "https://raw.githubusercontent.com/UniversalDependencies/{repo}/master/{name}"
USER_AGENT = "SentenceLab-AutoWebCorpusBot/1.0 (+https://github.com/Table79191/7prince)"

SOURCES = {
    "ewt": {"repo": "UD_English-EWT", "license": "CC-BY-SA-4.0"},
    "atis": {"repo": "UD_English-Atis", "license": "CC-BY-SA-4.0"},
    "childes": {"repo": "UD_English-CHILDES", "license": "CC-BY-SA-4.0"},
    "ctetex": {"repo": "UD_English-CTeTex", "license": "CC-BY-SA-4.0"},
    "eslspok": {"repo": "UD_English-ESLSpok", "license": "CC-BY-SA-4.0"},
    "littleprince": {"repo": "UD_English-LittlePrince", "license": "CC-BY-SA-4.0"},
    "pronouns": {"repo": "UD_English-Pronouns", "license": "CC-BY-SA-4.0"},
    "pud": {"repo": "UD_English-PUD", "license": "CC-BY-SA-3.0"},
}
ALLOWED_LICENSES = {"CC-BY-SA-4.0", "CC-BY-SA-3.0"}


def fetch_bytes(url: str, retries: int = 4) -> bytes:
    last: Exception | None = None
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"},
    )
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
            if attempt + 1 < retries:
                time.sleep(2**attempt)
    raise RuntimeError(f"failed to fetch {url}: {last}")


def fetch_json(url: str):
    return json.loads(fetch_bytes(url).decode("utf-8"))


def discover_conllu_files(repo: str) -> list[str]:
    payload = fetch_json(GITHUB_API.format(repo=repo))
    if not isinstance(payload, list):
        raise RuntimeError(f"unexpected GitHub contents response for {repo}")
    names = []
    for item in payload:
        name = item.get("name", "")
        if item.get("type") == "file" and name.endswith(".conllu") and "not-to-release" not in name:
            names.append(name)
    if not names:
        raise RuntimeError(f"no .conllu files discovered in {repo}")
    return sorted(names)


def parse_feats(value: str) -> dict[str, str]:
    if not value or value == "_":
        return {}
    out: dict[str, str] = {}
    for bit in value.split("|"):
        if "=" in bit:
            key, val = bit.split("=", 1)
            out[key] = val
    return out


def parse_misc(value: str) -> dict[str, str]:
    if not value or value == "_":
        return {}
    out: dict[str, str] = {}
    for bit in value.split("|"):
        if "=" in bit:
            key, val = bit.split("=", 1)
            out[key] = val
        else:
            out[bit] = "true"
    return out


def parse_conllu(text: str) -> Iterable[tuple[dict[str, str], list[dict]]]:
    meta: dict[str, str] = {}
    tokens: list[dict] = []

    def emit():
        nonlocal meta, tokens
        if tokens:
            result = (meta, tokens)
            meta, tokens = {}, []
            return result
        meta, tokens = {}, []
        return None

    for raw in text.splitlines() + [""]:
        line = raw.rstrip("\r")
        if not line:
            item = emit()
            if item:
                yield item
            continue
        if line.startswith("#"):
            match = re.match(r"^#\s*([^=]+?)\s*=\s*(.*)$", line)
            if match:
                meta[match.group(1).strip()] = match.group(2).strip()
            continue

        cols = line.split("\t")
        if len(cols) != 10:
            continue
        token_id = cols[0]
        if not token_id.isdigit():
            continue
        head = int(cols[6]) if cols[6].isdigit() else 0
        tokens.append(
            {
                "id": int(token_id),
                "text": cols[1],
                "lemma": "" if cols[2] == "_" else cols[2],
                "pos": "UNK" if cols[3] == "_" else cols[3],
                "xpos": "" if cols[4] == "_" else cols[4],
                "feats": parse_feats(cols[5]),
                "head": head,
                "deprel": "" if cols[7] == "_" else cols[7],
                "deps": "" if cols[8] == "_" else cols[8],
                "misc": parse_misc(cols[9]),
            }
        )


def normalized_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).lower()


def sentence_text(meta: dict[str, str], tokens: list[dict]) -> str:
    return meta.get("text") or " ".join(t["text"] for t in tokens)


def grammar_features(tokens: list[dict]) -> list[str]:
    rels = {t.get("deprel", "") for t in tokens}
    bases = {r.split(":", 1)[0] for r in rels}
    feats: list[str] = []
    if "acl:relcl" in rels:
        feats.append("relative_clause")
    if "advcl" in bases:
        feats.append("adverbial_clause")
    if "ccomp" in bases:
        feats.append("content_clause")
    if "xcomp" in bases:
        feats.append("open_complement")
    if "csubj" in bases:
        feats.append("clausal_subject")
    if any(r.startswith("nsubj:pass") or r.startswith("aux:pass") for r in rels):
        feats.append("passive")
    if "conj" in bases:
        feats.append("coordination")
    if any(t.get("pos") == "AUX" for t in tokens):
        feats.append("auxiliary")
    return feats


def analyze_sentence(source_key: str, source: dict, filename: str, meta: dict[str, str], tokens: list[dict]) -> dict:
    text = sentence_text(meta, tokens)
    decisions = canonicalize_ud(tokens)
    role_counts = Counter(d.role for d in decisions if d.role)
    needs_review = any(d.role == "AMBIG" or d.review_status != "auto_pass" for d in decisions)

    analyzed_tokens = []
    for token, decision in zip(tokens, decisions):
        out = dict(token)
        out["role"] = decision.role
        out["role_rule"] = decision.rule_id
        out["review_status"] = decision.review_status
        analyzed_tokens.append(out)

    sent_id = meta.get("sent_id", "")
    stable_basis = f"{source['repo']}\n{filename}\n{sent_id}\n{normalized_text(text)}"
    record_id = hashlib.sha256(stable_basis.encode("utf-8")).hexdigest()
    content_hash = hashlib.sha256(
        json.dumps(analyzed_tokens, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    return {
        "id": record_id,
        "text": text,
        "analysis": {
            "format": "UD-CoNLL-U + SentenceLab-canonical-roles",
            "status": "needs_review" if needs_review else "auto_pass",
            "role_counts": dict(sorted(role_counts.items())),
            "grammar_features": grammar_features(tokens),
            "tokens": analyzed_tokens,
        },
        "source": {
            "key": source_key,
            "repo": source["repo"],
            "upstream": f"https://github.com/UniversalDependencies/{source['repo']}",
            "raw_file": RAW.format(repo=source["repo"], name=filename),
            "filename": filename,
            "sent_id": sent_id,
            "license": source["license"],
            "license_file": RAW.format(repo=source["repo"], name="LICENSE.txt"),
        },
        "content_sha256": content_hash,
    }


def deterministic_sample(records: list[dict], max_items: int) -> list[dict]:
    if max_items <= 0 or len(records) <= max_items:
        return sorted(records, key=lambda r: r["id"])
    return sorted(records, key=lambda r: r["id"])[:max_items]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def collect_source(key: str, source: dict, max_per_source: int) -> tuple[list[dict], dict]:
    if source["license"] not in ALLOWED_LICENSES:
        raise RuntimeError(f"source {key} has a non-allowlisted license: {source['license']}")

    files = discover_conllu_files(source["repo"])
    records: list[dict] = []
    raw_files = []
    for filename in files:
        url = RAW.format(repo=source["repo"], name=filename)
        data = fetch_bytes(url)
        raw_files.append({
            "filename": filename,
            "url": url,
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
        })
        decoded = data.decode("utf-8")
        for meta, tokens in parse_conllu(decoded):
            if not (2 <= len(tokens) <= 180):
                continue
            records.append(analyze_sentence(key, source, filename, meta, tokens))

    deduped: dict[str, dict] = {}
    for rec in records:
        text_key = hashlib.sha256(normalized_text(rec["text"]).encode("utf-8")).hexdigest()
        deduped.setdefault(text_key, rec)
    sampled = deterministic_sample(list(deduped.values()), max_per_source)
    stats = {
        "source": key,
        "repo": source["repo"],
        "license": source["license"],
        "discovered_files": files,
        "raw_files": raw_files,
        "sentences_parsed": len(records),
        "sentences_after_dedupe": len(deduped),
        "sentences_written": len(sampled),
        "auto_pass": sum(r["analysis"]["status"] == "auto_pass" for r in sampled),
        "needs_review": sum(r["analysis"]["status"] == "needs_review" for r in sampled),
    }
    return sampled, stats


def validate_output(rows: list[dict]) -> None:
    seen: set[str] = set()
    for row in rows:
        if row["id"] in seen:
            raise RuntimeError(f"duplicate record id: {row['id']}")
        seen.add(row["id"])
        tokens = row.get("analysis", {}).get("tokens", [])
        if not tokens:
            raise RuntimeError(f"record has no tokens: {row['id']}")
        for token in tokens:
            if "role" not in token or "deprel" not in token or "head" not in token:
                raise RuntimeError(f"incomplete token analysis in {row['id']}")


def build_report(manifest: dict) -> str:
    lines = [
        "# Auto Web Corpus Bot report",
        "",
        f"Upstream snapshot: `{manifest['upstream_snapshot_sha256']}`",
        "",
        "This dataset contains internet-fetched **already annotated** UD English sentences plus SentenceLab S/V/O/C/M role analysis.",
        "No arbitrary webpages are scraped; only the explicit allowlist in `auto_web_corpus_bot.py` is used.",
        "",
        "| Source | License | Written | Auto-pass | Needs review |",
        "|---|---:|---:|---:|---:|",
    ]
    for key, stats in manifest["sources"].items():
        lines.append(
            f"| {key} | {stats['license']} | {stats['sentences_written']} | {stats['auto_pass']} | {stats['needs_review']} |"
        )
    lines += [
        "",
        f"**Total analyzed sentences:** {manifest['totals']['sentences_written']}",
        "",
        "Every JSONL record preserves the upstream repository, raw file URL, sentence id, expected license, content hash, UD parse, and canonical role rules.",
        "",
    ]
    return "\n".join(lines)


def self_test() -> None:
    fixture = """# sent_id = demo-1
# text = The student solved the problem.
1\tThe\tthe\tDET\tDT\tDefinite=Def|PronType=Art\t2\tdet\t_\t_
2\tstudent\tstudent\tNOUN\tNN\tNumber=Sing\t3\tnsubj\t_\t_
3\tsolved\tsolve\tVERB\tVBD\tTense=Past|VerbForm=Fin\t0\troot\t_\t_
4\tthe\tthe\tDET\tDT\tDefinite=Def|PronType=Art\t5\tdet\t_\t_
5\tproblem\tproblem\tNOUN\tNN\tNumber=Sing\t3\tobj\t_\tSpaceAfter=No
6\t.\t.\tPUNCT\t.\t_\t3\tpunct\t_\t_
"""
    parsed = list(parse_conllu(fixture))
    assert len(parsed) == 1
    meta, tokens = parsed[0]
    assert meta["sent_id"] == "demo-1" and len(tokens) == 6
    demo_source = {"repo": "UD_English-Demo", "license": "CC-BY-SA-4.0"}
    row = analyze_sentence("demo", demo_source, "demo.conllu", meta, tokens)
    by_text = {t["text"]: t["role"] for t in row["analysis"]["tokens"]}
    assert by_text["student"] == "S"
    assert by_text["solved"] == "V"
    assert by_text["problem"] == "O"
    validate_output([row])
    print("self-test: ok")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--max-per-source", type=int, default=1000, help="0 means no cap")
    parser.add_argument("--source", action="append", choices=sorted(SOURCES), help="collect only selected source(s)")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    selected = args.source or list(SOURCES)
    manifest = {
        "version": "AUTO-WEB-CORPUS-1",
        "policy": {
            "source_type": "allowlisted public Universal Dependencies English treebanks",
            "arbitrary_web_scraping": False,
            "max_per_source": args.max_per_source,
            "role_analyzer": "english-sentence-lab/scripts/canonical_roles.py",
        },
        "sources": {},
        "totals": {"sentences_written": 0, "auto_pass": 0, "needs_review": 0},
    }

    all_rows: list[dict] = []
    for key in selected:
        rows, stats = collect_source(key, SOURCES[key], args.max_per_source)
        validate_output(rows)
        write_jsonl(out / f"{key}.jsonl", rows)
        manifest["sources"][key] = stats
        manifest["totals"]["sentences_written"] += stats["sentences_written"]
        manifest["totals"]["auto_pass"] += stats["auto_pass"]
        manifest["totals"]["needs_review"] += stats["needs_review"]
        all_rows.extend(rows)
        print(f"{key:14s}: wrote {stats['sentences_written']:5d} analyzed sentences")

    validate_output(all_rows)
    snapshot_parts = []
    for key, stats in sorted(manifest["sources"].items()):
        for raw in stats["raw_files"]:
            snapshot_parts.append(f"{key}:{raw['filename']}:{raw['sha256']}")
    manifest["upstream_snapshot_sha256"] = hashlib.sha256("\n".join(snapshot_parts).encode("utf-8")).hexdigest()
    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out / "REPORT.md").write_text(build_report(manifest), encoding="utf-8")
    print(json.dumps(manifest["totals"], ensure_ascii=False))


if __name__ == "__main__":
    main()
