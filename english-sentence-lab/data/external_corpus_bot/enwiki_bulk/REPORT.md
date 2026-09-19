# SentenceLab enwiki bulk collector

- total accepted local records: 94220
- total pages sampled: 6246
- added this run: 7050
- rejected this run: {'canonical': 1345, 'char_length': 541, 'parser_integrity': 542, 'word_length': 197, 'duplicate': 24, 'markup': 105, 'punctuation': 24, 'nonprose': 26}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
