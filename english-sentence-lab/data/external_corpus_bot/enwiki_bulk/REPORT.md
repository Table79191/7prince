# SentenceLab enwiki bulk collector

- total accepted local records: 740808
- total pages sampled: 43811
- added this run: 3750
- rejected this run: {'canonical': 831, 'char_length': 324, 'word_length': 157, 'parser_integrity': 406, 'duplicate': 16, 'markup': 76, 'nonprose': 19, 'punctuation': 6}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
