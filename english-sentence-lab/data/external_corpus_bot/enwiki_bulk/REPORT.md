# SentenceLab enwiki bulk collector

- total accepted local records: 242603
- total pages sampled: 14873
- added this run: 6551
- rejected this run: {'parser_integrity': 584, 'word_length': 240, 'canonical': 1350, 'char_length': 538, 'nonprose': 36, 'duplicate': 19, 'markup': 66, 'repetition': 1, 'punctuation': 3}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
