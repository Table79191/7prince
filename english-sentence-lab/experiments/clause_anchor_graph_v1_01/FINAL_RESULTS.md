# ClauseAnchorGraph v1.01-FINAL — final fine-tune validation

Status: **PASS**

Parent: `CLAUSE-ANCHOR-GRAPH-V1.01-FT1`

This is the final pre-arena fine-tune. The final checkpoint was selected on the clean upstream dev set only. The new FINAL blind set, Hard14, and original 64-token challenge were not used for fitting or checkpoint selection.

## Final fine-tune strategy

- candidate clean-train sentences inspected: **13,632**
- hard examples mined from model errors: **3,600**
- replay examples: **1,400**
- final training set: **5,000**
- epochs attempted: **2**
- selected epoch: **2**
- learning rate: **5e-5**
- strategy: predicted-owner disagreement/error mining + replay
- complement (C) errors received additional loss emphasis
- official test/evaluation-only data excluded

## Clean dev

| metric | FT1 | FINAL | delta |
|---|---:|---:|---:|
| predicted-owner role accuracy | 93.99% | **94.17%** | **+0.17 pp** |
| predicted-owner sentence exact | **65.08%** | 64.19% | **-0.89 pp** |
| oracle-owner role accuracy | 95.64% | **95.81%** | **+0.16 pp** |
| clause-head F1 | 86.13% | **86.44%** | **+0.31 pp** |
| token→clause owner accuracy | 82.15% | **83.43%** | **+1.28 pp** |

The final tune trades a small amount of whole-sentence exact-match on the broad dev set for higher token role accuracy, owner accuracy, clause-head F1, and substantially stronger hard-case generalization.

## FINAL blind set

`FINAL_BLIND16_V1` was created before the final tune and frozen before training.

- sentences: **16**
- focused S/V/O/C checks: **103**
- used for training: **no**
- used for checkpoint selection: **no**

| metric | FT1 before final tune | FINAL | delta |
|---|---:|---:|---:|
| focused role accuracy | 87/103 = 84.47% | **89/103 = 86.41%** | **+1.94 pp** |
| exact sentences | 4/16 = 25.00% | **6/16 = 37.50%** | **+12.50 pp** |

Remaining FINAL-blind errors are concentrated in existential/free-relative attachment and complement recognition:
- `discrepancies S → O`
- relative `that O → S/M`
- `optimistic C → M`
- `reliable C → M`
- `Whoever O → S`
- `subsidiary S → O`
- `interns O → S`
- `unnecessary C → M`
- `which O → S`
- `reviewers S → M`
- `surprising C → O`
- `method S → M`

## Hard14 regression/generalization

| model | score | exact |
|---|---:|---:|
| FT1 | 76/87 = 87.36% | 5/14 = 35.71% |
| FINAL | **79/87 = 90.80%** | **7/14 = 50.00%** |

## Original 64-token challenge

| model | score |
|---|---:|
| v1 | 11/28 = 39.29% |
| v1.01 | 21/28 = 75.00% |
| FT1 | 21/28 = 75.00% |
| FINAL | **24/28 = 85.71%** |

Only four focused errors remain on the original challenge:
- `whom O → M`
- `data S → O`
- `model S → O`
- `director S → M`

## Acceptance

The FINAL gate required all of the following and passed:

1. clean-dev predicted-owner role accuracy improves over FT1,
2. completely new FINAL blind accuracy improves,
3. Hard14 does not regress below FT1,
4. original 64-token challenge does not regress below v1.01/FT1,
5. syntax and artifact checks pass.

The resulting checkpoint is `CLAUSE-ANCHOR-GRAPH-V1.01-FINAL`.

This remains isolated from the production browser/ONNX model and is the recommended ClauseAnchorGraph candidate for the planned arena against the original model.
