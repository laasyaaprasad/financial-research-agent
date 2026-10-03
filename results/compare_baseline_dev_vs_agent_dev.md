# baseline_dev vs agent_dev

| Metric | baseline_dev | agent_dev |
|---|---|---|
| Fixed answers fully correct | 21/25 | 18/25 |
| Fixed answers mean score | 0.959 | 0.901 |
| Time-sensitive rubric score | 0.942 | 0.890 |
| Numbers with a citation | 97% | 100% |
| Cited claims supported | 83% | 90% |
| Cited URLs that are primary | 39% | 82% |
| Tavily credits / question | 4.6 | 0.9 |
| Tokens / question | 25,169 | 49,455 |
| Median latency | 10.9 s | 21.4 s |

Verdict changes (10 of 30): G02 (correct→partial), G07 (correct→partial), G08 (partial→correct), G16 (correct→partial), G18 (correct→partial), G19 (partial→correct), G27 (correct→partial), G28 (partial→incorrect), G29 (partial→correct), G30 (correct→partial)
