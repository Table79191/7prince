# SentenceLab enwiki bulk collector

- total accepted local records: 167133
- total pages sampled: 10498
- added this run: 6861
- rejected this run: {'canonical': 1373, 'char_length': 524, 'parser_integrity': 512, 'word_length': 255, 'punctuation': 13, 'markup': 97, 'duplicate': 33, 'nonprose': 23}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
