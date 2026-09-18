# SentenceLab enwiki bulk collector

- total accepted local records: 5195
- total pages sampled: 1033
- added this run: 5195
- rejected this run: {'word_length': 863, 'char_length': 1685, 'canonical': 1171, 'parser_integrity': 979, 'markup': 180, 'nonprose': 57, 'duplicate': 25, 'punctuation': 54, 'long_token': 2}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
