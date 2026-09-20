# SentenceLab enwiki bulk collector

- total accepted local records: 393587
- total pages sampled: 23605
- added this run: 7279
- rejected this run: {'duplicate': 141, 'char_length': 602, 'canonical': 1391, 'word_length': 225, 'parser_integrity': 532, 'markup': 75, 'nonprose': 25, 'punctuation': 7}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
