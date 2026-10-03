# Technical statement

## The problem

An analyst asking "what was X's revenue last quarter, and did it beat guidance?" needs four things:
- the right company
- the right fiscal period
- the exact reported number
- a source they can click and check

The starter agent searched the web for everything, didn't know today's date, and did arithmetic in its head. On my 30-question dev set it fully answered 11–13 of 25 fixed-answer questions. Only about 20% of the links it cited were primary sources (SEC filings or company releases), and only half to three-quarters of its cited claims were supported by the text it had retrieved. For a regulated user, that is the gap that matters: an answer you can't verify is worse than no answer.

## Approach

I researched how shipped finance agents are built:
- OpenAI's `financial_research_agent`
- Anthropic's Claude for Financial Services
- Perplexity's finance search
- Bloomberg ASKB
- Tavily's own company-research agent

They agree on a few patterns:
- Use structured primary data first and the web second.
- Resolve fiscal periods explicitly.
- Verify claims against sources before answering.
- Size the model to each step.

I built the smallest version of that, scoped to one job: **cited, period-correct answers about SEC-reporting companies.**

1. **Resolve and calendar.** The model only names the companies; code resolves them against SEC data and builds each company's reporting calendar from its own filings: fiscal labels, exact dates, and whether each period is filed, announced only in an earnings release, or not yet reported. This targets the most common failure in finance benchmarks, fiscal vs. calendar confusion (63% of the best model's errors in Daloopa's benchmark).
2. **Plan.** One call picks the periods, the filings to read and at most three web searches. Code rejects anything that isn't in the calendar.
3. **Evidence.**
   - **SEC (free):** BM25-ranked passages from earnings releases and 10-Q/10-K filings, plus exact XBRL facts.
   - **Tavily:** only for what filings can't give: news, earnings-call commentary, and companies that don't file with the SEC. That's basic search plus one query-focused extract, with social-media sites excluded.
4. **Write, check, verify.**
   - **Quotes:** every claim carries verbatim quotes, and code rejects a quote that isn't in its source.
   - **Numbers:** code rejects any number that doesn't appear in a quote.
   - **Calculations:** growth rates, margins and implied values are expressions over quoted inputs, evaluated in code.
   - **Meaning:** a verifier checks company, metric, period, accounting basis and actual vs. guidance.
   - **Revision:** one is allowed. Claims that still fail are withheld, and anything the evidence can't support is stated as "not available" rather than estimated.

## How I kept it honest

- **Rebuilt an overfit first attempt.** It had company-specific rules and one prompt rule per test question, and its scores swung from 11/25 to 21/25 between runs. I reviewed and replaced it, rather than tuning it further.
- **Dev vs. held-out.** The 30 original questions became a dev set. A new 20-question held-out set about 21 other companies was built from SEC filings, checked against XBRL, and committed with its hash before the agent first ran on it.
- **Same model.** Baseline and agent both use DeepSeek V4.1 Flash, so the comparison measures architecture, not model choice.
- **Different-family judge.** The judge (Nemotron Ultra) is calibrated against the user's own grades (8 of 9 agreement).
- **Guard test.** A unit test fails if any evaluation-set company name appears in the agent's code.

## Results

_Filled in from the final runs: see README._

## Value

- **For the analyst:** a draft they can trust and check in seconds. Every figure links to the filing it came from, calculations are reproducible, and the agent says "not reported yet" instead of guessing.
- **For the business:**
  - **Low web cost:** most questions are answered from free SEC data, so Tavily spend is a fraction of the baseline's.
  - **Traceable runs:** each run is traced end to end in Langfuse with OpenTelemetry, with eval scores attached to each trace.
  - **Measurable progress:** the eval harness makes changes measurable before they ship.

## Limits

- **Scope:** SEC filers only. Private companies and foreign issuers' local filings are out of scope beyond what the web provides, and there is no licensed data (consensus, transcripts).
- **Latency:** typically 30–90 seconds per question, because of the verification passes.
- **Sample size:** a 20-question held-out set detects large differences, not small ones.
