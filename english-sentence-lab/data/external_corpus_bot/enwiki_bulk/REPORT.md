# SentenceLab enwiki bulk collector

- total accepted local records: 403772
- total pages sampled: 24215
- added this run: 5765
- rejected this run: {'char_length': 445, 'word_length': 223, 'canonical': 1057, 'parser_integrity': 500, 'duplicate': 56, 'markup': 78, 'nonprose': 38, 'punctuation': 2}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
