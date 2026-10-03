# baseline_test_r2 vs agent_test_r2

| Metric | baseline_test_r2 | agent_test_r2 |
|---|---|---|
| Fixed answers fully correct | 14/16 | 13/16 |
| Fixed answers mean score | 0.972 | 0.956 |
| Time-sensitive rubric score | 1.000 | 1.000 |
| Numbers with a citation | 97% | 98% |
| Cited claims supported | 80% | 94% |
| Cited URLs that are primary | 31% | 88% |
| Tavily credits / question | 3.5 | 0.6 |
| Tokens / question | 21,215 | 36,199 |
| Median latency | 7.8 s | 24.9 s |

Verdict changes (5 of 20): T11 (correct→partial), T13 (partial→correct), T14 (correct→partial), T18 (partial→correct), T19 (correct→partial)
