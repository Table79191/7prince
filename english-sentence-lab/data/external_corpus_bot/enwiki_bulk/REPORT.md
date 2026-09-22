# SentenceLab enwiki bulk collector

- total accepted local records: 797507
- total pages sampled: 46914
- added this run: 4247
- rejected this run: {'canonical': 915, 'char_length': 298, 'word_length': 149, 'parser_integrity': 280, 'markup': 58, 'punctuation': 3, 'duplicate': 9, 'nonprose': 19}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
