# SentenceLab enwiki bulk collector

- total accepted local records: 701758
- total pages sampled: 41510
- added this run: 6925
- rejected this run: {'char_length': 593, 'canonical': 1357, 'parser_integrity': 694, 'duplicate': 24, 'markup': 126, 'word_length': 242, 'nonprose': 65, 'punctuation': 29}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
