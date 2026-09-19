# SentenceLab enwiki bulk collector

- total accepted local records: 98756
- total pages sampled: 6559
- added this run: 4536
- rejected this run: {'canonical': 936, 'parser_integrity': 475, 'char_length': 357, 'word_length': 206, 'duplicate': 17, 'markup': 49, 'nonprose': 30, 'punctuation': 7, 'repetition': 2}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
