# SentenceLab enwiki bulk collector

- total accepted local records: 417387
- total pages sampled: 25012
- added this run: 4220
- rejected this run: {'canonical': 755, 'char_length': 292, 'parser_integrity': 356, 'word_length': 131, 'duplicate': 21, 'nonprose': 30, 'markup': 46, 'punctuation': 3}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
