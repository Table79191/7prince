# ClauseAnchorGraph v1.01 — validation log

Status: pending CI validation.

The v1 hard-sentence baseline is **11 / 28 = 39.29%** on the fixed challenge probe.

v1.01 is accepted only if:
- syntax + structural smoke tests pass,
- mini training learns above random initialization,
- punctuation remains null after decoding,
- VERB/AUX invariants hold,
- the fixed challenge does not regress below the v1 baseline.

CI artifacts contain the trained checkpoint, mini metrics, and challenge JSON.
