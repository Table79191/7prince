# SentenceLab enwiki bulk collector

- total accepted local records: 398007
- total pages sampled: 23879
- added this run: 4420
- rejected this run: {'canonical': 787, 'word_length': 170, 'parser_integrity': 412, 'char_length': 333, 'duplicate': 62, 'nonprose': 29, 'markup': 54, 'punctuation': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
