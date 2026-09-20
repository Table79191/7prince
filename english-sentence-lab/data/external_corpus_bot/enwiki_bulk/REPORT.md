# SentenceLab enwiki bulk collector

- total accepted local records: 450826
- total pages sampled: 26858
- added this run: 6400
- rejected this run: {'word_length': 220, 'canonical': 1279, 'parser_integrity': 483, 'char_length': 543, 'markup': 100, 'nonprose': 28, 'duplicate': 57, 'punctuation': 4, 'repetition': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
