# SentenceLab enwiki bulk collector

- total accepted local records: 381342
- total pages sampled: 22920
- added this run: 6655
- rejected this run: {'duplicate': 24, 'parser_integrity': 508, 'canonical': 1153, 'char_length': 571, 'word_length': 259, 'markup': 118, 'nonprose': 40, 'punctuation': 2}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
