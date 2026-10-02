# M3 company lookup and planner: planner_m3_validation_first

Model: `Qwen/Qwen3.8-27B`. Saved SEC inputs; live Nebius extraction + one planning call. **Tavily calls/credits: 0/0.**

Golden answers, evidence, company fields, lens and expected periods are never supplied to the model.

Dataset: validation. Frozen developer-authored validation. First-run results retained separately; repeated runs are regression confirmation. Not a blind or user-verified holdout.

| Acceptance check | Result |
|---|---|
| All required checks | 16/18 |
| Company identity, CIK, name and fiscal year end | 16/18 |
| Fixed-question fiscal identities and dates | 17/18 |
| Periods with correct company ownership | 16/18 |
| Required researchers included | 18/18 |
| Search budget respected | 18/18 |
| Queries under 400 characters | 18/18 |
| Expected unreported/missing data flagged | 2/2 |
| G11 potentially unreported | not run |
| Errors | 0 |

Average researchers per successful plan: 1.67.

Period comparison preserves fiscal/calendar identity, year/quarter and implied/actual aggregate basis; display descriptors and company-name prefixes are excluded. Start/end dates have zero tolerance. Ownership compares every company-period pair, allowing grouping of identical periods without hiding swapped, missing or duplicate owners.

| ID | Company | Periods | Ownership | Researchers | Extras / error |
|---|---|---|---|---|---|
| V01 | True | True | True | True | none |
| V02 | True | True | True | True | none |
| V03 | True | True | True | True | none |
| V04 | True | True | True | True | none |
| V05 | True | True | True | True | none |
| V06 | True | True | True | True | none |
| V07 | True | True | True | True | none |
| V08 | True | True | True | True | none |
| V09 | True | True | True | True | none |
| V10 | False | False | False | True | company, news |
| V11 | False | True | False | True | news |
| V12 | True | True | True | True | none |
| V13 | True | True | True | True | none |
| V14 | True | True | True | True | none |
| V15 | True | True | True | True | none |
| V16 | True | True | True | True | none |
| V17 | True | True | True | True | company, financials |
| V18 | True | True | True | True | company |

## Operations

Median resolution + planning latency: 3.06 s.
Mean model tokens per successful question: 4,872.
Mean planned search credits (not spent): 2.17.
Network requests: `{'api.studio.nebius.ai': 36}`. Other HTTPX hosts are blocked.
