# SentenceLab enwiki bulk collector

- total accepted local records: 72307
- total pages sampled: 5025
- added this run: 3831
- rejected this run: {'canonical': 742, 'char_length': 307, 'parser_integrity': 360, 'word_length': 155, 'markup': 41, 'nonprose': 19, 'duplicate': 4, 'punctuation': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
