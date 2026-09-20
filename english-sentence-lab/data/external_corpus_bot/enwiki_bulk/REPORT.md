# SentenceLab enwiki bulk collector

- total accepted local records: 499786
- total pages sampled: 29715
- added this run: 4282
- rejected this run: {'canonical': 760, 'word_length': 152, 'parser_integrity': 388, 'char_length': 364, 'markup': 48, 'nonprose': 12, 'duplicate': 19, 'punctuation': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
