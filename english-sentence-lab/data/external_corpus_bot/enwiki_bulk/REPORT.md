# SentenceLab enwiki bulk collector

- total accepted local records: 293441
- total pages sampled: 17807
- added this run: 5872
- rejected this run: {'canonical': 1218, 'parser_integrity': 600, 'word_length': 267, 'char_length': 535, 'markup': 121, 'nonprose': 19, 'duplicate': 20, 'punctuation': 3, 'repetition': 3}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
