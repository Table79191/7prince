# SentenceLab enwiki bulk collector

- total accepted local records: 327571
- total pages sampled: 19769
- added this run: 6502
- rejected this run: {'char_length': 474, 'canonical': 1290, 'parser_integrity': 610, 'word_length': 208, 'markup': 86, 'duplicate': 54, 'nonprose': 29, 'repetition': 1, 'punctuation': 10}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
