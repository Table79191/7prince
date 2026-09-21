# SentenceLab enwiki bulk collector

- total accepted local records: 584899
- total pages sampled: 34645
- added this run: 6278
- rejected this run: {'canonical': 1211, 'parser_integrity': 553, 'char_length': 518, 'word_length': 262, 'markup': 79, 'duplicate': 38, 'nonprose': 15, 'punctuation': 9, 'repetition': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
