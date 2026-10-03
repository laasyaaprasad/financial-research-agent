# Cited financial research agent (Tavily + SEC EDGAR)

An agent for financial analysts researching SEC-reporting companies. It answers questions, and builds comps and trend tables, about:
- reported results
- calculations over them
- guidance and management commentary
- recent developments

**How it works:**
- **Sources:** every number is quoted from a filing or release, or computed in code from quoted inputs.
- **Checks:** every claim is checked against its source before the answer is shown.
- **Refusals:** anything it can't support is refused explicitly instead of estimated.

It replaces the starter (a LangChain agent with one Tavily search tool) with a fixed pipeline modeled on production finance agents. It uses SEC filings first and Tavily for what filings can't give.

## Results

Three held-out sets, 96 graded items, each set frozen before either agent first ran on it. Two runs per agent, **same model for both** (`deepseek-ai/DeepSeek-V4.1-Flash`), graded by a different-family judge:

| Measure | Baseline (starter design) | New agent |
|---|---|---|
| Fixed answers fully correct | 79/84 (94%) | 81/84 (96%) |
| Table cells correct (8 comps/trend tasks, 86 cells × 2 runs) | 171/172 (99%) | 167/172 (97%) |
| **Verified-correct**: correct, every cited claim supported by retrieved text, every number cited | **40/84 (48%)** | **68/84 (81%)** |
| Cited claims not supported by the text the agent retrieved | 242/907 (27%) | 62/726 (9%) |
| Cited sources that are primary (SEC or company) | 45% | 87% |
| Refusals (unreported period, undisclosed metric, non-SEC company) | 10/12 | 12/12 |
| Tavily credits per question | 7.4 | **0.8** |
| Tavily credits per table task | 20.8 | **0.2** |
| Tokens per question | 58.7k | 61.6k |
| Median / p95 latency | 23 s / 138 s | 48 s / 245 s |

Baseline credits are counted from its calls (1 per basic, 2 per advanced search), because the starter's LangChain tool doesn't report usage; the new agent's are Tavily's per-call usage. Per-set tables, the dev set and per-question records are in [`results/final/results.md`](results/final/results.md). Regenerate it with `uv run python -m evals.report --final`.

**What this shows**
- **Correctness is a tie.** With a capable 2026 model, the starter's search-and-answer loop finds the right number about as often as this pipeline. Tavily reliably surfaces the press release or the sec.gov filing. On the starter's original model (Kimi K2.6), the same design scored only 11–13/25 on the dev set, so most of its original weakness was the model.
- **Trustworthiness is not.** About half of the baseline's correct answers rest on at least one claim its own sources don't support. On table tasks, 69% of its cited figures aren't in what it retrieved. The new agent's figures trace to a filing, and it refuses every request it can't support. For an analyst who must defend every number, that's the difference between a draft and a lead.
- **Cost scales differently.** The baseline's Tavily spend grows with the size of the task: one table task took 53 advanced searches (106 credits). The new agent answers most questions from free SEC data and uses Tavily only for news, call commentary and non-filers, at about 9× fewer credits overall and about 100× fewer on tables.
- **The price is latency:** about 2× slower, because of checking, verification and the larger evidence context.

## Architecture

```mermaid
flowchart TD
    Q[Question + as-of date] --> R[Resolve companies<br/>model names them; SEC ticker list confirms]
    R --> C[Reporting calendar per company<br/>fiscal labels, exact dates,<br/>filed / earnings release only / not yet reported]
    C --> P[Plan: one model call<br/>answer periods, filings to read, ≤3 web searches]
    P --> S[SEC evidence, free<br/>release and 10-Q/10-K passages,<br/>XBRL facts for every answer period]
    P --> W[Tavily<br/>basic search + one extract,<br/>news, call commentary, non-filers]
    S --> E[Numbered evidence]
    W --> E
    E --> D[Writer: claims and table cells<br/>with verbatim quotes; calculations as expressions]
    D --> K{Code checks: quote in source?<br/>number in quote? arithmetic in code}
    K --> V{Verifier: company, metric, period,<br/>basis, actual vs guidance}
    V -- problems, once --> D
    V -- 'not in evidence' gaps, once --> W
    V --> B[Cited brief or table<br/>not-available items · sources · draft for review]
```

| Step | Module | What it does |
|---|---|---|
| Resolve | `agents/company.py` | The model names the companies; code resolves them against SEC's ticker list. Private or ambiguous names stay unresolved. |
| Calendar | `agents/fiscal.py` | Builds each company's reporting periods from its own filings: fiscal labels (naming convention read from its annual-report XBRL), exact dates (including irregular quarters such as 12/12/12/16 weeks) and reporting status as of the question date. |
| Plan | `agents/planner.py` | One call picks the answer periods, the filings to read and any web searches; code drops anything not in the calendar. |
| Evidence | `agents/research.py` | **SEC:** BM25-ranked passages from earnings releases and 10-Q/10-K filings, plus XBRL facts for every answer period (core income-statement lines always included). **Tavily:** basic search, one query-focused extract, social media excluded, plus one gap-filling round if the writer reports something missing. |
| Write and verify | `agents/writer.py` | Claims and table cells must quote their sources verbatim. Code rejects any quote that isn't in its source, rejects any number that isn't in a quote, and evaluates calculations itself (for example, fiscal Q4 = full year minus nine months). A verifier checks meaning. One revision is allowed; anything that still fails is withheld. |
| Orchestrate | `agents/pipeline.py` | Runs the steps, renders the brief or table and provides the CLI. |
| Trace | `agents/tracing.py` | Langfuse via OpenTelemetry: one trace per question, with model and Tavily calls and the eval scores attached. |

## Scope

- **In scope:** SEC-reporting companies, covering:
  - figures in filings and earnings releases
  - calculations (growth, margins, TTM, implied quarters)
  - guidance and beat/miss
  - management-stated drivers
  - recent developments
  - multi-company and multi-period tables
- **Refused explicitly:**
  - periods not yet reported as of the question date
  - undisclosed metrics
  - non-SEC companies (their own published figures may be cited, labeled as such)
- **Out of scope:** licensed data (estimates, consensus, paywalled transcripts), real-time prices and advice.

## Evaluation

| Set | Contents | Role |
|---|---|---|
| `evals/golden.jsonl` | 30 questions across the Vals AI Finance Agent task categories and the known failure modes (fiscal periods, units, wrong entity, GAAP vs. non-GAAP, stale data, refusals); user-verified references | **Dev**: inspected during development |
| `evals/test_heldout.jsonl` | 20 questions, 21 other companies | Held-out |
| `evals/test_hard.jsonl` | 20 questions: point-in-time, filing-only figures for mid/small caps, multi-step fiscal calculations, traps, guidance vs. actual | Held-out |
| `evals/test_tables.jsonl` | 8 analyst table tasks (peer comps across fiscal calendars, 8-quarter trend with derived Q4, TTM and balance-sheet comps, segments), 86 cells | Held-out |
| `evals/dev_tables.jsonl` | 3 table tasks on dev-set companies | Dev for table support |

How the held-out sets were kept honest:
- **Built blind.** Each held-out set was built by a research subagent from SEC filings, without seeing either agent's outputs.
- **Checked.** References were cross-checked against SEC XBRL data.
- **Frozen first.** Each set's hash was committed before the first run on it (`*_manifest.json`).
- **No tuning on held-out results.** Agent code changes were driven only by dev-set failures.
- **Disclosed reuse.** The final agent is the third run on set 1 and the second on the hard set; only the table set was a true first run. The two harder sets were added because the first held-out set turned out too easy to separate the two agents.

How the answers were graded:
- **Rubric judge.** `nvidia/Nemotron-3-Ultra-550b-a55b` grades correctness against each question's rubric. It agreed with the user on 8 of 9 hand-graded answers.
- **Cell-by-cell tables.** For table tasks the judge only extracts each cell's value; code compares it to the reference within tolerance.
- **Citation checks.** Every cited claim is checked against the text the agent actually retrieved.
- **No self-grading.** The judge is a different model family from both agents.
- **Guard test.** `tests/test_agent.py` fails if any evaluation-set company name appears in `agents/`.

## Usage

```bash
cp .env.example .env    # add TAVILY_API_KEY, NEBIUS_API_KEY, SEC_USER_AGENT ("Name email"); optional LANGFUSE_*
uv sync
uv run python scripts/check_env.py
uv run python -m agents.pipeline "Compare revenue and operating margin for <company A> and <company B> in their latest reported quarters"
uv run python -m agents.pipeline --today 2026-03-31 "What was <company>'s most recently reported quarterly revenue?"
```

Evaluate and test:

```bash
uv run python -m evals.run run --agent agent --set test --name my_run      # sets: dev, test, hard, tables, dev_tables
uv run python -m evals.run run --agent baseline --set test --name my_baseline
uv run python -m evals.run compare my_baseline my_run
uv run python -m evals.report --final        # rebuild results/final/results.md
uv run pytest -q
uv run python scripts/check_secrets.py       # scan files for key material
```

## Limitations and what I didn't do

- **Not more accurate than the baseline.** On these sets, correctness is a tie, and the baseline is slightly ahead on table cells (99% vs. 97%). The gains are verifiability, primary sourcing, refusals and cost.
- **A known bug found in held-out runs.** A table calculation can come out in a different unit than its column: inputs in thousands under a "USD millions" column, so 1,000× too large. A unit check per column would catch it. It was not fixed after the held-out runs, so the results still include it.
- **Slower:** 2× median latency.
- **Not delivered by the verifier:** its "net sales is not revenue" strictness once withheld a correct cell.
- **SEC filers only:** foreign issuers' local filings and private companies get only what the web provides.
- **No licensed data:** no consensus, estimates or paywalled transcripts. The beat/miss checks use company guidance, not consensus.
- **Small samples:** 20-question sets and 8 table tasks detect large differences only, and the dev and table "dev" sets are small.
- **Skipped on purpose:**
  - a multi-agent supervisor: research found it costs about 15× the tokens, and these tasks have known shapes
  - Tavily `/research`: it hides source tiers and claim-level checking
  - a vector database: evidence is fetched fresh for each question
  - a web UI

## Repository

```
agents/      pipeline (company, fiscal, planner, research, writer, pipeline), baseline, tracing, llm, edgar
evals/       question sets + manifests + source notes, run.py (harness), scorers.py, report.py
results/     final/ (results.md, scorecards, per-question records), history_kimi_baseline/ (starter on its original model)
scripts/     check_env.py, check_secrets.py, verify_traces.py
tests/       offline unit tests (no network)
PLAN.md      milestones, the course correction and how the evaluation evolved
REPORT.md    final report and technical statement
```
