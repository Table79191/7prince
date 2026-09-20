# SentenceLab enwiki bulk collector

- total accepted local records: 408724
- total pages sampled: 24502
- added this run: 4952
- rejected this run: {'char_length': 363, 'canonical': 804, 'parser_integrity': 454, 'word_length': 139, 'markup': 65, 'duplicate': 21, 'nonprose': 21, 'repetition': 1, 'punctuation': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
