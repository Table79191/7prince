# SentenceLab enwiki bulk collector

- total accepted local records: 348135
- total pages sampled: 20996
- added this run: 6454
- rejected this run: {'char_length': 469, 'canonical': 1186, 'parser_integrity': 436, 'word_length': 187, 'markup': 75, 'nonprose': 50, 'duplicate': 14, 'punctuation': 7}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
