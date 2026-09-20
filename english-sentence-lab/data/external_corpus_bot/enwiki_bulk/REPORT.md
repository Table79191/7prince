# SentenceLab enwiki bulk collector

- total accepted local records: 458878
- total pages sampled: 27394
- added this run: 4003
- rejected this run: {'word_length': 146, 'canonical': 811, 'char_length': 315, 'parser_integrity': 328, 'duplicate': 19, 'nonprose': 26, 'markup': 63, 'punctuation': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
