# SentenceLab enwiki bulk collector

- total accepted local records: 1010117
- total pages sampled: 59178
- added this run: 4584
- rejected this run: {'canonical': 872, 'char_length': 423, 'parser_integrity': 408, 'word_length': 172, 'duplicate': 16, 'nonprose': 29, 'markup': 71, 'punctuation': 5}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
