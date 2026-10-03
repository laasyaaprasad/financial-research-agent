# Scorecard: agent_dev_smoke_fixes

Agent `agent` · set `dev` · model `deepseek-ai/DeepSeek-V4.1-Flash` · judge `nvidia/Nemotron-3-Ultra-550b-a55b` · code `7ae904f+uncommitted` · questions 3 · agent errors 0 · judge errors 0

| Slice | Qs | Fixed answers: fully correct (mean score) | Time-sensitive: rubric score | Numbers with a citation | Cited claims supported | Cited URLs that are primary |
|---|---|---|---|---|---|---|
| All | 3 | 1/2 (0.92) | 1.00 (n=1) | 100% | 96% | 82% |

| Median latency | p95 latency | Tokens / question | Tavily credits / question | Tavily credits total |
|---|---|---|---|---|
| 71.1 s | 75.4 s | 62,724 | 1.0 | 3 |

## By category

| Slice | Qs | Fixed answers: fully correct (mean score) | Time-sensitive: rubric score | Numbers with a citation | Cited claims supported | Cited URLs that are primary |
|---|---|---|---|---|---|---|
| Qualitative retrieval | 1 | 1/1 (1.00) | – | 100% | 100% | 100% |
| Quantitative retrieval | 1 | – | 1.00 (n=1) | 100% | 83% | 33% |
| Trends | 1 | 0/1 (0.83) | – | 100% | 100% | 100% |

## Per question

| ID | Category | Verdict | Score | Credits | Latency | Trace | Judge rationale |
|---|---|---|---|---|---|---|---|
| G08 | Quantitative retrieval | correct | 1.00 | 2 | 28 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/32f377cc1374a8ca439c2bceefd484a3) | All grading requirements are satisfied: the agent uses the latest pre-snapshot guidance (July 29, 2026 call), accurately quotes the ~45% constant-currency point estimate, specifies the currency basis and fiscal quarter (Q1 FY2027), does not |
| G17 | Qualitative retrieval | correct | 1.00 | 1 | 71 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/5178331e83ea8301ad08b0117e3645f3) | The agent's answer satisfies all four grading requirements: it lists management-cited drivers with source verification, quantifies the one-time tariff-refund benefit as 750bps, distinguishes reported (28.8%) from adjusted constant-currency  |
| G27 | Trends | partial | 0.83 | 0 | 75 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/6502896962b2a88bddf101f0ee67645a) | All GAAP gross margin percentages and full-year revenue growth are within the required tolerances. However, the agent fails to explicitly state the week counts (53 vs 52 for FY, 14 vs 13 for Q4) as disclosed in the source, instead noting th |
