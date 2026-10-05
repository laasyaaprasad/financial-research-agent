# Scorecard: half_baseline_exact50

Agent `baseline` · set `exact50` · model `deepseek-ai/DeepSeek-V4.1-Flash` · judge `gpt-6-luna` · code `6bc163c` · questions 25 · agent errors 0 · judge errors 0

| Slice | Qs | Fixed answers: fully correct (mean score) | Time-sensitive: rubric score | Numbers with a citation | Cited claims supported | Cited URLs that are primary |
|---|---|---|---|---|---|---|
| All | 25 | 7/13 (0.90) | 4/12 all met (0.73) | 99% | 72% | 25% |

| Median latency | p95 latency | Tokens / question | Tavily credits / question | Tavily credits total |
|---|---|---|---|---|
| 10.9 s | 42.0 s | 34,108 | 5.0 | 126 |

## By category

| Slice | Qs | Fixed answers: fully correct (mean score) | Time-sensitive: rubric score | Numbers with a citation | Cited claims supported | Cited URLs that are primary |
|---|---|---|---|---|---|---|
| Beat or miss | 2 | 1/2 (0.92) | – | 100% | 75% | 29% |
| Complex retrieval | 3 | 2/2 (1.00) | 1/1 all met (1.00) | 100% | 82% | 40% |
| Market analysis | 2 | 2/2 (1.00) | – | 100% | 48% | 78% |
| Qualitative retrieval | 2 | – | 1/2 all met (0.89) | 100% | 81% | 8% |
| Quantitative retrieval | 3 | 0/2 (0.78) | 1/1 all met (1.00) | 97% | 70% | 41% |
| ambiguous company | 1 | – | 0/1 all met (0.00) | 100% | 82% | 0% |
| call commentary | 2 | 2/2 (1.00) | – | 100% | 78% | 11% |
| company naming | 2 | – | 0/2 all met (0.73) | 100% | 56% | 0% |
| fiscal vs calendar | 2 | – | 1/2 all met (0.88) | 100% | 88% | 0% |
| foreign issuer | 1 | 0/1 (0.61) | – | 100% | 83% | 43% |
| missing period | 1 | – | 0/1 all met (0.57) | 100% | 58% | 0% |
| open-ended update | 1 | – | 0/1 all met (0.60) | 93% | 64% | 0% |
| recent event | 2 | 0/2 (0.88) | – | 100% | 73% | 44% |
| vague metric | 1 | – | 0/1 all met (0.54) | 100% | 60% | 0% |

## Per question

| ID | Category | Verdict | Score | Credits | Latency | Trace | Judge rationale |
|---|---|---|---|---|---|---|---|
| E02 | missing period | partial | 0.57 | 8 | 18 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/d4c586535db5dd40eb130e28281adc49) | The response identifies Wells Fargo and correctly gives Q2 2026 NIM as 2.43%, distinguishing it from NII. However, it omits required reporting-period context, lacks the specified earnings-release/10-Q citation, and includes NIM figures for  |
| E06 | vague metric | partial | 0.54 | 4 | 7 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/9ed3d900d1ea78c40eb7146a5c6f7dbe) | The answer identifies Berkshire and labels its figures as cash plus T-bills, but it omits the required June 30 date, filing/reporting details, Q3 status, the precise distinction between cash measures, and a filing citation. |
| E09 | open-ended update | partial | 0.60 | 3 | 10 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/7dc6c33378575d39767d53812eca9f70) | The answer identifies Medtronic and reports Q1 FY2027 with adjusted EPS and raised guidance, but omits the required quarter/report dates and fiscal-year-end context. Its cited source does not support the stated revenue amount, and it offers |
| E10 | fiscal vs calendar | correct | 1.00 | 2 | 7 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/0e36bf43cc8b80733df661f481eff2af) | The answer correctly identifies Adobe and reports cited FY2025 revenue, explicitly framing the period as fiscal rather than calendar 2025 and giving the end date and period coverage. It avoids the specified period-misinterpretation failures |
| E13 | fiscal vs calendar | partial | 0.75 | 2 | 8 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/702c2cd6d9e0ade539875d1116b42878) | The answer correctly identifies Estée Lauder, provides the sourced FY2026 net sales figure, and avoids treating guidance as actual. However, it does not explicitly say the current FY2027 is underway with no reported quarter yet, which is ce |
| E14 | company naming | partial | 0.75 | 4 | 9 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/b6fdade181a9b8ccfe32c4137760a410) | The parent-company identification and cited company-wide net sales figure are correct for the latest quarter, but the answer omits the specified fiscal-year-end/reporting-date context. |
| E17 | company naming | partial | 0.71 | 3 | 8 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/84a6272fd708e13d19f680c41c986dc2) | The core revenue answer and cited figure are correct, but the response omits required timing details and adds unsolicited share-price commentary. |
| E19 | ambiguous company | incorrect | 0.00 | 5 | 10 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/013f21ee7b9561b0f83b101652ea2cb7) | The answer violates the core clarify requirement by providing revenue figures for multiple plausible United companies rather than asking a single clarifying question. |
| H01 | Complex retrieval | correct | 1.00 | 12 | 37 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/79b4687c0ba3962e138ce0ddd6533f88) | The answer correctly identifies the latest reported quarter and its net sales, gives the current fiscal 2025 net sales guidance, and avoids treating the post-as-of Q3 results as current. |
| H02 | Complex retrieval | correct | 1.00 | 12 | 31 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/85c1f36f7ef5b27655bab572be1eb689) | The answer supplies both requested as-of-date figures and clearly distinguishes the later Q3 results and revised outlook as post-dating March 2, 2026. |
| T10 | Complex retrieval | correct | 1.00 | 4 | 11 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/c9d4cfe79eda28080f8f5963b458ffd3) | The answer gives both updated FY2027 ranges, identifies the September 23 Q1 FY2027 release as the latest update, and explicitly describes the lower June ranges as prior guidance rather than current. It also states the optional unchanged gui |
| T11 | Beat or miss | partial | 0.83 | 2 | 7 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/919ffda53ead6df1cb5abc46e430e734) | The answer correctly compares revenue and diluted EPS with the company's Q2 guidance and gets both outcomes right. It also gives the tariff-related EPS benefit and adjusted EPS, but omits the required fact that the guidance itself excluded  |
| T12 | Beat or miss | correct | 1.00 | 4 | 11 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/135147c55a55cedc9c4893c85d039785) | The answer correctly identifies both metrics as within Qualcomm's own Q3 FY2026 guidance ranges. It avoids the specified comparison errors. The optional GAAP-versus-GAAP-guidance fact is omitted, which does not affect the verdict. |
| T15 | Qualitative retrieval | partial | 0.78 | 2 | 12 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/17fffd0df530c83c147b728bd8e3d663) | The answer correctly identifies the October Q4/FY2026 report and states the central revenue and FY2027 outlook figures, without reverting to stale Q3 data. It omits the comparison against the specific guided Q4 revenue range and does not ci |
| T16 | Qualitative retrieval | correct | 1.00 | 2 | 8 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/fd49f68d0f3f5599c46100a09a82ffb4) | The answer identifies the September 29, 2026 announcement and accurately covers its scope, total charges, quarterly timing, and guidance exception. It distinguishes the earlier rounds rather than conflating them, and does not describe the c |
| T17 | Quantitative retrieval | correct | 1.00 | 4 | 13 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/01de9489f9b1d6052dd98e505ed8b7ac) | The answer clearly abstains on Q4 FY2026 actuals and keeps the Q3 figures and Q4 guidance explicitly separate from Q4 reported results. It does not fabricate Q4 figures. |
| T18 | Quantitative retrieval | partial | 0.75 | 2 | 6 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/c9f272766bb448287212791f1ceed97c) | The answer correctly abstains from giving a Cybertruck-only reported delivery count and accurately identifies the Model 3/Y and combined Other Models figures. However, it omits the required statement that the 10-Q contains no Cybertruck uni |
| T19 | Quantitative retrieval | partial | 0.80 | 6 | 24 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/cc91f1b8de48335cb616fec3681f83b2) | The response correctly abstains on Enterprise's unavailable earnings and states its private status and lack of SEC reports. However, it also supplies net-loss and operating-income figures for Hertz and Avis, contrary to the rule's literal f |
| T20 | Market analysis | correct | 1.00 | 7 | 42 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/edadc9aac34da771bbd01452ab3e5a2f) | All required figures and quarter mappings are correct, and the difference is exact. The optional YoY-growth detail is only rounded to 14% for both and does not meet the stated tolerance for Visa, but optional items do not affect the verdict |
| W01 | call commentary | correct | 1.00 | 8 | 21 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/b40d9b099f37f4dbd15266db3b340f2d) | The answer gives both required current outlooks and correctly compares each with the superseded guidance, while avoiding the listed traps. |
| W02 | call commentary | correct | 1.00 | 3 | 8 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/ea146fe98586a66bb46ebab7dbb68fca) | All required growth rates and the approximate Low NA EUV shipment figure are given correctly. The extra FY2026 sales and 2027-capacity context does not replace the requested growth rates. |
| W05 | recent event | partial | 0.88 | 4 | 11 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/800bbebc08fcc71b4e9fe6e40428d767) | The answer correctly gives the superseding US$7.02 best-and-final non-binding proposal, its status and dates, the 12.5% premium, and the US$0.27 (4.0%) increase. It omits the rollover alternative for eligible shareholders, which is included |
| W06 | recent event | partial | 0.89 | 5 | 17 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/d35201f7635d1bfc69959d98d791a767) | The answer correctly covers the interim CEO, timing, search status, reaffirmed guidance, and revenue ranges. It omits the required fact that Desai also left the board. |
| W10 | foreign issuer | partial | 0.61 | 4 | 15 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/7d922983ffc6193c5855c7aedce1d0de) | The answer correctly gives the quarter, operating income and its decline, net income and its increase, and the revised-versus-May forecast. However, it omits or misstates the specified line-item explanation for the divergence between operat |
| X01 | Market analysis | correct | 1.00 | 14 | 43 s | [trace](https://us.cloud.langfuse.com/project/cmuugqo1k06h0ad0dculyh3n5/traces/3b999c56c2cafd177c1fb2599d1c04e3) | 16/16 cells correct |
