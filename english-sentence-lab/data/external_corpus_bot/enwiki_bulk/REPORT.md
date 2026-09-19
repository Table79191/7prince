# SentenceLab enwiki bulk collector

- total accepted local records: 221691
- total pages sampled: 13709
- added this run: 4150
- rejected this run: {'char_length': 351, 'canonical': 886, 'word_length': 139, 'parser_integrity': 294, 'punctuation': 8, 'duplicate': 47, 'markup': 41, 'nonprose': 25, 'repetition': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
