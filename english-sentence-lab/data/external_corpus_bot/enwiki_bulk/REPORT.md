# SentenceLab enwiki bulk collector

- total accepted local records: 890849
- total pages sampled: 52218
- added this run: 3946
- rejected this run: {'word_length': 149, 'parser_integrity': 314, 'canonical': 782, 'char_length': 321, 'punctuation': 1, 'duplicate': 13, 'markup': 27, 'nonprose': 18}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
