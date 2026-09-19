# SentenceLab enwiki bulk collector

- total accepted local records: 236052
- total pages sampled: 14512
- added this run: 4815
- rejected this run: {'char_length': 347, 'canonical': 937, 'parser_integrity': 311, 'word_length': 146, 'duplicate': 18, 'markup': 36, 'nonprose': 17, 'punctuation': 3}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
