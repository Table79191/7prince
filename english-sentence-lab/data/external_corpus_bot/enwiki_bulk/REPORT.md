# SentenceLab enwiki bulk collector

- total accepted local records: 627644
- total pages sampled: 37184
- added this run: 6756
- rejected this run: {'canonical': 1315, 'duplicate': 24, 'word_length': 202, 'parser_integrity': 552, 'char_length': 499, 'punctuation': 16, 'markup': 90, 'nonprose': 41}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
