# SentenceLab enwiki bulk collector

- total accepted local records: 825828
- total pages sampled: 48609
- added this run: 4682
- rejected this run: {'char_length': 345, 'canonical': 858, 'duplicate': 14, 'parser_integrity': 400, 'word_length': 206, 'markup': 48, 'nonprose': 29, 'punctuation': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
