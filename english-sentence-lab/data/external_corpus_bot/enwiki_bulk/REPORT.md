# SentenceLab enwiki bulk collector

- total accepted local records: 305256
- total pages sampled: 18544
- added this run: 3687
- rejected this run: {'char_length': 315, 'parser_integrity': 320, 'word_length': 122, 'canonical': 720, 'markup': 32, 'nonprose': 11, 'duplicate': 24, 'punctuation': 4}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
