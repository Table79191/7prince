# SentenceLab enwiki bulk collector

- total accepted local records: 943825
- total pages sampled: 55260
- added this run: 4953
- rejected this run: {'parser_integrity': 398, 'punctuation': 12, 'char_length': 383, 'word_length': 177, 'markup': 76, 'canonical': 928, 'nonprose': 34, 'repetition': 1, 'duplicate': 17}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
