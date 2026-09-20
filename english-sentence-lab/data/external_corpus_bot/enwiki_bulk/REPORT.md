# SentenceLab enwiki bulk collector

- total accepted local records: 429485
- total pages sampled: 25740
- added this run: 4496
- rejected this run: {'canonical': 753, 'char_length': 396, 'parser_integrity': 320, 'word_length': 152, 'duplicate': 15, 'nonprose': 28, 'markup': 104, 'punctuation': 11}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
