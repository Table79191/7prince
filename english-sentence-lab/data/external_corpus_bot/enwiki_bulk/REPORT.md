# SentenceLab enwiki bulk collector

- total accepted local records: 756061
- total pages sampled: 44580
- added this run: 4282
- rejected this run: {'parser_integrity': 316, 'char_length': 443, 'duplicate': 14, 'canonical': 802, 'word_length': 153, 'nonprose': 42, 'punctuation': 21, 'markup': 71}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
