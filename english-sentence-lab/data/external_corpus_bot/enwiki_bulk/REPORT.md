# SentenceLab enwiki bulk collector

- total accepted local records: 863037
- total pages sampled: 50655
- added this run: 5412
- rejected this run: {'canonical': 981, 'parser_integrity': 522, 'char_length': 477, 'nonprose': 24, 'word_length': 241, 'markup': 77, 'punctuation': 34, 'duplicate': 11}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
