# SentenceLab enwiki bulk collector

- total accepted local records: 850499
- total pages sampled: 49913
- added this run: 4193
- rejected this run: {'canonical': 725, 'word_length': 131, 'char_length': 272, 'parser_integrity': 262, 'markup': 31, 'nonprose': 18, 'duplicate': 13, 'punctuation': 3}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
