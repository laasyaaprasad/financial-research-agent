# Table-task held-out evaluation set: sources and verification (built 2026-10-03)

Generated for `evals/test_tables.jsonl`: 8 table tasks (X01-X08), 86 reference cells, 21 distinct companies, none from the excluded list. Every figure comes from SEC EDGAR primary documents (Forms 10-Q and 10-K, and 8-K Exhibit 99.1 earnings releases) fetched through the project `EdgarClient` into a fresh scratch cache (the project's `results/sec` cache held stale companyfacts for some filers). No Tavily CLI or API was used. No agent outputs were seen and no task was tailored to a system. `verified_by_human` is false for every row; `verification_status` is `source_checked_by_agent`.

## Verification method and counts

1. Every input was matched to XBRL companyfacts for the same period (start/end) in a filing filed on or before the task's as_of date where the facts exist, and to the filing text (label followed by the number) in the cited document.
2. Every derived value (growth, margins, TTM, total and net debt, Q4 = FY minus nine months) was recomputed in Python from the filed inputs.
3. Independent cross-checks against the matching 8-K Exhibit 99.1 earnings release were run for X01, X03, X04 and X06 (all cells), X07 (all five growth inputs), and for the derived fourth-quarter cells of X02, X05 and X08.
4. 'Most recent reported' was confirmed from the EDGAR submissions index (all 10-K, 10-Q and 8-K Item 2.02 filings up to the as_of date) for all 21 companies; no 10-Q/A or 10-K/A amendments affect the periods used.

| Measure | Cells |
|---|---|
| Total reference cells | 86 (81 numeric + 5 text period-label cells in X07) |
| Numeric cells verified in filing text | 81 of 81 |
| Cells whose inputs match XBRL companyfacts for the same period and filing | 67 (not applicable for X05 segment values, NXP, KB Home, Toll Brothers and X07 labels) |
| Cells cross-checked to an 8-K Ex. 99.1 earnings release | 62 |
| Derived cells recomputed in Python (growth, margins, TTM, debt, Q4 = FY - 9M) | 48 |
| Verification failures at final build | 0 |
| Cells that could not be verified | 0 (any unverifiable cell caused the task design to change) |

Per-task cell counts: X01 16, X02 16, X03 8, X04 12, X05 8, X06 8, X07 10, X08 8.


## X01: Build a peer comp table for four analog and mixed-signal semiconductor companies: Texas Instruments, Analog De...

- **Companies:** Texas Instruments (TXN; FY ends Dec 31); Analog Devices (ADI; FY ends Saturday closest to Oct 31); Microchip Technology (MCHP; FY ends Mar 31); NXP Semiconductors (NXPI; FY ends Dec 31)
- **as_of:** 2026-10-03; category Market analysis; 16 cells; tolerance 0.5% of value for USD amounts, 0.3 for percentages, 0.01 for EPS, 0 for text.
- **Periods:** Texas Instruments Q2 FY2026 (2026-04-01 to 2026-06-30); Analog Devices Q2 FY2026 (2026-02-01 to 2026-05-02); Microchip Technology Q1 FY2027 (2026-04-01 to 2026-06-30); NXP Semiconductors Q2 FY2026 (2026-03-30 to 2026-06-28)
- **Verification:** XBRL companyfacts (TXN, ADI, MCHP) + 10-Q text for all four + 8-K Ex. 99.1 cross-check
- **Reference table:**

  | Row | Revenue | YoY revenue growth | Gross margin | Operating margin |
  |---|---|---|---|---|
  | Texas Instruments (Q2 FY2026, ended 2026-06-30) | 5,463.0 | 22.82% | 61.36% | 42.28% |
  | Analog Devices (Q2 FY2026, ended 2026-05-02) | 3,623.5 | 37.25% | 67.33% | 38.08% |
  | Microchip Technology (Q1 FY2027, ended 2026-06-30) | 1,484.7 | 38.05% | 63.24% | 22.68% |
  | NXP Semiconductors (Q2 FY2026, ended 2026-06-28) | 3,496.0 | 19.48% | 57.27% | 30.64% |

- **Source filings:**
  - [X01-E1](https://www.sec.gov/Archives/edgar/data/97476/000009747626000152/txn-20260630.htm): Texas Instruments Form 10-Q, quarter ended 2026-06-30 (Q2 FY2026) (filed/dated 2026-07-24)
  - [X01-E2](https://www.sec.gov/Archives/edgar/data/6281/000000628126000052/adi-20260502.htm): Analog Devices Form 10-Q, quarter ended 2026-05-02 (Q2 FY2026) (filed/dated 2026-05-20)
  - [X01-E3](https://www.sec.gov/Archives/edgar/data/827054/000082705426000038/mchp-20260630.htm): Microchip Technology Form 10-Q, quarter ended 2026-06-30 (Q1 FY2027) (filed/dated 2026-08-06)
  - [X01-E4](https://www.sec.gov/Archives/edgar/data/1413447/000141344726000045/nxpi-20260628.htm): NXP Semiconductors Form 10-Q, quarter ended 2026-06-28 (Q2 FY2026) (filed/dated 2026-07-28)
- **Caveats:**
  - Alignment rule is the exact window 2026-04-01 to 2026-07-31 on each company's own fiscal quarter. Each peer has exactly one qualifying quarter: TXN Q2 2026 (Apr 1-Jun 30), ADI fiscal Q2 2026 (Feb 1-May 2), MCHP fiscal Q1 2027 (Apr 1-Jun 30), NXP Q2 2026 (Mar 30-Jun 28). ON Semiconductor was rejected as a peer because two of its quarters (ended Apr 3 and Jul 3, 2026) fall in the window.
  - Decoys: ADI's fiscal Q3 2026 ended Aug 1, 2026 (10-Q filed 2026-08-19), one day outside the window; TXN's Q1 2026 ended Mar 31, 2026 and MCHP's Q4 FY2026 ended Mar 31, 2026 (both outside).
  - XBRL companyfacts for NXP had not ingested the 2026-07-28 10-Q when fetched (latest NXP facts were from the 2026-04-28 filing), so NXP's four inputs were verified in the 10-Q text and the 8-K Ex. 99.1 only (no XBRL check).
  - Line labels: TXN 'Operating profit', ADI 'Gross margin' (= gross profit, in $ thousands), MCHP 'Net sales'. NXP's GAAP 'Operating income (loss)' of 1,071 is after an 'Other income (expense)' line of (5) that NXP presents within operating income.
  - Growth and margins are computed from the unrounded filed values (ADI in thousands, MCHP in millions with one decimal), then rounded to 2 decimals; tolerance is 0.3 percentage points.

## X02: Build an eight-quarter trend table for Ralph Lauren (fiscal year ends the Saturday closest to March 31). For e...

- **Companies:** Ralph Lauren Corporation (RL; fiscal year ends the Saturday closest to March 31)
- **as_of:** 2026-10-03; category Trends; 16 cells; tolerance 0.5% of value for USD amounts, 0.3 for percentages, 0.01 for EPS, 0 for text.
- **Periods:** Q2 FY2025 (2024-06-30 to 2024-09-28); Q3 FY2025 (2024-09-29 to 2024-12-28); Q4 FY2025 (2024-12-29 to 2025-03-29); Q1 FY2026 (2025-03-30 to 2025-06-28); Q2 FY2026 (2025-06-29 to 2025-09-27); Q3 FY2026 (2025-09-28 to 2025-12-27); Q4 FY2026 (2025-12-28 to 2026-03-28); Q1 FY2027 (2026-03-29 to 2026-06-27)
- **Verification:** XBRL companyfacts + 10-Q/10-K text; Q4 cells also cross-checked to 8-K Ex. 99.1
- **Reference table:**

  | Row | Revenue | GAAP operating income |
  |---|---|---|
  | Q2 FY2025 (ended 2024-09-28) | 1,726.0 | 178.9 |
  | Q3 FY2025 (ended 2024-12-28) | 2,143.5 | 389.7 |
  | Q4 FY2025 (ended 2025-03-29) | 1,697.3 | 155.0 |
  | Q1 FY2026 (ended 2025-06-28) | 1,719.1 | 273.6 |
  | Q2 FY2026 (ended 2025-09-27) | 2,010.7 | 245.7 |
  | Q3 FY2026 (ended 2025-12-27) | 2,406.0 | 471.3 |
  | Q4 FY2026 (ended 2026-03-28) | 1,978.7 | 188.6 |
  | Q1 FY2027 (ended 2026-06-27) | 1,959.8 | 342.4 |

- **Source filings:**
  - [X02-E1](https://www.sec.gov/Archives/edgar/data/1037038/000103703824000029/rl-20240928.htm): Ralph Lauren Form 10-Q, quarter ended 2024-09-28 (Q2 FY2025) (filed/dated 2024-11-07)
  - [X02-E2](https://www.sec.gov/Archives/edgar/data/1037038/000103703825000007/rl-20241228.htm): Ralph Lauren Form 10-Q, quarter ended 2024-12-28 (Q3 FY2025) (filed/dated 2025-02-06)
  - [X02-E3](https://www.sec.gov/Archives/edgar/data/1037038/000103703825000018/rl-20250628.htm): Ralph Lauren Form 10-Q, quarter ended 2025-06-28 (Q1 FY2026) (filed/dated 2025-08-07)
  - [X02-E4](https://www.sec.gov/Archives/edgar/data/1037038/000162828025049927/rl-20250927.htm): Ralph Lauren Form 10-Q, quarter ended 2025-09-27 (Q2 FY2026) (filed/dated 2025-11-06)
  - [X02-E5](https://www.sec.gov/Archives/edgar/data/1037038/000162828026005784/rl-20251227.htm): Ralph Lauren Form 10-Q, quarter ended 2025-12-27 (Q3 FY2026) (filed/dated 2026-02-05)
  - [X02-E6](https://www.sec.gov/Archives/edgar/data/1037038/000162828026053992/rl-20260627.htm): Ralph Lauren Form 10-Q, quarter ended 2026-06-27 (Q1 FY2027) (filed/dated 2026-08-06)
  - [X02-E7](https://www.sec.gov/Archives/edgar/data/1037038/000103703825000011/rl-20250329.htm): Ralph Lauren Form 10-K for fiscal year ended 2025-03-29 (filed/dated 2025-05-22)
  - [X02-E8](https://www.sec.gov/Archives/edgar/data/1037038/000103703825000010/rl-20250329xex991xpressrel.htm): Ralph Lauren Q4 fiscal year release, 8-K Exhibit 99.1 (Q4 FY2025: reported directly) (filed/dated 2025-05-22)
  - [X02-E9](https://www.sec.gov/Archives/edgar/data/1037038/000162828026037074/rl-20260328.htm): Ralph Lauren Form 10-K for fiscal year ended 2026-03-28 (filed/dated 2026-05-21)
  - [X02-E10](https://www.sec.gov/Archives/edgar/data/1037038/000162828026037053/rl-20260328xex991xpressrel.htm): Ralph Lauren Q4 fiscal year release, 8-K Exhibit 99.1 (Q4 FY2026: reported directly) (filed/dated 2026-05-21)
- **Caveats:**
  - Eight quarters are Q2 FY2025 (ended 2024-09-28) through Q1 FY2027 (ended 2026-06-27); Q2 FY2027 (ends Sep 2026) is not reported by 2026-10-03. Ralph Lauren's fiscal 2025 and fiscal 2026 are both 52-week years (ended Mar 29, 2025 and Mar 28, 2026).
  - Q4 FY2025 and Q4 FY2026 are not in any 10-Q. They were derived as FY (10-K) minus nine months (Q3 10-Q) and match the Q4 8-K Ex. 99.1 exactly (revenue 1,697.3 and 1,978.7; operating income 155.0 and 188.6).
  - No restatements: the Q2 FY2025 and Q3 FY2025 values in the original 10-Qs equal the comparatives in the later 10-Qs and the XBRL facts. Decoy: adjusted operating income is higher (Q4 FY2025 175; Q4 FY2026 218).

## X03: Build a trailing-twelve-month (TTM) comp table for four U.S. restaurant companies: Darden Restaurants, Brinker...

- **Companies:** Darden Restaurants (DRI; FY ends last Sunday of May); Brinker International (EAT; FY ends last Wednesday of June); Cracker Barrel Old Country Store (CBRL; FY ends Friday nearest July 31); The Cheesecake Factory (CAKE; FY ends Tuesday nearest Dec 31)
- **as_of:** 2026-10-03; category Market analysis; 8 cells; tolerance 0.5% of value for USD amounts, 0.3 for percentages, 0.01 for EPS, 0 for text.
- **Periods:** Darden Restaurants TTM through Q1 FY2027 (13 weeks ended Aug 30, 2026) (2025-08-25 to 2026-08-30); Brinker International TTM through Q4 FY2026 (fiscal year ended Jun 24, 2026) (2025-06-26 to 2026-06-24); Cracker Barrel Old Country Store TTM through Q4 FY2026 (fiscal year ended Jul 31, 2026) (2025-08-02 to 2026-07-31); The Cheesecake Factory TTM through Q2 FY2026 (quarter ended Jun 30, 2026) (2025-07-02 to 2026-06-30)
- **Verification:** XBRL companyfacts + 10-K/10-Q text + 8-K Ex. 99.1 cross-check
- **Reference table:**

  | Row | TTM revenue | TTM net income |
  |---|---|---|
  | Darden Restaurants (TTM ended 2026-08-30) | 13,366.5 | 1,182.3 |
  | Brinker International (TTM ended 2026-06-24) | 5,807.4 | 487.0 |
  | Cracker Barrel Old Country Store (TTM ended 2026-07-31) | 3,318.7 | 31.7 |
  | The Cheesecake Factory (TTM ended 2026-06-30) | 3,877.3 | 178.6 |

- **Source filings:**
  - [X03-E1](https://www.sec.gov/Archives/edgar/data/940944/000094094426000025/dri-20260531.htm): Darden Restaurants, Inc. Form 10-K (fiscal year ended 2026-05-31) (filed/dated 2026-07-24)
  - [X03-E2](https://www.sec.gov/Archives/edgar/data/940944/000094094426000042/dri-20260830.htm): Darden Restaurants, Inc. Form 10-Q (quarter ended 2026-08-30) (filed/dated 2026-10-02)
  - [X03-E3](https://www.sec.gov/Archives/edgar/data/703351/000070335126000029/eat-20260624.htm): Brinker International, Inc. Form 10-K (fiscal year ended 2026-06-24) (filed/dated 2026-08-19)
  - [X03-E4](https://www.sec.gov/Archives/edgar/data/1067294/000110465926110772/cbrl-20260731x10k.htm): Cracker Barrel Old Country Store, Inc. Form 10-K (fiscal year ended 2026-07-31) (filed/dated 2026-09-25)
  - [X03-E5](https://www.sec.gov/Archives/edgar/data/887596/000110465926018643/cake-20251230x10k.htm): The Cheesecake Factory Incorporated Form 10-K (fiscal year ended 2025-12-30) (filed/dated 2026-02-23)
  - [X03-E6](https://www.sec.gov/Archives/edgar/data/887596/000110465926089840/cake-20260630x10q.htm): The Cheesecake Factory Incorporated Form 10-Q (quarter ended 2026-06-30) (filed/dated 2026-08-03)
- **Caveats:**
  - TTM rule is stated in the question: latest FY + current YTD - prior YTD (equals the fiscal year when the latest quarter is Q4). Darden 53-week FY2026 means its TTM window (2025-08-25 to 2026-08-30) is 53 weeks; the question says not to adjust for this.
  - Darden's most recent report is fiscal Q1 FY2027 (13 weeks ended 2026-08-30): earnings release 2026-09-24, 10-Q filed 2026-10-02 (the day before the as-of date). Brinker's 10-K (FY ended 2026-06-24) was filed 2026-08-19 and Cracker Barrel's 10-K (FY ended 2026-07-31) on 2026-09-25, so TTM = fiscal year for both. Cheesecake's FY2025 ended 2025-12-30; latest quarter Q2 2026 ended 2026-06-30 (10-Q filed 2026-08-03).
  - Net income is GAAP net income attributable to the company (XBRL NetIncomeLoss). Some companyfacts rows for annual net income come from DEF 14A proxy filings (e.g., Cheesecake FY2025 shown rounded as 148,000,000); only 10-K/10-Q values were used (Cheesecake FY2025 = 148.427).
  - Cheesecake TTM revenue = 3,751.806 + 2,008.466 - 1,883.022 = 3,877.250 (listed as 3,877.3); tolerance is 0.5% of value so rounding is immaterial.

## X04: Build a balance-sheet comp table for four U.S. retailers: TJX Companies, Ross Stores, Lowe's and Tractor Suppl...

- **Companies:** The TJX Companies (TJX; FY ends Saturday nearest Jan 31); Ross Stores (ROST; FY ends Saturday nearest Jan 31); Lowe's Companies (LOW; FY ends Friday nearest Jan 31); Tractor Supply (TSCO; FY ends last Saturday of Dec)
- **as_of:** 2026-10-03; category Market analysis; 12 cells; tolerance 0.5% of value for USD amounts, 0.3 for percentages, 0.01 for EPS, 0 for text.
- **Periods:** The TJX Companies balance sheet date (Q2 FY2027) (2026-08-01); Ross Stores balance sheet date (Q2 FY2026) (2026-08-01); Lowe's Companies balance sheet date (Q2 FY2026) (2026-07-31); Tractor Supply balance sheet date (Q2 FY2026) (2026-06-27)
- **Verification:** XBRL companyfacts + 10-Q balance-sheet text + 8-K Ex. 99.1 cross-check
- **Reference table:**

  | Row | Cash and cash equivalents | Total debt | Net debt |
  |---|---|---|---|
  | The TJX Companies (balance sheet 2026-08-01) | 6,004.0 | 2,871.0 | -3,133.0 |
  | Ross Stores (balance sheet 2026-08-01) | 4,288.1 | 1,018.5 | -3,269.6 |
  | Lowe's Companies (balance sheet 2026-07-31) | 3,172.0 | 37,556.0 | 34,384.0 |
  | Tractor Supply (balance sheet 2026-06-27) | 231.6 | 2,153.8 | 1,922.2 |

- **Source filings:**
  - [X04-E1](https://www.sec.gov/Archives/edgar/data/109198/000010919826000048/tjx-20260801.htm): The TJX Companies, Inc. Form 10-Q, balance sheet as of 2026-08-01 (Q2 FY2027) (filed/dated 2026-08-28)
  - [X04-E2](https://www.sec.gov/Archives/edgar/data/745732/000074573226000041/rost-20260801.htm): Ross Stores, Inc. Form 10-Q, balance sheet as of 2026-08-01 (Q2 FY2026) (filed/dated 2026-09-01)
  - [X04-E3](https://www.sec.gov/Archives/edgar/data/60667/000006066726000117/low-20260731.htm): Lowe's Companies, Inc. Form 10-Q, balance sheet as of 2026-07-31 (Q2 FY2026) (filed/dated 2026-08-27)
  - [X04-E4](https://www.sec.gov/Archives/edgar/data/916365/000091636526000059/tsco-20260627.htm): Tractor Supply Company Form 10-Q, balance sheet as of 2026-06-27 (Q2 FY2026) (filed/dated 2026-08-06)
- **Caveats:**
  - Debt definition is applied to the face of each balance sheet: 'current portion of long-term debt' + 'long-term debt'. TJX and Ross use 'Current portion of long-term debt' and 'Long-term debt' (XBRL LongTermDebtCurrent/Noncurrent); Lowe's captions are 'Current maturities of long-term debt' and 'Long-term debt, excluding current maturities' (these captions may include finance lease obligations and its term loan, which the question's face-of-balance-sheet rule accepts); Tractor Supply shows only 'Long-term debt' (no current portion line, so current portion = 0; finance lease liabilities are shown separately and excluded).
  - TJX and Ross are in net cash (negative net debt). Ross reports in thousands (cash 4,288,124; current portion 241,459; long-term debt 777,053).
  - Latest balance sheets by date: TJX and Ross Aug 1, 2026; Lowe's Jul 31, 2026; Tractor Supply Jun 27, 2026. Burlington (caption 'Current maturities of long term debt and other current debt'), Dollar General ('long-term obligations'), Kroger (captions include finance leases; XBRL tags exclude them) and Dollar Tree (only 'Long-term debt, net') were rejected as peers because their captions do not map cleanly to the stated definition.

## X05: For AMETEK, build a segment revenue trend: report net sales in USD millions for each of its two reportable seg...

- **Companies:** AMETEK, Inc. (AME; FY ends Dec 31; two reportable segments: Electronic Instruments Group and Electromechanical Group)
- **as_of:** 2026-10-03; category Trends; 8 cells; tolerance 0.5% of value for USD amounts, 0.3 for percentages, 0.01 for EPS, 0 for text.
- **Periods:** Q3 2025 (2025-07-01 to 2025-09-30); Q4 2025 (2025-10-01 to 2025-12-31); Q1 2026 (2026-01-01 to 2026-03-31); Q2 2026 (2026-04-01 to 2026-06-30)
- **Verification:** Filing text (segment tables) + consolidated XBRL tie-out; Q4 cells cross-checked to 8-K Ex. 99.1
- **Reference table:**

  | Row | Electronic Instruments Group (EIG) | Electromechanical Group (EMG) |
  |---|---|---|
  | Q3 2025 (ended 2025-09-30) | 1,246.3 | 646.3 |
  | Q4 2025 (ended 2025-12-31) | 1,369.5 | 628.9 |
  | Q1 2026 (ended 2026-03-31) | 1,264.5 | 663.9 |
  | Q2 2026 (ended 2026-06-30) | 1,321.2 | 723.2 |

- **Source filings:**
  - [X05-E1](https://www.sec.gov/Archives/edgar/data/1037868/000103786825000077/ame-20250930.htm): AMETEK Form 10-Q for quarter ended 2025-09-30 (Q3 2025) (filed/dated 2025-10-30)
  - [X05-E2](https://www.sec.gov/Archives/edgar/data/1037868/000103786826000144/ame-20260331.htm): AMETEK Form 10-Q for quarter ended 2026-03-31 (Q1 2026) (filed/dated 2026-04-30)
  - [X05-E3](https://www.sec.gov/Archives/edgar/data/1037868/000103786826000175/ame-20260630.htm): AMETEK Form 10-Q for quarter ended 2026-06-30 (Q2 2026) (filed/dated 2026-08-04)
  - [X05-E4](https://www.sec.gov/Archives/edgar/data/1037868/000103786826000016/ame-20251231.htm): AMETEK Form 10-K for fiscal year ended 2025-12-31 (filed/dated 2026-02-17)
  - [X05-E5](https://www.sec.gov/Archives/edgar/data/1037868/000103786826000006/ametek8kexhibit99102032026.htm): AMETEK Q4 2025 earnings release, 8-K Exhibit 99.1 (filed/dated 2026-02-03)
- **Caveats:**
  - Segment net sales are dimensional XBRL and are not in companyfacts, so they were read from the segment tables in the filings (10-Q tables list EMG before EIG) and tied to consolidated net sales (XBRL Revenue) for every quarter: EIG + EMG = consolidated.
  - Q4 2025 = FY2025 (10-K: EIG 4,919,100; EMG 2,482,016) minus nine months (Q3 2025 10-Q: EIG 3,549,576; EMG 1,853,092) = EIG 1,369,524; EMG 628,924, matching the Q4 2025 8-K Ex. 99.1.
  - Genuine Parts was rejected for this task: its FY2025 10-K recast segments to three (North America Automotive, International Automotive, Industrial), so Q3 2025 as originally reported (two segments) cannot be aligned with later quarters.

## X06: As of March 31, 2026, what were Conagra Brands' net sales (USD millions) and GAAP diluted EPS (USD, as reporte...

- **Companies:** Conagra Brands, Inc. (CAG; FY ends last Sunday of May)
- **as_of:** 2026-03-31; category Trends; 8 cells; tolerance 0.5% of value for USD amounts, 0.3 for percentages, 0.01 for EPS, 0 for text.
- **Periods:** Q3 FY2025 (2024-11-25 to 2025-02-23); Q4 FY2025 (2025-02-24 to 2025-05-25); Q1 FY2026 (2025-05-26 to 2025-08-24); Q2 FY2026 (2025-08-25 to 2025-11-23)
- **Verification:** XBRL companyfacts (as-of filtered) + 10-Q/10-K text + 8-K Ex. 99.1 cross-check for every quarter
- **Reference table:**

  | Row | Net sales (revenue) | Diluted EPS |
  |---|---|---|
  | Q3 FY2025 (ended 2025-02-23) | 2,841.0 | 0.30 |
  | Q4 FY2025 (ended 2025-05-25) | 2,781.8 | 0.53 |
  | Q1 FY2026 (ended 2025-08-24) | 2,632.6 | 0.34 |
  | Q2 FY2026 (ended 2025-11-23) | 2,979.1 | -1.39 |

- **Source filings:**
  - [X06-E1](https://www.sec.gov/Archives/edgar/data/23217/000155837025004399/tmb-20250223x10q.htm): Conagra Brands Form 10-Q for quarter ended 2025-02-23 (Q3 FY2025) (filed/dated 2025-04-03)
  - [X06-E2](https://www.sec.gov/Archives/edgar/data/23217/000002321725000011/tmb-20250403xex99d1.htm): Conagra earnings release for Q3 FY2025, 8-K Exhibit 99.1 (filed/dated 2025-04-03)
  - [X06-E3](https://www.sec.gov/Archives/edgar/data/23217/000110465925095651/tmb-20250824x10q.htm): Conagra Brands Form 10-Q for quarter ended 2025-08-24 (Q1 FY2026) (filed/dated 2025-10-01)
  - [X06-E4](https://www.sec.gov/Archives/edgar/data/23217/000002321725000083/tmb-20251001xex99d1.htm): Conagra earnings release for Q1 FY2026, 8-K Exhibit 99.1 (filed/dated 2025-10-01)
  - [X06-E5](https://www.sec.gov/Archives/edgar/data/23217/000110465925123200/tmb-20251123x10q.htm): Conagra Brands Form 10-Q for quarter ended 2025-11-23 (Q2 FY2026) (filed/dated 2025-12-19)
  - [X06-E6](https://www.sec.gov/Archives/edgar/data/23217/000002321725000094/tmb-20251219xex99d1.htm): Conagra earnings release for Q2 FY2026, 8-K Exhibit 99.1 (filed/dated 2025-12-19)
  - [X06-E7](https://www.sec.gov/Archives/edgar/data/23217/000155837025009180/tmb-20250525x10k.htm): Conagra Brands Form 10-K for fiscal year ended 2025-05-25 (filed/dated 2025-07-10)
  - [X06-E8](https://www.sec.gov/Archives/edgar/data/23217/000002321725000039/tmb-20250710xex99d1.htm): Conagra Q4 FY2025 earnings release, 8-K Exhibit 99.1 (filed/dated 2025-07-10)
- **Caveats:**
  - As-of rule: only filings made on or before 2026-03-31. Conagra's next results (fiscal Q3 FY2026, quarter ended 2026-02-22) were released and the 10-Q filed on 2026-04-01, so the last four reported quarters are Q3 FY2025 to Q2 FY2026. XBRL values were drawn only from filings filed on or before the as-of date.
  - Q4 FY2025 net sales = FY2025 (10-K, 11,612.8) minus nine months (8,831.0) = 2,781.8, matching the 8-K Ex. 99.1. Q4 FY2025 reported diluted EPS is 0.53 from the release (FY 2.40 minus nine-month 1.87 also gives 0.53).
  - GAAP diluted EPS (0.30, 0.53, 0.34, -1.39) vs adjusted EPS (0.51, 0.56, 0.39, 0.45); the Q2 FY2026 loss reflects goodwill and brand impairment charges.

## X07: As of October 3, 2026, for each of five U.S. homebuilders (Lennar, KB Home, Toll Brothers, D.R. Horton and Pul...

- **Companies:** Lennar (LEN; FY ends Nov 30); KB Home (KBH; FY ends Nov 30); Toll Brothers (TOL; FY ends Oct 31); D.R. Horton (DHI; FY ends Sep 30); PulteGroup (PHM; FY ends Dec 31)
- **as_of:** 2026-10-03; category Market analysis; 10 cells; tolerance 0.5% of value for USD amounts, 0.3 for percentages, 0.01 for EPS, 0 for text.
- **Periods:** Lennar Corporation Q3 FY2026 (2026-06-01 to 2026-08-31); KB Home Q3 FY2026 (2026-06-01 to 2026-08-31); Toll Brothers Q3 FY2026 (2026-05-01 to 2026-07-31); D.R. Horton Q3 FY2026 (2026-04-01 to 2026-06-30); PulteGroup Q2 FY2026 (2026-04-01 to 2026-06-30)
- **Verification:** XBRL companyfacts (LEN, DHI, PHM) + 10-Q/8-K text; KB Home and Toll Brothers from filing/release text only
- **Reference table:**

  | Company | Most recent reported quarter | YoY total revenue growth |
  |---|---|---|
  | Lennar Corporation | Q3 FY2026 (quarter ended Aug 31, 2026) | -8.67% |
  | KB Home | Q3 FY2026 (quarter ended Aug 31, 2026) | -19.96% |
  | Toll Brothers | Q3 FY2026 (quarter ended Jul 31, 2026) | -9.72% |
  | D.R. Horton | Q3 FY2026 (quarter ended Jun 30, 2026) | 0.02% |
  | PulteGroup | Q2 FY2026 (quarter ended Jun 30, 2026) | -9.56% |

- **Source filings:**
  - [X07-E1](https://www.sec.gov/Archives/edgar/data/920760/000162828026064557/len-20260831.htm): Lennar Corporation Form 10-Q for Q3 FY2026 (filed/dated 2026-10-02)
  - [X07-E2](https://www.sec.gov/Archives/edgar/data/920760/000162828026062287/ex991-2026831x8kq3.htm): Lennar Corporation earnings release (8-K Exhibit 99.1) for Q3 FY2026 (filed/dated 2026-09-16)
  - [X07-E3](https://www.sec.gov/Archives/edgar/data/795266/000079526626000068/exh991kbh-earningsrelease0.htm): KB Home earnings release (8-K Exhibit 99.1) for Q3 FY2026 (filed/dated 2026-09-22)
  - [X07-E4](https://www.sec.gov/Archives/edgar/data/794170/000079417026000102/tol-20260731.htm): Toll Brothers Form 10-Q for Q3 FY2026 (filed/dated 2026-08-28)
  - [X07-E5](https://www.sec.gov/Archives/edgar/data/794170/000079417026000096/tol-7312026x8kexh991.htm): Toll Brothers earnings release (8-K Exhibit 99.1) for Q3 FY2026 (filed/dated 2026-08-18)
  - [X07-E6](https://www.sec.gov/Archives/edgar/data/882184/000088218426000096/dhi-20260630.htm): D.R. Horton Form 10-Q for Q3 FY2026 (filed/dated 2026-07-23)
  - [X07-E7](https://www.sec.gov/Archives/edgar/data/882184/000088218426000092/a6302026exhibit991.htm): D.R. Horton earnings release (8-K Exhibit 99.1) for Q3 FY2026 (filed/dated 2026-07-21)
  - [X07-E8](https://www.sec.gov/Archives/edgar/data/822416/000082241626000036/phm-20260630.htm): PulteGroup Form 10-Q for Q2 FY2026 (filed/dated 2026-07-22)
  - [X07-E9](https://www.sec.gov/Archives/edgar/data/822416/000082241626000034/ex991earningspr06302026.htm): PulteGroup earnings release (8-K Exhibit 99.1) for Q2 FY2026 (filed/dated 2026-07-22)
- **Caveats:**
  - Latest quarters differ: Lennar and KB Home Q3 FY2026 (ended 2026-08-31), Toll Brothers Q3 FY2026 (ended 2026-07-31), D.R. Horton Q3 FY2026 (ended 2026-06-30), PulteGroup Q2 FY2026 (ended 2026-06-30).
  - KB Home had only the 2026-09-22 8-K earnings release for the quarter ended 2026-08-31 (its 10-Q was not filed by 2026-10-03). Lennar's 10-Q was filed 2026-10-02 (release 2026-09-16). Toll Brothers' income statement shows revenues as an unlabeled subtotal under 'Revenues' (home sales 2,652,476 + land sales and other 6,305 = 2,658,781 thousand) and XBRL companyfacts had no matching revenue tag.
  - D.R. Horton growth is +0.015% (9,227.1 vs 9,225.7): effectively flat, tolerance 0.3 pp. The period-label cells are free text: accept any equivalent phrasing that gives the correct fiscal quarter number and period-end date. Total revenues are consolidated (homebuilding plus financial services, multifamily and other).

## X08: For The Estee Lauder Companies (fiscal year ends June 30), report GAAP gross margin (gross profit / net sales,...

- **Companies:** The Estee Lauder Companies Inc. (EL; FY ends June 30)
- **as_of:** 2026-10-03; category Trends; 8 cells; tolerance 0.5% of value for USD amounts, 0.3 for percentages, 0.01 for EPS, 0 for text.
- **Periods:** Q1 FY2026 (2025-07-01 to 2025-09-30); Q2 FY2026 (2025-10-01 to 2025-12-31); Q3 FY2026 (2026-01-01 to 2026-03-31); Q4 FY2026 (2026-04-01 to 2026-06-30)
- **Verification:** XBRL companyfacts + 10-Q/10-K text; Q4 cells also cross-checked to 8-K Ex. 99.1
- **Reference table:**

  | Row | Gross margin | Operating margin |
  |---|---|---|
  | Q1 FY2026 (ended 2025-09-30) | 73.37% | 4.85% |
  | Q2 FY2026 (ended 2025-12-31) | 76.50% | 9.48% |
  | Q3 FY2026 (ended 2026-03-31) | 76.40% | 6.71% |
  | Q4 FY2026 (ended 2026-06-30) | 75.46% | -1.08% |

- **Source filings:**
  - [X08-E1](https://www.sec.gov/Archives/edgar/data/1001250/000100125025000109/el-20250930.htm): Estee Lauder Form 10-Q for quarter ended 2025-09-30 (Q1 FY2026) (filed/dated 2025-10-30)
  - [X08-E2](https://www.sec.gov/Archives/edgar/data/1001250/000100125026000006/el-20251231.htm): Estee Lauder Form 10-Q for quarter ended 2025-12-31 (Q2 FY2026) (filed/dated 2026-02-05)
  - [X08-E3](https://www.sec.gov/Archives/edgar/data/1001250/000100125026000019/el-20260331.htm): Estee Lauder Form 10-Q for quarter ended 2026-03-31 (Q3 FY2026) (filed/dated 2026-05-01)
  - [X08-E4](https://www.sec.gov/Archives/edgar/data/1001250/000100125026000041/el-20260630.htm): Estee Lauder Form 10-K for fiscal year ended 2026-06-30 (filed/dated 2026-08-19)
  - [X08-E5](https://www.sec.gov/Archives/edgar/data/1001250/000100125026000038/elq4fy2026exhibit991.htm): Estee Lauder Q4 and fiscal 2026 results, 8-K Exhibit 99.1 (filed/dated 2026-08-19)
- **Caveats:**
  - Fiscal year ends June 30. Q1-Q3 FY2026 are direct 10-Q values; Q4 FY2026 = FY2026 (10-K) minus nine months (Q3 10-Q): net sales 15,049 - 11,422 = 3,627; gross profit 11,362 - 8,625 = 2,737; operating income 780 - 819 = -39. These match the Q4 8-K Ex. 99.1 (net sales 3,627, gross profit 2,737, operating loss (39)).
  - Q4 GAAP operating margin is negative (-1.08%) because of 293 of restructuring and other charges; adjusted Q4 operating income (non-GAAP) was 267 and is a decoy.
