# SentenceLab enwiki bulk collector

- total accepted local records: 50326
- total pages sampled: 3659
- added this run: 3334
- rejected this run: {'char_length': 361, 'canonical': 743, 'parser_integrity': 359, 'word_length': 150, 'duplicate': 19, 'nonprose': 28, 'markup': 86, 'punctuation': 7}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
