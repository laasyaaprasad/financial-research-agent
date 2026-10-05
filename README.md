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

It replaces the starter (a LangChain agent with one Tavily search tool on Kimi K2.6) with a fixed pipeline modeled on production finance agents, running on DeepSeek V4.1 Flash. It uses SEC filings first and Tavily for what filings can't give.

## Results

Measured on **Exact50**: 50 held-out questions weighted toward what an analyst tool has to get right. That means ambiguous and edge-case requests, web-dependent questions (earnings-call commentary, recent events, foreign and private companies), date traps, actual versus guidance, and comparisons across fiscal calendars. Each column is one fresh run of all 50, graded by the same judge: GPT-6 Luna (OpenAI, high reasoning, a different model family from the agents), three votes per answer.

| Measure | Starter as shipped (Kimi K2.6) | Starter design on our model | **Our agent** |
|---|---|---|---|
| Fully correct | 14/50 | 25/50 | **32/50** |
| Mean rubric score | 0.66 | 0.80 | **0.89** |
| **Verified-correct**: correct, every cited claim supported, every number cited | 2/50 | 0/50 | **18/50** |
| Cited claims supported by the cited source | 66% | 69% | **94%** |
| Cited sources that are primary (SEC or company) | 15% | 26% | **73%** |
| Tavily credits (all 50 questions) | 373 | 338 | **115** |
| Tokens per question | 58k | 60k | 63k |
| Median latency | 26 s | **12 s** | 45 s |

| Fully correct, by question class | Starter as shipped | Starter design on our model | **Our agent** |
|---|---|---|---|
| Edge and ambiguous (16) | 1 | 1 | **11** |
| Traps: point-in-time, superseded, unreported, deregistered (16) | 6 | **10** | **10** |
| Web-dependent (10) | 3 | **7** | 3 |
| Actual versus guidance (4) | 3 | 3 | **4** |
| Comparisons across fiscal calendars (4) | 1 | **4** | **4** |

The middle column runs the starter's prompt, Tavily tool and agent loop on our model, DeepSeek V4.1 Flash, to separate what the architecture contributes from what the model contributes. Our agent's first version, before the evaluation review below, scored 24/50 fully correct and 11/50 verified-correct on the same questions.

**What this shows**
- **Against the starter as shipped:**
  - fully correct rises from 14 to 32 of 50
  - verified-correct rises from 2 to 18
  - cited claims supported rise from 66% to 94%, and primary sources from 15% to 73%
  - it uses about a third of the Tavily credits
  - the cost is latency: 45 s median against 26 s
- **Against the starter's design on the same model:**
  - fully correct rises from 25 to 32, and edge-case questions from 1 to 11 of 16
  - verified-correct rises from 0 to 18
  - Tavily credits fall from 338 to 115
  - our agent is weaker on web-dependent questions (3 against 7 of 10) and about 4× slower
- **Where the final gains came from:** generic fixes found by the evaluation review:
  - bugs in the number check
  - a lag in SEC's tagged financial data, now covered by reading the filing itself
  - chained calculations
  - planner and writer prompts that teach a way of working through a question rather than per-question rules

**How to read these numbers**
- One run per column: with 50 questions, differences of two or three answers are within run-to-run variation.
- Exact50's selection rules (`evals/exact50_selection.md`) were written after earlier results on these questions were known. The questions, references and rubrics are copied unchanged from the held-out sets.
- The final agent's fixes came from diagnosing held-out failures, using the run records and Langfuse traces. So the held-out sets are no longer a clean test of the final agent. The fixes contain no company- or question-specific rules, and the guard test still passes.
- Our agent's credits are Tavily's reported usage. The starters' are counted from their successful searches, because the starter's LangChain tool doesn't report usage.

Full tables and per-question verdicts are in [`results/final/exact50.md`](results/final/exact50.md); regenerate it with `uv run python -m evals.report --exact50`. The earlier results on the full held-out sets (2026-10-03/04: older agent, Nemotron judge, before the grading fixes) are kept in [`results/final/results.md`](results/final/results.md) as history. They are superseded.

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
| Plan | `agents/planner.py` | One call first works out what exactly is asked, where each piece is disclosed and what could make the obvious answer wrong today. It then picks the answer periods, the filings to read and any web searches; code drops anything not in the calendar. |
| Evidence | `agents/research.py` | **SEC:** BM25-ranked passages from earnings releases, 10-Q/10-K filings and up to 8 recent 8-Ks. Also XBRL facts for every answer period (core income-statement lines always included); a filing SEC's tagged data doesn't include yet is read directly. **Tavily:** basic search and one query-focused extract, with social media excluded. A result must be about the company: named in its title or URL, or at least twice in its text. Companies without quarterly SEC reports (foreign annual filers, private companies) have their own sites searched first. One gap-filling round runs if the writer reports something missing. |
| Write and verify | `agents/writer.py` | The writer works through the question first: every item asked, the exact passage for each one (watching for near-misses), what must be derived, and what a reader needs in order to rely on it. Claims and table cells must quote their sources verbatim. Code rejects any quote that isn't in its source and any number that isn't in a quote. It evaluates calculations itself, chained where one result feeds another (for example, fiscal Q4 = full year minus nine months). A verifier checks meaning. One revision is allowed; anything that still fails is withheld. |
| Orchestrate | `agents/pipeline.py` | Runs the steps, renders the brief or table and provides the CLI. |
| Follow-ups | `agents/followup.py` | In the chat, one model call rewrites a follow-up (or a reply to a clarification question) into a standalone question for the pipeline. It never answers. |
| Chat UI | `ui/` | Chainlit front end over the same pipeline (see [Chat UI](#chat-ui)). |
| Trace | `agents/tracing.py` | Plain OpenTelemetry over OTLP (Langfuse by default, any OTLP backend via `OTEL_EXPORTER_OTLP_ENDPOINT`; `TRACING=off` disables it): one trace per question, a span per pipeline step, a `chat <model>` span per model call with tokens and cost, a retriever span per Tavily call (live, cache or offline, credits, result URLs), and eval scores that re-grading updates in place. |

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
| `evals/dev_tables.jsonl`, `evals/edge_dev.jsonl`, `evals/web_dev.jsonl` | 3 table tasks, 24 ambiguous or edge-case requests, 10 web-dependent questions | Dev |
| `evals/test_heldout.jsonl` | 20 questions, 21 other companies | Held-out |
| `evals/test_hard.jsonl` | 20 questions: point-in-time, filing-only figures for mid/small caps, multi-step fiscal calculations, traps, guidance vs. actual | Held-out |
| `evals/test_tables.jsonl` | 8 analyst table tasks (peer comps across fiscal calendars, 8-quarter trend with derived Q4, TTM and balance-sheet comps, segments), 86 cells | Held-out |
| `evals/test_edge.jsonl` | 16 ambiguous or incomplete requests (missing period or company, shorthand, share classes, out-of-scope asks, unreported periods, private companies) | Held-out |
| `evals/test_web.jsonl` | 10 questions whose facts aren't in SEC filings (call commentary, recent events, foreign issuers, private companies, multi-hop) | Held-out |
| `evals/exact50.jsonl` | 50 of the 74 held-out questions, chosen by fixed rules (`evals/exact50_selection.md`): all edge and web questions, traps, actual vs. guidance and cross-calendar comparisons; plain single-figure lookups dropped | **Headline benchmark** |

How the held-out sets were kept honest:
- **Built blind.** Each held-out set was built by a research subagent from primary sources, without seeing either agent's outputs.
- **Checked.** References were cross-checked against SEC XBRL data where possible.
- **Frozen first.** Each set's hash was committed before the first run on it (`*_manifest.json`), Exact50 included.
- **Disclosed reuse.** Until 2026-10-05, agent changes came only from dev-set failures. The evaluation review on that day diagnosed held-out failures and made generic fixes (see Results).

How the answers are graded (`evals/scorers.py`):
- **Rubric judge.** `gpt-6-luna` (OpenAI, high reasoning) grades correctness against each question's rubric, with three votes; the median verdict counts. It agreed with the user on 8 of 10 hand-graded answers, as `nvidia/Nemotron-3-Ultra-550b-a55b` did before it (8 of 9). GLM-5.3-Flash was tried and dropped: it returned no grade for 5 of 24 answers.
- **Verdict computed from the rubric points.** The judge marks each requirement met or not; code derives the verdict. Items the rule calls optional never block "correct", and fail conditions are phrased as what the answer must avoid. A malformed reply is retried with the error; a rate limit is waited out.
- **Cell-by-cell tables.** For table tasks the judge only extracts each cell's value; code compares it to the reference within tolerance.
- **Citation check.** Every claim an answer makes about a company or source is checked against the source it cites. The judge sees each cited source in full (up to 30,000 characters), chosen the same way for every agent.
- **No self-grading.** The judge is a different model family from both agents.
- **Guard test.** `tests/test_agent.py` fails if any evaluation-set company name appears in `agents/`.

**The evaluation review (2026-10-05)** found problems in the harness, not only in the agents. Exact50 and the grading rules above are its result.
- **Judge failures scored as wrong answers.** 8 answers in one run were scored 0 because the judge's overall verdict contradicted its own per-point marks. That usually happened by counting an optional item as required.
- **Same-model judge.** One run was graded by the agents' own model.
- **A truncated citation check.** The check saw only the first 60,000 characters of everything retrieved. That hid the supporting text for long baseline retrievals and left many baseline claims undecided.
- **Questions that don't separate the agents.** Many held-out questions ask for one headline figure, which both agents find.

## Usage

```bash
cp .env.example .env    # add TAVILY_API_KEY, NEBIUS_API_KEY, SEC_USER_AGENT ("Name email"); optional LANGFUSE_*
uv sync
uv run python scripts/check_env.py
uv run python -m agents.pipeline "Compare revenue and operating margin for <company A> and <company B> in their latest reported quarters"
uv run python -m agents.pipeline --today 2026-03-31 "What was <company>'s most recently reported quarterly revenue?"
```

### Chat UI

A conversational front end built on [Chainlit](https://github.com/Chainlit/chainlit), an open-source chat UI for Python LLM apps. It's an optional dependency group, so the agent and eval environments don't change.

```bash
uv run --group ui python -m ui            # http://localhost:8000; Chainlit options pass through, e.g. --port 8001
```

- **Citations on every statement.** Each claim, table cell and "not available" item ends with `[n]` markers. A marker links to its source, opened at the quoted passage where the browser can find it (URL text fragments). Hovering a marker shows the verbatim quote the statement relies on.
- **Linked sources at the end.** A numbered list gives each source's title, domain, date and whether it is primary (SEC or company) or secondary.
- **Evidence panel.** A side panel lists every source of the answer with the quotes behind each statement and any calculation, both the inputs and the expression computed in code. Each answer has its own panel, newest first.
- **Progress steps.** While it runs (median 40 s), the chat shows each pipeline stage: companies identified (name, ticker, CIK), the research plan, filings read, web results, and statements verified or withheld.
- **Conversation.** Follow-ups ("and the prior quarter?", "compare that with its closest peer") and replies to clarification questions are rewritten into a standalone question, shown as **Researched as**, before research. The rewrite runs only when there is earlier conversation. Later in a conversation, a message that isn't a research request (thanks, a greeting) gets a short description of the tool instead of research.
- **Settings:** an as-of date for point-in-time questions, and a switch for live web search. With it off, the chat answers from SEC data and cached Tavily responses only, without spending credits.

**Look and feel.** The theme (`ui/public/theme.json`, `ui/public/brand.css`) follows the color palette in [Tavily's brand guidelines](https://www.tavily.com/brand): Off White and Black as the foundation, light by default, and Lavender as the accent. Lavender text on Off White falls short of WCAG AA contrast, so links are black with a lavender underline. Nothing is used that the project has no rights to: no Tavily logo, wordmark or brand mark (the app has its own name and mark), and no Suisse Int'l, the commercial typeface on tavily.com. Type is Inter and Geist Mono, both under the SIL Open Font License. The app's readme states that it is not affiliated with or endorsed by Tavily.

The UI calls `agents.pipeline.run` like the CLI and the eval harness do, so the answers are the ones that were evaluated. The CLI brief is unchanged byte for byte; the chat renders the same statements with links. Conversations are kept for the session only (no chat history database).

Evaluate and test:

```bash
uv run python -m evals.run run --agent agent --set test --name my_run      # sets: dev, test, hard, tables, dev_tables
uv run python -m evals.run run --agent baseline --set test --name my_baseline
uv run python -m evals.run compare my_baseline my_run
uv run python -m evals.report --final        # rebuild results/final/results.md
uv run pytest -q
uv run python scripts/check_secrets.py       # scan files for key material
```

### Deployment (AWS)

The chat UI runs on one EC2 instance (t3.micro, `us-east-2`) in Docker, behind Caddy for HTTPS, at an `sslip.io`
hostname of its Elastic IP. Sign-in uses one shared password, and the instance answers one question at a time.

- **CI** ([.github/workflows/ci-cd.yml](.github/workflows/ci-cd.yml)): every push runs the tests, checks the
  Terraform, builds the image and checks that it holds no `.env` file or API key.
- **CD (pull-based):** a push to `main` (or a manual run of the workflow) publishes the image to the public package
  `ghcr.io/laasyaaprasad/financial-research-agent` (it holds only this repo's code). A systemd timer on the instance
  checks for a new image every 2 minutes and restarts the app when the image or the secrets change.
  GitHub has no AWS access: the AWS organization's policy doesn't allow GitHub OIDC.
- **Infrastructure:** [infra/main.tf](infra/main.tf) (Terraform, local state). It creates the instance, the Elastic IP,
  a security group (ports 80 and 443 only; no SSH, SSM Session Manager instead) and the instance's IAM role. Every
  resource is named `fin-research-agent`, so it sits beside other deployments in the same account.
- **Secrets:** API keys live only in `.env` and in SSM Parameter Store (SecureString) under `/fin-research-agent/`,
  which only the instance can read. [deploy/put_secrets.py](deploy/put_secrets.py) copies them from `.env` without
  printing them. They never go into the image, the Terraform state or GitHub; the workflow uses only GitHub's
  built-in token.

One-time setup:

```bash
terraform -chdir=infra init
terraform -chdir=infra apply
uv run --with boto3 deploy/put_secrets.py
```

then push to `main` (or run the workflow) and make the package public once (GitHub → Packages → Package settings →
Change visibility), so the instance can pull it without credentials. The URL is `terraform -chdir=infra output -raw url`; sign in with the shared
password set in [ui/app.py](ui/app.py) (the name is optional).

**Cost:** t3.micro and 20 GB of gp3 storage are free-tier eligible (the free tier's 750 hours a month are shared by
every instance in the account); the public IPv4 address is about $3.60 a month. To remove everything, run
`terraform -chdir=infra destroy`, then delete the `/fin-research-agent/*` parameters.

## Limitations and what I didn't do

- **Web-dependent questions are the weakest class:** 3 of 10 on Exact50, against 7 for the starter's design on the same model. The answers often leave out details the rubric requires, or miss figures that are only in a company's own release.
- **Slower:** 45 s median latency against 12 s for the starter's design on the same model.
- **Small, single-run samples:** one run per configuration on Exact50, and only 4 to 16 questions per class. Small differences are within run-to-run variation.
- **Held-out sets used for diagnosis.** The final agent's fixes came from held-out failures (see Results), so its held-out results are not a clean test.
- **Simple lookups don't separate the designs.** On the earlier full held-out sets (mostly single-figure questions), the starter's design on the same model was about as accurate as ours. Exact50 leaves those out, so it shows where the designs differ, not accuracy on simple lookups.
- **A known table bug.** A table calculation can come out in a different unit than its column: inputs in thousands under a "USD millions" column, so 1,000× too large. A unit check per column would catch it.
- **Verifier strictness:** its "net sales is not revenue" rule once withheld a correct cell.
- **SEC filers first:** foreign issuers and private companies get only what the web and their own sites provide.
- **No licensed data:** no consensus, estimates or paywalled transcripts. Beat/miss checks use company guidance, not consensus.
- **Follow-up rewriting isn't evaluated.** The evaluation sets are single-turn, so the chat's rewrite of follow-ups into standalone questions was only checked by hand. A wrong rewrite is visible as **Researched as** above the answer.
- **Skipped on purpose:**
  - a multi-agent supervisor: research found it costs about 15× the tokens, and these tasks have known shapes
  - Tavily `/research`: it hides source tiers and claim-level checking
  - a vector database: evidence is fetched fresh for each question

## Repository

```
agents/      pipeline (company, fiscal, planner, research, writer, pipeline), followup, baseline, tracing, llm, edgar
ui/          chat UI (Chainlit app, chat rendering, config, readme)
evals/       question sets + manifests + source notes, run.py (harness), scorers.py, report.py
results/     final/ (exact50.md, earlier results.md, scorecards, per-question records), history_kimi_baseline/
scripts/     check_env.py, check_secrets.py, verify_traces.py
tests/       offline unit tests (no network)
PLAN.md      milestones, the course correction and how the evaluation evolved
REPORT.md    final report and technical statement
```
