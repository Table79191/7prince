# SentenceLab enwiki bulk collector

- total accepted local records: 989732
- total pages sampled: 57962
- added this run: 6628
- rejected this run: {'canonical': 1360, 'char_length': 573, 'parser_integrity': 528, 'duplicate': 91, 'word_length': 209, 'markup': 101, 'nonprose': 23, 'punctuation': 3}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
