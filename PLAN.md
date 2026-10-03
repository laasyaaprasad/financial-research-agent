# Plan

Each milestone ships something that can be tested on its own. Don't start the next one until the current one passes its acceptance criteria (AC).

The baseline comes first so every later change can be measured against the starter agent.

## Milestone overview

| # | Milestone | Proves | Status |
|---|---|---|---|
| M0 | Project setup | Repo runs and keys load safely | done |
| M1 | Baseline benchmark | How good the starter agent is today | done |
| M2 | Tracing | Every run is inspectable step by step | done |
| — | Course correction (2026-10-03) | First M3–M5 attempt was overfit; re-scoped and rebuilt | see below |
| M3 | Rebuilt agent | Generic pipeline: resolve → plan → evidence → write → verify | done |
| M4 | Held-out test sets | 20 questions (`7ae904f`), 20 hard questions (`80b9802`), 8 table tasks (`38a7190`), each frozen before the agent ran on it | done |
| M5 | Final evaluation | Baseline vs. agent on dev, held-out, hard and table sets, same model, within the credit budget | done |
| M6 | Submission package | README, final report, build record | done |

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

## M2: Tracing (done)

**What we build**
- OpenTelemetry traces sent to Langfuse or LangSmith, using the standard span names for agents and tools.
- Token and credit counts recorded on each span.
- Each eval trace tagged with its golden-question ID.

**Acceptance criteria**
- One baseline eval run appears as one trace per question, with every model call and Tavily call visible, including latency and tokens.
- Starting from a failing question in the scorecard, you can open its trace in two clicks.
- No key values appear in any span.

**Result (2026-10-02):**
- **Traces:** a traced baseline run over all 30 questions produced 30 complete Langfuse traces. `scripts/verify_traces.py` confirms each one has:
  - a single `invoke_agent` root span tagged with its `golden_id`
  - every model call, with token usage
  - one tool span per Tavily call
- **Secrets:** no Tavily, Nebius or Langfuse secret key appears in any trace. The Langfuse public key does appear in every span, because the SDK adds it to identify the project. It isn't a secret.
- **Scores and links:** eval scores are attached to each trace, and the scorecard links each question to its trace.
- **Span names:** the root span follows OpenTelemetry's naming for AI agents. Child spans keep LangChain's names (`ChatNebius`, `tavily_search`), with Langfuse types `GENERATION` and `TOOL`.
- **Langfuse API note:** new Langfuse organizations can only read data through the v2 observations API and the v3 scores API. The older trace endpoints are unavailable.

## Course correction (2026-10-03)

A first M3–M5 implementation (commits `b01e1ed`, `1898e41`, `9c42987` and uncommitted M5 work) reached 21/25 on the dev set in its best fresh run, but a review found it would not hold up:

- **Overfit to the dev set.** The planner prompt had one rule per golden question (implied Q4 from guidance, TTM plus RPO windows, constant-currency growth, cross-company capex, ex-division results, export controls, leadership changes). The code had named-company special cases (`if company_name == "Cargill, Incorporated"`, an alias table of exactly the golden companies, `'novo'` token handling) and keyword lists tuned to golden questions (`rpo`, `membership`, `DKK`).
- **Unstable.** Fresh full runs ranged from 11/25 to 21/25, and the held-out checks it ran scored 2/6 and 3/6.
- **Too large to review.** About 5,700 lines in a dense style, with dozens of result files.

**What changed**
- **Narrower scope:** cited, period-correct answers about SEC-reporting companies: reported results, calculations over them, management guidance and commentary, and recent developments. Private companies, unreported periods and undisclosed metrics get an explicit refusal.
- **No special period transforms.** The planner chooses reported fiscal periods from each company's real calendar. Derived figures (TTM, growth, implied quarters) are calculations over cited numbers, evaluated in code.
- **No company-specific code or question-specific prompt rules.** Fiscal-year naming comes from the company's own annual-report XBRL; quarters come from the order of its 10-Q filings.
- **Honest evaluation.** The original 30 questions are now the **dev set**, inspected during development. Final claims rest on a new **held-out test set** that is frozen before the agent runs on it.
- **Same model for both agents.** The baseline and the new agent both run on `deepseek-ai/DeepSeek-V4.1-Flash`, the cheapest Nebius model, so the comparison measures architecture rather than model choice.
- **Different-family judge.** The judge is `nvidia/Nemotron-3-Ultra-550b-a55b`, which agreed with the user's grades on 8 of 9 sample answers. That matches the earlier judge, and its one disagreement is the same G04 citation-quality case. The first choice, Qwen3.5-397B, also scored 8/9 but was withdrawn from Nebius mid-project.
- **Credit budget.** Tavily credits are capped at 1,500 for the rest of the project and used only for final end-to-end runs. Development runs use SEC data, which is free.

The superseded code was removed from the working tree; it remains in git history.

## M3: Rebuilt agent

**What we build** (package `agents/`)
- `company.py`: the model names the companies; code resolves them against SEC's ticker list. Unmatched names (e.g. private companies) are unresolved, never guessed.
- `fiscal.py`: each company's reporting calendar as of the question date. Every period has its fiscal label, exact dates and status: filed, earnings release only, or not yet reported.
- `planner.py`: one model call chooses answer periods, filings to read (earnings release and/or 10-Q/10-K), recent 8-Ks, and at most 3 web searches. Code validates every choice against the calendar.
- `research.py`: builds an evidence list:
  - passages from the chosen filings, ranked by relevance (BM25)
  - exact XBRL facts for the chosen periods
  - Tavily search plus extract for what filings can't give
- `writer.py`: the model writes claims, each with evidence IDs and verbatim quotes. Calculations are expressions over quoted inputs, evaluated in code.
- **Checks in code:** every quote must appear in its cited source, and every number must appear in a quote or come from a calculation. A separate verifier call then checks each claim's meaning: entity, metric, period, basis, and actual vs. guidance. The writer gets one revision; claims that still fail are removed and listed as unverified.
- `pipeline.py`: runs the steps above, renders a cited brief marked as a draft for analyst review, and provides a CLI.

**Acceptance criteria**
- Offline unit tests cover the calendar, quote and number checks, the calculator and planner validation.
- The production code contains no company names, tickers or question-specific rules (checked by grep).
- A dev-set run using SEC data only completes for all 30 questions with no crashes.

**Result (2026-10-03, dev set only; graded by the first judge, Qwen3.5-397B):**
- **SEC data only, no Tavily:** 17–18/25 fixed answers fully correct (mean 0.85–0.89); 98% of cited claims supported; 100% of cited URLs primary.
- **With Tavily:** 19/25 (mean 0.89); 98% of cited claims supported; 86% of cited URLs primary; 12 credits for all 30 questions; median latency 50 s.
- **The Kimi-based starter, for context:** 11–13/25 across three runs, with 20–24% of cited URLs primary.
- **Changes made after inspecting dev failures (all generic):**
  - Number grounding now ignores years, form names and period lengths.
  - Calculated values can be reused across claims.
  - Source precision is kept, and rates are computed from reported figures.
  - Common financial synonyms (sales/revenue, profit/income) are used for ranking.
  - Reasoning effort is set per step, which halved median latency.
  - The verifier checks that a claim uses exactly the metric the question asks about.
  - The planner searches earnings-call coverage when a question asks for guidance or management's explanation.
  - A failed revision or verifier call falls back to the checked draft instead of crashing.
- **Offline tests:** 19 pass, including a guard that no evaluation-set company appears in `agents/`.
- **Size:** agent code is about 1,400 lines, down from about 5,700.
- **Iteration scorecards:** in `results/dev_iterations/`. Final numbers come from the M5 runs with the final judge.

## M4: Held-out test set

**What we build**
- `evals/test_heldout.jsonl`: 20 questions about 15+ companies not used in development, covering:
  - reported figures
  - calculations
  - guidance and beat/miss
  - management drivers
  - recent developments
  - three refusals
  - one cross-calendar comparison
- References come from primary sources (SEC filings, company releases), drafted by a research subagent and checked against SEC XBRL data where possible.

**Acceptance criteria**
- Every fixed numeric reference is checked against SEC data or the cited document.
- The file's hash is recorded before the agent's first run on it.
- No code changes after that first run, other than crash fixes, which are reported.

## M5: Final evaluation

**What we build**
- Baseline (starter configuration on DeepSeek V4.1 Flash) and the new agent, scored by the same judge and scorers.

**What happened, in order (2026-10-03)**
1. **v1 (`c3c29cf`) on the held-out set (×2) and the dev set (×1).**
   - **Correctness was saturated.** The baseline on DeepSeek Flash is far stronger than the Kimi-based starter: 28/32 held-out answers fully correct vs. 29/32 for the agent, and 21/25 vs. 18/25 on dev.
   - **The agent won on trust and cost:**
     - unsupported cited claims: 3% vs. 14%
     - primary-source citations: 84% vs. 34%
     - Tavily credits: about 6× fewer
2. **v2 (`be27f6b`, `bb252b0`).** Changes driven only by dev-set failures:
   - gap-filling search
   - report disclosed rates as disclosed
   - tolerant quote matching
   - retries on provider errors

   Held-out 30/32; dev 19/25. These are reported as a second use of the held-out set.
3. **Judge replaced mid-run.** Qwen3.5-397B was withdrawn from Nebius; Nemotron-3-Ultra agreed with the user's grades on 8 of 9 and graded all final runs.
4. **Hard held-out set (`80b9802`).** 20 questions covering point-in-time, filing-only figures for mid- and small-caps, multi-step fiscal calculations, traps, and guidance vs. actual. Still near the ceiling for both agents: run 1 was 18/18 for the baseline and 17/18 for the agent. Finding: with a capable 2026 model, Tavily search reliably surfaces press releases and sec.gov filings, so single-answer questions don't separate the agents.
5. **Held-out table set (`38a7190`).** The task was widened rather than the company scope: 8 analyst table tasks, 86 cells, graded cell by cell. Table support in the agent (v3, `41e36b7`) was developed only on dev table tasks D01–D03.
6. **Final runs on v3:**
   - table set: both agents ×2
   - agent v3 on the held-out (×2), hard (×2) and dev (×1) sets
   - baseline runs on those sets reused, since the baseline code is unchanged

**Result (final runs, pooled over three held-out sets × two runs, same model):**

| Measure | Baseline | New agent |
|---|---|---|
| Fully correct | 79/84 | 81/84 |
| Table cells correct | 99% | 97% |
| Verified-correct | 40/84 | 68/84 |
| Cited claims not supported | 27% | 9% |
| Primary-source citations | 45% | 87% |
| Correct refusals | 10/12 | 12/12 |
| Tavily credits per question | 7.4 | 0.8 |
| Median latency | 23 s | 48 s |

- **Correctness:** a tie. **Trustworthiness and cost:** clear gains for the new agent. **Latency:** about 2× slower. Details are in `results/final/results.md`.
- **Acceptance criteria:**
  - **Met:**
    - every refusal correct
    - at least 90% of cited claims supported (91%)
    - within the Tavily budget
    - verified-correct well beyond run-to-run variation
  - **Not met as originally framed:** a correctness gain over the baseline. The README and REPORT say so plainly.

**Acceptance criteria**
- **Headline:** the README reports quality next to credits, tokens and latency, without picking runs.
- **Bar on the held-out sets:** the agent beats the baseline on at least one held-out measure an analyst cares about, by more than run-to-run variation. Otherwise the README says so plainly.
- **Refusals and support:** all refusals correct, and at least 90% of cited claims supported.
- **Budget:** total Tavily credits stay within 1,500 (about 735 used before the v3 final runs).

## M6: Submission package (done)

- **`README.md`:** results table, architecture diagram, scope, evaluation design, usage, limitations.
- **`REPORT.md`:** final report and technical statement, covering the problem, the baseline, why each component exists, results and how they were reached.
- **`results/final/`:** `results.md` (regenerate with `uv run python -m evals.report --final`), scorecards, and compact per-question records.
- **Build record:** the exported session transcript.
- **Repo contents:** no `starter_agent.py`, `.env` or assignment brief in the repo; `scripts/check_secrets.py` reports no key material.
