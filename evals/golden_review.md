# Golden-answer source review

Snapshot: **October 1, 2026, 17:51:43 America/Los_Angeles** (`2026-10-01T17:51:43-07:00`).

`evals/golden.jsonl` originally contained 30 drafted questions with empty answers, evidence and periods. All 30 now have source-backed reference text, evidence IDs and period metadata; 25 fixed-answer rows use primary sources. The five dynamic rows remain reference-free and their answers are labeled snapshots.

**Review status:** agent source-check, not human sign-off. Every `verified_by_human` remains `false`. M1 is not complete: user verification, the remaining primary-source gap below, and the baseline harness/scorecard acceptance criteria remain.

## Corrections to premises, grading and source instructions

| IDs | Correction |
| --- | --- |
| G01 | FY2026 begins January 27, 2025; corrected fiscal-calendar description and 10-K section. |
| G03 | Uses the 52-week annual membership-fee columns in the September 24 release. An annual 10-K is not required for this snapshot. |
| G08 | Azure guide is an approximately 45% constant-currency point estimate, not a range. |
| G09 | Nike Q1 FY2027 was available at the after-market cutoff on October 1. Earlier same-day runs may need Q4 FY2026. |
| G11 | Explicitly froze the question at October 1, 2026 so the expected refusal will not become false after Apple reports Q4. |
| G12 | Private-company EPS can exist; the issue is public disclosure. Removed the unsupported audit-status requirement and the blanket no-EDGAR-filings claim. |
| G14 | Removing equity-security gains drives non-GAAP EPS below GAAP. Stock compensation remains included in FY2027 non-GAAP measures. |
| G16–G17 | Net sales CC growth is 5.0%, within the guide; 5.1% refers to total revenue. Management quantified the tariff-refund growth contribution at approximately 750 bps. |
| G19 | Preserved Data Center market-platform comparability and used a Q1 FY2026 baseline for the first QoQ rate. |
| G21 | No Class A or Class C repurchases. Replaced the assumed populated class table and percentage tolerance with exact zero values; verified filing date July 23. |
| G23 | Quarter sum and the filed six-month total differ by USD 1M; recorded the rounding difference and separated actual quarters from guidance. |
| G24 | Current 10-Q comparative revenue can supply Q1 FY2026. Explicitly builds TTM revenue before comparing the approximate RPO amount. |
| G25 | Actual Q2 close was June 27 despite June 30 presentation; the June 29 spin is a Q3 event. Quantinuum deconsolidation, not the Aerospace spin itself, drives the EPS adjustment. |
| G26 | Official 2025 annual-average FX; management rounds operating-profit growth to -1%, while the five-year table gives -0.5%. |
| G27 | Confirmed 53-week year and 14-week Q4. Week counts are in the Q3 10-Q, not the Q4 release. |
| G28 | Both Microsoft and Amazon give numeric CY2026 capex guides. Preserved each lease/cash definition and corrected the qualitative-only premise. |
| G29 | Azure growth can be supplied, but its quarterly revenue dollars and operating margin are not disclosed separately. |
| G30 | Walmart and Target cover 13 weeks, Costco 16; use each disclosed adjustment basis and avoid a market-share ranking. |

The per-question sources below support these corrections. Numeric inputs, formulas and extracted source facts are also stored in the JSONL.

## Source limitations and date conventions

- **G28 Amazon:** approximately USD 220B CY2026 cash capex was checked against third-party copies of the July 30 call and corroborating AP coverage. A company-hosted transcript supporting this exact guide was not retrieved. Its evidence is explicitly labeled `secondary_transcript`; this row does not yet meet the primary-only reference-source criterion.
- **G13:** news is a dated research snapshot. C4ADS publication and media reporting are not regulatory enactments. The August 26 company outlook is labeled older context, outside the 30-day news window. This row follows its news-specific rubric rather than treating press reporting as a company filing.
- Period ends and week counts come from source documents. When a start date is not printed, it is derived inclusively from the disclosed week count and prior period end. Honeywell uses the filing’s calendar presentation in `expected_periods`, with the actual June 27 close recorded separately.
- Dynamic rows G02, G08, G09, G13 and G28 must be refreshed against the run timestamp; their snapshot answers must not be treated as timeless fixed references.

## Validation

Passed 774 structural, citation-reference, cutoff, period-length and arithmetic checks. Confirmed 30 unique ordered IDs, the original coverage metadata and five dynamic classifications, all 25 static answers with primary evidence, and zero human-verification flags. Recomputed numerical answers and checked weekly period lengths and Micron’s quarterly-to-annual revenue sum. These are data checks; no baseline agent score is claimed.

## References for all 30 questions

### G01 — NVIDIA Corporation (NVDA)

What was NVIDIA's total revenue for fiscal 2026, in USD millions, and how much did it grow vs fiscal 2025?

NVIDIA FY2026 revenue was USD 215,938 million, versus USD 130,497 million in FY2025: growth of 65.4735% (65% as rounded in the filing). [G01-E1](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm)

Periods: FY2026: 2025-01-27 to 2026-01-25; FY2025: 2024-01-29 to 2025-01-26.

- [G01-E1: NVIDIA FY2026 Form 10-K](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm) — Consolidated Statements of Income; Note 1 fiscal-year policy; primary; dated 2026-02-25.

### G02 — Apple Inc. (AAPL)

Who is Apple's CEO right now, when did the change take effect, and what is Tim Cook's current role?

As of October 1, 2026, John Ternus is Apple CEO. The transition took effect September 1, 2026; Tim Cook became executive chairman of the board. [G02-E1](https://www.apple.com/newsroom/2026/04/tim-cook-to-become-apple-executive-chairman-john-ternus-to-become-apple-ceo/)

- [G02-E1: Apple CEO succession announcement](https://www.apple.com/newsroom/2026/04/tim-cook-to-become-apple-executive-chairman-john-ternus-to-become-apple-ceo/) — Leadership transition; primary; dated 2026-04-20.

### G03 — Costco Wholesale Corporation (COST)

What was Costco's membership fee income for fiscal 2026, in USD millions, and the YoY growth?

Costco FY2026 membership fee income was USD 5,907 million, versus USD 5,323 million in FY2025: 10.9713% YoY growth. These are the 52-week annual columns. [G03-E1](https://investor.costco.com/news/news-details/2026/Costco-Wholesale-Corporation-Reports-Fourth-Quarter-and-Fiscal-Year-2026-Operating-Results/default.aspx)

Periods: FY2026: 2025-09-01 to 2026-08-30; FY2025: 2024-09-02 to 2025-08-31.

- [G03-E1: Costco Q4 and FY2026 earnings release](https://investor.costco.com/news/news-details/2026/Costco-Wholesale-Corporation-Reports-Fourth-Quarter-and-Fiscal-Year-2026-Operating-Results/default.aspx) — Consolidated Statements of Income, 52 Weeks Ended columns; primary; dated 2026-09-24.

Review note: Verified against the company’s September 24 release, using the 52-week annual columns. No assumption that the FY2026 10-K was already available is required.

### G04 — Oracle Corporation (ORCL)

What was Oracle's total remaining performance obligations at the end of Q1 FY2027, and what percentage does Oracle expect to recognize as revenue over the next 12 months?

Oracle had USD 664 billion of RPO at August 31, 2026 and expected to recognize approximately 13% over the next twelve months. [G04-E1](https://www.sec.gov/Archives/edgar/data/1341439/000119312526389274/orcl-20260831.htm)

Periods: Q1 FY2027: 2026-06-01 to 2026-08-31.

- [G04-E1: Oracle Q1 FY2027 Form 10-Q](https://www.sec.gov/Archives/edgar/data/1341439/000119312526389274/orcl-20260831.htm) — Note 1, Remaining Performance Obligations; primary; dated 2026-09-11.

### G05 — Cisco Systems, Inc. (CSCO)

What was Cisco's fiscal 2026 total revenue growth YoY and its GAAP net margin (net income / revenue)?

Cisco FY2026 revenue growth was 11.7750% YoY. GAAP net margin was 20.9507%: USD 13,267 million GAAP net income / USD 63,325 million revenue. FY2025 revenue was USD 56,654 million. [G05-E1](https://www.sec.gov/Archives/edgar/data/858877/000085887726000132/csco-20260725.htm)

Periods: FY2026: 2025-07-27 to 2026-07-25; FY2025: 2024-07-28 to 2025-07-26.

- [G05-E1: Cisco FY2026 Form 10-K](https://www.sec.gov/Archives/edgar/data/858877/000085887726000132/csco-20260725.htm) — Consolidated Statements of Operations; MD&A annual results; primary.

### G06 — Meta Platforms, Inc. (META; formerly Facebook, Inc. / FB)

What was Facebook's total revenue in Q2 2026, and what was the Reality Labs operating margin (operating loss / segment revenue) in that quarter?

Interpreting Facebook as Meta Platforms, rather than the Facebook app, Q2 2026 total revenue was USD 60,801 million. Reality Labs revenue was USD 431 million and its signed operating loss was USD -4,619 million, giving an operating margin of -1071.6937%. [G06-E1](https://www.sec.gov/Archives/edgar/data/1326801/000162828026050596/meta-06302026xexhibit991.htm)

Periods: Q2 2026: 2026-04-01 to 2026-06-30.

- [G06-E1: Meta Q2 2026 earnings release, Form 8-K Exhibit 99.1](https://www.sec.gov/Archives/edgar/data/1326801/000162828026050596/meta-06302026xexhibit991.htm) — Segment Results, three months ended June 30, 2026; primary; dated 2026-07-29.

### G07 — Salesforce, Inc. (CRM)

What was Salesforce's current RPO at the end of Q2 FY2027, its YoY growth in both nominal and constant currency, and what share of total RPO it represents?

Salesforce cRPO at July 31, 2026 was USD 33.5 billion, up 14% YoY in both nominal and constant currency terms. Total RPO was USD 66.3 billion, so cRPO represented 50.5279% of total RPO. [G07-E1](https://investor.salesforce.com/news/news-details/2026/Salesforce-Delivers-Record-Second-Quarter-Fiscal-2027-Results/default.aspx)

Periods: Q2 FY2027: 2026-05-01 to 2026-07-31.

- [G07-E1: Salesforce Q2 FY2027 earnings release](https://investor.salesforce.com/news/news-details/2026/Salesforce-Delivers-Record-Second-Quarter-Fiscal-2027-Results/default.aspx) — Highlights and Remaining Performance Obligation; primary; dated 2026-08-26.

### G08 — Microsoft Corporation (MSFT)

What is Microsoft's most recent guidance for Azure revenue growth for the upcoming quarter, and is it in constant currency?

The July 29, 2026 FY2026 Q4 call guided Azure revenue growth of approximately 45% in constant currency for Q1 FY2027, July 1–September 30, 2026. This was a point estimate, not a disclosed growth range. It is the latest earnings-call guide before the October 1 snapshot. [G08-E1](https://www.microsoft.com/en-us/investor/events/fy-2026/earnings-fy-2026-q4)

Periods: Q1 FY2027: 2026-07-01 to 2026-09-30.

- [G08-E1: Microsoft FY2026 Q4 earnings call transcript](https://www.microsoft.com/en-us/investor/events/fy-2026/earnings-fy-2026-q4) — Amy Hood, Q1 FY2027 outlook, Azure; primary; dated 2026-07-29.

Review note: Verified the point estimate in Amy Hood outlook; the original rubric incorrectly required a range.

### G09 — NIKE, Inc. (NKE)

What was Nike's revenue in its most recently reported quarter, and which fiscal quarter and date range was that?

At the October 1, 2026 after-market snapshot, Nike had released Q1 FY2027 results: revenue was USD 11,213 million for June 1–August 31, 2026. The release is dated October 1. [G09-E1](https://investors.nike.com/investors/news-events-and-reports/investor-news/investor-news-details/2026/NIKE-Inc--Reports-Fiscal-2027-First-Quarter-Results/default.aspx)

Periods: Q1 FY2027: 2026-06-01 to 2026-08-31.

- [G09-E1: Nike Q1 FY2027 earnings release](https://investors.nike.com/investors/news-events-and-reports/investor-news/investor-news-details/2026/NIKE-Inc--Reports-Fiscal-2027-First-Quarter-Results/default.aspx) — Consolidated Statements of Income, three months ended August 31, 2026; primary; dated 2026-10-01.

Review note: Release available at review snapshot, 2026-10-01 17:51:43 America/Los_Angeles. Earlier same-day runs must use the newest release available at their own timestamp.

### G10 — Apple Inc. (AAPL)

How many iPhone units did Apple sell in fiscal 2025?

Apple did not disclose FY2025 iPhone unit sales in its 10-K. A reported unit count cannot be supplied. The filing reports iPhone net sales of USD 209,586 million; revenue is not a unit count, and third-party shipment estimates must be labeled as estimates. [G10-E1](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm)

Periods: FY2025: 2024-09-29 to 2025-09-27.

- [G10-E1: Apple FY2025 Form 10-K](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm) — Item 7, Products and Services Performance; Note 2 Revenue; primary; dated 2025-10-31.

### G11 — Apple Inc. (AAPL)

As of October 1, 2026, what were Apple's total revenue and iPhone revenue for the September 2026 quarter?

As of October 1, 2026, Apple had not reported September-quarter FY2026 actual results. Total revenue and iPhone revenue for Q4 FY2026, ended September 26, cannot yet be supplied as actuals. The latest reported quarter was Q3 FY2026, ended June 27. [G11-E1](https://www.apple.com/newsroom/2026/07/apple-reports-third-quarter-results/)

Periods: Q4 FY2026: 2026-06-28 to 2026-09-26.

- [G11-E1: Apple FY2026 Q3 earnings release](https://www.apple.com/newsroom/2026/07/apple-reports-third-quarter-results/) — Release date and reported fiscal period; primary; dated 2026-07-30.

Review note: The refusal is date-dependent. This question explicitly freezes the October 1, 2026 cutoff; future reports must not change the reference answer.

### G12 — Cargill, Incorporated (private; no ticker)

Pull Cargill's FY2026 10-K: GAAP revenue, net income, and diluted EPS.

Cargill is privately held and restricts detailed financial information to authorized institutions; no public FY2026 10-K supports the request. [G12-E2](https://www.cargill.com/about/financial/credit-financial-information) Its own annual report states FY2026 revenue of USD 164 billion. This is company-published revenue, not a verified SEC-filed GAAP figure; public net income and diluted EPS are not disclosed in the cited report. [G12-E1](https://www.cargill.com/about/2026-annual-report/2026-letter-to-our-stakeholders)

Periods: FY2026: 2025-06-01 to 2026-05-31.

- [G12-E1: Cargill FY2026 annual report, stakeholder letter](https://www.cargill.com/about/2026-annual-report/2026-letter-to-our-stakeholders) — FY2026 revenue disclosure; primary.

- [G12-E2: Cargill credit and financial information](https://www.cargill.com/about/financial/credit-financial-information) — Private access for authorized users; primary.

### G13 — NVIDIA Corporation (NVDA)

What are the latest developments in the past 30 days on U.S. export controls affecting NVIDIA's data center GPU sales to China, and what does NVIDIA's own Q3 FY2027 outlook assume about China?

Snapshot: September 2–October 1, 2026. September 9: C4ADS published evidence of restricted NVIDIA chips reaching China through institutional purchases and Southeast Asian trade networks; this is an enforcement-gap report, not a new U.S. rule. [G13-E1](https://c4ads.org/reports/covert-compute/) September 28: Ars, citing The Information, reported China considering RTX Pro 5500 purchases by Alibaba and ByteDance; approval was uncertain and this concerns Chinese import policy, not a confirmed U.S. export-rule change. [G13-E2](https://arstechnica.com/tech-policy/2026/09/nvidia-may-sell-more-chips-in-china-as-jensen-huangs-influence-over-trump-grows/) The reviewed sources do not establish a newly enacted U.S. control in this window. Separately, NVIDIA’s August 26 outlook assumes no Data Center compute revenue from China in Q3 FY2027, within its USD 108 billion ±2% total-revenue guide. That company statement is older context and remains distinct from September reporting. [G13-E3](https://investor.nvidia.com/news/press-release-details/2026/NVIDIA-Announces-Financial-Results-for-Second-Quarter-Fiscal-2027/)

Periods: 30-day news window (inclusive calendar dates): 2026-09-02 to 2026-10-01; Q3 FY2027 outlook: 2026-07-27 to 2026-10-25.

- [G13-E1: C4ADS, Covert Compute: How Advanced AI Chips Reach China](https://c4ads.org/reports/covert-compute/) — Executive Summary; primary_research; dated 2026-09-09.

- [G13-E2: Ars Technica, reported potential NVIDIA chip purchases in China](https://arstechnica.com/tech-policy/2026/09/nvidia-may-sell-more-chips-in-china-as-jensen-huangs-influence-over-trump-grows/) — Reported Chinese approval discussions; secondary_news; dated 2026-09-28.

- [G13-E3: NVIDIA Q2 FY2027 earnings release](https://investor.nvidia.com/news/press-release-details/2026/NVIDIA-Announces-Financial-Results-for-Second-Quarter-Fiscal-2027/) — Outlook, Q3 FY2027; primary; dated 2026-08-26.

Review note: Dated snapshot for the reference-free grader. Distinguish publication date from the historical transactions studied by C4ADS. Do not present an investigative report, prospective Chinese approval, or the August company outlook as a September U.S. regulatory enactment; do not extrapolate an uncited revenue impact.

### G14 — NVIDIA Corporation (NVDA)

NVIDIA's Q2 FY2027 GAAP diluted EPS came in above non-GAAP. What were the two figures, and which reconciling items explain the gap?

Q2 FY2027 diluted EPS was $2.46 GAAP and $2.22 non-GAAP. The reconciliation removes USD 7,771 million of equity-security gains, offset by USD 222 million of operating-cost adjustments, USD 298 million of other-income adjustments and USD 1,517 million of tax effects. Net income falls from USD 59,688 million to USD 53,954 million. Stock compensation remains included in non-GAAP starting FY2027. [G14-E1](https://investor.nvidia.com/news/press-release-details/2026/NVIDIA-Announces-Financial-Results-for-Second-Quarter-Fiscal-2027/)

Periods: Q2 FY2027: 2026-04-27 to 2026-07-26.

- [G14-E1: NVIDIA Q2 FY2027 earnings release](https://investor.nvidia.com/news/press-release-details/2026/NVIDIA-Announces-Financial-Results-for-Second-Quarter-Fiscal-2027/) — GAAP-to-non-GAAP reconciliation, three months ended July 26, 2026; primary; dated 2026-08-26.

Review note: Largest negative item: equity-security gains. Do not invent a stock-compensation addback; NVIDIA includes it in FY2027 non-GAAP measures.

### G15 — Costco Wholesale Corporation (COST)

Excluding the non-recurring IEEPA tariff refund benefit, what was Costco's Q4 FY2026 diluted EPS, and what was the YoY growth on that basis vs Q4 FY2025?

Costco Q4 FY2026 diluted EPS excluding the disclosed net tariff-refund benefit was $6.60 ($6.75 - $0.15), up 12.4361% from Q4 FY2025 EPS of $5.87. Both quarters contained 16 weeks. The $0.15 benefit is already net of partial reinvestment in member values. [G15-E1](https://investor.costco.com/news/news-details/2026/Costco-Wholesale-Corporation-Reports-Fourth-Quarter-and-Fiscal-Year-2026-Operating-Results/default.aspx)

Periods: Q4 FY2026: 2026-05-11 to 2026-08-30; Q4 FY2025: 2025-05-12 to 2025-08-31.

- [G15-E1: Costco Q4 and FY2026 earnings release](https://investor.costco.com/news/news-details/2026/Costco-Wholesale-Corporation-Reports-Fourth-Quarter-and-Fiscal-Year-2026-Operating-Results/default.aspx) — Quarterly net income narrative and 16-week EPS columns; primary; dated 2026-09-24.

### G16 — Walmart Inc. (WMT)

Did Walmart's Q2 FY2027 results land above, within, or below the Q2 guidance it gave in its Q1 FY2027 release, on net sales growth (cc), adjusted operating income growth (cc), and adjusted EPS?

Against the Q1 release guide: net sales growth in constant currency was 5.0% versus 4.0–5.0%, within at the upper end; adjusted operating income growth in constant currency was 17.4% versus 7.0–10.0%, above; adjusted EPS was $0.81 versus $0.72–$0.74, above. Use net sales growth, not the 5.1% constant-currency total-revenue headline. The guide excluded tariff-refund benefits. [G16-E1](https://stock.walmart.com/sec-filings/all-sec-filings/content/0000104169-26-000095/earningsreleasefy27q1.htm), [G16-E2](https://stock.walmart.com/sec-filings/all-sec-filings/content/0000104169-26-000145/earningsreleasefy27q2.htm)

Periods: Q2 FY2027: 2026-05-01 to 2026-07-31; Q1 FY2027: 2026-02-01 to 2026-04-30.

- [G16-E1: Walmart Q1 FY2027 release, 8-K Exhibit 99.1](https://stock.walmart.com/sec-filings/all-sec-filings/content/0000104169-26-000095/earningsreleasefy27q1.htm) — Q2 FY2027 Guidance; primary; dated 2026-05-21.

- [G16-E2: Walmart Q2 FY2027 release, 8-K Exhibit 99.1](https://stock.walmart.com/sec-filings/all-sec-filings/content/0000104169-26-000145/earningsreleasefy27q2.htm) — Constant Currency table; adjusted operating income and EPS; primary; dated 2026-08-20.

### G17 — Walmart Inc. (WMT)

According to Walmart management, what drove the growth in Q2 FY2027 adjusted operating income, and how much of it was one-time?

Management cited strong sales, better business mix from advertising and membership, improving eCommerce economics, and tariff refunds partly reinvested in prices. Gross-profit rate rose 96 basis points; operating-cost deleverage included higher U.S. self-insured liability claims, depreciation and healthcare expenses. [G17-E1](https://stock.walmart.com/sec-filings/all-sec-filings/content/0000104169-26-000145/earningsreleasefy27q2.htm), [G17-E2](https://stock.walmart.com/sec-filings/all-sec-filings/content/0000104169-26-000145/earningspresentationfy27.htm) Adjusted operating income rose 17.4% in constant currency, versus 28.8% reported growth. Management quantified the one-time net tariff-refund contribution at approximately 750 basis points (7.5 percentage points) of operating-income growth, leaving underlying growth at the top end of the 7–10% guide. Nearly USD 2.9 billion of refunds received is the gross refund amount, not the net profit benefit. [G17-E3](https://corporate.walmart.com/news/2026/08/20/walmart-releases-q2-fy27-earnings)

Periods: Q2 FY2027: 2026-05-01 to 2026-07-31.

- [G17-E1: Walmart Q2 FY2027 release](https://stock.walmart.com/sec-filings/all-sec-filings/content/0000104169-26-000145/earningsreleasefy27q2.htm) — Highlights; gross profit and operating expenses commentary; primary; dated 2026-08-20.

- [G17-E2: Walmart Q2 FY2027 earnings presentation](https://stock.walmart.com/sec-filings/all-sec-filings/content/0000104169-26-000145/earningspresentationfy27.htm) — Business mix and operating income commentary; primary; dated 2026-08-20.

- [G17-E3: Walmart Q2 FY2027 management commentary](https://corporate.walmart.com/news/2026/08/20/walmart-releases-q2-fy27-earnings) — Delivering value and convenience; Operating with discipline; primary; dated 2026-08-20.

### G18 — Broadcom Inc. (AVGO)

Did Broadcom's Q3 FY2026 AI semiconductor revenue beat the guidance it gave on its Q2 FY2026 call, and by how much in dollars and percent?

Broadcom Q3 FY2026 AI semiconductor revenue was $16.7 billion versus its Q2-release guidance of $16.0 billion: a $0.7 billion beat, or 4.375% of guidance. [G18-E1](https://investors.broadcom.com/news-releases/news-release-details/broadcom-inc-announces-second-quarter-fiscal-year-2026-financial), [G18-E2](https://investors.broadcom.com/news-releases/news-release-details/broadcom-inc-announces-third-quarter-fiscal-year-2026-financial)

Periods: Q3 FY2026: 2026-05-04 to 2026-08-02; Q2 FY2026: 2026-02-02 to 2026-05-03.

- [G18-E1: Broadcom Q2 FY2026 earnings release](https://investors.broadcom.com/news-releases/news-release-details/broadcom-inc-announces-second-quarter-fiscal-year-2026-financial) — Hock Tan Q3 AI semiconductor outlook; primary; dated 2026-06-03.

- [G18-E2: Broadcom Q3 FY2026 earnings release](https://investors.broadcom.com/news-releases/news-release-details/broadcom-inc-announces-third-quarter-fiscal-year-2026-financial) — Hock Tan AI semiconductor results; primary; dated 2026-09-02.

### G19 — NVIDIA Corporation (NVDA)

Give NVIDIA's Data Center revenue for each quarter from Q2 FY2026 through Q2 FY2027 and the QoQ growth for each.

Data Center market-platform revenue (USD millions) / calculated QoQ growth: Q2 FY2026: 41,096 / 5.0726%; Q3 FY2026: 51,215 / 24.6228%; Q4 FY2026: 62,314 / 21.6714%; Q1 FY2027: 75,246 / 20.7530%; Q2 FY2027: 89,023 / 18.3093%. Q2 FY2026 growth uses the Q1 FY2026 baseline of USD 39,112 million. These are Data Center figures, not Compute & Networking segment revenue. [G19-E1](https://s201.q4cdn.com/141608511/files/doc_financials/2026/Q426/Rev_by_Mkt_Qtrly_Trend_Q426.pdf), [G19-E2](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000075/nvda-20260726.htm)

Periods: Q2 FY2026: 2025-04-28 to 2025-07-27; Q3 FY2026: 2025-07-28 to 2025-10-26; Q4 FY2026: 2025-10-27 to 2026-01-25; Q1 FY2027: 2026-01-26 to 2026-04-26; Q2 FY2027: 2026-04-27 to 2026-07-26.

- [G19-E1: NVIDIA FY2026 quarterly revenue trend](https://s201.q4cdn.com/141608511/files/doc_financials/2026/Q426/Rev_by_Mkt_Qtrly_Trend_Q426.pdf) — Revenue by markets, Data Center row; primary; dated 2026-02-25.

- [G19-E2: NVIDIA Q2 FY2027 Form 10-Q](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000075/nvda-20260726.htm) — Note 13 and MD&A, Revenue by Market Platform; primary.

### G20 — Apple Inc. (AAPL)

Show Apple's Services net sales and Services gross margin percentage for FY2023, FY2024, and FY2025, and the change in Services gross margin over the period.

Apple Services net sales / Services gross margin were: FY2023, USD 85,200 million / 70.8%; FY2024, USD 96,169 million / 73.9%; FY2025, USD 109,158 million / 75.4%. Services gross margin increased 4.6 percentage points from FY2023 to FY2025. FY2023 had 53 weeks, versus 52 weeks in FY2024 and FY2025. [G20-E1](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm)

Periods: FY2023: 2022-09-25 to 2023-09-30; FY2024: 2023-10-01 to 2024-09-28; FY2025: 2024-09-29 to 2025-09-27.

- [G20-E1: Apple FY2025 Form 10-K](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm) — Item 7, Products and Services Performance and Gross Margin; fiscal-year policy; primary; dated 2025-10-31.

### G21 — Alphabet Inc. (GOOGL, GOOG)

How much did Alphabet spend on share repurchases in Q2 2026, split between Class A (GOOGL) and Class C (GOOG), with share counts for each?

Alphabet repurchased no Class A or Class C shares in Q2 2026. Class A (GOOGL): USD 0 million and 0 shares. Class C (GOOG): USD 0 million and 0 shares. Total: USD 0 million. An unused authorization is not repurchase spending. [G21-E1](https://www.sec.gov/Archives/edgar/data/1652044/000165204426000071/goog-20260630.htm)

Periods: Q2 2026: 2026-04-01 to 2026-06-30.

- [G21-E1: Alphabet Q2 2026 Form 10-Q](https://www.sec.gov/Archives/edgar/data/1652044/000165204426000071/goog-20260630.htm) — Note 11, Share Repurchases; primary; dated 2026-07-23.

Review note: The original expected-source text incorrectly assumed a populated Class A/C repurchase table.

### G22 — Deere & Company (DE)

Given Deere's updated fiscal 2026 net income guidance from its Q3 release, what Q4 FY2026 net income attributable to Deere & Company is implied at the low and high ends?

Deere’s updated FY2026 net-income-attributable-to-Deere guide is USD 4,750–5,000 million. Subtract nine-month attributable net income of USD 3,808 million: implied Q4 FY2026 attributable net income is USD 942 million at the low end and USD 1,192 million at the high end. These are derived outlook amounts, not reported Q4 actuals. [G22-E1](https://www.sec.gov/Archives/edgar/data/315189/000110465926098904/de-20260820xex99d1.htm)

Periods: 9M FY2026: 2025-11-03 to 2026-08-02; Q4 FY2026 implied: 2026-08-03 to 2026-11-01.

- [G22-E1: Deere Q3 FY2026 release, Form 8-K Exhibit 99.1](https://www.sec.gov/Archives/edgar/data/315189/000110465926098904/de-20260820xex99d1.htm) — Company Outlook and Statements of Consolidated Income; primary; dated 2026-08-20.

### G23 — NVIDIA Corporation (NVDA)

Using NVIDIA's reported Q1 and Q2 FY2027 revenue plus the midpoint of its Q3 FY2027 outlook, what is the implied revenue for the first three quarters of FY2027, and the growth vs the first three quarters of FY2026?

Implied first-three-quarter FY2027 revenue is USD 285,836 million: Q1 actual USD 81,615 million + Q2 actual USD 96,221 million + Q3 guidance midpoint USD 108,000 million. [G23-E1](https://investor.nvidia.com/news/press-release-details/2026/NVIDIA-Announces-Financial-Results-for-Second-Quarter-Fiscal-2027/) Against FY2026 nine-month actual revenue of USD 147,811 million, growth is 93.3794%. [G23-E2](https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-third-quarter-fiscal-2026) This combines two actual quarters and one guided quarter; it is not reported nine-month revenue. The six-month filing total differs from the sum of the displayed quarters by USD 1 million due to rounding. [G23-E3](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000075/nvda-20260726.htm)

Periods: 9M FY2027 implied: 2026-01-26 to 2026-10-25; 9M FY2026 actual: 2025-01-27 to 2025-10-26.

- [G23-E1: NVIDIA Q2 FY2027 earnings release](https://investor.nvidia.com/news/press-release-details/2026/NVIDIA-Announces-Financial-Results-for-Second-Quarter-Fiscal-2027/) — Quarterly summary and Q3 Outlook; primary; dated 2026-08-26.

- [G23-E2: NVIDIA Q3 FY2026 earnings release](https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-third-quarter-fiscal-2026) — Consolidated Statements of Income, nine months ended October 26, 2025; primary; dated 2025-11-19.

- [G23-E3: NVIDIA Q2 FY2027 Form 10-Q](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000075/nvda-20260726.htm) — Consolidated Statements of Income and quarterly MD&A; primary.

Review note: Use the explicitly requested quarter sum (USD 285,836M); USD 285,837M from filed six-month total plus guidance is also within the original tolerance. Do not present either as actual nine-month results.

### G24 — Oracle Corporation (ORCL)

Oracle says roughly X% of its RPO at Aug 31, 2026 will be recognized in the next 12 months. What dollar amount does that imply, and how does it compare (as a ratio) to Oracle's trailing-twelve-month total revenue through Q1 FY2027?

Approximately 13% of Oracle’s USD 664 billion RPO implies USD 86.32 billion recognized over the next twelve months. TTM total revenue through Q1 FY2027 is USD 71,776 million: FY2026 USD 67,357 million + Q1 FY2027 USD 19,345 million − Q1 FY2026 USD 14,926 million. The implied RPO amount / TTM revenue ratio is 1.2026x. The 13% is approximate and RPO recognition is not total-revenue guidance. [G24-E1](https://www.sec.gov/Archives/edgar/data/1341439/000119312526389274/orcl-20260831.htm), [G24-E2](https://www.sec.gov/Archives/edgar/data/1341439/000119312526277521/orcl-20260531.htm)

Periods: FY2026: 2025-06-01 to 2026-05-31; Q1 FY2027: 2026-06-01 to 2026-08-31; Q1 FY2026: 2025-06-01 to 2025-08-31; TTM through Q1 FY2027: 2025-09-01 to 2026-08-31; Next twelve months RPO recognition: 2026-09-01 to 2027-08-31.

- [G24-E1: Oracle Q1 FY2027 Form 10-Q](https://www.sec.gov/Archives/edgar/data/1341439/000119312526389274/orcl-20260831.htm) — Remaining Performance Obligations and Condensed Consolidated Statements of Operations; primary; dated 2026-09-11.

- [G24-E2: Oracle FY2026 Form 10-K](https://www.sec.gov/Archives/edgar/data/1341439/000119312526277521/orcl-20260531.htm) — Consolidated Statements of Operations; Segment Information; primary.

### G25 — Honeywell International Inc. / 'Honeywell Technologies' (HON, CIK 773840) — not Honeywell Aerospace Inc. (HONA)

Honeywell reported Q2 2026 a few weeks after spinning off Aerospace. What were consolidated sales vs sales excluding Aerospace, and why is GAAP EPS from continuing operations so far above adjusted EPS?

HON consolidated Q2 2026 sales were USD 9,719 million; sales excluding Aerospace were USD 5,187 million. Consolidated GAAP continuing-operations EPS of $17.83 reconciles to adjusted EPS of $4.52, principally by removing $15.87 per share of Quantinuum deconsolidation gains; other net adjustments add $2.56. Ex-Aerospace EPS was $16.65 GAAP / $1.95 adjusted. The Q2 actual close was June 27, although presented as June 30: the June 29 Aerospace spin occurred in Q3. Aerospace remains consolidated in this Q2 presentation and becomes discontinued operations beginning Q3. [G25-E1](https://investor.honeywell.com/news-releases/news-release-details/honeywell-technologies-reports-second-quarter-results), [G25-E2](https://www.sec.gov/Archives/edgar/data/773840/000077384026000124/hon-20260630.htm)

Periods: Q2 2026 (reported calendar convention): 2026-04-01 to 2026-06-30.

- [G25-E1: Honeywell Technologies Q2 2026 earnings release](https://investor.honeywell.com/news-releases/news-release-details/honeywell-technologies-reports-second-quarter-results) — Tables 1 and 2; EPS reconciliation and footnotes; primary; dated 2026-07-23.

- [G25-E2: Honeywell International Inc. Q2 2026 Form 10-Q](https://www.sec.gov/Archives/edgar/data/773840/000077384026000124/hon-20260630.htm) — Note 1 calendar convention; Note 3 Aerospace spin-off; primary; dated 2026-07-23.

Review note: Source-check corrected the spin timing and EPS cause. All EPS values in the release reflect the June 29 reverse split retrospectively.

### G26 — Novo Nordisk A/S (NVO; 20-F filer)

What were Novo Nordisk's 2025 sales and operating profit, with growth in reported DKK vs constant exchange rates, and the USD equivalent of 2025 sales?

Novo Nordisk 2025 sales were DKK 309,064 million, up 6% reported / 10% at constant exchange rates. Operating profit was DKK 127,658 million, down 1% reported / up 6% at CER. Using the Federal Reserve 2025 annual-average rate of DKK 6.6137 per USD, sales translate to approximately USD 46.7309 billion. This is an analyst translation of DKK-reported IFRS sales. [G26-E1](https://annualreport.novonordisk.com/2025/strategic-aspirations/financial-performance.html), [G26-E2](https://www.federalreserve.gov/releases/g5a/current/)

Periods: FY2025: 2025-01-01 to 2025-12-31.

- [G26-E1: Novo Nordisk Annual Report 2025](https://annualreport.novonordisk.com/2025/strategic-aspirations/financial-performance.html) — Financial performance; Development in costs and operating profit; primary.

- [G26-E2: Federal Reserve annual exchange rates, G.5A](https://www.federalreserve.gov/releases/g5a/current/) — 2025 average, Denmark krone; primary; dated 2026-01-05.

Review note: Use 2025 annual-average FX, not spot FX. Management rounds reported operating-profit growth to -1%; the five-year table gives -0.5%. Do not substitute growth excluding restructuring costs.

### G27 — Micron Technology, Inc. (MU)

For Micron's fiscal 2026, give GAAP gross margin for each quarter, full-year revenue growth, and flag any difference in week count that distorts YoY comparisons.

Micron FY2026 GAAP gross margin: Q1 56.0%, Q2 74.4%, Q3 84.6%, Q4 86.8%. [G27-E1](https://investors.micron.com/news/press-release/2025/Micron-Technology-Inc--Reports-Results-for-the-First-Quarter-of-Fiscal-2026-12-17-2025/default.aspx), [G27-E2](https://investors.micron.com/news/press-release/2026/Micron-Technology-Inc--Reports-Results-for-the-Second-Quarter-of-Fiscal-2026-03-18-2026/default.aspx), [G27-E3](https://investors.micron.com/news/press-release/2026/Micron-Technology-Inc--Reports-Record-Results-for-the-Third-Quarter-of-Fiscal-2026/default.aspx), [G27-E4](https://investors.micron.com/news/press-release/2026/Micron-Technology-Inc--Reports-Record-Fiscal-Fourth-Quarter-and-Full-Year-2026-Results/default.aspx)(https://investors.micron.com/news/press-release/2026/Micron-Technology-Inc--Reports-Record-Fiscal-Fourth-Quarter-and-Full-Year-2026-Results/default.aspx) Full-year revenue was USD 133,188 million versus USD 37,378 million in FY2025, growth of 256.3273%. [G27-E4](https://investors.micron.com/news/press-release/2026/Micron-Technology-Inc--Reports-Record-Fiscal-Fourth-Quarter-and-Full-Year-2026-Results/default.aspx) FY2026 had 53 weeks and Q4 had 14 weeks, versus 52 weeks / 13 weeks in FY2025. The extra week boosts unadjusted YoY revenue comparisons; the sources do not isolate its revenue contribution, so no week-adjusted growth is supplied. [G27-E5](https://www.sec.gov/Archives/edgar/data/723125/000072312526000015/R26.htm)

Periods: Q1 FY2026: 2025-08-29 to 2025-11-27; Q2 FY2026: 2025-11-28 to 2026-02-26; Q3 FY2026: 2026-02-27 to 2026-05-28; Q4 FY2026: 2026-05-29 to 2026-09-03; FY2026: 2025-08-29 to 2026-09-03; FY2025: 2024-08-30 to 2025-08-28.

- [G27-E1: Micron Q1 FY2026 earnings release](https://investors.micron.com/news/press-release/2025/Micron-Technology-Inc--Reports-Results-for-the-First-Quarter-of-Fiscal-2026-12-17-2025/default.aspx) — Quarterly Financial Results, GAAP column; primary; dated 2025-12-17.

- [G27-E2: Micron Q2 FY2026 earnings release](https://investors.micron.com/news/press-release/2026/Micron-Technology-Inc--Reports-Results-for-the-Second-Quarter-of-Fiscal-2026-03-18-2026/default.aspx) — Quarterly Financial Results, GAAP column; primary; dated 2026-03-18.

- [G27-E3: Micron Q3 FY2026 earnings release](https://investors.micron.com/news/press-release/2026/Micron-Technology-Inc--Reports-Record-Results-for-the-Third-Quarter-of-Fiscal-2026/default.aspx) — Quarterly Financial Results, GAAP column; primary; dated 2026-06-24.

- [G27-E4: Micron Q4 and FY2026 earnings release](https://investors.micron.com/news/press-release/2026/Micron-Technology-Inc--Reports-Record-Fiscal-Fourth-Quarter-and-Full-Year-2026-Results/default.aspx) — Quarterly Financial Results and Consolidated Statements of Operations; primary; dated 2026-09-30.

- [G27-E5: Micron Q3 FY2026 Form 10-Q, accounting policies](https://www.sec.gov/Archives/edgar/data/723125/000072312526000015/R26.htm) — Fiscal Period policy; primary.

Review note: The week counts are explicitly disclosed in the Q3 FY2026 10-Q accounting policy, not in the Q4 release. Use the one-decimal GAAP percentages supplied by the releases.

### G28 — Alphabet (GOOGL), Meta Platforms (META), Amazon.com (AMZN), Microsoft (MSFT)

What are Alphabet, Meta, Amazon, and Microsoft each currently guiding for capital expenditures, and how do they line up on a calendar-2026 basis?

As of October 1, 2026, all four provide calendar-2026 capex numbers: Alphabet USD 195–205 billion (July 22 Q2 call); [G28-E1](https://s206.q4cdn.com/479360582/files/doc_events/2026/Jul/22/2026_Q2_Earnings_Transcript.pdf) Meta USD 130–145 billion including finance-lease principal payments (July 29 Q2 release); [G28-E2](https://www.sec.gov/Archives/edgar/data/1326801/000162828026050596/meta-06302026xexhibit991.htm) Amazon approximately USD 220 billion in cash capex (July 30 Q2 call); [G28-E3](https://tickertrends.io/transcripts/AMZN/Q2-earnings-transcript-2026) Microsoft approximately USD 175 billion (July 29 FY2026 Q4 call), including finance leases but excluding operating leases. Microsoft lowered the displayed capex amount because extending building useful lives shifts some future leases to operating classification; investment expectations apart from that change were unchanged. [G28-E4](https://www.microsoft.com/en-us/investor/events/fy-2026/earnings-fy-2026-q4)(https://www.microsoft.com/en-us/investor/events/fy-2026/earnings-fy-2026-q4) Nominal ordering is Amazon, Alphabet, Microsoft, Meta, but the lease definitions differ, so these are not fully harmonized cash-spending measures. Microsoft separately expects FY2027 capex to grow YoY and Q1 FY2027 capex above USD 50 billion; those fiscal guides are not additional CY2026 totals. [G28-E4](https://www.microsoft.com/en-us/investor/events/fy-2026/earnings-fy-2026-q4)(https://www.microsoft.com/en-us/investor/events/fy-2026/earnings-fy-2026-q4)

Periods: Calendar 2026 guidance: 2026-01-01 to 2026-12-31.

- [G28-E1: Alphabet Q2 2026 company-hosted call transcript](https://s206.q4cdn.com/479360582/files/doc_events/2026/Jul/22/2026_Q2_Earnings_Transcript.pdf) — Anat Ashkenazi, investment outlook, PDF page 13; primary; dated 2026-07-22.

- [G28-E2: Meta Q2 2026 earnings release](https://www.sec.gov/Archives/edgar/data/1326801/000162828026050596/meta-06302026xexhibit991.htm) — CFO Outlook Commentary; primary; dated 2026-07-29.

- [G28-E3: Amazon Q2 2026 call transcript, third-party copy](https://tickertrends.io/transcripts/AMZN/Q2-earnings-transcript-2026) — Andy Jassy, investment commentary; secondary_transcript; dated 2026-07-30.

- [G28-E4: Microsoft FY2026 Q4 call transcript](https://www.microsoft.com/en-us/investor/events/fy-2026/earnings-fy-2026-q4) — Amy Hood, useful-life update and capital expenditure outlook; primary; dated 2026-07-29.

Review note: Alphabet, Meta and Microsoft verified directly against company documents. Amazon’s numeric guide was verified against third-party copies of the management call and corroborated by dated AP reporting. A primary transcript supporting that guide was not retrieved; its source_type remains explicitly secondary_transcript. This row does not yet satisfy PLAN.md’s primary-only reference-source gate and needs primary-source review.

### G29 — Amazon.com (AMZN), Alphabet (GOOGL), Microsoft (MSFT)

For the April–June 2026 quarter, compare YoY revenue growth and operating margin for AWS, Google Cloud, and Microsoft Azure.

For April–June 2026: AWS revenue grew 36.7927% YoY (USD 42,232 million / USD 30,873 million) and operating margin was 39.3564% (USD 16,621 million operating income / USD 42,232 million revenue). [G29-E1](https://www.sec.gov/Archives/edgar/data/1018724/000101872426000026/amzn-20260630.htm) Google Cloud revenue grew 81.7968% (USD 24,768 million / USD 13,624 million) and margin was 35.5862% (USD 8,814 million / USD 24,768 million). [G29-E2](https://www.sec.gov/Archives/edgar/data/1652044/000165204426000071/goog-20260630.htm) Microsoft Azure and other cloud services grew 43% in fiscal Q4 FY2026; the call’s convention indicates the same rate in constant currency. Azure quarterly revenue dollars and Azure operating margin are not separately disclosed, so Azure margin cannot be calculated. Intelligent Cloud margin is a broader segment metric and must not be substituted. [G29-E3](https://www.microsoft.com/en-us/investor/events/fy-2026/earnings-fy-2026-q4)

Periods: Amazon and Alphabet Q2 2026: 2026-04-01 to 2026-06-30; Microsoft Q4 FY2026: 2026-04-01 to 2026-06-30.

- [G29-E1: Amazon Q2 2026 Form 10-Q](https://www.sec.gov/Archives/edgar/data/1018724/000101872426000026/amzn-20260630.htm) — Note 8, Segment Information, three-month columns; primary.

- [G29-E2: Alphabet Q2 2026 Form 10-Q](https://www.sec.gov/Archives/edgar/data/1652044/000165204426000071/goog-20260630.htm) — Segment revenues and operating income, three-month columns; primary.

- [G29-E3: Microsoft FY2026 Q4 call transcript](https://www.microsoft.com/en-us/investor/events/fy-2026/earnings-fy-2026-q4) — Opening currency convention and Amy Hood, Intelligent Cloud results; primary; dated 2026-07-29.

Review note: Partial abstention only for Azure margin/dollars. The CC rate follows the call’s explicit convention and is not a substitute Intelligent Cloud growth figure.

### G30 — Walmart (WMT), Costco (COST), Target (TGT)

Compare U.S. comparable sales growth (ex-fuel where reported) for Walmart U.S. (Q2 FY2027), Costco U.S. (Q4 FY2026), and Target (Q2 2026), and explain why the periods aren't directly comparable.

Walmart U.S. Q2 FY2027 comp sales grew 2.6% excluding fuel, for 13 weeks ended July 31, 2026. [G30-E1](https://stock.walmart.com/sec-filings/all-sec-filings/content/0000104169-26-000145/earningsreleasefy27q2.htm) Costco U.S. Q4 FY2026 comps grew 7.2% excluding gasoline-price and FX effects, for 16 weeks ended August 30, 2026 (headline U.S. comp growth was 10.7%). [G30-E2](https://investor.costco.com/news/news-details/2026/Costco-Wholesale-Corporation-Reports-Fourth-Quarter-and-Fiscal-Year-2026-Operating-Results/default.aspx) Target Q2 2026 comparable sales grew 3.8% for 13 weeks ended August 1, 2026, under Target’s own store-and-digital definition; the release does not present a matching gas/FX-adjusted figure. [G30-E3](https://corporate.target.com/press/release/2026/08/target-corporation-reports-second-quarter-earnings) The quarters differ in length, end dates and adjustment definitions: Costco’s period is three weeks longer and includes more August trading. These figures therefore do not support a directly comparable market-share ranking.

Periods: Walmart U.S. Q2 FY2027 comp window: 2026-05-02 to 2026-07-31; Costco U.S. Q4 FY2026: 2026-05-11 to 2026-08-30; Target Q2 2026: 2026-05-03 to 2026-08-01.

- [G30-E1: Walmart Q2 FY2027 earnings release](https://stock.walmart.com/sec-filings/all-sec-filings/content/0000104169-26-000145/earningsreleasefy27q2.htm) — Walmart U.S. comps and 13-week comp footnote; primary; dated 2026-08-20.

- [G30-E2: Costco Q4 and FY2026 earnings release](https://investor.costco.com/news/news-details/2026/Costco-Wholesale-Corporation-Reports-Fourth-Quarter-and-Fiscal-Year-2026-Operating-Results/default.aspx) — Fourth-quarter comparable sales table, U.S.; primary; dated 2026-09-24.

- [G30-E3: Target Q2 2026 earnings release](https://corporate.target.com/press/release/2026/08/target-corporation-reports-second-quarter-earnings) — Second-quarter highlights and comparable-sales definition; primary; dated 2026-08-19.
