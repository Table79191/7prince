# Auto Web Corpus Bot report

Upstream snapshot: `b99d09afd946f910a9ec0f5e0081ee8ac7da74241652b5d537b1793b54b3c512`

Incremental allowlisted Universal Dependencies English corpus.
Existing records are retained; only unseen sentences are appended.
Per-source storage is unlimited by default. When a source is exhausted, its unused run budget is redistributed to other active sources.
Exhausted unchanged sources are checked by upstream HEAD and skip large raw downloads.

| Source | License | Stored | Added | Quota | Remaining | Download | Auto-pass | Review |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| atis | CC-BY-SA-4.0 | 5430 | 182 | 333 | 0 | fetched | 5354 | 76 |
| childes | CC-BY-SA-4.0 | 5732 | 484 | 484 | 39767 | fetched | 5673 | 59 |
| ctetex | CC-BY-SA-4.0 | 274 | 0 | 0 | 0 | skipped | 218 | 56 |
| eslspok | CC-BY-SA-4.0 | 2154 | 0 | 0 | 0 | skipped | 2054 | 100 |
| ewt | CC-BY-SA-4.0 | 5588 | 334 | 334 | 9462 | fetched | 4988 | 600 |
| littleprince | CC-BY-SA-4.0 | 492 | 0 | 0 | 0 | skipped | 474 | 18 |
| pronouns | CC-BY-SA-4.0 | 285 | 0 | 0 | 0 | skipped | 275 | 10 |
| pud | CC-BY-SA-3.0 | 1000 | 0 | 0 | 0 | skipped | 882 | 118 |

**Total analyzed sentences:** 20955
**New items added this run:** 1000
**Raw sources fetched/skipped this run:** 3/5

Every record retains its original UD provenance/license and canonical role analysis.
