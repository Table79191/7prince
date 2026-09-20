# SentenceLab enwiki bulk collector

- total accepted local records: 557828
- total pages sampled: 33059
- added this run: 3578
- rejected this run: {'char_length': 294, 'canonical': 658, 'parser_integrity': 287, 'word_length': 126, 'nonprose': 18, 'punctuation': 5, 'markup': 55, 'repetition': 1, 'duplicate': 6}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
