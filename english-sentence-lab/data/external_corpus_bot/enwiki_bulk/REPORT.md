# SentenceLab enwiki bulk collector

- total accepted local records: 433843
- total pages sampled: 25950
- added this run: 4358
- rejected this run: {'char_length': 322, 'canonical': 845, 'word_length': 182, 'parser_integrity': 361, 'markup': 39, 'nonprose': 25, 'duplicate': 17}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
