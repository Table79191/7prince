# SentenceLab enwiki bulk collector

- total accepted local records: 960981
- total pages sampled: 56297
- added this run: 5028
- rejected this run: {'parser_integrity': 275, 'markup': 61, 'canonical': 945, 'char_length': 328, 'word_length': 127, 'punctuation': 3, 'nonprose': 8, 'duplicate': 15, 'repetition': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
