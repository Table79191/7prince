# SentenceLab enwiki bulk collector

- total accepted local records: 129032
- total pages sampled: 8352
- added this run: 7210
- rejected this run: {'canonical': 1345, 'word_length': 197, 'char_length': 565, 'parser_integrity': 574, 'markup': 79, 'nonprose': 32, 'duplicate': 22, 'punctuation': 4}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
