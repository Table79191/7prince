# SentenceLab enwiki bulk collector

- total accepted local records: 801691
- total pages sampled: 47156
- added this run: 4184
- rejected this run: {'canonical': 890, 'word_length': 139, 'parser_integrity': 325, 'char_length': 280, 'markup': 71, 'nonprose': 24, 'duplicate': 24, 'punctuation': 2}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
