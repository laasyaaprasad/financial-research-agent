# Scorecard: half_starter_exact50

Agent `starter` · set `exact50` · model `moonshotai/Kimi-K2.6` · judge `gpt-6-luna` · code `6bc163c` · questions 25 · agent errors 0 · judge errors 0

| Slice | Qs | Fixed answers: fully correct (mean score) | Time-sensitive: rubric score | Numbers with a citation | Cited claims supported | Cited URLs that are primary |
|---|---|---|---|---|---|---|
| All | 25 | 6/13 (0.84) | 1/12 all met (0.51) | 90% | 70% | 14% |

| Median latency | p95 latency | Tokens / question | Tavily credits / question | Tavily credits total |
|---|---|---|---|---|
| 33.7 s | 98.2 s | 43,697 | 6.2 | 156 |

## By category

| Slice | Qs | Fixed answers: fully correct (mean score) | Time-sensitive: rubric score | Numbers with a citation | Cited claims supported | Cited URLs that are primary |
|---|---|---|---|---|---|---|
| Beat or miss | 2 | 1/2 (0.92) | – | 100% | 75% | 0% |
| Complex retrieval | 3 | 2/2 (1.00) | 0/1 all met (0.75) | 100% | 59% | 11% |
| Market analysis | 2 | 1/2 (0.80) | – | 47% | 60% | 0% |
| Qualitative retrieval | 2 | – | 0/2 all met (0.42) | 100% | 69% | 0% |
| Quantitative retrieval | 3 | 0/2 (0.75) | 1/1 all met (1.00) | 81% | 76% | 38% |
| ambiguous company | 1 | – | 0/1 all met (0.00) | 100% | 62% | 0% |
| call commentary | 2 | 2/2 (1.00) | – | 100% | 77% | 12% |
| company naming | 2 | – | 0/2 all met (0.53) | 100% | 71% | 20% |
| fiscal vs calendar | 2 | – | 0/2 all met (0.46) | 100% | 53% | 0% |
| foreign issuer | 1 | 0/1 (0.61) | – | 100% | 85% | 40% |
| missing period | 1 | – | 0/1 all met (0.57) | 100% | 100% | 0% |
| open-ended update | 1 | – | 0/1 all met (0.33) | 100% | 75% | 0% |
| recent event | 2 | 0/2 (0.71) | – | 50% | 57% | 33% |
| vague metric | 1 | – | 0/1 all met (0.60) | 100% | 50% | 0% |

## Per question

| ID | Category | Verdict | Score | Credits | Latency | Trace | Judge rationale |
|---|---|---|---|---|---|---|---|
| E02 | missing period | incorrect | 0.57 | 2 | 22 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/bb12ae7d7922b76772be73c4a5d73555) | The answer identifies Wells Fargo and distinguishes NIM from NII, but it supplies only stale FY 2024 and Q3 2024 NIM figures. It omits the required Q2 2026 NIM and the required latest-quarter/Q3 reporting context, so the core answer is wron |
| E06 | vague metric | partial | 0.60 | 2 | 24 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/5e34f9f5c5466fd6681ad94e236c955c) | The answer identifies Berkshire Hathaway and explicitly mentions Treasury-inclusive liquidity, but it omits the required June 30, 2026 reporting-date details and Q3 status, and it does not make the required distinction between the balance-s |
| E09 | open-ended update | incorrect | 0.33 | 2 | 27 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/709e195338a9986a63bea24b1833389d) | Although the answer identifies the correct company and quarter and gives cited organic growth, it omits revenue, EPS, and raised FY2027 guidance, and adds an investment/valuation view. These are explicit failure conditions; it does not supp |
| E10 | fiscal vs calendar | incorrect | 0.25 | 1 | 26 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/cc75f7a659f53e97465e48f402959194) | Although it names Adobe, the answer identifies FY2023—not FY2025—as the last completed fiscal year, omits the required dates, and gives a cited revenue figure for the wrong fiscal year. |
| E13 | fiscal vs calendar | incorrect | 0.67 | 10 | 45 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/82bf79b4309db835f2671c1bf9c525e4) | Although it identifies Estée Lauder and includes fiscal dates, it answers with stale FY2025 information and incorrectly treats FY2026 as the current fiscal year. It neither identifies FY2026 as the latest completed year with its annual net  |
| E14 | company naming | partial | 0.80 | 12 | 46 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/ef109cebede13301511e351f857e5498) | The answer correctly maps Jack Daniel’s maker to Brown-Forman, uses the latest cited quarter, and provides the company-wide net-sales figure with a citation. It omits the required statement that Brown-Forman’s fiscal year ends April 30. |
| E17 | company naming | partial | 0.25 | 1 | 27 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/c377985f37fd474d43276ed2607e9161) | The answer gets the share-class distinction and the conclusion that neither ticker has higher revenue right, but uses an obsolete quarter and revenue figure, and includes investment/market commentary prohibited by the rule. |
| E19 | ambiguous company | incorrect | 0.00 | 4 | 12 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/265a9a557b8b2a1d1bb700ba53159493) | The answer fails the clarification requirement and supplies revenue figures for multiple possible United companies, so the core answer is wrong. |
| H01 | Complex retrieval | correct | 1.00 | 12 | 137 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/b43bba675bbbc54addd18828acac464c) | The answer correctly identifies Q2 fiscal 2025 and its $679.6 million net sales, and gives the current fiscal 2025 net-sales outlook range. It avoids the later Q3 results and the superseded range. |
| H02 | Complex retrieval | correct | 1.00 | 10 | 94 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/b894b695009d941acba238be347e10b4) | The answer gives the correct latest reported quarter and diluted EPS, the fiscal 2026 EBITDA growth range in effect, and avoids treating post-as-of-date Q3 results or guidance as current. |
| T10 | Complex retrieval | partial | 0.75 | 2 | 8 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/912fb1eaee8a7c3298a6b8abdf943835) | Both requested current guidance ranges are correct and the superseded ranges are clearly labeled as prior. However, the answer does not identify the September 23, 2026 release as the latest update, so it misses a required recency point. |
| T11 | Beat or miss | partial | 0.83 | 3 | 51 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/9f54c17f56f6ab11bc86f91ebfae1c31) | The answer correctly assesses revenue as below and diluted EPS as above the company's Q2 ranges, and includes the $0.86/share benefit and adjusted EPS comparison. It omits the required clarification that the company's guidance excluded IEEP |
| T12 | Beat or miss | correct | 1.00 | 4 | 18 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/3cd367e1f37f22b15c03bb964917c672) | The answer correctly compares both actual metrics with Qualcomm’s own Q3 guidance and classifies each as within range. |
| T15 | Qualitative retrieval | partial | 0.70 | 2 | 11 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/8bdcf6b497ef860c22fbd48a8656c13a) | The answer gets the central quarter/full-year results and FY2027 revenue and EPS outlook substantially right, and avoids the stale-Q3 failure. It omits the October 1 release date, does not establish that Q4 revenue exceeded the company’s gu |
| T16 | Qualitative retrieval | incorrect | 0.14 | 2 | 34 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/9fa73ca374056275522fb3c17c9cdad8) | The answer is about an earlier February restructuring, not the September 29, 2026 announcement asked about. It consequently gives the wrong workforce details and charge estimate, omits the expected FY2027 charge timing and guidance update,  |
| T17 | Quantitative retrieval | correct | 1.00 | 8 | 42 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/9e84c4fd71612a570e2f5c9aa9e7881e) | The response abstains from giving Q4 FY2026 actual results and clearly distinguishes the Q3 actuals and Q4 estimates from Q4 reported results. |
| T18 | Quantitative retrieval | partial | 0.75 | 1 | 13 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/68862c62c4ff17ea02e951f0ea536bf6) | The answer correctly abstains from giving a Cybertruck delivery count and provides the reported delivery categories and figures, but it omits the required statement that the 10-Q contains no Cybertruck unit count. |
| T19 | Quantitative retrieval | incorrect | 0.75 | 10 | 85 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/b738b9ba803da9d4c91771fa1c893493) | The answer correctly identifies Enterprise's private status and lack of publicly disclosed profit figures, but it also gives net income and operating income figures, contrary to the explicit fail condition. |
| T20 | Market analysis | partial | 0.60 | 8 | 71 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/23d04afcde8d63d7d2abc778c78df307) | Both revenue figures fall within their stated tolerances and the fiscal-quarter mapping is correct, but the difference is outside tolerance and the response characterizes the figures as estimates rather than reported actuals. |
| W01 | call commentary | correct | 1.00 | 4 | 36 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/1264ed31b59b57de1036981102cbc9f8) | The answer provides both requested July full-year outlooks and the required January/April comparisons, while avoiding the specified traps. |
| W02 | call commentary | correct | 1.00 | 2 | 16 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/3b7405798b756051ec3fd2bf8999dce6) | All required growth rates and the expected Low NA EUV shipment count are stated accurately. The extra FY2026 total-sales range is explicitly separate and does not replace the requested segment growth rates; the answer avoids the specified t |
| W05 | recent event | partial | 0.75 | 34 | 98 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/195508d5cadd2e8f5457e200f1d8cd16) | The answer correctly gives the updated price, non-binding status, premium, and increase, and avoids the specified point-in-time traps. Strictly, it omits the rollover alternative and the required 6 August reaffirmation. |
| W06 | recent event | partial | 0.67 | 2 | 18 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/c88f7bc975a02d12484175b5a9bef2d1) | The response correctly identifies Ittycheria's interim role and effective dates, reports the reaffirmed guidance and both revenue ranges, and avoids the specified traps. It omits the required detail about Ittycheria's prior CEO tenure, Desa |
| W10 | foreign issuer | partial | 0.61 | 2 | 48 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/dce040e966da4af0c35c4d7c5bb900ad) | The answer gets the quarter's two headline earnings figures and the revised-versus-May forecast comparison right, and it correctly reports the pre-tax income figure and growth. However, its explanation omits the required approximately ¥900  |
| X01 | Market analysis | correct | 1.00 | 16 | 93 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/e6d54c6bdd498390199992c2fdda4660) | 16/16 cells correct |
