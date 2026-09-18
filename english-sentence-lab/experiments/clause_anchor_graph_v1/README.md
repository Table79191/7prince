# ClauseAnchorGraph v1

A completely separate experimental SentenceLab parser.

This experiment does **not** reuse RoleNet, GRU layers, self-attention blocks, browser weak-role inputs, or the browser heuristic decoder.

## Core idea

Instead of directly classifying each token as S/V/O/C/M, ClauseAnchorGraph decomposes parsing into four problems:

1. **Clause-head detection** — identify the structural head of each clause.
2. **Token-to-clause graph attachment** — attach every token to one clause head with a biaffine graph scorer.
3. **Clause-conditioned role decoding** — predict S/V/O/C/M from the token representation **and the representation of its selected clause head**.
4. **Global structural decoding** — punctuation is null and every decoded clause must contain at least one V token.

This makes clause locality explicit. A matrix verb cannot simply overwrite the role of a token inside an embedded clause because every token first chooses a clause owner.

## Architecture

- hashed word embedding: 64
- POS embedding: 24
- morphology/shape projection: 16
- absolute position embedding: 16
- projection: 128
- **6 residual dilated convolution blocks** with dilations `1, 2, 4, 8, 16, 1`
- clause-head binary scorer
- biaffine token→clause owner scorer
- relative-distance embedding
- clause-conditioned role MLP

No RNN and no Transformer/self-attention are used.

## Training targets

Training uses only approved upstream **train** records from `data/web_corpus_bot`.
Validation uses upstream **dev** records only.
Official test/evaluation-only sources are excluded.

Canonical S/V/O/C/M targets follow `docs/role_label_spec_v2.md`.

Clause-owner targets are derived independently from the gold UD dependency tree:

- root token = clause head
- `acl`, `advcl`, `ccomp`, `xcomp`, `parataxis` heads start new clauses
- verbal `conj` tokens can start coordinated clauses
- every token walks its gold dependency ancestors until it reaches the closest clause head

The dependency tree is used only to create training targets. The model does not receive gold dependency edges at inference.

## Loss

```
L = role_ce
  + 0.35 * clause_head_bce
  + 0.30 * owner_ce
```

Source imbalance is controlled with per-source sentence weights.

## Files

- `model.py` — independent neural architecture and decoder
- `data.py` — dataset builder and clause graph target construction
- `train.py` — training and validation
- `infer.py` — standalone inference from pre-tokenized tokens/POS
- `smoke_test.py` — architecture/data invariants

Artifacts are written under:

`experiments/clause_anchor_graph_v1/artifacts/`

This experiment is deliberately isolated from production. Nothing in this folder replaces the current ONNX/browser model automatically.
