# SentenceLab enwiki bulk collector

- total accepted local records: 363827
- total pages sampled: 21956
- added this run: 6881
- rejected this run: {'canonical': 1290, 'char_length': 600, 'parser_integrity': 604, 'word_length': 244, 'markup': 165, 'duplicate': 47, 'nonprose': 42, 'punctuation': 8, 'repetition': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
