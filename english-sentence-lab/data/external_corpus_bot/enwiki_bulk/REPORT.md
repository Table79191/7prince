# SentenceLab enwiki bulk collector

- total accepted local records: 439937
- total pages sampled: 26328
- added this run: 6094
- rejected this run: {'char_length': 480, 'canonical': 1146, 'parser_integrity': 519, 'word_length': 220, 'markup': 115, 'punctuation': 19, 'duplicate': 31, 'nonprose': 37}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
