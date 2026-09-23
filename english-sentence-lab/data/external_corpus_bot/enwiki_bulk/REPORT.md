# SentenceLab enwiki bulk collector

- total accepted local records: 903231
- total pages sampled: 52988
- added this run: 4352
- rejected this run: {'char_length': 364, 'parser_integrity': 402, 'duplicate': 19, 'word_length': 161, 'canonical': 835, 'nonprose': 20, 'markup': 54, 'punctuation': 7}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
