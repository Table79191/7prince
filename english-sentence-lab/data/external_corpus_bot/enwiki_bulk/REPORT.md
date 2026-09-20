# SentenceLab enwiki bulk collector

- total accepted local records: 522208
- total pages sampled: 31006
- added this run: 4157
- rejected this run: {'char_length': 265, 'parser_integrity': 256, 'canonical': 749, 'nonprose': 19, 'duplicate': 17, 'word_length': 107, 'markup': 30, 'punctuation': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
