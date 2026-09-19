# SentenceLab enwiki bulk collector

- total accepted local records: 139477
- total pages sampled: 8967
- added this run: 4337
- rejected this run: {'canonical': 807, 'parser_integrity': 574, 'char_length': 309, 'word_length': 168, 'markup': 68, 'nonprose': 37, 'punctuation': 11, 'duplicate': 7}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
