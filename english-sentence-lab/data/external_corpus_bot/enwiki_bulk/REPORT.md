# SentenceLab enwiki bulk collector

- total accepted local records: 1024228
- total pages sampled: 59991
- added this run: 6758
- rejected this run: {'canonical': 1210, 'parser_integrity': 637, 'word_length': 244, 'char_length': 545, 'markup': 161, 'nonprose': 36, 'duplicate': 16, 'punctuation': 18}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
