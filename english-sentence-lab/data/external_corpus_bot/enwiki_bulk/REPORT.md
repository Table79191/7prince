# SentenceLab enwiki bulk collector

- total accepted local records: 495504
- total pages sampled: 29453
- added this run: 6374
- rejected this run: {'duplicate': 19, 'canonical': 1191, 'word_length': 169, 'parser_integrity': 440, 'char_length': 414, 'markup': 72, 'nonprose': 22, 'punctuation': 5}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
