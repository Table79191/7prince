# English Sentence Lab — neural parser workspace

English Sentence Lab is a compact English S/V/O/C/M role parser with corpus collection, training, evaluation, ONNX browser export, and clause-analysis APIs.

## Current production model

- family: SentenceLab RoleNet
- production version: **1.8.2-R012-SCHOOL-REGRESSION**
- role semantics: **Canonical Role Spec v2 (school-head)**
- architecture: hashed word/prefix/suffix embeddings + POS/base-role embeddings + 3-layer bidirectional GRU + 4-head self-attention + S/V/O/C/M/NONE head
- production checkpoint: `artifacts/v1.8.2_r012_school_regression_role.pt`
- browser model: `web/r012/r012_role.onnx`
- parameter scale: ~615k

Pipeline:

`R011 clean canonical -> R012 safe feed -> R012 regression -> ONNX export -> browser smoke/evaluation`

Each stage writes a distinct checkpoint so training jobs do not overwrite one another.

## Split and leakage policy

- upstream `*-train.conllu`: fitting only
- upstream `*-dev.conllu`: validation/model selection only
- upstream `*-test.conllu`: never used for fitting or model selection
- test-only treebanks (CTeTex, LittlePrince, Pronouns, PUD): evaluation-only
- Tatoeba parser labels: weak/silver only, consensus-filtered and low-weight
- regression synthetic holdout: disjoint from regression fine-tuning examples

See `docs/training_feed_policy_v2.json` and `docs/role_label_spec_v2.md`.

## Evaluation notes

ChaosMix50 is a **development stress set**, not a pristine final holdout, because post-processing rules were iterated against it. Tatoeba Daily500 is an independent silver-reference benchmark (Stanza-derived, not human gold). Neither should be described as a human-audited final test.

Third-party licenses and upstream URLs remain with the corresponding corpora and must not be removed.
