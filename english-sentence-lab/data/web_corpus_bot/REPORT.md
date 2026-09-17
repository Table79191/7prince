# Auto Web Corpus Bot report

Upstream snapshot: `b99d09afd946f910a9ec0f5e0081ee8ac7da74241652b5d537b1793b54b3c512`

Incremental allowlisted Universal Dependencies English corpus.
Existing records are retained; only unseen sentences are appended.
Per-source storage is unlimited by default. When a source is exhausted, its unused run budget is redistributed to other active sources.
Exhausted unchanged sources are checked by upstream HEAD and skip large raw downloads.

| Source | License | Stored | Added | Quota | Remaining | Download | Auto-pass | Review |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| atis | CC-BY-SA-4.0 | 5430 | 0 | 0 | 0 | skipped | 5354 | 76 |
| childes | CC-BY-SA-4.0 | 14232 | 500 | 500 | 31267 | fetched | 14074 | 158 |
| ctetex | CC-BY-SA-4.0 | 274 | 0 | 0 | 0 | skipped | 218 | 56 |
| eslspok | CC-BY-SA-4.0 | 2154 | 0 | 0 | 0 | skipped | 2054 | 100 |
| ewt | CC-BY-SA-4.0 | 14088 | 500 | 500 | 962 | fetched | 12581 | 1507 |
| littleprince | CC-BY-SA-4.0 | 492 | 0 | 0 | 0 | skipped | 474 | 18 |
| pronouns | CC-BY-SA-4.0 | 285 | 0 | 0 | 0 | skipped | 275 | 10 |
| pud | CC-BY-SA-3.0 | 1000 | 0 | 0 | 0 | skipped | 882 | 118 |

**Total analyzed sentences:** 37955
**New items added this run:** 1000
**Raw sources fetched/skipped this run:** 2/6

Every record retains its original UD provenance/license and canonical role analysis.
