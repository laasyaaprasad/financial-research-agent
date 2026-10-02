# M3 company lookup and planner: planner_m3_final_verified

Model: `Qwen/Qwen3.8-27B`. Saved SEC inputs; live Nebius extraction + one planning call. **Tavily calls/credits: 0/0.**

Golden answers, evidence, company fields, lens and expected periods are never supplied to the model.

| Acceptance check | Result |
|---|---|
| Company identity, CIK, name and fiscal year end | 30/30 |
| Fixed-question fiscal identities and dates | 25/25 |
| Required researchers included | 30/30 |
| Search budget respected | 30/30 |
| Queries under 400 characters | 30/30 |
| G11 potentially unreported | True |
| Errors | 0 |

Average researchers per successful plan: 2.30.

Period comparison preserves fiscal/calendar identity, year/quarter and implied/actual aggregate basis; display descriptors and company-name prefixes are excluded. Start/end dates have zero tolerance. Multi-company period ownership is tested separately in unit tests.

| ID | Company | Periods | Researchers | Extras / error |
|---|---|---|---|---|
| G01 | True | True | True | none |
| G02 | True | True | True | none |
| G03 | True | True | True | news |
| G04 | True | True | True | none |
| G05 | True | True | True | news |
| G06 | True | True | True | news |
| G07 | True | True | True | news |
| G08 | True | True | True | financials |
| G09 | True | True | True | none |
| G10 | True | True | True | news |
| G11 | True | True | True | none |
| G12 | True | True | True | company |
| G13 | True | True | True | company |
| G14 | True | True | True | company |
| G15 | True | True | True | company |
| G16 | True | True | True | none |
| G17 | True | True | True | financials |
| G18 | True | True | True | none |
| G19 | True | True | True | none |
| G20 | True | True | True | none |
| G21 | True | True | True | news |
| G22 | True | True | True | news |
| G23 | True | True | True | company, news |
| G24 | True | True | True | news |
| G25 | True | True | True | company |
| G26 | True | True | True | news |
| G27 | True | True | True | news |
| G28 | True | True | True | financials |
| G29 | True | True | True | none |
| G30 | True | True | True | company |

## Operations

Median resolution + planning latency: 3.02 s.
Mean model tokens per successful question: 6,267.
Mean planned search credits (not spent): 2.97.
Network requests: `{'api.studio.nebius.ai': 60}`. Other HTTPX hosts are blocked.
