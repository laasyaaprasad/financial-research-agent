# agent_dev_secOnly_v2 vs agent_dev_secOnly_v3

| Metric | agent_dev_secOnly_v2 | agent_dev_secOnly_v3 |
|---|---|---|
| Fixed answers fully correct | 18/25 | 17/25 |
| Fixed answers mean score | 0.888 | 0.854 |
| Time-sensitive rubric score | 0.510 | 0.442 |
| Numbers with a citation | 100% | 99% |
| Cited claims supported | 98% | 98% |
| Cited URLs that are primary | 100% | 100% |
| Tavily credits / question | 0.0 | 0.0 |
| Tokens / question | 48,748 | 40,406 |
| Median latency | 77.3 s | 41.2 s |

Verdict changes (6 of 30): G05 (partial→correct), G13 (correct→partial), G16 (correct→partial), G21 (correct→partial), G24 (correct→partial), G30 (partial→correct)
