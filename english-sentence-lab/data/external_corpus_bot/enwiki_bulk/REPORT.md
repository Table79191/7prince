# SentenceLab enwiki bulk collector

- total accepted local records: 253697
- total pages sampled: 15557
- added this run: 3734
- rejected this run: {'canonical': 695, 'word_length': 188, 'parser_integrity': 381, 'char_length': 384, 'duplicate': 25, 'markup': 51, 'nonprose': 14, 'punctuation': 1, 'repetition': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
