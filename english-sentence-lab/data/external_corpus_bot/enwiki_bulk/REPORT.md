# SentenceLab enwiki bulk collector

- total accepted local records: 846306
- total pages sampled: 49696
- added this run: 4923
- rejected this run: {'canonical': 1067, 'word_length': 181, 'parser_integrity': 396, 'markup': 94, 'char_length': 385, 'nonprose': 22, 'duplicate': 388, 'punctuation': 9}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
