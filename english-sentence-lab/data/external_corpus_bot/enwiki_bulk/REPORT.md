# SentenceLab enwiki bulk collector

- total accepted local records: 278519
- total pages sampled: 16933
- added this run: 4460
- rejected this run: {'char_length': 294, 'parser_integrity': 371, 'canonical': 887, 'word_length': 137, 'duplicate': 6, 'punctuation': 7, 'markup': 69, 'nonprose': 23}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
