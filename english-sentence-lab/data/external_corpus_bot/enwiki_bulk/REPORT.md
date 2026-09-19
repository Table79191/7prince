# SentenceLab enwiki bulk collector

- total accepted local records: 217541
- total pages sampled: 13485
- added this run: 4582
- rejected this run: {'char_length': 737, 'parser_integrity': 751, 'canonical': 956, 'nonprose': 40, 'word_length': 359, 'markup': 57, 'duplicate': 16, 'punctuation': 75}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
