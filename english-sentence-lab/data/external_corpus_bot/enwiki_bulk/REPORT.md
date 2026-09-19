# SentenceLab enwiki bulk collector

- total accepted local records: 135140
- total pages sampled: 8741
- added this run: 6108
- rejected this run: {'canonical': 1293, 'parser_integrity': 633, 'word_length': 245, 'char_length': 459, 'duplicate': 33, 'markup': 87, 'nonprose': 33, 'punctuation': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
