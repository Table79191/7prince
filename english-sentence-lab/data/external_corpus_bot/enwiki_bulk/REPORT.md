# SentenceLab enwiki bulk collector

- total accepted local records: 978183
- total pages sampled: 57268
- added this run: 4128
- rejected this run: {'char_length': 303, 'canonical': 789, 'word_length': 163, 'parser_integrity': 334, 'markup': 32, 'duplicate': 12, 'nonprose': 12, 'punctuation': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
