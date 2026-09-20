# SentenceLab enwiki bulk collector

- total accepted local records: 550061
- total pages sampled: 32570
- added this run: 5985
- rejected this run: {'canonical': 1169, 'char_length': 523, 'parser_integrity': 521, 'markup': 93, 'word_length': 243, 'duplicate': 31, 'nonprose': 37, 'punctuation': 14, 'repetition': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
