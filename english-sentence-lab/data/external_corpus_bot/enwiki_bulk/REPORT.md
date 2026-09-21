# SentenceLab enwiki bulk collector

- total accepted local records: 656689
- total pages sampled: 38973
- added this run: 6253
- rejected this run: {'char_length': 618, 'canonical': 1147, 'word_length': 250, 'parser_integrity': 486, 'nonprose': 23, 'markup': 57, 'duplicate': 68, 'punctuation': 3}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
