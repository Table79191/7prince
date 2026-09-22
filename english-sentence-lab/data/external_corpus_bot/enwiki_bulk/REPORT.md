# SentenceLab enwiki bulk collector

- total accepted local records: 870412
- total pages sampled: 51067
- added this run: 4177
- rejected this run: {'canonical': 802, 'parser_integrity': 382, 'char_length': 345, 'word_length': 167, 'duplicate': 16, 'markup': 70, 'nonprose': 29, 'punctuation': 9}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
