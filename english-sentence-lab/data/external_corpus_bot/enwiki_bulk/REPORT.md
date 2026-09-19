# SentenceLab enwiki bulk collector

- total accepted local records: 68476
- total pages sampled: 4755
- added this run: 3681
- rejected this run: {'canonical': 705, 'parser_integrity': 351, 'word_length': 150, 'punctuation': 3, 'char_length': 294, 'duplicate': 6, 'nonprose': 15, 'markup': 56}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
