# SentenceLab enwiki bulk collector

- total accepted local records: 40176
- total pages sampled: 2998
- added this run: 4254
- rejected this run: {'canonical': 702, 'char_length': 344, 'parser_integrity': 388, 'word_length': 158, 'duplicate': 11, 'markup': 36, 'nonprose': 13, 'punctuation': 5, 'page_duplicate': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
