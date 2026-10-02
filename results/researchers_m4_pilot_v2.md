# M4 retrieval: researchers_m4_pilot_v2

Baseline: baseline_r3_traced. Same questions/as-of dates; fixed M3 plans isolate retrieval. Judge: deepseek-ai/DeepSeek-V4-Pro.

| Metric | Researchers | Baseline |
|---|---|---|
| Relevant retrieved sources | 59.1% | 35.0% |
| Primary retrieved sources | 63.6% | 16.7% |
| Sources | 22 | 60 |

Numeric period/unit/as-of completeness: True. Evidence facts: 67. Mean/max Tavily credits: 4.00/8.00.

Relevance is judged from the same maximum 1,200 characters per source, without golden answers. The baseline was recorded earlier, so live-index drift remains a limitation. Primary classification of baseline is its recorded scorer; new source tiers use resolved company/hostname checks, not the golden source list.

| ID | Sources | Primary | Facts | Credits | Relevance | Baseline relevance |
|---|---|---|---|---|---|---|
| G01 | 3 | 3 | 10 | 1.00 | 3/3 | 6/10 |
| G10 | 2 | 2 | 3 | 3.00 | 0/2 | 0/10 |
| G29 | 17 | 9 | 54 | 8.00 | 10/17 | 15/40 |
