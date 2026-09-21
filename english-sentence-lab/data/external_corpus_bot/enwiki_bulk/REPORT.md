# SentenceLab enwiki bulk collector

- total accepted local records: 725841
- total pages sampled: 42869
- added this run: 3968
- rejected this run: {'char_length': 340, 'word_length': 147, 'parser_integrity': 416, 'canonical': 789, 'punctuation': 17, 'duplicate': 10, 'markup': 116, 'nonprose': 22}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
