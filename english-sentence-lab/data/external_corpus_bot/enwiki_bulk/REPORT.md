# SentenceLab enwiki bulk collector

- total accepted local records: 226734
- total pages sampled: 14046
- added this run: 5043
- rejected this run: {'char_length': 419, 'canonical': 865, 'parser_integrity': 461, 'nonprose': 24, 'word_length': 158, 'markup': 60, 'punctuation': 11, 'duplicate': 15}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
