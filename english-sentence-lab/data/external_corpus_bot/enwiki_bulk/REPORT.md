# SentenceLab enwiki bulk collector

- total accepted local records: 675535
- total pages sampled: 39985
- added this run: 6268
- rejected this run: {'canonical': 1193, 'word_length': 223, 'parser_integrity': 496, 'char_length': 491, 'markup': 94, 'nonprose': 37, 'duplicate': 13, 'punctuation': 7}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
