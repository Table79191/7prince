# SentenceLab enwiki bulk collector

- total accepted local records: 21293
- total pages sampled: 1931
- added this run: 6846
- rejected this run: {'char_length': 537, 'canonical': 1355, 'parser_integrity': 664, 'word_length': 278, 'markup': 128, 'duplicate': 14, 'nonprose': 29, 'punctuation': 9}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
