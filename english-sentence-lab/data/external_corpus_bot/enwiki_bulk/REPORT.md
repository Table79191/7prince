# SentenceLab enwiki bulk collector

- total accepted local records: 56350
- total pages sampled: 4005
- added this run: 6024
- rejected this run: {'char_length': 527, 'canonical': 1164, 'word_length': 218, 'parser_integrity': 594, 'markup': 74, 'nonprose': 41, 'duplicate': 31, 'punctuation': 4}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
