# SentenceLab enwiki bulk collector

- total accepted local records: 650436
- total pages sampled: 38587
- added this run: 3824
- rejected this run: {'char_length': 320, 'canonical': 840, 'word_length': 158, 'parser_integrity': 315, 'nonprose': 25, 'duplicate': 37, 'markup': 85, 'punctuation': 75}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
