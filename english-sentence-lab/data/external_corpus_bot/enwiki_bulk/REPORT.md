# SentenceLab enwiki bulk collector

- total accepted local records: 732403
- total pages sampled: 43330
- added this run: 6562
- rejected this run: {'canonical': 1198, 'char_length': 586, 'parser_integrity': 567, 'word_length': 263, 'markup': 71, 'nonprose': 30, 'punctuation': 4, 'duplicate': 18, 'page_duplicate': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
