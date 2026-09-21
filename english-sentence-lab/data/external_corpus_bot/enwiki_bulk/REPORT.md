# SentenceLab enwiki bulk collector

- total accepted local records: 604969
- total pages sampled: 35808
- added this run: 4243
- rejected this run: {'canonical': 814, 'char_length': 334, 'parser_integrity': 355, 'word_length': 152, 'markup': 47, 'duplicate': 46, 'nonprose': 9, 'long_token': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
