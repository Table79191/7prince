# SentenceLab enwiki bulk collector

- total accepted local records: 562325
- total pages sampled: 33279
- added this run: 4497
- rejected this run: {'char_length': 495, 'canonical': 888, 'word_length': 180, 'parser_integrity': 350, 'nonprose': 39, 'markup': 49, 'duplicate': 17, 'punctuation': 10}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
