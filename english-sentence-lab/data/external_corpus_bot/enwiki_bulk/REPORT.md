# SentenceLab enwiki bulk collector

- total accepted local records: 186186
- total pages sampled: 11592
- added this run: 4567
- rejected this run: {'canonical': 863, 'char_length': 371, 'parser_integrity': 637, 'word_length': 203, 'duplicate': 18, 'markup': 82, 'nonprose': 24, 'punctuation': 9}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
