# SentenceLab enwiki bulk collector

- total accepted local records: 32872
- total pages sampled: 2584
- added this run: 3634
- rejected this run: {'char_length': 335, 'canonical': 774, 'parser_integrity': 407, 'markup': 40, 'word_length': 120, 'nonprose': 23, 'duplicate': 19, 'punctuation': 5}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
