# SentenceLab enwiki bulk collector

- total accepted local records: 573167
- total pages sampled: 33973
- added this run: 4184
- rejected this run: {'char_length': 422, 'canonical': 877, 'parser_integrity': 454, 'word_length': 148, 'nonprose': 29, 'markup': 57, 'duplicate': 17, 'punctuation': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
