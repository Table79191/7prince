# SentenceLab enwiki bulk collector

- total accepted local records: 874502
- total pages sampled: 51308
- added this run: 4090
- rejected this run: {'canonical': 844, 'word_length': 142, 'parser_integrity': 328, 'char_length': 347, 'markup': 39, 'duplicate': 20, 'punctuation': 1, 'nonprose': 20}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
