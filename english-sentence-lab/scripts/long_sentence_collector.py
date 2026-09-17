#!/usr/bin/env python3
"""Collect long/complex sentences from the canonical UD corpus.

The derived queue is deliberately stored outside data/web_corpus_bot so the
main corpus collector/validator never mistakes it for an upstream source.
"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "web_corpus_bot"
OUT = ROOT / "data" / "long_sentence_bot" / "queue.jsonl"


def main():
    rows = []
    for f in SRC.glob("*.jsonl"):
        with f.open(encoding="utf-8") as h:
            for line in h:
                if not line.strip():
                    continue
                r = json.loads(line)
                text = r.get("text", "")
                tokens = r.get("analysis", {}).get("tokens", [])
                words = len(tokens)
                if words >= 25 or text.count(",") >= 2:
                    rows.append({
                        "text": text,
                        "tokens": words,
                        "source": r.get("source", {}),
                        "analysis": r.get("analysis", {})
                    })
    rows.sort(key=lambda x: x["tokens"], reverse=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as h:
        for r in rows:
            h.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"long_sentences={len(rows)}")
    print(f"output={OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
