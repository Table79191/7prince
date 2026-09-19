# SentenceLab enwiki bulk collector

- total accepted local records: 267693
- total pages sampled: 16358
- added this run: 3321
- rejected this run: {'canonical': 700, 'word_length': 146, 'char_length': 291, 'parser_integrity': 262, 'nonprose': 19, 'markup': 52, 'punctuation': 9, 'duplicate': 52}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
