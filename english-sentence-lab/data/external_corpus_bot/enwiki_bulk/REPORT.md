# SentenceLab enwiki bulk collector

- total accepted local records: 24918
- total pages sampled: 2135
- added this run: 3625
- rejected this run: {'parser_integrity': 362, 'char_length': 337, 'canonical': 698, 'word_length': 198, 'duplicate': 22, 'markup': 63, 'nonprose': 21, 'punctuation': 3}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
