# Plan

Each milestone ships something that can be tested on its own. Don't start the next one until the current one passes its acceptance criteria (AC).

The baseline comes first so every later change can be measured against the starter agent.

## Milestone overview

| # | Milestone | Proves | Depends on |
|---|---|---|---|
| M0 | Project setup | Repo runs and keys load safely | none |
| M1 | Baseline benchmark | How good the starter agent is today | M0 |
| M2 | Tracing | Every run is inspectable step by step | M1 |
| M3 | Company lookup and planner | Right company and fiscal calendar; correct periods, researchers and queries planned before any search runs | M1 |
| M4 | Researchers and evidence store | Better retrieval than the baseline | M3 |
| M5 | Writer and verifier | Better answers and citations end to end | M4 |
| M6 | Fresh eval set and tuning | Holds up on new questions; settings justified by data | M5 |
| M7 | Submission package | Deliverables complete | M5 (M6 optional) |

## M0: Project setup

**What we build**
- A `uv` project (`pyproject.toml`).
- `.gitignore` covering `.env` and `starter_agent.py`, plus `CLAUDE.md`.
- `scripts/check_env.py`, which prints only `present` or `missing` for each required key.

**Acceptance criteria**
- `uv run scripts/check_env.py` reports every required key as `present`, and never prints a value.
- After `git init`, `git status` doesn't list `.env` or `starter_agent.py`.

## M1: Baseline benchmark (done)

**What we build**
- `evals/golden.jsonl`: 30 questions, drafted by an analyst-persona subagent and built on the published benchmark designs from FinanceBench and the Vals Finance Agent benchmark.
  - **Coverage:**
    - all 9 Vals task categories
    - difficulty: 10 easy, 12 medium, 8 hard
    - 25 questions with fixed answers and 5 time-sensitive ones
    - 3 that must be refused, plus 1 partial refusal
    - 18 questions targeting fiscal vs. calendar period confusion
    - a foreign (20-F) filer, a private company and a spin-off
  - **Fields:**
    - each question's category and the failure mode it targets
    - where the answer should come from
    - a grading rule (tolerance or rubric)
    - `answer`, `evidence` and `expected_periods` fields, plus `verified_by_human`
  - **Source review (2026-10-01):** all 30 answers and evidence fields are populated, with period metadata. All 25 fixed-answer rows have primary-source evidence; the 5 dynamic rows contain dated snapshots and remain reference-free. `evals/golden_review.md` records corrections and source limitations. Amazon's G28 capex guide still needs primary-source support. The user signed off on 2026-10-01: all 25 fixed-answer rows have `verified_by_human: true`. The 5 time-sensitive rows are dated snapshots, graded without a fixed answer.
  - **`expected_periods`:** a list of `{label, start, end}`, filled in at the same time. The dates come from the filing itself (period dates in the XBRL data or on the cover page), not from the question text. M3 tests the planner against these.
  - **How the 5 time-sensitive questions are graded:** without a fixed answer, on recency and whether each claim is supported by its source.

- `agents/baseline.py`: a function that reproduces the starter agent's setup exactly (same model, prompt and `TavilySearch` defaults), with no streaming output. Because `starter_agent.py` can't be in the repo, the configuration is copied here.
- `evals/run.py` takes one argument, the agent to test. For each question it records:
  - the answer
  - the tool calls and results
  - tokens
  - Tavily credits
  - latency
- `evals/scorers.py`, with these scores:
  - **Correctness:** numbers within ±1% with the right period and unit; a rubric for written analysis; whether it correctly said "not available"
  - **Citations:** share of numbers that cite a source, and whether the cited text supports the claim
  - **Sources:** share of primary sources (sec.gov, the company's investor-relations site)
- The judge is a different model family on Nebius from the one being tested.
- Output goes to `results/scorecard_baseline.md`, with the raw per-question data in `results/raw/`.

**Acceptance criteria**
- All 25 fixed-answer questions have an `answer`, `evidence` and `expected_periods`, with `verified_by_human` set to true.
- Reference answers come only from primary sources: sec.gov filings or the company's own releases. The Tavily CLI can help find a document, but a Tavily snippet is never the evidence, which keeps the benchmark from depending on the tool it tests.
- Each Tavily client is created with a `project_id` (`dev`, `eval-baseline`, `eval-v1`) so credits can be separated by purpose.
  - **Exception:** the baseline uses the starter agent's `langchain-tavily` tool, which can't send `X-Project-ID` (checked in the package source). Its credits are counted from its calls: 1 per `basic`/`fast` search, 2 per `advanced`. From M4 on, `tavily-python` clients set `project_id`.
- `uv run evals/run.py --agent baseline` runs all questions in one command and writes the scorecard.
- The scorecard reports, per category and overall:
  - correctness
  - citation coverage and support
  - share of primary sources
  - median and 95th-percentile latency
  - tokens and Tavily credits per question
- The baseline has been run twice, and the variation between runs is reported.
- The judge agrees with the user's own grades on at least 9 of 10 sampled answers.
- `grep -r "tvly-" results/` finds nothing.

**Result (2026-10-01):**
- **Fixed-answer questions fully correct:** 11/25 in run 1 and 13/25 in run 2. Mean scores 0.71 and 0.80.
- **Time-sensitive questions:** rubric scores 0.69 and 0.30.
- **Sources:** about 86% of numbers cite a source, but only 51–75% of cited claims are supported by the retrieved text, and only 20–24% of cited URLs are primary sources.
- **Cost:** 7–9 Tavily credits and about 81k tokens per question.
- **Run-to-run variation:** 12 of 30 verdicts changed between the two runs. Re-judging run 1's saved answers changed only 1 of 30, so the variation comes from the agent, not the judge.
- **Judge agreement:** 8 of 9 with the user's grades, 9 of 10 including one delegated grade. See `results/judge_agreement_baseline_r1.md`.

## M2: Tracing

**What we build**
- OpenTelemetry traces sent to Langfuse or LangSmith, using the standard span names for agents and tools.
- Token and credit counts recorded on each span.
- Each eval trace tagged with its golden-question ID.

**Acceptance criteria**
- One baseline eval run appears as one trace per question, with every model call and Tavily call visible, including latency and tokens.
- Starting from a failing question in the scorecard, you can open its trace in two clicks.
- No key values appear in any span.

## M3: Company lookup and planner

**What we build**
- **Company lookup:** `resolve(question)` returns `{ticker, cik, company_name, fiscal_year_end}`. It uses the SEC's `company_tickers.json` and the submissions API, with a small model to pull the company name out of the question.
- **Planner:** `plan(question, entity, today, budget)` makes one call to a small model and returns a structured plan. It runs once, with no re-planning loop, the same as OpenAI's `financial_research_agent`.
  - **Research brief:** the metrics, the answer type, and `may_be_unreported` (true when the period may not be reported yet).
  - **Periods:** each one has a fiscal label and an explicit start and end date, worked out from the fiscal year end. For example, Walmart's "Q2 2026" becomes "Q2 FY2027" with that quarter's exact start and end dates.
  - **EDGAR fetches:** the form, period end and item to retrieve. Code runs these, not web search.
  - **Searches:** up to about 8, each with:
    - its researcher (`financials`, `news`, `company` or `industry`)
    - a reason
    - the query, under 400 characters, using the fiscal labels and dates
    - its Tavily settings (`topic`, `search_depth`, date filter, preferred domains)
  - **Researchers are chosen per question.** The planner only includes the researchers a question needs, which follows Anthropic's rule of scaling effort to the question. For example, a revenue lookup needs only financials.

**Acceptance criteria**
- **Company lookup:**
  - 100% exact match on the golden set's company fields, including the ambiguous-company questions.
  - Questions about non-US companies or companies EDGAR doesn't cover return a clear "unresolved" result rather than a guess.
- **Planner periods:** match `expected_periods` exactly, both fiscal label and dates, on every fixed-answer golden question.
- **Unreported periods:** `may_be_unreported` is true on the "should say not available" questions about periods that haven't been reported (G11).
- **Researcher choice:**
  - Every researcher listed in a question's `lens` field is included.
  - Extra researchers are allowed but reported, and the average number of researchers per question is shown.
- **Budget:** no plan goes over it, and every query is under 400 characters.
- **Tests:** unit tests pass using saved EDGAR responses, with no network access. Planner tests run on all 30 golden questions without calling Tavily.

## M4: Researchers and evidence store

**What we build**
- **Up to four researchers running in parallel,** only the ones the planner chose: financials (EDGAR XBRL `companyfacts` plus Tavily `topic=finance`), news, company (investor-relations site `map` + `extract`) and industry. They run the planner's queries rather than writing their own.
- **Optional, only if the scorecard shows retrieval misses:** one extra search round for a researcher that found nothing above the score threshold. The Vals benchmark found that agents which adjust their search do better.
- **The same Tavily process in each:** search, drop results scoring below the threshold, then `extract` the top URLs.
  - Queries stay under 400 characters, as `tavily-best-practices` recommends.
  - `extract` passes a `query` with `chunks_per_source`. It tries `basic` depth first and retries with `advanced` only when that fails.
- **Checks after filtering:** Tavily's relevance score doesn't confirm a result is about the right company.
  - Each result must mention the resolved company's name or ticker.
  - The source tier is decided from the hostname, because `include_domains` alone doesn't guarantee every result comes from an allowed host.
- **Notes from a small model:** about 300 words, citing sources.
- **The evidence store:** `{id, url, tier, value, period, unit, as_of, tavily_request_id, basis}` with duplicate URLs removed, saved as JSON for each run. `basis` is either `page` (full extract) or `snippet` (search result only).
- **Replay mode** for saved Tavily results.

**Acceptance criteria**
- Retrieval scores on the golden set beat the baseline on two measures: relevance and share of primary sources.
- Every number in the evidence store has a period, a unit and an as-of date.
- Tavily credits stay at or below the agreed budget, about 25 per question.
- A replay run makes no Tavily calls and reproduces the saved evidence exactly.
- Before relying on `topic="finance"`, test whether it changes results compared with `general`, and write down what you find.

## M5: Writer and verifier (end to end)

**What we build**
- A writer that produces structured claims, each citing an evidence ID, and can answer "not found".
- A verifier that labels each claim supported, unsupported, contradicted or stale, allows one revision, and then flags anything still failing.
- A cited brief rendered from the claims, marked as a draft for analyst review.

**Acceptance criteria**
- `uv run evals/run.py --agent v1` produces a scorecard next to the baseline.
- No numbers without a citation.
- At least 90% of cited claims are supported by their sources.
- Every company field correct.
- Correctness beats the baseline overall and on the fiscal-year questions. The improvement must be larger than the run-to-run variation measured in M1.
- All "should say not available" questions are refused correctly.
- If a numeric error is planted in a draft, the verifier flags it at least 9 times out of 10.
- Cost and latency are reported. Any increase over the baseline is explained by the quality it buys.

## M6: Fresh eval set and tuning (optional)

**What we build**
- One batch of fresh questions generated from recent news, using Tavily's Dynamic Eval Dataset Generator pattern.
- These are scored without fixed answers: relevance, citation support and recency.
- Then test one setting at a time: search depth, `max_results`, the score threshold and the model used for each step.

**Acceptance criteria**
- Scores on the fresh batch are reported next to the fixed set.
- Each default setting has a recorded reason in the form "setting X: +a% quality for b× cost".

## M7: Submission package

**What we build**
- **A README** with:
  - the architecture diagram
  - a one-command setup
  - the baseline vs. v1 scorecard
  - "what I didn't do and why"
- **A technical statement** on the approach, the reasoning and the business value.
- **The exported build transcript.**

**Acceptance criteria**
- A fresh clone plus `.env` runs both the agent and the eval by following the README alone.
- The repo doesn't include `starter_agent.py` or `.env`.
- Every claim in the statement has a measured result or a source behind it.
