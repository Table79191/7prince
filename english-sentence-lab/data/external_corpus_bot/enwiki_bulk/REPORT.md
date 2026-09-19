# SentenceLab enwiki bulk collector

- total accepted local records: 245937
- total pages sampled: 15093
- added this run: 3334
- rejected this run: {'canonical': 643, 'parser_integrity': 270, 'word_length': 85, 'char_length': 302, 'duplicate': 26, 'markup': 49, 'punctuation': 1, 'nonprose': 6}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
