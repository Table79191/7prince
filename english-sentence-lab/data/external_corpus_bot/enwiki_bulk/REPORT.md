# SentenceLab enwiki bulk collector

- total accepted local records: 974055
- total pages sampled: 57032
- added this run: 4492
- rejected this run: {'canonical': 901, 'char_length': 300, 'duplicate': 21, 'word_length': 182, 'parser_integrity': 408, 'markup': 52, 'nonprose': 18, 'punctuation': 2, 'repetition': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
