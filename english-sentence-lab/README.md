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

`random init -> R011 clean canonical -> R012 gold-only safe feed -> R012 regression -> ONNX export -> browser smoke/evaluation`

Each stage writes a distinct checkpoint so training jobs do not overwrite one another.

Regression promotion uses both UD token accuracy and sentence-exact safety gates; official test/evaluation-only corpora remain blind during training and epoch selection.

## Split and leakage policy

- upstream `*-train.conllu`: fitting only
- upstream `*-dev.conllu`: validation/model selection only
- upstream `*-test.conllu`: never used for fitting or model selection
- test-only treebanks (CTeTex, LittlePrince, Pronouns, PUD): evaluation-only
- Tatoeba parser labels: weak/silver only, consensus-filtered and low-weight
- regression synthetic validation: at least 128 sentences, disjoint from regression fine-tuning examples

See `docs/training_feed_policy_v2.json` and `docs/role_label_spec_v2.md`.

## Evaluation notes

ChaosMix50 is a **development stress set**, not a pristine final holdout, because post-processing rules were iterated against it. Tatoeba Daily500 is an independent silver-reference benchmark (Stanza-derived, not human gold). Neither should be described as a human-audited final test.

Third-party licenses and upstream URLs remain with the corresponding corpora and must not be removed.


## Legacy checkpoint warning

The committed `v1.7.x` checkpoints are historical artifacts only. Their old loaders could repurpose test-only treebanks into train/validation data, so they must not be used as bases for current production training or as evidence of uncontaminated generalization. The current lineage starts from random initialization at R011.


## Automatic external feed

External Tatoeba and MediaWiki rows remain parser-generated silver data and are never trained directly.

The autonomous feed is:

`external collection -> strict promotion filter -> promoted_silver -> low-weight fine-tune -> gold-dev/regression gates -> accepted production candidate -> ONNX/browser/evaluation`

Promotion requires an auto-pass source row, current canonical roles without `AMBIG`, strict spaCy/Stanza agreement on every core role and at least 92% overall role agreement, no overlap with the gold/dev/evaluation corpus, and no overlap with Tatoeba Daily500.

At least 128 newly promoted rows must accumulate before a training attempt. Training replays 10,000 gold sentences and uses at most 1,200 recent promoted-silver rows at weight 0.12. A candidate replaces production only if all safety gates pass and the composite development score improves. Rejected candidates do not replace production.

Current accepted automatic stage: `v1.8.3-AUTO-PROMOTED-SILVER`.
