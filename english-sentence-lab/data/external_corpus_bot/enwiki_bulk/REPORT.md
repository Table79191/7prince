# SentenceLab enwiki bulk collector

- total accepted local records: 544076
- total pages sampled: 32200
- added this run: 4810
- rejected this run: {'canonical': 845, 'char_length': 331, 'parser_integrity': 373, 'duplicate': 34, 'word_length': 161, 'markup': 50, 'nonprose': 16, 'punctuation': 6}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
