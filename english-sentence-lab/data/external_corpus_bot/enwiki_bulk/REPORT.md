# SentenceLab enwiki bulk collector

- total accepted local records: 274059
- total pages sampled: 16715
- added this run: 6366
- rejected this run: {'parser_integrity': 495, 'char_length': 552, 'word_length': 214, 'canonical': 1264, 'nonprose': 25, 'duplicate': 27, 'repetition': 1, 'markup': 40, 'punctuation': 6}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
