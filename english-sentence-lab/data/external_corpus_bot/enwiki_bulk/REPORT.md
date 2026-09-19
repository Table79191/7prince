# SentenceLab enwiki bulk collector

- total accepted local records: 231237
- total pages sampled: 14250
- added this run: 4503
- rejected this run: {'canonical': 872, 'char_length': 297, 'word_length': 100, 'parser_integrity': 325, 'duplicate': 18, 'markup': 33, 'punctuation': 3, 'nonprose': 15}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
