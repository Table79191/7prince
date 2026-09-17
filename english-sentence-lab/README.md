# English Sentence Lab — neural parser workspace

This directory contains the browser/PyTorch assets for the English Sentence Lab parser and public annotated English corpora used for future training.

## Current neural model

- family: SentenceLab RoleNet
- version line: v1.6.1 / GRU3 + Self-Attention
- architecture: hashed word/prefix/suffix embeddings + POS/base-role embeddings + 3-layer bidirectional GRU (64 x 2) + 4-head self-attention + FFN + S/V/O/C/M/NONE role head
- trained sentences in the current checkpoint: 6,000
- trained tokens in the current checkpoint: 397,971
- current parameter count: 615,574

The model weights are stored in `model/v1.6.1/weights/` as a loss-minimized float16 NPZ encoded into text chunks so they can be committed through the repository API. `model/v1.6.1/restore_weights.py` reconstructs the NPZ.

## Data

`data/ud/` is populated from public Universal Dependencies English treebanks by `scripts/download_ud.py` and the GitHub Actions bootstrap workflow.

Selected corpora intentionally cover different domains:

- English ATIS — spoken airline-information questions
- English PUD — news/wiki
- English Pronouns — targeted grammar examples
- English CTeTex — technical/software-requirement text
- English CHILDES — child/adult spoken interaction
- English LittlePrince — manually corrected fiction
- English ESLSpok — spoken L2 English

Third-party licenses and upstream URLs are listed in `data/SOURCES.md`. Do not silently remove upstream attribution/license files.

## Important evaluation rule

Existing sealed holdouts (Complex200, Novel Stress120, Chaos Long50) are evaluation-only and must not be copied into training data.
