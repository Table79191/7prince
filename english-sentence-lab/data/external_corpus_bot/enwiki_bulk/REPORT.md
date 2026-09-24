# SentenceLab enwiki bulk collector

- total accepted local records: 983104
- total pages sampled: 57565
- added this run: 4921
- rejected this run: {'canonical': 867, 'parser_integrity': 424, 'word_length': 197, 'nonprose': 29, 'char_length': 399, 'markup': 133, 'duplicate': 27, 'punctuation': 11, 'repetition': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
