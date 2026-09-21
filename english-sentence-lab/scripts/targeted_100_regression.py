#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = ROOT / "api" / "analyze.py"
REPORT_PATH = ROOT / "artifacts" / "targeted100_latest.json"

PROBE_TEXT = "while studing english i sometimes couldn't understant the sentence structure"

spec = importlib.util.spec_from_file_location("sentencelab_backend_targeted100", BACKEND_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load analyzer backend: {BACKEND_PATH}")
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)

cases = []

# 50 emphatic direct-WH copular questions.
fillers = [
    ("the hell", ["the", "hell"]),
    ("on earth", ["on", "earth"]),
    ("in the world", ["in", "the", "world"]),
]
frames = [
    ("is", "this"), ("is", "that"),
    ("are", "these"), ("are", "those"),
    ("was", "this"), ("was", "that"),
    ("were", "these"), ("were", "those"),
]
for wh in ("What", "Who"):
    for filler, filler_tokens in fillers:
        for cop, subj in frames:
            cases.append({
                "kind": "emphatic_wh",
                "text": f"{wh} {filler} {cop} {subj}?",
                "wh": wh,
                "filler_tokens": filler_tokens,
                "cop": cop,
                "subject": subj,
            })

# Two extra WH cases => 50.
cases.extend([
    {
        "kind": "emphatic_wh",
        "text": "What the hell is it?",
        "wh": "What", "filler_tokens": ["the", "hell"], "cop": "is", "subject": "it",
    },
    {
        "kind": "emphatic_wh",
        "text": "Who on earth was it?",
        "wh": "Who", "filler_tokens": ["on", "earth"], "cop": "was", "subject": "it",
    },
])

# 50 colloquial / approximate percentage-object sentences.
subjects = [
    ("I", "my", "power"),
    ("We", "our", "energy"),
    ("She", "her", "battery"),
    ("He", "his", "strength"),
    ("They", "their", "capacity"),
]
patterns = [
    ("have only used", "like", "0.001", "so far"),
    ("have used", "about", "0.01", "so far"),
    ("have used", "around", "0.1", "today"),
    ("used", "approximately", "1", "yesterday"),
    ("used", "roughly", "2.5", "already"),
    ("consumed", "about", "3", "today"),
    ("spent", "around", "4", "so far"),
    ("burned", "nearly", "5", "already"),
    ("drained", "almost", "7.5", "today"),
    ("used", "like", "10", "just now"),
]
for subject, poss, noun in subjects:
    for verb_phrase, marker, amount, tail in patterns:
        cases.append({
            "kind": "percentage_object",
            "text": f"{subject} {verb_phrase} {marker} {amount}% of {poss} {noun} {tail}.",
            "subject": subject,
            "amount": amount,
            "noun": noun,
        })

assert len(cases) == 100, len(cases)
assert len({c["text"] for c in cases}) == 100

def token_rows(result):
    return result["tokens"]

def role_of_first(rows, text, start=0):
    for row in rows[start:]:
        if row["text"].lower() == text.lower():
            return row["r012_role"], row["i"]
    return None, -1

failures = []
passed = 0
kind_stats = {}

for index, case in enumerate(cases, 1):
    result = backend.analyze(case["text"])
    rows = token_rows(result)
    checks = []

    if case["kind"] == "emphatic_wh":
        wh_role, wh_i = role_of_first(rows, case["wh"])
        cop_role, cop_i = role_of_first(rows, case["cop"], max(0, wh_i + 1))
        subj_role, subj_i = role_of_first(rows, case["subject"], max(0, cop_i + 1))

        checks.append(("wh=C", wh_role == "C", wh_role))
        checks.append(("cop=V", cop_role == "V", cop_role))
        checks.append(("subject=S", subj_role == "S", subj_role))

        for filler in case["filler_tokens"]:
            role, _ = role_of_first(rows, filler, max(0, wh_i + 1))
            checks.append((f"filler:{filler}=M", role == "M", role))

    else:
        subj_role, subj_i = role_of_first(rows, case["subject"])
        pct_role, pct_i = role_of_first(rows, "%")
        of_role, _ = role_of_first(rows, "of", max(0, pct_i + 1))
        amount_role, _ = role_of_first(rows, case["amount"])
        noun_role, _ = role_of_first(rows, case["noun"], max(0, pct_i + 1))

        lexical_verbs = [r for r in rows if r["pos"] == "VERB"]
        lexical_ok = bool(lexical_verbs) and all(r["r012_role"] == "V" for r in lexical_verbs)

        checks.append(("subject=S", subj_role == "S", subj_role))
        checks.append(("%=O", pct_role == "O", pct_role))
        checks.append(("amount=M", amount_role == "M", amount_role))
        checks.append(("of=M", of_role == "M", of_role))
        checks.append(("of-noun=M", noun_role == "M", noun_role))
        checks.append(("lexical-verb=V", lexical_ok, [(r["text"], r["r012_role"]) for r in lexical_verbs]))

    ok = all(x[1] for x in checks)
    kind_stats.setdefault(case["kind"], {"passed": 0, "failed": 0})
    kind_stats[case["kind"]]["passed" if ok else "failed"] += 1

    if ok:
        passed += 1
    else:
        failures.append({
            "index": index,
            "kind": case["kind"],
            "text": case["text"],
            "checks": [
                {"name": name, "ok": ok_, "actual": actual}
                for name, ok_, actual in checks
            ],
            "tokens": [
                {
                    "text": r["text"],
                    "pos": r["pos"],
                    "dep": r["dep"],
                    "raw": r["r012_raw_role"],
                    "final": r["r012_role"],
                    "reason": r["role_reason"],
                }
                for r in rows
            ],
        })

report = {
    "suite": "SentenceLab targeted 100 regression",
    "total": len(cases),
    "passed": passed,
    "failed": len(failures),
    "pass_rate": passed / len(cases),
    "kind_stats": kind_stats,
    "failures": failures,
    "sentences": [c["text"] for c in cases],
}

REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

probe = backend.analyze(PROBE_TEXT)
print(json.dumps({
    "probe": PROBE_TEXT,
    "tokens": [
        {
            "text": r["text"],
            "pos": r["pos"],
            "dep": r["dep"],
            "raw": r["r012_raw_role"],
            "final": r["r012_role"],
            "reason": r["role_reason"],
        }
        for r in probe["tokens"]
    ],
}, ensure_ascii=False, indent=2))

print(json.dumps({
    "total": report["total"],
    "passed": report["passed"],
    "failed": report["failed"],
    "pass_rate": report["pass_rate"],
    "kind_stats": report["kind_stats"],
}, ensure_ascii=False, indent=2))

if failures:
    for f in failures[:20]:
        print("FAIL", f["index"], f["text"])
        print(json.dumps(f["checks"], ensure_ascii=False))
    raise SystemExit(1)
