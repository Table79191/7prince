# SentenceLab enwiki bulk collector

- total accepted local records: 321069
- total pages sampled: 19457
- added this run: 7463
- rejected this run: {'canonical': 1389, 'char_length': 598, 'parser_integrity': 612, 'word_length': 237, 'markup': 78, 'duplicate': 33, 'nonprose': 60, 'punctuation': 3, 'long_token': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
