# SentenceLab RoleNet R015 — accumulated-data fine-tune

Status: **PASS / accepted arena candidate**

Version: `1.8.5-R015-ACCUMULATED-FINAL`

Parent: `1.8.3-AUTO-PROMOTED-SILVER`

R015 is a separate fine-tuned candidate for the original SentenceLab RoleNet family. It does **not** replace the current production checkpoint automatically.

## Data actually used

- approved upstream gold-train sentences: **48,140**
- accumulated promoted-silver sentences: **15,620**
- promoted rows dropped on recheck: **0**
- school-style regression replay: **445**
- combined training sentences: **64,205**
- promoted-silver loss weight: **0.08**
- parameters: **615,558**

Raw Tatoeba/MediaWiki rows were not trained directly. Only rows already promoted through `PROMOTED-SILVER-1` were included. UD dev, official test/evaluation-only data, Tatoeba Daily500, and the shared hard sets were excluded from fitting and model selection.

## Fine-tune schedule

1. `upper_accumulated`: lower feature stack frozen, LR `2.5e-6`, 1 epoch
2. `full_polish`: all parameters trainable, LR `6e-7`, up to 2 epochs

The accepted checkpoint is **upper_accumulated epoch 1**. The later full-model polish remained safe but scored slightly lower, so it was rejected by checkpoint selection.

## Clean validation

| metric | v1.8.3 parent | R015 | delta |
|---|---:|---:|---:|
| UD dev token role accuracy | 96.5295% | **96.5458%** | **+0.0163 pp** |
| UD dev sentence exact | 76.8403% | **77.0144%** | **+0.1741 pp** |
| school validation role accuracy | 92.1533% | **92.3358%** | **+0.1825 pp** |
| school validation sentence exact | 119 / 176 | **120 / 176** | +1 sentence |

Composite clean-selection score: `1.0802143 → 1.0807045`.

## Shared hard-set diagnostics

These sets were scored only after checkpoint selection and were not used to fit or choose the R015 checkpoint.

| set | v1.8.3 | R015 |
|---|---:|---:|
| Novel Hard14 | 80 / 87 = **91.95%** | 80 / 87 = **91.95%** |
| Final Blind16 | 89 / 103 = **86.41%** | 89 / 103 = **86.41%** |
| original 64-token challenge | 24 / 28 = **85.71%** | 24 / 28 = **85.71%** |

Thus the accumulated-data fine-tune produced a small clean-validation improvement while preserving all three shared hard-set scores.

## Arena status

Recommended original-family candidate for the upcoming model arena:

`1.8.5-R015-ACCUMULATED-FINAL`

The ClauseAnchorGraph opponent remains:

`CLAUSE-ANCHOR-GRAPH-V1.01-FINAL`

Both candidates remain isolated from production until the arena/evaluation stage is completed.
