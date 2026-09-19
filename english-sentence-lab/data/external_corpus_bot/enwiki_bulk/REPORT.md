# SentenceLab enwiki bulk collector

- total accepted local records: 79759
- total pages sampled: 5402
- added this run: 7452
- rejected this run: {'canonical': 1409, 'word_length': 209, 'parser_integrity': 503, 'char_length': 548, 'markup': 90, 'nonprose': 30, 'duplicate': 35, 'repetition': 2, 'punctuation': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
