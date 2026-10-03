# Final report: a cited financial research agent

## 1. Problem

Financial analysts research companies against a hard standard. Every number must be:
- for the right company and the right fiscal period
- exactly as reported
- traceable to a source they can defend

The starter was a LangChain agent with one Tavily search tool. The task was to improve it in a way that creates real value for such a user. My scope, after an early overfit attempt (see §5): **cited, period-correct answers and tables about SEC-reporting companies**:
- reported results
- calculations over them
- guidance and commentary
- recent developments

Anything it can't support is refused explicitly.

## 2. Base agent results

The starter's design searches the web for everything, doesn't know today's date, and does arithmetic in its head.

| Starter configuration | Dev set (25 fixed-answer questions) | Primary-source citations | Cited claims supported |
|---|---|---|---|
| As shipped (Kimi K2.6), 3 runs | 11–13 fully correct | 20–24% | 51–75% |
| Same design on DeepSeek V4.1 Flash (the comparison baseline) | 21 fully correct | 39% | 83% |

Moving the starter to a stronger model fixed most of its correctness. To isolate what the architecture contributes, every comparison below runs the baseline and the new agent on the **same model**.

## 3. Architecture and why each part exists

`question → resolve → reporting calendar → plan → evidence (SEC first, Tavily for gaps) → write → code checks → verify → cited brief/table`

| Component | Why it's there |
|---|---|
| **Company resolution against SEC's ticker list** (`company.py`) | **Wrong-entity errors:** Facebook vs. Meta, share classes, spin-offs. The model only names companies, so it can never invent an identifier. |
| **Reporting calendar from each company's own filings** (`fiscal.py`) | **Fiscal-period errors:** confusing fiscal and calendar periods caused 63% of the best model's errors in Daloopa's benchmark. The calendar gives fiscal labels with exact dates, handles start-year naming and irregular 16-week quarters, and gives each period's reporting status as of the question date, which drives both refusals and point-in-time answers. |
| **One planning call, validated in code** (`planner.py`) | Scales effort to the question (Anthropic's guidance; OpenAI's `financial_research_agent`). It can't pick a period the company hasn't reported, and it plans at most 3 searches. |
| **SEC-first evidence:** ranked passages from releases and 10-Q/10-K filings, plus XBRL facts | Primary, exact numbers at no cost. In Daloopa's benchmark, structured filings data took agents from 20–71% accuracy to about 90%. Always including the core income-statement lines fixed missing-revenue gaps. |
| **Tavily for what filings lack, plus one gap-filling round** | News, earnings-call guidance, and companies that don't file with the SEC. Basic search plus one query-focused extract, social media excluded. Added after dev failures where guidance existed only on the call. |
| **Claims and cells with verbatim quotes; code checks; calculations in code** (`writer.py`) | **Hallucinated or mis-computed numbers:** a quote must exist in its source, every number must appear in a quote, and arithmetic (growth, TTM, fiscal Q4 = full year minus nine months) is evaluated by code, never by the model. |
| **Verifier pass, one revision, withhold what still fails** | **Meaning errors code can't see:** wrong metric (net sales vs. revenue), GAAP vs. non-GAAP, actual vs. guidance. This follows OpenAI's verifier pattern and Bloomberg's post-generation checks. |
| **Tables** | Comps and trend tables are what analysts build daily, and where per-cell provenance matters most. |
| **Langfuse tracing (OpenTelemetry) and an eval harness** | Every run is inspectable step by step with scores attached. Every change is measured before it ships. |
| **Reasoning effort set per step** | Halved median latency without changing quality on the dev set. |

All production code is generic: a unit test fails if any evaluation-set company name appears in `agents/`.

## 4. Final results vs. the base agent

**Held-out sets:** three sets, each frozen and hashed before the first run on it:
- 20 questions
- 20 hard questions (point-in-time, filing-only, multi-step fiscal, traps)
- 8 table tasks with 86 cells

That's 96 graded items. Each agent ran each set twice on the same model, graded by a different-family judge (Nemotron Ultra, 8/9 agreement with the user's grades).

| Measure | Baseline | New agent |
|---|---|---|
| Fixed answers fully correct | 79/84 (94%) | 81/84 (96%) |
| Table cells correct | 171/172 (99%) | 167/172 (97%) |
| **Verified-correct** (correct, every cited claim supported, every number cited) | **40/84 (48%)** | **68/84 (81%)** |
| Cited claims not supported by retrieved text | 27% | 9% (on tables: 69% vs. 6%) |
| Primary-source citations | 45% | 87% |
| Refusals correct | 10/12 | 12/12 |
| Tavily credits per question* | 7.4 | 0.8 (per table task: 20.8 vs. 0.2) |
| Median latency | 23 s | 48 s |

\* The new agent's credits are Tavily's own per-call usage. The baseline's are counted from its calls (1 per basic search, 2 per advanced), because the starter's LangChain tool doesn't report usage.

**How it compares**
- **Correctness: a tie.** A capable model plus Tavily finds the right figure as often as the pipeline. Tavily surfaces the right release or sec.gov filing.
- **Trust: a large gain.** 81% of the new agent's answers can be used as they stand, against 48% for the baseline: every cited claim supported and every number traceable. Its unsupported-claim rate is a third of the baseline's (about a tenth on tables), and every refusal is correct.
- **Cost: about 9× fewer Tavily credits.** The baseline's spend grows with task size: one table task took 53 advanced searches. The pipeline answers most questions from free SEC data.
- **Trade-off:** about 2× latency.

## 5. How the result was reached

1. **A first implementation was rebuilt.** It reached 21/25 on the dev set but was overfit: named-company rules and one prompt rule per test question. It was also unstable, ranging from 11 to 21 out of 25 across runs. It was replaced by the generic pipeline above, about 1,400 lines instead of about 5,700.
2. **Two more held-out sets were added.** The first held-out set couldn't separate the agents because both scored near the ceiling, so I added the harder set and the table set. They were built blind from SEC filings, without seeing either agent's outputs.
3. **Changes came only from dev failures.** Agent changes were driven by dev-set failures; none were made in response to held-out results. The known held-out issues stay unfixed and are reported: a unit mismatch in one table calculation, and an over-strict verifier rule.
4. **Within budget.** About 1,170 of the 1,500 Tavily credits were used by per-call accounting, most of them on the baseline. Tavily's dashboard showed 711 at the time; it lags.

Details: [`README.md`](README.md), [`results/final/results.md`](results/final/results.md), [`PLAN.md`](PLAN.md).
