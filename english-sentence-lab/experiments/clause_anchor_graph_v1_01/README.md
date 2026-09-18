# ClauseAnchorGraph v1.01

A versioned successor to ClauseAnchorGraph v1. The original v1 folder is preserved unchanged.

## v1.01 changes

1. **Distance-aware owner graph** — the biaffine token→clause scorer receives a trainable relative-distance prior initialized to prefer local clause ownership without forbidding long attachments.
2. **Class-balanced role loss** — S/O/C are no longer overwhelmed by the much more frequent M class during early training.
3. **Higher owner-loss weight** — owner CE increases from 0.30 to 0.45 because the v1 hard-sentence failure was dominated by tokens attaching to the wrong clause.
4. **Self-owned clause heads** — every selected clause head is forced to own itself at decode time.
5. **POS-safe structural decoding** — only plausible lexical/predicative POS categories can become clause heads.
6. **Role-spec V invariant** — every lexical VERB and AUX is V, matching `role_label_spec_v2.md`.
7. **Punctuation-last invariant** — punctuation is set to null after every repair, preventing the v1 regression where punctuation could become V.
8. **Conservative missing-subject repair** — if a decoded clause has no S, the nearest preceding nominal member is promoted to S.

The architecture remains RNN-free and Transformer-free: hashed lexical/POS/shape/position features → six gated dilated convolution blocks → clause-head scorer → distance-aware biaffine owner graph → clause-conditioned role MLP.

## Training

Training still uses approved upstream train data only. Dev is validation-only and official test sources stay excluded.

Loss:

```
L = class_balanced_role_ce
  + 0.35 * clause_head_bce
  + 0.45 * owner_ce
```

This folder is isolated from production and does not replace the current browser/ONNX model.
