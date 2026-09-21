# SentenceLab enwiki bulk collector

- total accepted local records: 588869
- total pages sampled: 34908
- added this run: 3970
- rejected this run: {'word_length': 158, 'canonical': 758, 'char_length': 360, 'parser_integrity': 413, 'markup': 39, 'duplicate': 9, 'punctuation': 4, 'nonprose': 17, 'repetition': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
