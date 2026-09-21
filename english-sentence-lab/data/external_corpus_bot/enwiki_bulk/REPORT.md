# SentenceLab enwiki bulk collector

- total accepted local records: 578621
- total pages sampled: 34305
- added this run: 5454
- rejected this run: {'canonical': 1021, 'char_length': 383, 'nonprose': 51, 'word_length': 185, 'markup': 58, 'parser_integrity': 574, 'duplicate': 12, 'punctuation': 15}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
