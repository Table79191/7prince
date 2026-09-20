# SentenceLab enwiki bulk collector

- total accepted local records: 518051
- total pages sampled: 30795
- added this run: 4098
- rejected this run: {'char_length': 336, 'canonical': 807, 'word_length': 144, 'parser_integrity': 334, 'duplicate': 38, 'markup': 38, 'nonprose': 19, 'repetition': 1, 'punctuation': 2}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
