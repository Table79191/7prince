# SentenceLab enwiki bulk collector

- total accepted local records: 309468
- total pages sampled: 18790
- added this run: 4212
- rejected this run: {'duplicate': 11, 'char_length': 298, 'canonical': 770, 'word_length': 128, 'parser_integrity': 400, 'markup': 72, 'nonprose': 27, 'punctuation': 16}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
