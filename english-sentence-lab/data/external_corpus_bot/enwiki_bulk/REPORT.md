# SentenceLab enwiki bulk collector

- total accepted local records: 812126
- total pages sampled: 47739
- added this run: 6578
- rejected this run: {'parser_integrity': 548, 'char_length': 467, 'canonical': 1228, 'word_length': 235, 'duplicate': 19, 'nonprose': 32, 'markup': 113, 'repetition': 1, 'punctuation': 4}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
