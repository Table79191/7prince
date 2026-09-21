# SentenceLab enwiki bulk collector

- total accepted local records: 635613
- total pages sampled: 37691
- added this run: 4199
- rejected this run: {'canonical': 767, 'markup': 76, 'parser_integrity': 427, 'char_length': 381, 'word_length': 156, 'duplicate': 26, 'nonprose': 39, 'punctuation': 13, 'long_token': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
