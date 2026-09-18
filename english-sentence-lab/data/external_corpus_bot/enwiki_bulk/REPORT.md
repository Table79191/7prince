# SentenceLab enwiki bulk collector

- total accepted local records: 64795
- total pages sampled: 4533
- added this run: 4321
- rejected this run: {'canonical': 803, 'char_length': 322, 'parser_integrity': 353, 'word_length': 150, 'markup': 49, 'duplicate': 7, 'nonprose': 18, 'punctuation': 5}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
