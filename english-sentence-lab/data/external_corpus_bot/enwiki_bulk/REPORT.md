# SentenceLab enwiki bulk collector

- total accepted local records: 774517
- total pages sampled: 45655
- added this run: 3450
- rejected this run: {'canonical': 728, 'char_length': 306, 'parser_integrity': 374, 'nonprose': 31, 'word_length': 135, 'markup': 42, 'duplicate': 11, 'punctuation': 3, 'long_token': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
