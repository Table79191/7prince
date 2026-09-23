# SentenceLab enwiki bulk collector

- total accepted local records: 926669
- total pages sampled: 54245
- added this run: 4185
- rejected this run: {'canonical': 831, 'char_length': 449, 'nonprose': 20, 'duplicate': 49, 'word_length': 223, 'parser_integrity': 491, 'markup': 54, 'punctuation': 17}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
