# SentenceLab enwiki bulk collector

- total accepted local records: 413167
- total pages sampled: 24775
- added this run: 4443
- rejected this run: {'canonical': 775, 'char_length': 345, 'parser_integrity': 363, 'word_length': 156, 'markup': 42, 'nonprose': 24, 'duplicate': 13, 'punctuation': 6}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
