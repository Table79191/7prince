# SentenceLab enwiki bulk collector

- total accepted local records: 113039
- total pages sampled: 7412
- added this run: 6426
- rejected this run: {'canonical': 1200, 'parser_integrity': 616, 'char_length': 623, 'word_length': 305, 'duplicate': 20, 'markup': 191, 'nonprose': 45, 'punctuation': 34}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
