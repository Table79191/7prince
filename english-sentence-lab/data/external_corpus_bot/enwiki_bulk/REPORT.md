# SentenceLab enwiki bulk collector

- total accepted local records: 153261
- total pages sampled: 9762
- added this run: 4074
- rejected this run: {'canonical': 848, 'char_length': 312, 'parser_integrity': 405, 'markup': 36, 'word_length': 173, 'nonprose': 21, 'duplicate': 84, 'punctuation': 8}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
