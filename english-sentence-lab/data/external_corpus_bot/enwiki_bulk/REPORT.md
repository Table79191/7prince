# SentenceLab enwiki bulk collector

- total accepted local records: 208974
- total pages sampled: 12959
- added this run: 6539
- rejected this run: {'word_length': 153, 'char_length': 465, 'canonical': 1291, 'punctuation': 8, 'parser_integrity': 444, 'duplicate': 17, 'markup': 77, 'nonprose': 29}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
