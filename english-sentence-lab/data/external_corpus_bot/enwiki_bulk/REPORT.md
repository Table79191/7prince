# SentenceLab enwiki bulk collector

- total accepted local records: 367810
- total pages sampled: 22149
- added this run: 3983
- rejected this run: {'char_length': 460, 'canonical': 849, 'duplicate': 10, 'word_length': 246, 'parser_integrity': 435, 'nonprose': 49, 'markup': 66, 'punctuation': 5}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
