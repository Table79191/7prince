# SentenceLab enwiki bulk collector

- total accepted local records: 481369
- total pages sampled: 28640
- added this run: 5471
- rejected this run: {'canonical': 1101, 'word_length': 228, 'char_length': 383, 'parser_integrity': 791, 'nonprose': 31, 'markup': 43, 'duplicate': 20, 'punctuation': 3}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
