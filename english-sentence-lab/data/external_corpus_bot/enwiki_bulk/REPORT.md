# SentenceLab enwiki bulk collector

- total accepted local records: 282668
- total pages sampled: 17185
- added this run: 4149
- rejected this run: {'canonical': 862, 'char_length': 409, 'parser_integrity': 446, 'word_length': 218, 'nonprose': 23, 'markup': 98, 'duplicate': 15, 'punctuation': 2, 'repetition': 8}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
