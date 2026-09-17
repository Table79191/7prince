#!/usr/bin/env python3
"""Download selected public English Universal Dependencies treebanks.

This script intentionally vendors the upstream CoNLL-U files and license/readme text
into english-sentence-lab/data/ud so GitHub training jobs can work offline after checkout.
"""
from __future__ import annotations

import hashlib
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "ud"
BASE = "https://raw.githubusercontent.com/UniversalDependencies/{repo}/master/{name}"

CORPORA = {
    "atis": {
        "repo": "UD_English-Atis",
        "files": ["en_atis-ud-train.conllu", "en_atis-ud-dev.conllu", "en_atis-ud-test.conllu"],
    },
    "pud": {
        "repo": "UD_English-PUD",
        "files": ["en_pud-ud-test.conllu"],
    },
    "pronouns": {
        "repo": "UD_English-Pronouns",
        "files": ["en_pronouns-ud-test.conllu"],
    },
    "ctetex": {
        "repo": "UD_English-CTeTex",
        "files": ["en_ctetex-ud-test.conllu"],
    },
    "childes": {
        "repo": "UD_English-CHILDES",
        "files": ["en_childes-ud-train.conllu", "en_childes-ud-dev.conllu", "en_childes-ud-test.conllu"],
    },
    "littleprince": {
        "repo": "UD_English-LittlePrince",
        "files": ["en_littleprince-ud-test.conllu"],
    },
    "eslspok": {
        "repo": "UD_English-ESLSpok",
        "files": ["en_eslspok-ud-train.conllu", "en_eslspok-ud-dev.conllu", "en_eslspok-ud-test.conllu"],
    },
}


def fetch(url: str, retries: int = 4) -> bytes:
    last = None
    req = urllib.request.Request(url, headers={"User-Agent": "SentenceLab-UD-fetch/1.0"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read()
        except Exception as exc:  # network retry on GitHub runner
            last = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f"failed to download {url}: {last}")


def conllu_stats(data: bytes) -> dict:
    text = data.decode("utf-8")
    sentences = 0
    tokens = 0
    for line in text.splitlines():
        if line.startswith("# text ="):
            sentences += 1
        elif line and not line.startswith("#"):
            cols = line.split("\t")
            if cols and cols[0].isdigit():
                tokens += 1
    return {"sentences": sentences, "tokens": tokens}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {"format": "CoNLL-U", "corpora": {}, "totals": {"sentences": 0, "tokens": 0, "bytes": 0}}

    for key, spec in CORPORA.items():
        repo = spec["repo"]
        dest = OUT / key
        dest.mkdir(parents=True, exist_ok=True)
        entry = {
            "upstream": f"https://github.com/UniversalDependencies/{repo}",
            "files": [],
            "sentences": 0,
            "tokens": 0,
            "bytes": 0,
        }

        for upstream_name, local_name in [("LICENSE.txt", "LICENSE.txt"), ("README.md", "UPSTREAM_README.md")]:
            url = BASE.format(repo=repo, name=upstream_name)
            data = fetch(url)
            (dest / local_name).write_bytes(data)

        for name in spec["files"]:
            url = BASE.format(repo=repo, name=name)
            data = fetch(url)
            path = dest / name
            path.write_bytes(data)
            stats = conllu_stats(data)
            rec = {
                "name": name,
                "url": url,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                **stats,
            }
            entry["files"].append(rec)
            for fld in ("sentences", "tokens", "bytes"):
                entry[fld] += rec[fld]
                manifest["totals"][fld] += rec[fld]

        manifest["corpora"][key] = entry
        print(f"{key:13s} {entry['sentences']:7d} sentences {entry['tokens']:9d} tokens {entry['bytes']/1e6:7.2f} MB")

    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("TOTAL", manifest["totals"])


if __name__ == "__main__":
    main()
