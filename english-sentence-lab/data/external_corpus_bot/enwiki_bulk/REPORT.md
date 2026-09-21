# SentenceLab enwiki bulk collector

- total accepted local records: 683900
- total pages sampled: 40508
- added this run: 4219
- rejected this run: {'char_length': 306, 'canonical': 799, 'duplicate': 14, 'parser_integrity': 321, 'word_length': 115, 'markup': 34, 'nonprose': 12, 'punctuation': 3}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
