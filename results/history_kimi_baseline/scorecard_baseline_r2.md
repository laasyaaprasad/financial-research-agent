# Scorecard: baseline_r2

Agent: `baseline` · Judge: `deepseek-ai/DeepSeek-V4-Pro` · Questions: 30 · Errors: 0

## Overall

| Slice | Qs | Fixed: fully correct (mean score) | Time-sensitive: rubric score | Numbers with a citation | Cited claims supported | Cited URLs that are primary |
|---|---|---|---|---|---|---|
| All | 30 | 13/25 (0.80) | 0.30 (n=5) | 85% | 75% | 24% |

## Operations (per question)

| Median latency | p95 latency | Tokens | Tavily credits | Searches |
|---|---|---|---|---|
| 20.4 s | 45.3 s | 58,868 | 7.2 | 3.8 |

Cited claims whose URL the agent never retrieved: 4 of 227.

## By category

| Slice | Qs | Fixed: fully correct (mean score) | Time-sensitive: rubric score | Numbers with a citation | Cited claims supported | Cited URLs that are primary |
|---|---|---|---|---|---|---|
| Adjustments | 3 | 1/3 (0.78) | – | 89% | 97% | 30% |
| Beat or miss | 2 | 2/2 (1.00) | – | 86% | 61% | 50% |
| Complex retrieval | 2 | 0/2 (0.33) | – | 94% | 100% | 50% |
| Financial modeling | 3 | 2/3 (0.75) | – | 64% | 79% | 8% |
| Market analysis | 3 | 2/2 (1.00) | 0.25 (n=1) | 78% | 36% | 43% |
| Numerical reasoning | 3 | 1/3 (0.78) | – | 72% | 100% | 20% |
| Qualitative retrieval | 3 | 0/1 (0.50) | 0.62 (n=2) | 100% | 74% | 11% |
| Quantitative retrieval | 8 | 4/6 (0.90) | 0.00 (n=2) | 85% | 68% | 13% |
| Trends | 3 | 1/3 (0.81) | – | 96% | 85% | 33% |

## By difficulty

| Slice | Qs | Fixed: fully correct (mean score) | Time-sensitive: rubric score | Numbers with a citation | Cited claims supported | Cited URLs that are primary |
|---|---|---|---|---|---|---|
| easy | 10 | 3/7 (0.82) | 0.33 (n=3) | 81% | 80% | 23% |
| medium | 12 | 7/11 (0.80) | 0.25 (n=1) | 94% | 79% | 20% |
| hard | 8 | 3/7 (0.76) | 0.25 (n=1) | 78% | 66% | 29% |

## Per question

| ID | Category | Verdict | Score | Credits | Latency | Judge rationale |
|---|---|---|---|---|---|---|
| G01 | Quantitative retrieval | partial | 0.75 | 10 | 36 s | The revenue number ($215,900M) and growth (65%) are both within tolerance. However, the agent explicitly states the wrong fiscal year-end date: "January 31, 2026" instead of the correct January 25, 2026. The grading rule |
| G02 | Qualitative retrieval | correct | 1.00 | 1 | 17 s | The agent correctly identifies John Ternus as CEO, September 1, 2026 as the effective date, and Tim Cook's role as Executive Chairman. All three factual elements are supported by dated primary sources (Apple Newsroom, Ap |
| G03 | Quantitative retrieval | correct | 1.00 | 2 | 10 s | The agent correctly reports FY2026 membership fee income as $5,907 million and ~11% YoY growth, both within tolerance. The answer uses the 52-week annual column, does not present FY2025 as current, and sources are from F |
| G04 | Quantitative retrieval | partial | 0.67 | 6 | 28 s | The agent correctly identifies the RPO as $664 billion and the correct fiscal period (Q1 FY2027 = August 31, 2026). However, the next-12-month recognition percentage is stated as approximately 12%, while the verified ref |
| G05 | Numerical reasoning | partial | 0.67 | 8 | 14 s | The agent's revenue growth of +12% is 0.225pp above the reference 11.7750%, which exceeds the ±0.2pp tolerance. The net margin of ~21.0% is within tolerance. The inputs appear to be from the correct fiscal periods based  |
| G06 | Numerical reasoning | partial | 0.67 | 2 | 9 s | The revenue figure is correct and within tolerance, and the agent correctly resolves 'Facebook' to Meta Platforms. However, the Reality Labs operating margin is reported as a positive ratio (~1,072%) rather than the requ |
| G07 | Numerical reasoning | correct | 1.00 | 5 | 24 s | All three requirements are met: cRPO is $33.5B (exact match), both growth rates are 14% and correctly labeled as nominal and constant currency, and the share of ~50.5% is within ±1pp of the reference 50.53%. The agent co |
| G08 | Quantitative retrieval | incorrect | 0.00 | 38 | 96 s | The agent completely failed to use the latest guidance. Despite having retrieved sources that clearly state the correct guidance (approximately 45% constant currency for Q1 FY2027 from the July 2026 call), the agent inst |
| G09 | Quantitative retrieval | incorrect | 0.00 | 16 | 42 s | The agent identified Q4 FY2025 (ended May 31, 2025) as the most recent quarter. However, as of the query date (October 1, 2026), Nike had already released Q1 FY2027 results (June 1–August 31, 2026) with revenue of $11,21 |
| G10 | Quantitative retrieval | correct | 1.00 | 2 | 16 s | The agent correctly refuses to provide an official unit sales figure, clearly stating Apple does not disclose this metric. It provides the correct iPhone net sales figure from the 10-K ($209.6B). All third-party shipment |
| G11 | Quantitative retrieval | correct | 1.00 | 2 | 13 s | The agent correctly refuses to provide actual results for the unreported period, clearly stating the quarter had not been reported as of October 1, 2026. It offers management's Q4 outlook and analyst consensus estimates, |
| G12 | Quantitative retrieval | correct | 1.00 | 3 | 14 s | The agent correctly identifies Cargill as privately held with no public 10-K, states that net income and diluted EPS are not publicly disclosed, supplies the company-published FY2026 revenue of ~$164 billion with a citat |
| G13 | Qualitative retrieval | partial | 0.25 | 4 | 20 s | The agent correctly identifies and paraphrases NVIDIA's stated China assumption from the Q2 FY27 outlook (point 2 met). However, it fails on three other requirements: (1) developments are not consistently dated and sever |
| G14 | Adjustments | partial | 0.75 | 2 | 15 s | The agent correctly provides both EPS figures ($2.46 GAAP, $2.22 non-GAAP) and explains the counter-intuitive direction driven by equity security gains. However, the agent fails to name the largest reconciling line items |
| G15 | Adjustments | correct | 1.00 | 4 | 11 s | All grading requirements are met. The agent provides the correct adjusted EPS of $6.60 (exact match), YoY growth of ~12.4% (within 0.5pp of 12.4361%), uses Costco's disclosed $0.15 per-share benefit, and correctly refere |
| G16 | Beat or miss | correct | 1.00 | 4 | 25 s | All four grading requirements are met. The agent correctly states the three guidance ranges from the Q1 FY2027 release, correctly states the actual results (using net sales CC growth, not total revenue), gives the correc |
| G17 | Qualitative retrieval | partial | 0.50 | 12 | 26 s | The agent correctly identifies tariff refunds as the key one-time driver and quantifies the benefit (750 bps / 7.5 pp, ~$2.9B). However, the answer fails to: (1) list all management-cited drivers (missing sales growth, a |
| G18 | Beat or miss | correct | 1.00 | 8 | 28 s | All three grading requirements are met. The agent correctly identifies the Q3 FY2026 AI semiconductor revenue as $16.7B vs. the company's own Q2-call guidance of $16.0B, yielding a $0.7B beat (~4.4%), both within the spe |
| G19 | Trends | incorrect | 0.60 | 10 | 25 s | The question asks for specific quarterly Data Center revenue values and QoQ growth for Q2 FY2026 through Q2 FY2027. The agent provided no quarterly revenue figures and no QoQ growth calculations. While the agent correctl |
| G20 | Trends | correct | 1.00 | 2 | 9 s | All seven grading requirements are met. Net sales figures for all three fiscal years match exactly. Gross margin percentages for all three years match exactly to 0.1pp. The change is correctly expressed in percentage poi |
| G21 | Complex retrieval | incorrect | 0.00 | 2 | 11 s | The agent refused to answer for Q2 2026, claiming it is in the future, and instead provided Q2 2024 data with substantial positive repurchase amounts for both Class A and Class C. The correct answer is that Alphabet disc |
| G22 | Financial modeling | correct | 1.00 | 2 | 11 s | All requirements are met. The agent correctly uses the updated FY2026 guidance range ($4.75B–$5.00B), the nine-month YTD attributable net income ($3.808B), and computes the implied Q4 attributable net income as $942M (lo |
| G23 | Financial modeling | correct | 1.00 | 12 | 25 s | All four grading requirements are met. The implied 9M FY2027 revenue of $285.8B is within 0.5% of the reference 285,836 million. Growth of ~93.4% is within 0.5pp of 93.38%. The agent clearly distinguishes actual/reported |
| G24 | Financial modeling | incorrect | 0.25 | 4 | 30 s | The agent used the wrong RPO recognition percentage (12% instead of ~13%), producing an implied 12-month RPO of $79.7B vs the correct $86.32B — well outside the ±1% tolerance. The TTM revenue figure is correct at $71.8B, |
| G25 | Adjustments | partial | 0.60 | 10 | 21 s | The agent correctly reports consolidated sales ($9,719M) and ex-Aerospace sales ($5,187M), and keeps the consolidated and ex-Aerospace EPS bases distinct. However, it fails to identify the Quantinuum gain as -$15.87 per  |
| G26 | Complex retrieval | partial | 0.67 | 2 | 10 s | The agent correctly reports the core DKK sales and operating profit figures with proper labeling and gets the reported/CER growth rates right (operating profit reported growth of -0.5% is within the 1pp tolerance of -1%) |
| G27 | Trends | partial | 0.83 | 6 | 11 s | All four GAAP gross margin figures are correct and within tolerance. The week-count distortion is properly flagged with both FY (53 vs 52) and Q4 (14 vs 13) week counts disclosed. However, the full-year revenue growth is |
| G28 | Market analysis | incorrect | 0.25 | 24 | 40 s | The agent gets the headline numbers approximately right for all four companies, but fails on multiple critical requirements: (1) no dates are provided for any guidance, (2) lease/cash definitions are not preserved for Me |
| G29 | Market analysis | correct | 1.00 | 10 | 45 s | All four grading requirements are met. AWS and Google Cloud growth and margin figures are within the ±0.5pp tolerance. Azure growth is correctly stated at 43% with the constant currency note. The agent explicitly states  |
| G30 | Market analysis | correct | 1.00 | 3 | 35 s | All four grading requirements are met. The agent provides exact comp figures with adjustment bases (2.6% ex-fuel for Walmart, 7.2% gas/FX-adjusted for Costco, 3.8% for Target). End dates are stated for all three, and Cos |
