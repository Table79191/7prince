# Auto Web Corpus Bot report

Upstream snapshot: `5a6819f53e0225632336a39e444397070eec63a828758b631d4d3acb1ba91b6f`

This dataset contains internet-fetched **already annotated** UD English sentences plus SentenceLab S/V/O/C/M role analysis.
No arbitrary webpages are scraped; only the explicit allowlist in `auto_web_corpus_bot.py` is used.

| Source | License | Written | Auto-pass | Needs review |
|---|---:|---:|---:|---:|
| ewt | CC-BY-SA-4.0 | 1000 | 898 | 102 |
| atis | CC-BY-SA-4.0 | 1000 | 987 | 13 |
| childes | CC-BY-SA-4.0 | 1000 | 986 | 14 |
| ctetex | CC-BY-SA-4.0 | 274 | 218 | 56 |
| eslspok | CC-BY-SA-4.0 | 1000 | 960 | 40 |
| littleprince | CC-BY-SA-4.0 | 492 | 474 | 18 |
| pronouns | CC-BY-SA-4.0 | 285 | 275 | 10 |
| pud | CC-BY-SA-3.0 | 1000 | 882 | 118 |

**Total analyzed sentences:** 6051

Every JSONL record preserves the upstream repository, raw file URL, sentence id, expected license, content hash, UD parse, and canonical role rules.
