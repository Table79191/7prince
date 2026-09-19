# SentenceLab enwiki bulk collector

- total accepted local records: 257651
- total pages sampled: 15792
- added this run: 3954
- rejected this run: {'canonical': 725, 'char_length': 309, 'parser_integrity': 368, 'nonprose': 35, 'word_length': 159, 'duplicate': 16, 'markup': 51, 'punctuation': 4}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
