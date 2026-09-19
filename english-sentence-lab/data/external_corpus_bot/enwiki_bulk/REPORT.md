# SentenceLab enwiki bulk collector

- total accepted local records: 160272
- total pages sampled: 10166
- added this run: 7011
- rejected this run: {'char_length': 715, 'parser_integrity': 648, 'canonical': 1363, 'word_length': 312, 'markup': 117, 'nonprose': 35, 'duplicate': 35, 'punctuation': 9}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
