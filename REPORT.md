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

The starter as shipped (Kimi K2.6) searches the web for everything, doesn't know today's date, and does arithmetic in its head. It was graded by the final judge:

| Set | Fully correct | Verified-correct | Primary-source citations | Tavily credits per question |
|---|---|---|---|---|
| Held-out sets 1 and 2 (34 fixed-answer questions × 2 runs) | 40/68 (59%) | 23/68 (34%) | 21% | 8.7 |
| Dev set (25 fixed-answer questions, 3 runs) | 40/75 (53%) | 20/75 (27%) | 22% | 8.7 |

It also refused only 7 of 12 requests that should have been refused, and 19% of its cited claims aren't supported by the text it retrieved.

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

**Held-out sets:** all frozen and hashed before their first run:
- 20 questions
- 20 hard questions (point-in-time, filing-only, multi-step fiscal, traps)
- 8 table tasks with 86 cells

Every run was graded by the same different-family judge (Nemotron Ultra, 8/9 agreement with the user's grades). Our agent includes its model choice, DeepSeek V4.1 Flash. The middle column runs the starter's design on that same model, to separate the architecture's contribution from the model's.

| Held-out sets 1 and 2 | Starter (as shipped) | Starter design, our model | **Our agent** |
|---|---|---|---|
| Fully correct | 40/68 (59%) | 64/68 (94%) | **67/68 (99%)** |
| **Verified-correct** (correct, every cited claim supported, every number cited) | 23/68 (34%) | 38/68 (56%) | **56/68 (82%)** |
| Cited claims not supported by retrieved text | 19% | 16% | **9%** |
| Primary-source citations | 21% | 41% | **82%** |
| Refusals correct | 7/12 | 10/12 | **12/12** |
| Tavily credits per question\* | 8.7 | 4.7 | **0.9** |
| Median latency | 18 s | 17 s | 40 s |

**Table set:** the as-shipped starter was not run on it, to protect the credit budget. Against the starter's design on our model, our agent got 167/172 cells correct vs. 171/172. Its cited figures not supported by retrieved text were 6% vs. 69%, and it used 0.2 credits per task vs. 20.8.

\* Our agent's credits are Tavily's own per-call usage. The starter's are counted from its calls (1 per basic search, 2 per advanced), because its LangChain tool doesn't report usage.

**How it compares**
- **Against what was shipped:**
  - fully correct rises from 59% to 99%
  - answers usable without re-checking rise from 34% to 82%
  - unsupported claims fall from 19% to 9%
  - primary sources rise from 21% to 82%
  - refusals correct rise from 7/12 to 12/12
  - about 10× fewer Tavily credits
  - about 2.2× slower
- **Attribution:**
  - **Correctness** comes mostly from the model choice: the starter's design reaches 94% on DeepSeek Flash.
  - **Trust and cost** come from the architecture: verified-correct 56% → 82%, primary sources 41% → 82%, refusals 10/12 → 12/12, credits 4.7 → 0.9 per question, and on tables unsupported figures 69% → 6% at about 100× fewer credits.

## 5. How the result was reached

1. **A first implementation was rebuilt.** It reached 21/25 on the dev set but was overfit: named-company rules and one prompt rule per test question. It was also unstable, ranging from 11 to 21 out of 25 across runs. It was replaced by the generic pipeline above, about 1,400 lines instead of about 5,700.
2. **Two more held-out sets were added.** On the first held-out set, the starter's design on our model and our agent both scored near the ceiling, so I added the harder set and the table set to test where the architecture matters. They were built blind from SEC filings, without seeing either agent's outputs.
3. **The as-shipped starter is the headline baseline.** It was run on the held-out sets once the comparison was framed as "what was shipped vs. what we built". The same-model runs stay as the architecture-only comparison.
4. **Changes came only from dev failures.** Agent changes were driven by dev-set failures; none were made in response to held-out results. The known held-out issues stay unfixed and are reported: a unit mismatch in one table calculation, and an over-strict verifier rule.
5. **Budget.** Most of the Tavily credits went to the starter runs. By conservative per-call accounting the total reached about the 1,500 limit, which is why the as-shipped starter has two runs on held-out sets 1 and 2 and none on the table set. Tavily's dashboard lagged and read 711.

Details: [`README.md`](README.md), [`results/final/results.md`](results/final/results.md), [`PLAN.md`](PLAN.md).
