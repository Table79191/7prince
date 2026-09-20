# SentenceLab enwiki bulk collector

- total accepted local records: 352334
- total pages sampled: 21228
- added this run: 4199
- rejected this run: {'char_length': 282, 'canonical': 786, 'parser_integrity': 287, 'word_length': 125, 'markup': 38, 'duplicate': 15, 'nonprose': 12}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
