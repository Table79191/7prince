# SentenceLab enwiki bulk collector

- total accepted local records: 620888
- total pages sampled: 36788
- added this run: 3154
- rejected this run: {'char_length': 235, 'word_length': 107, 'parser_integrity': 275, 'markup': 37, 'canonical': 677, 'nonprose': 17, 'duplicate': 10, 'punctuation': 2}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
