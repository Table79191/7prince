# SentenceLab enwiki bulk collector

- total accepted local records: 907644
- total pages sampled: 53196
- added this run: 4413
- rejected this run: {'canonical': 856, 'parser_integrity': 309, 'word_length': 159, 'char_length': 320, 'markup': 58, 'punctuation': 26, 'duplicate': 36, 'nonprose': 7}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
