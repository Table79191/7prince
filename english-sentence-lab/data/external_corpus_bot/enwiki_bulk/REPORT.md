# SentenceLab enwiki bulk collector

- total accepted local records: 172112
- total pages sampled: 10817
- added this run: 4979
- rejected this run: {'word_length': 187, 'char_length': 445, 'parser_integrity': 435, 'canonical': 865, 'nonprose': 29, 'markup': 70, 'duplicate': 15, 'punctuation': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
