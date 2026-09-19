# SentenceLab enwiki bulk collector

- total accepted local records: 181619
- total pages sampled: 11319
- added this run: 5193
- rejected this run: {'word_length': 203, 'canonical': 901, 'char_length': 367, 'parser_integrity': 507, 'repetition': 1, 'punctuation': 4, 'markup': 46, 'nonprose': 15, 'duplicate': 22}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
