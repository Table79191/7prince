# SentenceLab enwiki bulk collector

- total accepted local records: 918583
- total pages sampled: 53779
- added this run: 6938
- rejected this run: {'canonical': 1464, 'word_length': 245, 'parser_integrity': 1166, 'char_length': 514, 'markup': 72, 'nonprose': 61, 'duplicate': 33, 'punctuation': 20}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
