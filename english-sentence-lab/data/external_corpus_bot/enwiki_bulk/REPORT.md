# SentenceLab enwiki bulk collector

- total accepted local records: 249963
- total pages sampled: 15325
- added this run: 4026
- rejected this run: {'word_length': 156, 'canonical': 823, 'parser_integrity': 463, 'char_length': 391, 'nonprose': 14, 'markup': 64, 'punctuation': 15, 'duplicate': 6}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
