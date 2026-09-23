# SentenceLab enwiki bulk collector

- total accepted local records: 930901
- total pages sampled: 54457
- added this run: 4232
- rejected this run: {'char_length': 333, 'canonical': 801, 'parser_integrity': 313, 'word_length': 140, 'markup': 95, 'nonprose': 18, 'punctuation': 6, 'duplicate': 24}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
