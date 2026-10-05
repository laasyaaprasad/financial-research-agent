# Cited financial research agent (Tavily + SEC EDGAR)

A research assistant for financial analysts. It answers questions about US-listed companies with numbers taken straight from official filings or company releases, checks every claim against its source before showing it, and says so plainly when something can't be supported.

**Links:** [live chat app](https://3-143-102-144.sslip.io) (shared-password sign-in) · [technical statement and report](REPORT.md) · [kanban](https://github.com/users/laasyaaprasad/projects/3)

## What it does

- **Answers analyst questions** about SEC-reporting companies: reported results, calculations over them (growth, margins, trailing twelve months), guidance and management commentary, and recent developments. It also builds comparison and trend tables.
- **Every number has a source.** Each figure is quoted from a filing or release, or computed in code from quoted figures. Each statement cites its source.
- **Checks before it answers.** Code checks and a separate review step test each claim against its source. Anything that fails is withheld, and anything it can't find is reported as not available instead of estimated.
- **Out of scope:** licensed data (consensus, estimates, paywalled transcripts), real-time prices and investment advice.

## Results at a glance

Measured on **Exact50**, 50 held-out questions on what an analyst tool has to get right: ambiguous requests, date traps, actual versus guidance, comparisons across fiscal calendars, and questions that need the web.

| | Starter as shipped | **Our agent** |
|---|---|---|
| Fully correct | 14/50 | **32/50** |
| Verified-correct (correct, every claim supported, every number cited) | 2/50 | **18/50** |
| Cited claims supported by the cited source | 66% | **94%** |
| Cited sources that are primary (SEC or the company) | 15% | **73%** |
| Cost per question (model + Tavily) | $0.126 | **$0.049** |
| Median time to answer | 26 s | 45 s |

**The trade-off:** more trustworthy and cheaper, but slower. Running the starter's own design on our model scores 25/50, so part of the gain comes from the model and part from the design. The full comparison, results by question type and caveats are in the [report](REPORT.md#4-results).

## How it works

![Architecture: a question and as-of date go through company resolution, the reporting calendar and one planning call; SEC evidence and Tavily feed numbered evidence; the writer quotes sources verbatim; code checks and a verifier run before the cited brief or table is shown. The verifier can send problems back to the writer once and evidence gaps back to Tavily once.](docs/architecture.png)

1. **Resolve the company** against SEC's official list, so the answer is about the right company.
2. **Build its reporting calendar** from its own filings: which fiscal periods exist, their exact dates, and what has been reported as of the question date.
3. **Plan** what to look up, in one model call that code checks.
4. **Gather evidence:** SEC filings first (exact and free), Tavily web search only for what filings don't contain.
5. **Write** an answer in which every claim quotes its source; code checks each quote, number and calculation.
6. **Verify** the meaning (right metric, period and basis), fix once, and withhold whatever still fails.

The agent runs on DeepSeek V4.1 Flash (Nebius). Evaluations are graded by GPT-6 Luna (OpenAI), a different model family. Why each step and model was chosen: [report §3](REPORT.md#3-architecture).

## Quick start

```bash
cp .env.example .env    # TAVILY_API_KEY, NEBIUS_API_KEY, SEC_USER_AGENT ("Name email"); OPENAI_API_KEY for the eval judge; optional LANGFUSE_*
uv sync
uv run python scripts/check_env.py
uv run python -m agents.pipeline "Compare revenue and operating margin for <company A> and <company B> in their latest reported quarters"
uv run python -m agents.pipeline --today 2026-03-31 "What was <company>'s most recently reported quarterly revenue?"
```

**Chat UI** (sign-in password from `APP_PASSWORD`):

```bash
uv run --group ui python -m ui            # http://localhost:8000
```

**Evaluate and test:**

```bash
uv run python -m evals.run suite --agents baseline,agent --sets exact50 --name my_suite
uv run --group ui pytest -q
uv run python scripts/check_secrets.py      # scan files for key material
```

More commands, the chat UI's features and the deployment setup are in the [report's appendices](REPORT.md#appendix-a-chat-ui).

## Deployment

- **Where:** one AWS EC2 instance (t3.micro) running Docker, behind Caddy for HTTPS.
- **How:** every push runs the tests in GitHub Actions; a push to `main` publishes a new image, which the instance picks up within about 2 minutes.
- **Secrets:** API keys live only in `.env` and in AWS SSM Parameter Store, never in the image, Terraform state or GitHub.

Setup, cost and teardown: [report appendix B](REPORT.md#appendix-b-deployment).

## Limitations

- **Web-dependent questions are the weakest class:** 3 of 10, against 7 for the starter's design on the same model.
- **Slower:** 45 s median, mostly spent writing and verifying the answer.
- **Small samples:** one run per configuration, so differences of two or three answers are within run-to-run variation.

The full list and next steps are in [report §8](REPORT.md#8-limitations-and-next-steps).

## Repository

```
agents/      pipeline steps (company, fiscal, planner, research, writer, pipeline), followup, baseline, tracing, llm, edgar
ui/          chat UI (Chainlit app, chat rendering, config, readme)
evals/       question sets, manifests and source notes; run.py (harness), scorers.py (judge), report.py
results/     final/: exact50.md, results.md (earlier held-out runs), scorecards and per-question records
infra/       Terraform for the AWS deployment; deploy/ holds the instance's deploy script and secrets upload
docs/        architecture diagram
scripts/     check_env.py, check_secrets.py, verify_traces.py
tests/       offline unit tests (no network)
PLAN.md      milestones and acceptance criteria
REPORT.md    technical statement and full report
```

Work was tracked on the [kanban board](https://github.com/users/laasyaaprasad/projects/3): the early milestones were committed straight to `main`, and later work went through pull requests.
