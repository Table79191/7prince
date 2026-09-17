# Third-party annotated English corpora

The files under `data/ud/` are downloaded from the official Universal Dependencies GitHub repositories. Keep each upstream `LICENSE.txt` beside the copied data.

| Corpus | Upstream | License | Notes |
|---|---|---|---|
| UD English-Atis | https://github.com/UniversalDependencies/UD_English-Atis | CC BY-SA 4.0 | 5,382 spoken airline-information utterances; train/dev/test |
| UD English-PUD | https://github.com/UniversalDependencies/UD_English-PUD | CC BY-SA 3.0 | 1,000 news/wiki sentences; test split |
| UD English-Pronouns | https://github.com/UniversalDependencies/UD_English-Pronouns | CC BY-SA 4.0 | targeted grammatical/pronoun examples |
| UD English-CTeTex | https://github.com/UniversalDependencies/UD_English-CTeTex | CC BY-SA 4.0 | technical/software-requirement text |
| UD English-CHILDES | https://github.com/UniversalDependencies/UD_English-CHILDES | CC BY-SA 4.0 | child/adult spoken interaction; large train/dev/test treebank |
| UD English-LittlePrince | https://github.com/UniversalDependencies/UD_English-LittlePrince | CC BY-SA 4.0 | 500 manually corrected fiction sentences |
| UD English-ESLSpok | https://github.com/UniversalDependencies/UD_English-ESLSpok | CC BY-SA 4.0 | spoken second-language English; train/dev/test |

## Format

The corpora use CoNLL-U. Important columns include token FORM, LEMMA, UPOS, FEATS, syntactic HEAD and DEPREL. These annotations are useful as supervised signal for POS, clause structure and dependency-aware role training.

## License handling

The downloader copies each upstream `LICENSE.txt` into its corpus directory. Any derived/repacked copies must continue to satisfy the applicable attribution/share-alike terms. Do not mix these files into a differently licensed redistribution without checking the upstream license conditions.
