# SentenceLab enwiki bulk collector

- total accepted local records: 947542
- total pages sampled: 55530
- added this run: 3717
- rejected this run: {'char_length': 371, 'canonical': 728, 'parser_integrity': 311, 'duplicate': 19, 'word_length': 159, 'nonprose': 24, 'markup': 50, 'punctuation': 2}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
