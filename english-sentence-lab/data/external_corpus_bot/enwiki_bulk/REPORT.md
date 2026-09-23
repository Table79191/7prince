# SentenceLab enwiki bulk collector

- total accepted local records: 969563
- total pages sampled: 56781
- added this run: 4268
- rejected this run: {'char_length': 344, 'canonical': 798, 'parser_integrity': 412, 'word_length': 157, 'markup': 55, 'punctuation': 3, 'nonprose': 21, 'duplicate': 14}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
