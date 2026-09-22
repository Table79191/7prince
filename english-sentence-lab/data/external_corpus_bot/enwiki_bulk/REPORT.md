# SentenceLab enwiki bulk collector

- total accepted local records: 821146
- total pages sampled: 48376
- added this run: 3564
- rejected this run: {'canonical': 739, 'parser_integrity': 1813, 'char_length': 324, 'nonprose': 21, 'word_length': 182, 'markup': 33, 'duplicate': 10}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
