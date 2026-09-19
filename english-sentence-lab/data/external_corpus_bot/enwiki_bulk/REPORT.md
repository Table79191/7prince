# SentenceLab enwiki bulk collector

- total accepted local records: 301569
- total pages sampled: 18276
- added this run: 3992
- rejected this run: {'canonical': 755, 'parser_integrity': 511, 'char_length': 438, 'word_length': 193, 'duplicate': 12, 'markup': 51, 'nonprose': 27, 'punctuation': 9, 'repetition': 12}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
