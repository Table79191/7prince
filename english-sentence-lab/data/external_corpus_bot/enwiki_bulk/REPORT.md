# SentenceLab enwiki bulk collector

- total accepted local records: 46992
- total pages sampled: 3438
- added this run: 6816
- rejected this run: {'parser_integrity': 1226, 'canonical': 1275, 'char_length': 916, 'word_length': 385, 'markup': 57, 'punctuation': 67, 'nonprose': 155, 'duplicate': 26}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
