# SentenceLab enwiki bulk collector

- total accepted local records: 14447
- total pages sampled: 1580
- added this run: 5530
- rejected this run: {'word_length': 154, 'parser_integrity': 365, 'canonical': 957, 'duplicate': 8, 'char_length': 386, 'nonprose': 7, 'markup': 72, 'punctuation': 5}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
