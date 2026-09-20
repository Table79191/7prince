# SentenceLab enwiki bulk collector

- total accepted local records: 525488
- total pages sampled: 31215
- added this run: 3280
- rejected this run: {'duplicate': 10, 'canonical': 661, 'char_length': 325, 'word_length': 133, 'parser_integrity': 363, 'markup': 51, 'nonprose': 25, 'punctuation': 4}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
