# SentenceLab enwiki bulk collector

- total accepted local records: 421000
- total pages sampled: 25250
- added this run: 3613
- rejected this run: {'parser_integrity': 276, 'char_length': 270, 'canonical': 664, 'word_length': 101, 'markup': 61, 'duplicate': 10, 'nonprose': 11, 'punctuation': 9}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
