# Scorecard: starter_hard_r1

Agent `starter` · set `hard` · model `moonshotai/Kimi-K2.6` · judge `nvidia/Nemotron-3-Ultra-550b-a55b` · code `e4ab79c` · questions 20 · agent errors 0 · judge errors 0

| Slice | Qs | Fixed answers: fully correct (mean score) | Time-sensitive: rubric score | Numbers with a citation | Cited claims supported | Cited URLs that are primary |
|---|---|---|---|---|---|---|
| All | 20 | 10/18 (0.68) | 0.67 (n=2) | 95% | 78% | 13% |

| Median latency | p95 latency | Tokens / question | Tavily credits / question | Tavily credits total |
|---|---|---|---|---|
| 32.4 s | 169.3 s | 123,612 | 13.5 | 270 |

## By category

| Slice | Qs | Fixed answers: fully correct (mean score) | Time-sensitive: rubric score | Numbers with a citation | Cited claims supported | Cited URLs that are primary |
|---|---|---|---|---|---|---|
| Adjustments | 1 | 1/1 (1.00) | – | 100% | 83% | 100% |
| Beat or miss | 2 | 2/2 (1.00) | – | 100% | 44% | 0% |
| Complex retrieval | 3 | 0/3 (0.17) | – | 100% | 93% | 0% |
| Financial modeling | 2 | 1/2 (0.58) | – | 84% | 75% | 0% |
| Numerical reasoning | 2 | 1/2 (0.50) | – | 100% | 50% | 0% |
| Qualitative retrieval | 3 | 1/1 (1.00) | 0.67 (n=2) | 94% | 100% | 0% |
| Quantitative retrieval | 7 | 4/7 (0.79) | – | 96% | 92% | 33% |

## Per question

| ID | Category | Verdict | Score | Credits | Latency | Trace | Judge rationale |
|---|---|---|---|---|---|---|---|
| H01 | Complex retrieval | incorrect | 0.00 | 38 | 169 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/a9c8458ad941110125c39f86b5f8bf5f) | No answer produced. |
| H02 | Complex retrieval | incorrect | 0.00 | 14 | 62 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/be5f0f5657289a5ed5530c5611db3ca6) | Both required key points are incorrect. The agent used fiscal Q3 2026 results (released 2026-03-09) and the later 18%-20% EBITDA outlook, both of which post-date the as_of date of March 2, 2026. The correct values as of that date are fiscal |
| H03 | Quantitative retrieval | correct | 1.00 | 18 | 35 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/902e18505766788a61b38907814dea51) | The agent's answer precisely matches both required key points: it identifies the correct fiscal quarter (Q3 2025 ended Sep 27, 2025), reports domestic same-store sales growth of -5.6%, and states system-wide sales of $1,356 million ($1.4 bi |
| H04 | Complex retrieval | partial | 0.50 | 18 | 74 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/30d6968cef4b800baa9420ed2a3e7f53) | The agent correctly identified the latest reported quarter (fiscal Q3 2026) and its adjusted EPS ($2.38), but provided an outdated net sales growth guidance range (3.5%-4.5%) instead of the updated 3.5%-4.0% range that was in effect on the  |
| H05 | Adjustments | correct | 1.00 | 2 | 19 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/fddc31c68448fdab20aebc0c716ee30a) | The agent correctly provided both GAAP and adjusted diluted EPS guidance ranges as of July 15, 2026, matching the May 28, 2026 update, and did not confuse with the later August 27 update. |
| H06 | Quantitative retrieval | incorrect | 0.50 | 2 | 7 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/6f8a8d27131701239b768131eb23d9ed) | The core figure for remaining performance obligations is reported with a units error (missing 'thousands'), which the grading rule explicitly treats as a failure. Although the 23% recognition share is correct, the RPO amount is wrong in sca |
| H07 | Quantitative retrieval | correct | 1.00 | 2 | 13 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/0ce80fb4dc3a8b376aa11bd628236eb4) | The agent correctly identifies all four customers that contributed 10% or more of Fabrinet's revenue in fiscal 2026 and provides the exact percentages from the 10-K (19.9%, 16.3%, 10.7%, 10.5%), matching the reference answer within the allo |
| H08 | Quantitative retrieval | correct | 1.00 | 4 | 11 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/e3d6557b3ca31486e2cfddec2fd4f677) | The agent's answer precisely matches the required figure, date, and unit, with no confusion with total backlog or other dates. |
| H09 | Quantitative retrieval | partial | 0.25 | 32 | 73 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/2111b24f61207efdc2ab81acca2e8987) | The agent correctly identified the total repurchase cost (~$45.6M) and the remaining authorization (~$973M) for the correct fiscal quarter (Q1 FY2027 ended July 31, 2026). However, the agent failed to provide the number of shares repurchase |
| H10 | Numerical reasoning | incorrect | 0.00 | 16 | 79 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/39113c1e308a702427789e35bf32d93c) | No answer produced. |
| H11 | Financial modeling | correct | 1.00 | 27 | 72 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/80a18d0f49481f580485ea01bf02c638) | All grading requirements are satisfied. The agent correctly derived implied Q4 FY2026 revenue, GAAP income from operations, and GAAP operating margin using the proper FY2026 and nine-month figures, with all values within the specified toler |
| H12 | Numerical reasoning | correct | 1.00 | 24 | 95 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/cb1ea531d4dfb1c35616ae9b7aa91e2a) | All required figures are within the specified tolerances, the computation method yields the correct TTM values, and none of the failure modes are present. |
| H13 | Financial modeling | incorrect | 0.17 | 6 | 12 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/1a37d15619ab35059795b815af207e48) | The agent's answer fails on all substantive requirements: revenue is slightly outside tolerance, operating margin is significantly off (0.76pp vs allowed 0.2pp), implied income from operations is far from the reference, and the margin likel |
| H14 | Quantitative retrieval | correct | 1.00 | 16 | 51 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/71d7972ede51136dd14fa2acb2949e24) | The agent correctly abstains from providing Q4 2026 revenue or EPS as reported fact, clearly states results have not been announced as of early October 2026, and avoids all failure modes (fabrication, mislabeling guidance/estimates as repor |
| H15 | Qualitative retrieval | correct | 1.00 | 10 | 21 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/3caacc11378599e114cc21c7a0b8ef13) | The agent correctly states that Kinsale does not disclose a combined ratio for the Commercial Property division, only consolidated ratios. It provides quarterly consolidated combined ratios as context, which is acceptable. No division-level |
| H16 | Quantitative retrieval | partial | 0.80 | 3 | 16 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/a7cc8bb1e14156113a4ae6a01e543555) | The agent correctly identifies that no 10-Q exists for June 30, 2026, provides the correct last available quarter (June 30, 2025) with accurate figures labeled as 2025, and does not fabricate any 2026 numbers. However, the agent fails to ex |
| H17 | Beat or miss | correct | 1.00 | 20 | 41 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/56cacc5e6ba796387b58f23c5931f6f5) | The agent's answer correctly identifies all three key metrics relative to the company's April 29, 2026 guidance: revenue above, GAAP diluted EPS above, and non-GAAP operating margin within (at the high end). It uses the proper benchmark, av |
| H18 | Beat or miss | correct | 1.00 | 4 | 17 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/6831ea9284ac1229d7999d51dcd94b2b) | All key metrics (revenue, non-GAAP operating margin, GAAP EPS) are correctly compared to the company's May 2026 guidance. GAAP EPS is correctly identified as below guidance, and the quarter is not portrayed as a clean beat. No failure modes |
| H19 | Qualitative retrieval | correct | 1.00 | 2 | 7 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/fd49cd0a778aaa51fa8929e05f35d53c) | The agent's answer accurately identifies the most significant news as the definitive agreement to acquire Brakebush Brothers announced September 30, 2026, for approximately $1.055 billion, expected to close in Hormel's fiscal Q1 2027 subjec |
| H20 | Qualitative retrieval | incorrect | 0.33 | 12 | 29 s | [trace](https://us.cloud.langfuse.com/project/cmuqbnq6m0cg6ad0c1jrlh729/traces/ea08375a42a977c9a6ba2fddd61d11e0) | The agent's answer fails to meet three of the four key dated requirements: the quarterly results lack the exact date (Sept 30) and several key figures (EPS, selling price decline); the dividend point omits the cumulative loss recovery amoun |
