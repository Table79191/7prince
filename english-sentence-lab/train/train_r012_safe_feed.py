#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

import spacy
import torch
import torch.nn as nn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "train"))
sys.path.insert(0, str(ROOT / "scripts"))

import train_ud_role as base
from train_gold_finetune import load_gold, clone_state
from train_gold_replay import freeze_lower
from canonical_roles import canonicalize_ud

SOURCE_WEIGHTS = {
    "ewt": 1.00,
    "atis": 0.70,
    "childes": 0.35,
    "eslspok": 0.70,
    "esl": 0.70,
}
TEST_ONLY = {"ctetex", "littleprince", "pronouns", "pud"}
WEAK_WEIGHT = 0.15


def norm_text(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def current_school_roles(tokens):
    decisions = canonicalize_ud(tokens)
    return [d.role for d in decisions]


def to_example(row: dict, family: str, sample_weight: float):
    raw_toks = row["analysis"]["tokens"]
    roles = current_school_roles(raw_toks)
    if any(r == "AMBIG" for r in roles):
        return None

    # Surface normalization changes only text/lemma features; dependency structure
    # and token count stay aligned with the canonical labels above.
    toks = base.normalize_surface_tokens(raw_toks)
    weak = base.weak_base_roles(toks)
    feats = [base.feat_token(t, b) for t, b in zip(toks, weak)]
    labels = [base.ROLE2I[r] for r in roles]
    return (feats, labels, row.get("text", ""), family, float(sample_weight))

def load_ud_web(root: Path):
    train, dev, eval_only = [], [], []
    seen_train = set()
    stats = Counter()

    for path in sorted(root.glob("*.jsonl")):
        for row in iter_jsonl(path):
            ana = row.get("analysis", {})
            if ana.get("status") != "auto_pass":
                stats["drop_not_auto_pass"] += 1
                continue
            src = row.get("source", {})
            key = src.get("key", path.stem)
            filename = src.get("filename", "")
            text_key = norm_text(row.get("text", ""))
            if not text_key:
                continue

            if "-train." in filename:
                if key not in SOURCE_WEIGHTS:
                    stats[f"drop_train_unapproved_source:{key}"] += 1
                    continue
                if text_key in seen_train:
                    stats["drop_train_duplicate"] += 1
                    continue
                ex = to_example(row, f"gold:{key}", SOURCE_WEIGHTS[key])
                if ex is None:
                    stats["drop_train_ambig"] += 1
                    continue
                seen_train.add(text_key)
                train.append(ex)
                stats[f"gold_train:{key}"] += 1
            elif "-dev." in filename:
                ex = to_example(row, f"dev:{key}", 1.0)
                if ex is not None:
                    dev.append(ex)
                    stats[f"dev:{key}"] += 1
            elif "-test." in filename and key in TEST_ONLY:
                ex = to_example(row, f"eval_only:{key}", 1.0)
                if ex is not None:
                    eval_only.append(ex)
                    stats[f"eval_only:{key}"] += 1

    return train, dev, eval_only, stats, seen_train


def benchmark_ids(path: Path) -> set[int]:
    ids = set()
    if not path.exists():
        return ids
    with path.open(encoding="utf-8") as f:
        next(f, None)
        for line in f:
            if not line.strip():
                continue
            try:
                ids.add(int(line.split("\t", 1)[0]))
            except Exception:
                pass
    return ids


def spacy_roles(doc):
    out = []
    for t in doc:
        dep = t.dep_.lower()
        if t.is_punct or t.pos_ == "PUNCT":
            role = None
        elif dep in {"nsubj", "nsubjpass", "csubj", "csubjpass", "expl"}:
            role = "S"
        elif dep in {"dobj", "obj", "iobj", "dative"}:
            role = "O"
        elif t.pos_ in {"VERB", "AUX"}:
            role = "V"
        elif dep in {"attr", "acomp", "oprd"}:
            role = "C"
        else:
            role = "M"
        out.append(role)
    return out


def strict_consensus(nlp, row: dict) -> bool:
    toks = row["analysis"]["tokens"]
    text = row.get("text", "")
    doc = nlp(text)
    if len(doc) != len(toks):
        return False

    for a, b in zip(doc, toks):
        if norm_text(a.text) != norm_text(str(b.get("text", ""))):
            return False

    secondary = spacy_roles(doc)
    primary = current_school_roles(toks)
    if "AMBIG" in primary:
        return False
    comparable = [(a, b) for a, b in zip(primary, secondary) if a is not None]
    if not comparable:
        return False

    # Core labels must agree exactly. Overall agreement must also be very high.
    for a, b in comparable:
        if a in {"S", "V", "O", "C"} and a != b:
            return False
    agree = sum(a == b for a, b in comparable) / len(comparable)
    return agree >= 0.92


def load_tatoeba_weak(
    root: Path,
    nlp,
    excluded_ids: set[int],
    seen_gold: set[str],
    max_rows: int,
):
    candidates = []
    seen = set()
    stats = Counter()

    for path in sorted((root / "shards").glob("tatoeba-*.jsonl")):
        for row in iter_jsonl(path):
            sid = int(row.get("source", {}).get("sentence_id", 0) or 0)
            if sid in excluded_ids:
                stats["drop_benchmark_id"] += 1
                continue
            ana = row.get("analysis", {})
            toks = ana.get("tokens", [])
            if ana.get("status") != "auto_pass":
                stats["drop_not_auto_pass"] += 1
                continue
            if not (6 <= len(toks) <= 100):
                stats["drop_length"] += 1
                continue
            roles = [t.get("role") for t in toks]
            if "AMBIG" in roles:
                stats["drop_ambig"] += 1
                continue
            if "V" not in roles or not any(r in {"S", "O", "C"} for r in roles):
                stats["drop_no_core_structure"] += 1
                continue
            k = norm_text(row.get("text", ""))
            if not k or k in seen_gold or k in seen:
                stats["drop_duplicate"] += 1
                continue
            if not strict_consensus(nlp, row):
                stats["drop_consensus"] += 1
                continue
            ex = to_example(row, "weak:tatoeba", WEAK_WEIGHT)
            if ex is None:
                continue
            seen.add(k)
            candidates.append((hashlib.sha256(k.encode()).hexdigest(), ex))
            stats["consensus_candidates"] += 1

    candidates.sort(key=lambda x: x[0])
    selected = [x[1] for x in candidates[:max_rows]]
    stats["selected"] = len(selected)
    return selected, stats


def weighted_train_epoch(model, data, opt, lossfn, device, batch, seed):
    rows = list(data)
    random.Random(seed).shuffle(rows)
    model.train()
    total_loss = 0.0
    total_weighted_tokens = 0.0
    total_tokens = 0
    correct = 0

    for st in range(0, len(rows), batch):
        items = rows[st:st + batch]
        b, y, m = base.collate(items, device)
        sw = torch.tensor([float(x[4]) for x in items], device=device).unsqueeze(1)
        opt.zero_grad(set_to_none=True)
        z = model(b, m)
        raw = lossfn(z.view(-1, 6), y.view(-1)).view_as(y)
        weighted_mask = m.float() * sw
        denom = weighted_mask.sum().clamp_min(1.0)
        loss = (raw * weighted_mask).sum() / denom
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()

        with torch.no_grad():
            p = z.argmax(-1)
            n = int(m.sum().item())
            total_tokens += n
            correct += int(((p == y) & m).sum().item())
            wtok = float(weighted_mask.sum().item())
            total_weighted_tokens += wtok
            total_loss += float(loss.item()) * wtok

    return {
        "sentences": len(rows),
        "tokens": total_tokens,
        "weighted_tokens": total_weighted_tokens,
        "loss": total_loss / max(total_weighted_tokens, 1.0),
        "train_acc": correct / max(total_tokens, 1),
    }


def evaluate(model, data, device, batch):
    return base.evaluate(model, data, device, batch) if data else {
        "sentences": 0, "tokens": 0, "base_role_acc": 0.0,
        "neural_role_acc": 0.0, "sentence_exact": 0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="artifacts/v1.8.0_r011_canonical_role.pt")
    ap.add_argument("--web-corpus", default="data/web_corpus_bot")
    ap.add_argument("--tatoeba", default="data/external_corpus_bot/tatoeba")
    ap.add_argument("--benchmark-tsv", default="data/tatoeba500/TatoebaDaily500_CC0.tsv")
    ap.add_argument("--out", default="artifacts/v1.8.1_r012_safe_feed_role.pt")
    ap.add_argument("--metrics", default="artifacts/v1.8.1_r012_safe_feed_metrics.json")
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--batch", type=int, default=32)
    args = ap.parse_args()

    torch.set_num_threads(4)
    random.seed(79191)
    torch.manual_seed(79191)
    device = torch.device("cpu")

    gold_train, ud_dev, eval_only, ud_stats, seen_gold = load_ud_web(Path(args.web_corpus))
    if not gold_train or not ud_dev:
        raise SystemExit("safe feed requires non-empty upstream train and dev sets")

    # Silver/weak corpora are audit-only. They are deliberately excluded from
    # supervised fitting so R012 remains gold-only.
    weak_train = []
    weak_stats = {"disabled_for_training": 1}

    ck = torch.load(args.base, map_location="cpu", weights_only=False)
    model = base.RoleNet().to(device)
    model.load_state_dict(ck["model"], strict=True)
    freeze_lower(model)

    baseline = {
        "ud_dev": evaluate(model, ud_dev, device, args.batch),
    }

    mix = list(gold_train)
    opt = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=2.0e-5,
        weight_decay=3e-4,
    )
    class_weights = torch.tensor([0.35, 0.75, 0.9, 1.05, 1.6, 0.8], device=device)
    lossfn = nn.CrossEntropyLoss(weight=class_weights, reduction="none")

    best_state = clone_state(model)
    best_epoch = 0
    best_dev = baseline["ud_dev"]["neural_role_acc"]
    history = []

    for ep in range(1, args.epochs + 1):
        train_log = weighted_train_epoch(
            model, mix, opt, lossfn, device, args.batch, 91200 + ep
        )
        current = {
            "ud_dev": evaluate(model, ud_dev, device, args.batch),
        }
        # Model selection is based only on the current head-only UD dev split.
        safe = (
            current["ud_dev"]["neural_role_acc"]
            >= baseline["ud_dev"]["neural_role_acc"] - 0.003
        )
        history.append({
            "epoch": ep,
            "train": train_log,
            "eval": current,
            "safe": safe,
        })
        if safe and current["ud_dev"]["neural_role_acc"] > best_dev:
            best_dev = current["ud_dev"]["neural_role_acc"]
            best_state = clone_state(model)
            best_epoch = ep

    model.load_state_dict(best_state)
    selected = {
        "ud_dev": evaluate(model, ud_dev, device, args.batch),
    }

    metrics = {
        "version": "1.8.1-R012-SAFE-FEED-SCHOOL-HEADS",
        "base": Path(args.base).name,
        "selected_epoch": best_epoch,
        "candidate_accepted": best_epoch > 0,
        "policy": {
            "gold_only_upstream_train": True,
            "dev_test_never_trained": True,
            "tatoeba_daily500_excluded": True,
            "weak_max_fraction": 0.0,
            "weak_loss_weight": 0.0,
            "weak_requires_spacy_stanza_consensus": False,
            "safety_max_regression": 0.003,
            "school_style_head_only_roles": True,
            "relabel_saved_corpora_with_current_canonicalizer": True,
            "normalize_contraction_surfaces": True,
            "legacy_phrase_span_synthetic_removed": True,
            "eval_only_corpora_not_scored_during_training": True,
        },
        "feed": {
            "gold_train_sentences": len(gold_train),
            "weak_tatoeba_sentences": len(weak_train),
            "combined_sentences": len(mix),
            "weak_fraction": len(weak_train) / len(mix) if mix else 0.0,
            "ud_stats": dict(ud_stats),
            "weak_stats": dict(weak_stats),
        },
        "baseline": baseline,
        "selected": selected,
        "history": history,
        "note": (
            "R012 trains only on upstream UD train rows. Tatoeba and other parser-generated "
            "silver labels are audit-only and excluded from supervised fitting. Saved dependency "
            "parses are relabeled at training time with the current school-style head-only "
            "canonicalizer, and contraction surfaces are normalized. UD dev/test and Tatoeba "
            "Daily500 are excluded from training. Test/evaluation-only corpora are not scored "
            "inside this training workflow, preventing manual holdout-driven model selection."
        ),
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model": model.state_dict(),
            "config": {
                "gru": 3,
                "attn": 1,
                "source": "R011 + upstream gold-train only",
                "roles": base.I2ROLE,
            },
            "metrics": metrics,
        },
        out,
    )
    Path(args.metrics).write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
