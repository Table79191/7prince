# SentenceLab enwiki bulk collector

- total accepted local records: 894682
- total pages sampled: 52447
- added this run: 3833
- rejected this run: {'char_length': 303, 'canonical': 721, 'word_length': 119, 'parser_integrity': 379, 'duplicate': 10, 'nonprose': 21, 'markup': 41, 'punctuation': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
