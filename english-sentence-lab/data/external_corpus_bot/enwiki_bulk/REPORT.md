# SentenceLab enwiki bulk collector

- total accepted local records: 688713
- total pages sampled: 40703
- added this run: 4813
- rejected this run: {'char_length': 401, 'canonical': 866, 'parser_integrity': 387, 'markup': 30, 'word_length': 293, 'nonprose': 20, 'duplicate': 18, 'punctuation': 6}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
