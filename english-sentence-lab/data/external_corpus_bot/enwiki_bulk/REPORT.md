# SentenceLab enwiki bulk collector

- total accepted local records: 955953
- total pages sampled: 56028
- added this run: 3926
- rejected this run: {'char_length': 323, 'canonical': 790, 'word_length': 144, 'parser_integrity': 439, 'markup': 52, 'nonprose': 18, 'duplicate': 10, 'punctuation': 6}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
