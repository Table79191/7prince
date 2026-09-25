# SentenceLab enwiki bulk collector

- total accepted local records: 1017470
- total pages sampled: 59611
- added this run: 7353
- rejected this run: {'char_length': 637, 'duplicate': 22, 'canonical': 1445, 'parser_integrity': 688, 'nonprose': 49, 'word_length': 308, 'markup': 166, 'punctuation': 8}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
