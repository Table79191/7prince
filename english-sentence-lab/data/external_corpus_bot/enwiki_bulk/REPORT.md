# SentenceLab enwiki bulk collector

- total accepted local records: 194816
- total pages sampled: 12080
- added this run: 3717
- rejected this run: {'char_length': 311, 'canonical': 690, 'parser_integrity': 364, 'word_length': 118, 'markup': 54, 'nonprose': 19, 'duplicate': 11, 'punctuation': 2}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
