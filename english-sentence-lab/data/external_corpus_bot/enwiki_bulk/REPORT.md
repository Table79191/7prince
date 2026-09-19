# SentenceLab enwiki bulk collector

- total accepted local records: 264372
- total pages sampled: 16162
- added this run: 6721
- rejected this run: {'canonical': 1312, 'parser_integrity': 782, 'char_length': 551, 'word_length': 305, 'nonprose': 56, 'markup': 106, 'duplicate': 22, 'repetition': 1, 'punctuation': 4}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
