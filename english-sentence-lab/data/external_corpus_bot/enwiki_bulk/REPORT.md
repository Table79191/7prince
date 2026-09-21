# SentenceLab enwiki bulk collector

- total accepted local records: 611608
- total pages sampled: 36218
- added this run: 6639
- rejected this run: {'canonical': 1271, 'parser_integrity': 543, 'char_length': 616, 'markup': 76, 'word_length': 221, 'nonprose': 20, 'duplicate': 15, 'punctuation': 14}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
