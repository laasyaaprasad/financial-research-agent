# Scorecard: starter_dev_r1

Agent `starter` · set `dev` · model `moonshotai/Kimi-K2.6` · judge `nvidia/Nemotron-3-Ultra-550b-a55b` · code `6300b5f (M1 harness)` · questions 30 · agent errors 0 · judge errors 0

| Slice | Qs | Fixed answers: fully correct (mean score) | Time-sensitive: rubric score | Numbers with a citation | Cited claims supported | Cited URLs that are primary |
|---|---|---|---|---|---|---|
| All | 30 | 11/25 (0.73) | 0.67 (n=5) | 91% | 71% | 20% |

| Median latency | p95 latency | Tokens / question | Tavily credits / question | Tavily credits total |
|---|---|---|---|---|
| 28.6 s | 69.0 s | 80,723 | 9.0 | 271 |

## By category

| Slice | Qs | Fixed answers: fully correct (mean score) | Time-sensitive: rubric score | Numbers with a citation | Cited claims supported | Cited URLs that are primary |
|---|---|---|---|---|---|---|
| Adjustments | 3 | 1/3 (0.71) | – | 100% | 93% | 33% |
| Beat or miss | 2 | 1/2 (0.75) | – | 85% | 17% | 0% |
| Complex retrieval | 2 | 0/2 (0.44) | – | 100% | 86% | 50% |
| Financial modeling | 3 | 1/3 (0.62) | – | 74% | 70% | 15% |
| Market analysis | 3 | 0/2 (0.62) | 0.33 (n=1) | 84% | 39% | 0% |
| Numerical reasoning | 3 | 1/3 (0.78) | – | 100% | 54% | 43% |
| Qualitative retrieval | 3 | 0/1 (0.25) | 0.50 (n=2) | 100% | 52% | 20% |
| Quantitative retrieval | 8 | 5/6 (0.90) | 1.00 (n=2) | 85% | 94% | 10% |
| Trends | 3 | 2/3 (0.89) | – | 100% | 92% | 46% |

## Per question

| ID | Category | Verdict | Score | Credits | Latency | Trace | Judge rationale |
|---|---|---|---|---|---|---|---|
| G01 | Quantitative retrieval | correct | 1.00 | 6 | 23 s | – | All grading requirements are satisfied: revenue and growth figures are within specified tolerances, the correct fiscal period (FY ended 2026-01-25) is used, and no prohibited calendar or future-quarter data is referenced. |
| G02 | Qualitative retrieval | correct | 1.00 | 6 | 50 s | – | The agent correctly identifies John Ternus as CEO, the September 1, 2026 effective date, and Tim Cook's role as Executive Chairman, with dated primary support from both cited and retrieved sources. |
| G03 | Quantitative retrieval | correct | 1.00 | 8 | 20 s | – | All grading requirements are satisfied: the FY2026 membership fee income and YoY growth match the reference values within tolerance, the correct 52-week annual period is used, FY2025 is not misrepresented as current, units are in millions,  |
| G04 | Quantitative retrieval | correct | 1.00 | 4 | 21 s | – | The agent's answer matches the verified reference exactly: RPO of $664 billion at August 31, 2026 (Q1 FY2027), with approximately 13% expected to be recognized over the next 12 months. All grading criteria are satisfied. |
| G05 | Numerical reasoning | partial | 0.67 | 4 | 14 s | – | The agent correctly used the proper fiscal periods and reported GAAP net margin within tolerance, but revenue growth YoY was outside the ±0.2pp tolerance. |
| G06 | Numerical reasoning | partial | 0.67 | 6 | 29 s | – | The numerical answers are correct within the specified tolerances, but the agent failed to explicitly state the required interpretation of 'Facebook' as Meta Platforms, which is a mandatory requirement per the grading rule. |
| G07 | Numerical reasoning | correct | 1.00 | 28 | 69 s | – | All requirements are met: cRPO value, both growth rates, share, fiscal period, and correct labeling are exactly as disclosed or within allowed tolerances. |
| G08 | Quantitative retrieval | correct | 1.00 | 6 | 16 s | – | The agent's answer accurately quotes the point estimate (~45%), states constant currency basis, identifies the correct fiscal quarter (Q1 FY2027), and does not invent a range. It matches the October 1 snapshot exactly and avoids the tested  |
| G09 | Quantitative retrieval | correct | 1.00 | 4 | 15 s | – | The agent correctly identifies Q1 FY2027 (June 1–August 31, 2026) as the most recent quarter released on October 1, 2026, with revenue of $11.21 billion, which is within the required tolerance of the snapshot value (11,213 million). All gra |
| G10 | Quantitative retrieval | correct | 1.00 | 2 | 10 s | – | The agent correctly refuses to provide an official unit sales figure, clearly labels all third-party numbers as estimates with sources, and does not pass them off as Apple-reported data. The optional provision of iPhone net sales from the 1 |
| G11 | Quantitative retrieval | correct | 1.00 | 10 | 33 s | – | The agent fully complies with the abstain requirement: it refuses to supply unreported Q4 FY2026 actuals, clearly labels the available guidance as guidance, provides only the latest reported quarter (Q3 FY2026) as reference, and avoids all  |
| G12 | Quantitative retrieval | incorrect | 0.43 | 8 | 29 s | – | The agent fails multiple core requirements: it provides a net income figure (which is not publicly disclosed), misstates diluted EPS as non-existent rather than not disclosed, and labels revenue as 'GAAP-equivalent' instead of company-publi |
| G13 | Qualitative retrieval | incorrect | 0.00 | 16 | 41 s | – | The answer fails all four key requirements: it presents outdated developments as current, misattributes NVIDIA's own outlook assumption to a secondary source, does not cleanly separate company statements from media reports, and makes uncite |
| G14 | Adjustments | partial | 0.75 | 3 | 29 s | – | The agent correctly provides both EPS figures and explains the inversion, but fails to name all the largest reconciling line items with their signs as required. Only the equity securities gain is explicitly quantified and signed; the operat |
| G15 | Adjustments | correct | 1.00 | 2 | 10 s | – | All grading requirements are satisfied: adjusted EPS and YoY growth are within specified tolerances, the per-share benefit used matches Costco's disclosed $0.15, and the underlying data aligns with 16-week quarters for both periods. |
| G16 | Beat or miss | partial | 0.50 | 22 | 49 s | – | Agent correctly states guidance ranges and avoids consensus benchmarks, but uses the wrong actual for net sales growth (5.1% total revenue vs 5.0% net sales CC) and consequently misclassifies the net sales verdict as 'Above' instead of 'wit |
| G17 | Qualitative retrieval | partial | 0.25 | 32 | 69 s | – | Agent correctly distinguishes reported vs adjusted growth but misses key drivers cited by management, misquantifies the one-time net benefit, and lacks specific citations for causal claims. |
| G18 | Beat or miss | correct | 1.00 | 2 | 10 s | – | All three grading requirements are satisfied: the beat amount and percentage match the reference values within the specified tolerances, and the agent correctly uses the company's own AI semiconductor revenue guidance as the benchmark. |
| G19 | Trends | correct | 1.00 | 2 | 35 s | – | All quarterly revenue values are within the ±0.5% tolerance, all QoQ growth percentages are within the ±0.5 percentage-point tolerance, the segment used is Data Center market platform (not Compute & Networking), and the fiscal quarters are  |
| G20 | Trends | correct | 1.00 | 2 | 37 s | – | All required figures are present and accurate: net sales for each fiscal year are within the ±0.5% tolerance, gross margin percentages match exactly to 0.1pp, and the change is correctly expressed as 4.6 percentage points. No confusion with |
| G21 | Complex retrieval | incorrect | 0.00 | 1 | 11 s | – | The agent failed to answer the question for Q2 2026, instead providing data for Q2 2024. The correct answer is zero for both classes in Q2 2026. |
| G22 | Financial modeling | correct | 1.00 | 20 | 44 s | – | All grading requirements are satisfied: the implied Q4 low/high figures are exactly correct, the calculation uses the updated guidance and nine-month attributable YTD figure, and the answer correctly identifies the metric as attributable to |
| G23 | Financial modeling | partial | 0.67 | 16 | 35 s | – | The agent correctly calculates the implied revenue and growth, and distinguishes actuals from guidance, but presents the implied revenue in billions instead of the required millions, which constitutes a unit/scale error. |
| G24 | Financial modeling | incorrect | 0.20 | 3 | 23 s | – | The agent's implied 12-month RPO ($79.68bn) and TTM revenue ($67.357bn) are both materially different from the correct values ($86.32bn and $71.776bn), exceeding the allowed tolerances. The TTM construction is fundamentally wrong (missing t |
| G25 | Adjustments | partial | 0.38 | 4 | 20 s | – | The agent correctly reports the EPS figures (consolidated GAAP $17.83, adjusted $4.52; ex-Aerospace GAAP $16.65, adjusted $1.95) and identifies the Quantinuum gain as the key adjustment. However, it fails to provide the exact sales figures  |
| G26 | Complex retrieval | partial | 0.88 | 6 | 43 s | – | The agent correctly provides DKK sales and operating profit figures within tolerance, and all growth rates within 1 percentage point. However, the USD conversion requirement is not met because the agent does not state a specific exchange ra |
| G27 | Trends | partial | 0.67 | 16 | 37 s | – | The agent's Q2 GAAP gross margin is outside the ±0.2pp tolerance (75.0% vs 74.4%), and the week-count disclosure does not explicitly state the prior-year week counts (FY2025 52 weeks, prior Q4 13 weeks) as required. |
| G28 | Market analysis | partial | 0.33 | 10 | 16 s | – | The agent correctly identifies the four numeric capex guidance figures for calendar 2026, but fails to date each guidance to its specific earnings call/release and fails to preserve the lease definitions that distinguish cash capex, finance |
| G29 | Market analysis | partial | 0.75 | 2 | 19 s | – | The agent accurately reports AWS and Google Cloud growth and margins within tolerance, correctly states Azure growth with constant currency basis, and explicitly notes Azure margin is not disclosed. However, the agent fails to label Microso |
| G30 | Market analysis | partial | 0.50 | 20 | 72 s | – | The answer correctly explains why the periods are not directly comparable and avoids a ranking conclusion, but it fails to provide exact comparable sales figures (Costco's numbers are wrong) and omits the required period end dates and week  |
