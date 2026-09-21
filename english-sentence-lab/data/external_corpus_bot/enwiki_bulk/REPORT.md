# SentenceLab enwiki bulk collector

- total accepted local records: 600726
- total pages sampled: 35563
- added this run: 3394
- rejected this run: {'canonical': 702, 'char_length': 227, 'markup': 54, 'parser_integrity': 246, 'word_length': 120, 'nonprose': 10, 'duplicate': 10, 'punctuation': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
