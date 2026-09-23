# SentenceLab enwiki bulk collector

- total accepted local records: 952027
- total pages sampled: 55760
- added this run: 4485
- rejected this run: {'canonical': 876, 'char_length': 330, 'parser_integrity': 313, 'duplicate': 13, 'word_length': 162, 'nonprose': 24, 'markup': 63, 'punctuation': 9}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
