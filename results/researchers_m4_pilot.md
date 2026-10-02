# M4 retrieval: researchers_m4_pilot

Baseline: baseline_r3_traced. Same questions/as-of dates; fixed M3 plans isolate retrieval. Judge: deepseek-ai/DeepSeek-V4-Pro.

| Metric | Researchers | Baseline |
|---|---|---|
| Relevant retrieved sources | 31.6% | 33.3% |
| Primary retrieved sources | 57.9% | 16.7% |
| Sources | 19 | 60 |

Numeric period/unit/as-of completeness: True. Evidence facts: 59. Mean/max Tavily credits: 3.33/6.00.

Relevance is judged from the same maximum 1,200 characters per source, without golden answers. The baseline was recorded earlier, so live-index drift remains a limitation. Primary classification of baseline is its recorded scorer; new source tiers use resolved company/hostname checks, not the golden source list.

| ID | Sources | Primary | Facts | Credits | Relevance | Baseline relevance |
|---|---|---|---|---|---|---|
| G01 | 3 | 3 | 9 | 2.00 | 2/3 | 6/10 |
| G10 | 3 | 3 | 7 | 2.00 | 0/3 | 0/10 |
| G29 | 13 | 5 | 43 | 6.00 | 4/13 | 14/40 |
