# SentenceLab enwiki bulk collector

- total accepted local records: 854264
- total pages sampled: 50122
- added this run: 3765
- rejected this run: {'char_length': 291, 'parser_integrity': 251, 'markup': 35, 'canonical': 743, 'word_length': 133, 'duplicate': 13, 'nonprose': 20}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
