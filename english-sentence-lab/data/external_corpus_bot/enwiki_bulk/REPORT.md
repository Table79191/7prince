# SentenceLab enwiki bulk collector

- total accepted local records: 745086
- total pages sampled: 44019
- added this run: 4278
- rejected this run: {'canonical': 829, 'parser_integrity': 338, 'char_length': 305, 'nonprose': 17, 'word_length': 139, 'duplicate': 10, 'markup': 66, 'punctuation': 2}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
