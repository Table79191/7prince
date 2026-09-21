# SentenceLab enwiki bulk collector

- total accepted local records: 679681
- total pages sampled: 40233
- added this run: 4146
- rejected this run: {'canonical': 839, 'char_length': 324, 'word_length': 154, 'parser_integrity': 317, 'markup': 40, 'punctuation': 11, 'duplicate': 7, 'nonprose': 16}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
