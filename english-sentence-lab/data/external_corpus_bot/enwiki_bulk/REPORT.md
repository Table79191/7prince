# SentenceLab enwiki bulk collector

- total accepted local records: 475898
- total pages sampled: 28394
- added this run: 3980
- rejected this run: {'canonical': 767, 'char_length': 379, 'word_length': 152, 'parser_integrity': 488, 'markup': 42, 'nonprose': 28, 'punctuation': 9, 'duplicate': 7, 'repetition': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
