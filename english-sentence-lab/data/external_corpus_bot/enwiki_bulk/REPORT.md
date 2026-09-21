# SentenceLab enwiki bulk collector

- total accepted local records: 661596
- total pages sampled: 39205
- added this run: 4907
- rejected this run: {'canonical': 1026, 'char_length': 335, 'parser_integrity': 309, 'word_length': 144, 'nonprose': 11, 'markup': 45, 'duplicate': 18, 'punctuation': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
