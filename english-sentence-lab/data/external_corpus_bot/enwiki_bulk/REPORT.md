# SentenceLab enwiki bulk collector

- total accepted local records: 934917
- total pages sampled: 54711
- added this run: 4016
- rejected this run: {'char_length': 326, 'canonical': 786, 'duplicate': 11, 'parser_integrity': 368, 'word_length': 139, 'markup': 60, 'nonprose': 18, 'repetition': 1, 'punctuation': 4}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
