# SentenceLab enwiki bulk collector

- total accepted local records: 1005533
- total pages sampled: 58888
- added this run: 7368
- rejected this run: {'char_length': 632, 'canonical': 1543, 'parser_integrity': 571, 'word_length': 290, 'nonprose': 55, 'duplicate': 22, 'markup': 192, 'punctuation': 20}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
