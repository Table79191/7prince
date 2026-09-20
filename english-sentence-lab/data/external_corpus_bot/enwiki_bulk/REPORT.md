# SentenceLab enwiki bulk collector

- total accepted local records: 533489
- total pages sampled: 31644
- added this run: 4526
- rejected this run: {'canonical': 752, 'parser_integrity': 332, 'char_length': 284, 'nonprose': 14, 'word_length': 111, 'markup': 38, 'duplicate': 77, 'punctuation': 9, 'repetition': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
