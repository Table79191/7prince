# SentenceLab enwiki bulk collector

- total accepted local records: 60474
- total pages sampled: 4249
- added this run: 4124
- rejected this run: {'canonical': 865, 'parser_integrity': 251, 'word_length': 85, 'char_length': 247, 'duplicate': 33, 'markup': 51, 'punctuation': 4, 'nonprose': 15}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
