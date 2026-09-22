# SentenceLab enwiki bulk collector

- total accepted local records: 886903
- total pages sampled: 51978
- added this run: 7170
- rejected this run: {'char_length': 639, 'word_length': 356, 'canonical': 1295, 'parser_integrity': 816, 'markup': 107, 'nonprose': 41, 'punctuation': 4, 'duplicate': 41, 'long_token': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
