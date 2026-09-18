# ClauseAnchorGraph v1.01 — validation log

Status: **PASS**

Validated by the dedicated `SentenceLab ClauseAnchorGraph v1.01` GitHub Actions workflow.

## Training / validation setup

- seed: 79191
- training sentences: 967
- upstream dev sentences: 6,317
- dev tokens: 55,353
- epochs: 2
- parameters: 1,893,304
- production model untouched
- official test/evaluation-only data excluded from fitting and selection

## Dev results

The `oracle_owner_*` metrics provide the gold clause owner to the role decoder and are diagnostic only.
The `predicted_owner_*` metrics use the model's own token→clause graph and are the honest neural end-to-end role metrics before decode-time structural repairs.

| metric | random initialization | v1.01 selected |
|---|---:|---:|
| predicted-owner role accuracy | 45.28% | **89.81%** |
| predicted-owner sentence exact | 2.11% | **44.94%** |
| oracle-owner role accuracy | 46.71% | **91.93%** |
| oracle-owner sentence exact | 2.31% | **52.37%** |
| clause-head F1 | 30.09% | **82.72%** |
| token→clause owner accuracy | 11.43% | **75.63%** |

## Fixed hard-sentence challenge

The exact same 64-token sentence that was used to expose the v1 failure is kept as a fixed regression probe.

- v1: **11 / 28 = 39.29%**
- v1.01: **21 / 28 = 75.00%**
- absolute gain: **+35.71 percentage points**
- punctuation-null invariant: PASS
- VERB/AUX→V invariant: PASS

Remaining challenge errors:

- `researcher`: S → O
- `whom`: O → S
- `committee`: S → M
- `model`: S → O
- `interns`: S → C
- `director`: S → C
- `team`: O → S

The remaining failures are concentrated in nested relative/clausal attachment and S/O/C disambiguation rather than the broad M-collapse seen in v1.

## v1.01 changes validated

1. trainable distance-aware biaffine owner prior,
2. class-balanced role loss,
3. stronger owner objective (0.45),
4. self-owned decoded clause heads,
5. POS-safe clause-head candidates,
6. role-spec VERB/AUX→V invariant,
7. punctuation-last null invariant,
8. conservative missing-subject repair.

The original `clause_anchor_graph_v1` experiment remains preserved separately.
