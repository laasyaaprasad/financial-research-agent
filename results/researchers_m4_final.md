# M4 retrieval: researchers_m4_final

Baseline: baseline_r3_traced. Same questions/as-of dates; fixed M3 plans isolate retrieval. Judge: deepseek-ai/DeepSeek-V4-Pro.

| Metric | Researchers | Baseline |
|---|---|---|
| Relevant retrieved sources | 44.6% | 24.6% |
| Primary retrieved sources | 68.2% | 11.4% |
| Sources | 157 | 993 |

Numeric period/unit/as-of completeness: True. Evidence facts: 530. Mean/max Tavily credits: 3.73/8.00.

Relevance is judged from the same maximum 1,200 characters per source, without golden answers. The baseline was recorded earlier, so live-index drift remains a limitation. Primary classification of baseline is its recorded scorer; new source tiers use resolved company/hostname checks, not the golden source list.

| ID | Sources | Primary | Facts | Credits | Relevance | Baseline relevance |
|---|---|---|---|---|---|---|
| G01 | 3 | 3 | 8 | 2.00 | 3/3 | 6/10 |
| G02 | 15 | 5 | 5 | 5.00 | 11/15 | 37/45 |
| G03 | 4 | 4 | 22 | 1.00 | 1/4 | 1/13 |
| G04 | 3 | 3 | 5 | 2.00 | 1/3 | 15/55 |
| G05 | 3 | 3 | 41 | 1.00 | 1/3 | 5/10 |
| G06 | 3 | 3 | 17 | 3.00 | 2/3 | 6/10 |
| G07 | 3 | 3 | 3 | 4.00 | 0/3 | 2/32 |
| G08 | 3 | 1 | 9 | 5.00 | 1/3 | 4/10 |
| G09 | 1 | 1 | 3 | 2.00 | 1/1 | 1/40 |
| G10 | 2 | 2 | 3 | 2.00 | 0/2 | 0/10 |
| G11 | 0 | 0 | 0 | 2.00 | 0/0 | 0/20 |
| G12 | 0 | 0 | 0 | 4.00 | 0/0 | 2/18 |
| G13 | 2 | 2 | 5 | 7.00 | 1/2 | 12/20 |
| G14 | 3 | 3 | 13 | 3.00 | 0/3 | 6/70 |
| G15 | 6 | 4 | 8 | 4.00 | 2/6 | 3/10 |
| G16 | 11 | 8 | 40 | 4.00 | 3/11 | 3/10 |
| G17 | 4 | 4 | 25 | 6.00 | 0/4 | 13/65 |
| G18 | 9 | 4 | 11 | 4.00 | 4/9 | 8/10 |
| G19 | 6 | 6 | 17 | 2.00 | 4/6 | 22/67 |
| G20 | 4 | 4 | 56 | 1.00 | 3/4 | 4/19 |
| G21 | 2 | 2 | 19 | 2.00 | 1/2 | 0/11 |
| G22 | 5 | 4 | 20 | 4.00 | 4/5 | 4/61 |
| G23 | 5 | 5 | 6 | 5.00 | 2/5 | 7/26 |
| G24 | 13 | 5 | 13 | 6.00 | 6/13 | 3/27 |
| G25 | 3 | 3 | 19 | 2.00 | 1/3 | 13/114 |
| G26 | 3 | 3 | 19 | 4.00 | 0/3 | 20/54 |
| G27 | 8 | 5 | 78 | 3.00 | 4/8 | 4/53 |
| G28 | 12 | 5 | 6 | 8.00 | 2/12 | 10/34 |
| G29 | 15 | 7 | 54 | 7.00 | 8/15 | 12/40 |
| G30 | 6 | 5 | 5 | 7.00 | 4/6 | 21/29 |
