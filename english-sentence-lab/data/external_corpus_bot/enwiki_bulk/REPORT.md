# SentenceLab enwiki bulk collector

- total accepted local records: 8917
- total pages sampled: 1285
- added this run: 3722
- rejected this run: {'canonical': 734, 'word_length': 162, 'parser_integrity': 315, 'char_length': 285, 'nonprose': 23, 'markup': 52, 'duplicate': 12, 'punctuation': 6}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
