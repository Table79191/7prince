# SentenceLab enwiki bulk collector

- total accepted local records: 764382
- total pages sampled: 45081
- added this run: 4404
- rejected this run: {'canonical': 762, 'char_length': 384, 'parser_integrity': 429, 'markup': 84, 'nonprose': 31, 'word_length': 144, 'duplicate': 28, 'punctuation': 15}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
