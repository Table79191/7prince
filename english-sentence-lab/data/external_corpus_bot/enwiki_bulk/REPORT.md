# SentenceLab enwiki bulk collector

- total accepted local records: 833707
- total pages sampled: 49029
- added this run: 4098
- rejected this run: {'canonical': 756, 'char_length': 347, 'parser_integrity': 308, 'word_length': 154, 'markup': 62, 'nonprose': 36, 'duplicate': 22, 'punctuation': 23}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
