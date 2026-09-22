# SentenceLab enwiki bulk collector

- total accepted local records: 771067
- total pages sampled: 45435
- added this run: 6685
- rejected this run: {'canonical': 1333, 'parser_integrity': 449, 'word_length': 208, 'char_length': 467, 'markup': 68, 'nonprose': 19, 'duplicate': 14, 'punctuation': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
