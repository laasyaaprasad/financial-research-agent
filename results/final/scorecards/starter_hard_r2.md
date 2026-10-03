# Scorecard: starter_hard_r2

Agent `starter` · set `hard` · model `moonshotai/Kimi-K2.6` · judge `nvidia/Nemotron-3-Ultra-550b-a55b` · code `f223242` · questions 20 · agent errors 0 · judge errors 0

| Slice | Qs | Fixed answers: fully correct (mean score) | Time-sensitive: rubric score | Numbers with a citation | Cited claims supported | Cited URLs that are primary |
|---|---|---|---|---|---|---|
| All | 20 | 8/18 (0.70) | 0.25 (n=2) | 96% | 91% | 19% |

| Median latency | p95 latency | Tokens / question | Tavily credits / question | Tavily credits total |
|---|---|---|---|---|
| 19.5 s | 138.6 s | 74,471 | 8.6 | 172 |

## By category

| Slice | Qs | Fixed answers: fully correct (mean score) | Time-sensitive: rubric score | Numbers with a citation | Cited claims supported | Cited URLs that are primary |
|---|---|---|---|---|---|---|
| Adjustments | 1 | 1/1 (1.00) | – | 100% | 100% | 0% |
| Beat or miss | 2 | 2/2 (1.00) | – | 100% | 92% | 25% |
| Complex retrieval | 3 | 0/3 (0.17) | – | 100% | 80% | 0% |
| Financial modeling | 2 | 1/2 (0.71) | – | 100% | 81% | 25% |
| Numerical reasoning | 2 | 1/2 (0.92) | – | 100% | 100% | 0% |
| Qualitative retrieval | 3 | 0/1 (0.50) | 0.25 (n=2) | 100% | 78% | 0% |
| Quantitative retrieval | 7 | 3/7 (0.77) | – | 87% | 100% | 40% |

## Per question

| ID | Category | Verdict | Score | Credits | Latency | Trace | Judge rationale |
|---|---|---|---|---|---|---|---|
| H01 | Complex retrieval | incorrect | 0.00 | 18 | 139 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/2e4569e1aeec37eebbe9fa4b9c5fd8b0) | No answer produced. |
| H02 | Complex retrieval | incorrect | 0.00 | 4 | 20 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/7f7d66e3d8ce4651ec2ed83e67b96c47) | Both required key points are incorrect: the agent used fiscal Q3 2026 results (released after the as_of date) and the later 18%-20% EBITDA outlook, failing to provide the correct latest reported quarter (fiscal Q2 2026, EPS $5.53) and the c |
| H03 | Quantitative retrieval | correct | 1.00 | 6 | 64 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/3f928cb0f02ca0e9a5f5c350a1261890) | The agent correctly identifies the latest reported quarter as fiscal Q3 2025, provides the correct domestic same store sales growth of -5.6%, and system-wide sales of $1.4 billion (approx 10% y/y), consistent with the reference. The agent a |
| H04 | Complex retrieval | partial | 0.50 | 14 | 42 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/f96442b8e5ae790a112089494954f236) | The agent correctly identifies the latest reported quarter (Q3 FY2026) and adjusted EPS ($2.38), but incorrectly states the fiscal 2026 net sales growth guidance range as 3.5%-4.5% instead of the updated 3.5%-4.0% range that was in effect a |
| H05 | Adjustments | correct | 1.00 | 1 | 11 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/46f944775cda30e03fa0b0876ae2c84d) | The agent correctly provides both required guidance ranges as of July 15, 2026: GAAP diluted EPS $1.28–$1.37 and adjusted diluted EPS $1.43–$1.51. The answer also correctly notes that the Q3 update (August 26, 2026) came after the as-of dat |
| H06 | Quantitative retrieval | incorrect | 0.67 | 2 | 10 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/2a16089fd6182f4c3547a50fed80c5ba) | The agent reported the correct numeric value for RPO but omitted the 'thousands' unit, resulting in a factor-of-1,000 error. The 12-month recognition share (23%) and optional 18% detail are correct. |
| H07 | Quantitative retrieval | partial | 0.56 | 2 | 8 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/bebda4bcc2ba43b01e65df66f9346de2) | The agent correctly identifies all four customers (Cisco, NVIDIA, Nokia, Amazon) that contributed ≥10% of Fabrinet's FY2026 revenue and avoids the FY2025 confusion. However, three of the four reported percentages (NVIDIA 16% vs 16.3%, Nokia |
| H08 | Quantitative retrieval | correct | 1.00 | 2 | 6 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/51bc598dab2069de32b896dbcbd34f41) | The agent provided the correct BASX-branded backlog figure for June 30, 2026, in USD millions, within the allowed tolerance, and did not confuse it with total backlog or other dates. |
| H09 | Quantitative retrieval | partial | 0.80 | 16 | 45 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/6b2a26ad67d5f5ebe850475d3ea9e21a) | The agent correctly reports the share count, total cost, average price, and remaining authorization within tolerance, and identifies the correct fiscal quarter. However, the agent omits mention of the board's expansion of the repurchase pro |
| H10 | Numerical reasoning | correct | 1.00 | 12 | 68 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/7fda4d53fa75ad12622678586a99d712) | All six requirements are satisfied. The agent's reported TTM net sales, net income, and net margin match the reference values within the specified tolerances. The TTM window is correct, GAAP net income is used, and none of the listed failur |
| H11 | Financial modeling | correct | 1.00 | 14 | 90 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/600751589e59bbc405c8ed271236aa93) | All grading requirements are satisfied: the agent uses the correct nine-month period, computes implied Q4 revenue and GAAP operating income accurately within tolerance, calculates the correct GAAP operating margin, and avoids the non-GAAP t |
| H12 | Numerical reasoning | partial | 0.83 | 26 | 102 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/4249bba702e484ca1c2fc48dfb8ceaaa) | The agent's final TTM net sales, EBIT, and margin are numerically correct within the allowed tolerances, and the answer avoids the explicit failure modes (reporting nine-month, fiscal-2025, or quarterly values as the final answer). However, |
| H13 | Financial modeling | incorrect | 0.43 | 2 | 17 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/a07e89cf421d510422c17ccb199b032c) | The agent's reported revenue is within tolerance, but the income-from-operations margin (8.51%) is materially different from the correct 7.75% (outside the ±0.2pp tolerance). This error indicates the trailing-twelve-month window was not cor |
| H14 | Quantitative retrieval | correct | 1.00 | 6 | 19 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/2dcdeb9dc7a452380ebff76259eb8418) | The agent correctly abstains by stating Q4 2026 results are not yet reported as of early October 2026, provides no Q4 revenue or EPS as fact, and avoids all failure modes (does not fabricate numbers, present guidance or analyst consensus as |
| H15 | Qualitative retrieval | partial | 0.50 | 32 | 64 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/55f24bf933ef67c8620aed8534359f7b) | The agent correctly identifies that no division-level combined ratio is disclosed and avoids the critical failure modes (presenting a division-level ratio or misattributing the consolidated 75.9% ratio). However, the agent does not explicit |
| H16 | Quantitative retrieval | partial | 0.40 | 5 | 33 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/8f3a2a65d446c73e01180dff21116491) | The agent correctly identifies that no 10-Q for June 30, 2026 is on EDGAR and provides the last available quarter (2025) with accurate figures, but fails to state the essential reason: Skechers was taken private in September 2025 (merger cl |
| H17 | Beat or miss | correct | 1.00 | 4 | 12 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/ee118f02c0808a6d8f82f3595ea3bac8) | All key grading requirements are satisfied: the agent correctly compares each metric to the company's own Q3 FY2026 guidance from the April 29, 2026 release, labels revenue and GAAP diluted EPS as above guidance, and correctly identifies no |
| H18 | Beat or miss | correct | 1.00 | 2 | 10 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/7d81e6316d5d158884ea4175b33711e5) | All required points are met: the agent accurately reports revenue, non-GAAP operating margin, and GAAP EPS versus the company's own May 2026 guidance, correctly identifies GAAP EPS as below guidance, avoids all listed failure modes, and use |
| H19 | Qualitative retrieval | partial | 0.50 | 4 | 10 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/84f86b72b92666768525f0a3f7abb482) | The answer correctly identifies the Brakebush acquisition as the most significant news, provides the correct announcement date (Sept 30, 2026) and purchase price (~$1.055B cash), and states the expected closing quarter (fiscal Q1 2027). How |
| H20 | Qualitative retrieval | incorrect | 0.00 | 0 | 6 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/92c88a6174dd146ad07a691d03907069) | The agent refused to answer, citing the date as in the future, and provided none of the required financial announcements from the 30 days before October 3, 2026. All four key points are missing. |
