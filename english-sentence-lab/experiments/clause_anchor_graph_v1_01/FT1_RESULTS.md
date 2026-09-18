# ClauseAnchorGraph v1.01-FT1 — fine-tune validation

Status: **PASS**

Parent: `CLAUSE-ANCHOR-GRAPH-V1.01`

The FT1 checkpoint was produced by resuming the validated v1.01 checkpoint and fine-tuning on a broader clean upstream-train subset only.

## Fine-tune setup

- fine-tune train sentences: **4,807**
- fine-tune epochs: **2**
- fine-tune learning rate: **1e-4**
- seed: **79191**
- new hard holdout used for training: **no**
- official test/evaluation-only sources used for training: **no**

## Clean dev

| metric | v1.01 before FT | v1.01-FT1 | delta |
|---|---:|---:|---:|
| predicted-owner role accuracy | 89.81% | **93.99%** | **+4.18 pp** |
| predicted-owner sentence exact | 44.94% | **65.06%** | **+20.12 pp** |
| oracle-owner role accuracy | 91.93% | **95.64%** | **+3.71 pp** |
| clause-head F1 | 82.72% | **86.13%** | **+3.41 pp** |
| token→clause owner accuracy | 75.63% | **82.15%** | **+6.52 pp** |

## Completely new hard holdout

`NOVEL_HARD14_V1` contains 14 sentences / 87 focused S/V/O/C checks. Its structures differ from the original 64-token challenge and include inversion, cleft/pseudo-cleft, reduced passive/relative clauses, nominal subjects, conditional inversion, extraposition, object complements, object control, not-only inversion, free relatives, and comparative correlatives.

| metric | before FT | after FT | delta |
|---|---:|---:|---:|
| focused role accuracy | 64 / 87 = 73.56% | **76 / 87 = 87.36%** | **+13.79 pp** |
| exact sentences | 1 / 14 = 7.14% | **5 / 14 = 35.71%** | **+28.57 pp** |

Notable improvements:
- inversion: 3/6 → **6/6**
- neither/nor inversion: 4/6 → **6/6**
- extraposition: 2/6 → **5/6**
- object-control: 6/7 → **7/7**
- free-relative: 6/7 → **7/7**

Remaining hard-holdout errors are concentrated in:
- cleft complement: `technician C → S`
- pseudo-cleft: `What O → M`, `unacceptable C → O`
- reduced passive: `heat O → S`
- nominal subject: `them O → S`, `unclear C → O`
- extraposition: `obvious C → O`
- object complement: `evasive C → M`
- not-only coordination: `analysis S → M`
- comparative correlative: `plausible C → M`
- reduced relative: `inconsistencies O → S`

## Original hard-sentence regression

The original 64-token v1.01 challenge was rerun against the FT1 checkpoint.

- v1.01 before FT: **21 / 28 = 75.00%**
- v1.01-FT1: **21 / 28 = 75.00%**
- regression: **none**

Thus FT1 improves both clean dev and a completely unseen hard set while preserving the original hard-sentence score.

The model remains experimental and isolated from the production browser/ONNX model.
