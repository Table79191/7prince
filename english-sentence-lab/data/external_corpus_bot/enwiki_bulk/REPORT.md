# SentenceLab enwiki bulk collector

- total accepted local records: 331848
- total pages sampled: 20012
- added this run: 4277
- rejected this run: {'canonical': 810, 'word_length': 121, 'char_length': 272, 'parser_integrity': 331, 'punctuation': 4, 'nonprose': 13, 'markup': 43, 'duplicate': 5}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
