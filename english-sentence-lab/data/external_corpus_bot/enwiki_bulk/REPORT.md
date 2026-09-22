# SentenceLab enwiki bulk collector

- total accepted local records: 805548
- total pages sampled: 47361
- added this run: 3857
- rejected this run: {'word_length': 117, 'nonprose': 16, 'parser_integrity': 326, 'canonical': 704, 'char_length': 271, 'duplicate': 11, 'markup': 27, 'repetition': 2, 'punctuation': 2}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
