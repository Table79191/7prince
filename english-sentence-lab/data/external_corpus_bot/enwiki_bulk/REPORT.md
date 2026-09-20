# SentenceLab enwiki bulk collector

- total accepted local records: 356946
- total pages sampled: 21489
- added this run: 4612
- rejected this run: {'canonical': 952, 'char_length': 422, 'word_length': 213, 'duplicate': 17, 'parser_integrity': 536, 'punctuation': 4, 'markup': 48, 'nonprose': 35}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
