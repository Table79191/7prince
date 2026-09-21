# SentenceLab enwiki bulk collector

- total accepted local records: 568983
- total pages sampled: 33734
- added this run: 3702
- rejected this run: {'char_length': 417, 'parser_integrity': 367, 'canonical': 684, 'word_length': 175, 'duplicate': 28, 'nonprose': 30, 'markup': 74, 'punctuation': 11}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
