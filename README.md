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

The baseline is the **starter exactly as shipped**: its prompt, Tavily tool and agent loop, on its default model, Kimi K2.6. Our agent includes our model choice, DeepSeek V4.1 Flash, the cheapest Nebius model. A middle column runs the starter's design on our model, to separate what the architecture contributes from what the model contributes. All runs are graded by the same different-family judge. Each held-out set was frozen before its first run.

**Held-out sets 1 and 2:** 40 questions, 38 companies. The second set adds point-in-time questions, figures found only in filings for mid- and small-caps, multi-step fiscal calculations and traps.

| Measure | Starter (as shipped) | Starter design on our model | **Our agent** |
|---|---|---|---|
| Fixed answers fully correct | 40/68 (59%) | 64/68 (94%) | **67/68 (99%)** |
| **Verified-correct**: correct, every cited claim supported by retrieved text, every number cited | 23/68 (34%) | 38/68 (56%) | **56/68 (82%)** |
| Cited claims not supported by the text the agent retrieved | 19% | 16% | **9%** |
| Cited sources that are primary (SEC or company) | 21% | 41% | **82%** |
| Refusals correct (unreported period, undisclosed metric, non-SEC company) | 7/12 | 10/12 | **12/12** |
| Tavily credits per question | 8.7 | 4.7 | **0.9** |
| Tokens per question | 80k | 33k | 51k |
| Median / p95 latency | 18 s / 118 s | 17 s / 116 s | 40 s / 217 s |

Two runs per column (68 graded fixed answers each). The as-shipped starter wasn't run on held-out set 3, the analyst tables (8 tasks, 86 cells): at about 9 credits per question it would have exceeded the 1,500-credit budget. On that set, against the starter's design on our model:

| Measure | Starter design on our model | Our agent |
|---|---|---|
| Table cells correct | 171/172 (99%) | 167/172 (97%) |
| Cited figures not supported by retrieved text | 69% | 6% |
| Tavily credits per table task | 20.8 | 0.2 |

**Dev set:** 30 questions, inspected during development. The starter as shipped got 40/75 fully correct over three runs (53%); our agent got 20/25 (80%).

Baseline credits are counted from its calls (1 per basic search, 2 per advanced), because the starter's LangChain tool doesn't report usage; our agent's are Tavily's per-call usage. All tables, per-question scorecards and records are in [`results/final/results.md`](results/final/results.md). Regenerate it with `uv run python -m evals.report --final`.

**What this shows**
- **Against what was shipped:**
  - fully correct rises from 59% to 99%
  - answers an analyst can use without re-checking rise from 34% to 82%
  - cited claims not supported by the source fall from 19% to 9%
  - primary sources rise from 21% to 82%
  - refusals correct rise from 7/12 to 12/12
  - about 10× fewer Tavily credits
  - the cost is about 2.2× median latency
- **Where the gain comes from:**
  - **The model choice** accounts for most of the correctness gain: the starter's own design on DeepSeek Flash reaches 94%.
  - **The architecture** accounts for most of the trust and cost gains: verified-correct 56% → 82%, primary sources 41% → 82%, every refusal correct, and Tavily credits 4.7 → 0.9 per question. On tables, unsupported figures fall from 69% to 6%, with about 100× fewer credits.
- **The search-loop design's cost grows with the task:** one table task took 53 advanced searches. Our agent answers most questions from free SEC data and uses Tavily for news, earnings-call commentary and companies that don't file with the SEC.

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
- **CD (pull-based):** a push to `main` (or a manual run of the workflow) publishes the image to the private package
  `ghcr.io/laasyaaprasad/financial-research-agent`. A systemd timer on the instance checks for a new image every
  2 minutes, logging in with a read-only package token, and restarts the app when the image or the secrets change.
  GitHub has no AWS access: the AWS organization's policy doesn't allow GitHub OIDC.
- **Infrastructure:** [infra/main.tf](infra/main.tf) (Terraform, local state). It creates the instance, the Elastic IP,
  a security group (ports 80 and 443 only; no SSH, SSM Session Manager instead) and the instance's IAM role. Every
  resource is named `fin-research-agent`, so it sits beside other deployments in the same account.
- **Secrets:** API keys live only in `.env` and in SSM Parameter Store (SecureString) under `/fin-research-agent/`,
  which only the instance can read. [deploy/put_secrets.py](deploy/put_secrets.py) copies them from `.env` without
  printing them. They never go into the image, the Terraform state or GitHub; the workflow uses only GitHub's
  built-in token.

One-time setup: create a GitHub token with only the `read:packages` scope and add it to `.env` as `GHCR_TOKEN`, then

```bash
terraform -chdir=infra init
terraform -chdir=infra apply
uv run --with boto3 deploy/put_secrets.py
```

and push to `main` (or run the workflow). The URL is `terraform -chdir=infra output -raw url`. To read the shared
password:

```bash
aws ssm get-parameter --region us-east-2 --name /fin-research-agent/APP_PASSWORD --with-decryption --query Parameter.Value --output text
```

**Cost:** t3.micro and 20 GB of gp3 storage are free-tier eligible (the free tier's 750 hours a month are shared by
every instance in the account); the public IPv4 address is about $3.60 a month. To remove everything, run
`terraform -chdir=infra destroy`, then delete the `/fin-research-agent/*` parameters.

## Limitations and what I didn't do

- **The architecture alone doesn't raise correctness.** Given the same model, the starter's design is about as accurate as ours and slightly ahead on table cells (99% vs. 97%). The architecture's gains are verifiability, primary sourcing, refusals and cost; the correctness gain over the shipped starter comes mostly from the model choice.
- **The as-shipped starter wasn't run on the table set** (Tavily budget). On held-out sets 1 and 2 all three configurations have two runs.
- **A known bug found in held-out runs.** A table calculation can come out in a different unit than its column: inputs in thousands under a "USD millions" column, so 1,000× too large. A unit check per column would catch it. It was not fixed after the held-out runs, so the results still include it.
- **Slower:** 2× median latency.
- **Not delivered by the verifier:** its "net sales is not revenue" strictness once withheld a correct cell.
- **SEC filers only:** foreign issuers' local filings and private companies get only what the web provides.
- **No licensed data:** no consensus, estimates or paywalled transcripts. The beat/miss checks use company guidance, not consensus.
- **Small samples:** 20-question sets and 8 table tasks detect large differences only, and the dev and table "dev" sets are small.
- **Follow-up rewriting isn't evaluated.** The evaluation sets are single-turn, so the chat's rewrite of follow-ups into standalone questions was only checked by hand; a wrong rewrite is visible as **Researched as** above the answer.
- **Skipped on purpose:**
  - a multi-agent supervisor: research found it costs about 15× the tokens, and these tasks have known shapes
  - Tavily `/research`: it hides source tiers and claim-level checking
  - a vector database: evidence is fetched fresh for each question

## Repository

```
agents/      pipeline (company, fiscal, planner, research, writer, pipeline), followup, baseline, tracing, llm, edgar
ui/          chat UI (Chainlit app, chat rendering, config, readme)
evals/       question sets + manifests + source notes, run.py (harness), scorers.py, report.py
results/     final/ (results.md, scorecards, per-question records), history_kimi_baseline/ (starter on its original model)
scripts/     check_env.py, check_secrets.py, verify_traces.py
tests/       offline unit tests (no network)
PLAN.md      milestones, the course correction and how the evaluation evolved
REPORT.md    final report and technical statement
```
