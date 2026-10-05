# Scorecard: half_agent_exact50

Agent `agent` · set `exact50` · model `deepseek-ai/DeepSeek-V4.1-Flash` · judge `gpt-6-luna` · code `6bc163c` · questions 25 · agent errors 0 · judge errors 0

| Slice | Qs | Fixed answers: fully correct (mean score) | Time-sensitive: rubric score | Numbers with a citation | Cited claims supported | Cited URLs that are primary |
|---|---|---|---|---|---|---|
| All | 25 | 6/13 (0.82) | 8/12 all met (0.91) | 100% | 91% | 77% |

| Median latency | p95 latency | Tokens / question | Tavily credits / question | Tavily credits total |
|---|---|---|---|---|
| 28.8 s | 166.7 s | 55,434 | 1.7 | 43 |

## By category

| Slice | Qs | Fixed answers: fully correct (mean score) | Time-sensitive: rubric score | Numbers with a citation | Cited claims supported | Cited URLs that are primary |
|---|---|---|---|---|---|---|
| Beat or miss | 2 | 1/2 (0.93) | – | 100% | 95% | 100% |
| Complex retrieval | 3 | 2/2 (1.00) | 1/1 all met (1.00) | 100% | 81% | 100% |
| Market analysis | 2 | 0/2 (0.62) | – | 100% | 73% | 86% |
| Qualitative retrieval | 2 | – | 1/2 all met (0.94) | 100% | 100% | 71% |
| Quantitative retrieval | 3 | 2/2 (1.00) | 1/1 all met (1.00) | 100% | 94% | 79% |
| ambiguous company | 1 | – | 0/1 all met (0.67) | n/a | n/a | n/a |
| call commentary | 2 | 1/2 (0.94) | – | 100% | 89% | 42% |
| company naming | 2 | – | 1/2 all met (0.75) | 100% | 78% | 100% |
| fiscal vs calendar | 2 | – | 2/2 all met (1.00) | 100% | 100% | 100% |
| foreign issuer | 1 | 0/1 (0.36) | – | 100% | 92% | 33% |
| missing period | 1 | – | 0/1 all met (0.89) | 100% | 100% | 100% |
| open-ended update | 1 | – | 1/1 all met (1.00) | 100% | 100% | 67% |
| recent event | 2 | 0/2 (0.67) | – | 100% | 100% | 75% |
| vague metric | 1 | – | 1/1 all met (1.00) | 100% | 77% | 100% |

## Per question

| ID | Category | Verdict | Score | Credits | Latency | Trace | Judge rationale |
|---|---|---|---|---|---|---|---|
| E02 | missing period | partial | 0.89 | 0 | 46 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/da6d6db378e07649a30fee9f68b0be45) | The Q2 2026 Wells Fargo NIM is correctly identified, period-labeled, and cited, and the response correctly states Q3 had not been reported as of the snapshot date. However, it omits the required expectation that Q3 results were due mid-Octo |
| E06 | vague metric | correct | 1.00 | 0 | 71 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/db54fc8f508b69c433d4dfced2d87bf5) | The answer identifies Berkshire Hathaway as one company, uses and labels the latest reported June 30, 2026 balance sheet, notes Q3 is not yet reported, and clearly distinguishes cash and cash equivalents from Treasury-bill-inclusive liquidi |
| E09 | open-ended update | correct | 1.00 | 4 | 69 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/1623b2c0c69d1d34ba3ac1dc468bcfd0) | The answer accurately identifies MDT and reports the latest Q1 FY2027 results, fiscal timing, headline revenue and growth, labeled EPS, and raised FY2027 guidance with citations. It avoids the specified stale-quarter and investment-view fai |
| E10 | fiscal vs calendar | correct | 1.00 | 0 | 15 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/b43a4b15cb44f7475bc271c4c0cc69cf) | The answer correctly identifies Adobe, treats last year as FY2025 rather than calendar 2025, provides the dates, and cites Adobe's FY2025 total revenue. It does not misrepresent FY2026 as a completed year. |
| E13 | fiscal vs calendar | correct | 1.00 | 0 | 19 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/8f58e823fbc53ed33837b1647a2b4dc5) | The answer meets the fiscal-year interpretation and timing requirements, clearly labels the latest completed fiscal year and its dates, and cites the supported FY2026 net sales figure without treating FY2027 estimates or calendar 2026 as ac |
| E14 | company naming | correct | 1.00 | 0 | 16 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/7255a91344051d6fe5975174faf5debf) | The answer satisfies each requirement: it identifies Brown-Forman as Jack Daniel’s maker, specifies the latest fiscal quarter and fiscal year-end, and cites the company's $911 million net-sales figure. |
| E17 | company naming | partial | 0.50 | 0 | 2 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/e387d8629d9b41e6a0cc3fd0d3ecc1e0) | The answer correctly identifies the tickers as share classes of the same Under Armour company and avoids the tested failure mode, but omits the required latest-quarter details and the cited revenue figure. |
| E19 | ambiguous company | partial | 0.67 | 0 | 3 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/9d7f8f2e062548934cb1e2a36cdce40d) | The response appropriately asks for clarification and gives no figures, but it omits United Parcel Service (UPS) from the plausible-company options. |
| H01 | Complex retrieval | correct | 1.00 | 1 | 18 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/27f43a0efdc15eb36728a9893da24618) | The answer satisfies both required figures and fiscal period, and avoids the specified date and guidance-range failure modes. |
| H02 | Complex retrieval | correct | 1.00 | 2 | 25 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/8dd9e6db4a6b1e9204bb4ba3b482eeeb) | The answer provides the required Q2 FY2026 diluted EPS and FY2026 EBITDA growth guidance, and avoids both specified date-related failure modes. |
| T10 | Complex retrieval | correct | 1.00 | 1 | 27 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/551124954a86220cb3c21e9a620b08c2) | The answer reports both updated FY2027 ranges and their prior June ranges, correctly attributes the update to the September 23 Q1 release, and does not misrepresent the superseded guidance as current. |
| T11 | Beat or miss | partial | 0.86 | 0 | 20 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/02c95a75cb4ecb83fc08df943ea48474) | The core comparisons and the refund context are correct and benchmarked to company guidance. However, the answer omits the required adjusted-EPS comparison showing that EPS excluding the $0.86 refund-related benefit was about $2.06 and stil |
| T12 | Beat or miss | correct | 1.00 | 0 | 26 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/04bdc982822b4a4e779be97295adfffd) | The answer correctly compares both actual results with the company's Q3 FY2026 guidance and identifies both as within range. It does not misuse GAAP EPS or consensus; the optional GAAP comparison is omitted. |
| T15 | Qualitative retrieval | partial | 0.89 | 2 | 37 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/35cabc517a6b22d2c5a8e6bd27b1535e) | The response correctly identifies and supports the latest October 1, 2026 results and most of the key figures and FY2027 outlook. It omits the specifically expected 6% year-over-year Q4 revenue growth in U.S. dollars, although it gives the  |
| T16 | Qualitative retrieval | correct | 1.00 | 2 | 56 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/960d799837011e06de344729ab8b3203) | The answer is current, relies on Workday’s September 29 SEC filing for the key claims, accurately reports the workforce and office actions, charge amounts and timing, and the guidance exception. It keeps the earlier February reduction disti |
| T17 | Quantitative retrieval | correct | 1.00 | 2 | 26 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/a7041d9f744a83d26cb7756f3d2839bd) | The answer clearly abstains on Q4 FY2026 actuals as of the specified snapshot date. It includes reported Q3 figures and Q4 guidance only with their periods and status clearly distinguished, and does not misrepresent either as Q4 actuals. |
| T18 | Quantitative retrieval | correct | 1.00 | 1 | 20 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/8afe2535ea3cdc7ff6bd58fb6b190c11) | The answer abstains from assigning a reported Cybertruck delivery count and accurately identifies Tesla's combined reporting categories and the absence of a Cybertruck unit count in the 10-Q. |
| T19 | Quantitative retrieval | correct | 1.00 | 3 | 242 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/2ae19f8f42a85a593cd5e948c00551d4) | The answer clearly abstains on Enterprise’s requested figures, identifies the company as privately held and non-filing with the SEC, and does not substitute Hertz or Avis values for Enterprise. Peer net-income figures are separately labeled |
| T20 | Market analysis | partial | 0.50 | 2 | 29 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/d6c885fc149f05e1607038aecbcd6791) | The Mastercard figure and matching period are correct, and the answer avoids treating Visa's March quarter as the requested period. However, it omits Visa's required June-quarter revenue and the resulting difference, so it does not provide  |
| W01 | call commentary | partial | 0.88 | 5 | 130 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/643d1a956662674e918c32c30e712453) | The answer gives the required current NII and operating-leverage outlooks and correctly compares the NII outlook with January and April. However, its operating-leverage comparison gives a prior 200–300 bps range rather than the required Apr |
| W02 | call commentary | correct | 1.00 | 3 | 85 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/8c93613dd0ddf29ad6f6a4166e4b4f8b) | All required figures and the approximate Low NA EUV shipment count are stated. The answer also avoids substituting the total-sales outlook, 2027 capacity increase, Q3 guidance, or Q3 2026 results for the requested Q2-call figures. |
| W05 | recent event | partial | 0.61 | 5 | 92 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/b1497e0e99178ad2c4d32a8433bab9f3) | The answer correctly identifies the $7.02 current proposal as best-and-final and non-binding, and correctly gives the $0.27 (4.0%) increase from the $6.75 first proposal. However, it omits the cash/rollover terms and the proposal and reaffi |
| W06 | recent event | partial | 0.73 | 3 | 38 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/43d64c8efa1de8a1bdf137b440a18955) | The guidance characterization and both revenue ranges are correct, and the answer gives the departure, historical tenure, effective date, and permanent-CEO search. However, it does not clearly identify Dev Ittycheria as the interim CEO, omi |
| W10 | foreign issuer | incorrect | 0.36 | 6 | 167 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/247c4b318d958a755b6b9845329ebb37) | Although it gets the revised-versus-previous operating-income forecast right and avoids the period/forecast/net-income failure conditions, it omits the required Q1 operating-income amount, does not establish the attributable net-income figu |
| X01 | Market analysis | partial | 0.75 | 1 | 119 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/52577a69e21b74fa4e27ab2a6fa53b52) | 12/16 cells correct |
