# SentenceLab enwiki bulk collector

- total accepted local records: 817582
- total pages sampled: 48126
- added this run: 5456
- rejected this run: {'parser_integrity': 535, 'char_length': 496, 'word_length': 225, 'canonical': 1082, 'nonprose': 36, 'duplicate': 16, 'markup': 84, 'punctuation': 4}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
