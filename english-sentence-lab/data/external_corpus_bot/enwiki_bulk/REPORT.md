# SentenceLab enwiki bulk collector

- total accepted local records: 121822
- total pages sampled: 7960
- added this run: 4024
- rejected this run: {'canonical': 727, 'word_length': 107, 'parser_integrity': 307, 'char_length': 294, 'markup': 45, 'duplicate': 18, 'nonprose': 12}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
