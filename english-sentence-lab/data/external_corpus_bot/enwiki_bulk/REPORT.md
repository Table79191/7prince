# SentenceLab enwiki bulk collector

- total accepted local records: 785969
- total pages sampled: 46329
- added this run: 3516
- rejected this run: {'canonical': 699, 'parser_integrity': 535, 'char_length': 371, 'word_length': 156, 'markup': 48, 'nonprose': 53, 'punctuation': 10, 'duplicate': 7}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
