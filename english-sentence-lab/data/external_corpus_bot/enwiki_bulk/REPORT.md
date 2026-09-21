# SentenceLab enwiki bulk collector

- total accepted local records: 721873
- total pages sampled: 42654
- added this run: 3937
- rejected this run: {'canonical': 781, 'word_length': 140, 'char_length': 310, 'parser_integrity': 372, 'nonprose': 27, 'duplicate': 23, 'markup': 39, 'punctuation': 3}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
