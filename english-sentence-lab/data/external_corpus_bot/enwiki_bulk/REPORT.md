# SentenceLab enwiki bulk collector

- total accepted local records: 145797
- total pages sampled: 9376
- added this run: 6320
- rejected this run: {'canonical': 1215, 'char_length': 589, 'parser_integrity': 480, 'word_length': 203, 'markup': 91, 'nonprose': 29, 'punctuation': 4, 'duplicate': 32, 'repetition': 2}

This collector never writes promoted_silver directly. The central promotion gate performs global dedupe and strict cross-parser consensus.
