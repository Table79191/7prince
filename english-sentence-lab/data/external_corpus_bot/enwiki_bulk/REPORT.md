# SentenceLab enwiki bulk collector

- total accepted local records: 922484
- total pages sampled: 54006
- added this run: 3901
- rejected this run: {'canonical': 751, 'char_length': 328, 'parser_integrity': 358, 'word_length': 128, 'markup': 27, 'nonprose': 12, 'duplicate': 13, 'punctuation': 4}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
