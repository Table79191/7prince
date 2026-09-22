# SentenceLab enwiki bulk collector

- total accepted local records: 782453
- total pages sampled: 46106
- added this run: 4031
- rejected this run: {'parser_integrity': 277, 'canonical': 774, 'char_length': 319, 'word_length': 143, 'nonprose': 18, 'punctuation': 4, 'markup': 56, 'duplicate': 10}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
