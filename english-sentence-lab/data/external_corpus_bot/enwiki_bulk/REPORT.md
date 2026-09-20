# SentenceLab enwiki bulk collector

- total accepted local records: 485600
- total pages sampled: 28877
- added this run: 4231
- rejected this run: {'char_length': 299, 'parser_integrity': 299, 'canonical': 826, 'nonprose': 23, 'word_length': 142, 'duplicate': 16, 'markup': 86, 'punctuation': 17}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
