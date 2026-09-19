# SentenceLab enwiki bulk collector

- total accepted local records: 103543
- total pages sampled: 6813
- added this run: 4787
- rejected this run: {'canonical': 918, 'parser_integrity': 437, 'word_length': 166, 'char_length': 340, 'markup': 65, 'nonprose': 27, 'duplicate': 17, 'punctuation': 2}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
