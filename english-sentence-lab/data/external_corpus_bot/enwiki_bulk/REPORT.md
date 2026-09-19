# SentenceLab enwiki bulk collector

- total accepted local records: 87170
- total pages sampled: 5842
- added this run: 3238
- rejected this run: {'canonical': 627, 'word_length': 146, 'parser_integrity': 370, 'char_length': 244, 'markup': 43, 'duplicate': 11, 'nonprose': 13, 'punctuation': 2}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
