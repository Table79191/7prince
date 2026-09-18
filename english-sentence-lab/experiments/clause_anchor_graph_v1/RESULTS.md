# ClauseAnchorGraph v1 — initial validation

Initial independent smoke + mini-train validation.

## Architecture smoke

- status: PASS
- parameters: 1,893,175
- forward shapes:
  - clause-head logits: B x L
  - token→clause owner logits: B x L x L
  - role logits: B x L x 6
- backward pass: PASS
- all trainable parameters received gradients

## Mini learning test

This is only a learning sanity check, not a production benchmark.

- training sentences: 487
- upstream dev sentences: 6,317
- epochs: 1
- production model untouched

| metric | random initialization | after mini-train |
|---|---:|---:|
| role accuracy | 26.94% | 59.44% |
| clause-head F1 | 30.09% | 76.76% |
| token→clause owner accuracy | 13.71% | 59.51% |
| sentence exact | — | 122 / 6,317 (1.93%) |

The mini run demonstrates that all three objectives learn simultaneously:

1. clause segmentation/head discovery,
2. token-to-clause graph attachment,
3. clause-conditioned S/V/O/C/M role prediction.

A full training run is intentionally not connected to production. This experiment remains isolated until it is evaluated against the same clean held-out protocol as the current SentenceLab model.
