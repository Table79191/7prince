# SentenceLab enwiki bulk collector

- total accepted local records: 489130
- total pages sampled: 29090
- added this run: 3530
- rejected this run: {'canonical': 773, 'char_length': 307, 'word_length': 174, 'parser_integrity': 389, 'markup': 51, 'nonprose': 15, 'punctuation': 5, 'duplicate': 6}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
