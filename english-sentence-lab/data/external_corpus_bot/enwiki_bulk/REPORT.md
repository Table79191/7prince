# SentenceLab enwiki bulk collector

- total accepted local records: 528963
- total pages sampled: 31404
- added this run: 3475
- rejected this run: {'canonical': 639, 'word_length': 139, 'duplicate': 11, 'parser_integrity': 309, 'char_length': 277, 'nonprose': 31, 'long_token': 2, 'markup': 35, 'punctuation': 5}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
