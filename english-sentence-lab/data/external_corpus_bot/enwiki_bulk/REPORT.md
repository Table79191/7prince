# SentenceLab enwiki bulk collector

- total accepted local records: 386308
- total pages sampled: 23218
- added this run: 4966
- rejected this run: {'canonical': 984, 'char_length': 407, 'parser_integrity': 440, 'nonprose': 19, 'word_length': 154, 'markup': 66, 'punctuation': 11, 'duplicate': 13}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
