# SentenceLab enwiki bulk collector

- total accepted local records: 694833
- total pages sampled: 41095
- added this run: 6120
- rejected this run: {'char_length': 554, 'parser_integrity': 854, 'canonical': 1170, 'word_length': 251, 'repetition': 1, 'duplicate': 18, 'markup': 70, 'nonprose': 23, 'punctuation': 8}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
