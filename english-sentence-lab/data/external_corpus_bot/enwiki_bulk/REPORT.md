# SentenceLab enwiki bulk collector

- total accepted local records: 857625
- total pages sampled: 50337
- added this run: 3361
- rejected this run: {'canonical': 659, 'parser_integrity': 339, 'char_length': 290, 'nonprose': 32, 'word_length': 121, 'markup': 39, 'duplicate': 11, 'punctuation': 1, 'repetition': 1}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
