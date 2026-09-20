# SentenceLab enwiki bulk collector

- total accepted local records: 510646
- total pages sampled: 30361
- added this run: 6407
- rejected this run: {'canonical': 1170, 'parser_integrity': 813, 'char_length': 564, 'word_length': 287, 'markup': 175, 'nonprose': 73, 'duplicate': 47, 'punctuation': 22}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
