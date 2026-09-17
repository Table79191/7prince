# Sealed Chaos Long50 evaluation data

These two files are **evaluation-only** encodings recovered from the original SentenceLab v1.5.3 Chaos Long50 holdout package.

- `chaos50_base_v153.json.gz.b64`: frozen v1.5.3 token/POS/base-role outputs for all 50 sentences.
- `chaos50_gold.json.gz.b64`: 755 focus-token gold POS/S/V/O/C/M checks.

Do not use these files in any training, replay, calibration, threshold selection, or model selection step. They exist only to reproduce the historical sealed evaluation. The v1.7.5 evaluator also asserts the historical v1.5.3 baseline counts (POS 670/755, Role 534/755, Both 528/755, exact 0/50) before scoring a newer model.
