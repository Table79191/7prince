# SentenceLab enwiki bulk collector

- total accepted local records: 337736
- total pages sampled: 20393
- added this run: 5888
- rejected this run: {'parser_integrity': 396, 'word_length': 188, 'canonical': 1077, 'char_length': 476, 'markup': 62, 'punctuation': 5, 'repetition': 8, 'nonprose': 34, 'duplicate': 31}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
