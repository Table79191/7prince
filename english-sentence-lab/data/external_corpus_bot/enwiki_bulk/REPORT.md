# SentenceLab enwiki bulk collector

- total accepted local records: 29238
- total pages sampled: 2377
- added this run: 4320
- rejected this run: {'char_length': 387, 'canonical': 823, 'parser_integrity': 397, 'word_length': 148, 'markup': 49, 'nonprose': 23, 'repetition': 1, 'duplicate': 13, 'punctuation': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
