# baseline_test_r1 vs agent_test_r1

| Metric | baseline_test_r1 | agent_test_r1 |
|---|---|---|
| Fixed answers fully correct | 14/16 | 16/16 |
| Fixed answers mean score | 0.972 | 1.000 |
| Time-sensitive rubric score | 0.969 | 1.000 |
| Numbers with a citation | 99% | 100% |
| Cited claims supported | 91% | 99% |
| Cited URLs that are primary | 38% | 82% |
| Tavily credits / question | 4.3 | 0.7 |
| Tokens / question | 34,574 | 34,401 |
| Median latency | 10.3 s | 21.9 s |

Verdict changes (3 of 20): T13 (partial→correct), T16 (partial→correct), T18 (partial→correct)
