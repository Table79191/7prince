# SentenceLab enwiki bulk collector

- total accepted local records: 793260
- total pages sampled: 46683
- added this run: 7291
- rejected this run: {'canonical': 1338, 'parser_integrity': 541, 'char_length': 566, 'word_length': 237, 'nonprose': 35, 'markup': 53, 'duplicate': 31, 'punctuation': 6, 'repetition': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
