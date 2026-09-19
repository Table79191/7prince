# SentenceLab enwiki bulk collector

- total accepted local records: 313606
- total pages sampled: 19036
- added this run: 4138
- rejected this run: {'canonical': 759, 'parser_integrity': 395, 'char_length': 341, 'word_length': 135, 'nonprose': 17, 'markup': 59, 'duplicate': 13, 'repetition': 1, 'punctuation': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
