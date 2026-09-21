# SentenceLab enwiki bulk collector

- total accepted local records: 617734
- total pages sampled: 36583
- added this run: 6126
- rejected this run: {'parser_integrity': 607, 'char_length': 630, 'canonical': 1327, 'word_length': 205, 'markup': 71, 'nonprose': 51, 'duplicate': 13, 'punctuation': 10}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
