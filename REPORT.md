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

The starter as shipped (Kimi K2.6) searches the web for everything, doesn't know today's date, and does arithmetic in its head. On Exact50 (50 held-out questions; see §4), graded by GPT-6 Luna:
- **Correctness:** fully correct on 14 of 50, and on 1 of the 16 ambiguous or edge-case requests.
- **Usable answers:** 2 of 50 are verified-correct (correct, every cited claim supported, every number cited).
- **Sources:** 66% of its cited claims are supported by the cited source, and 15% of its citations are primary sources.
- **Cost:** it used 373 Tavily credits for the 50 questions, about $0.126 per question with model tokens.

## 3. Architecture and why each part exists

```mermaid
flowchart TD
    Q[Question + as-of date] --> R[Resolve companies<br/>model names them; SEC ticker list confirms]
    R --> C[Reporting calendar per company<br/>fiscal labels, exact dates,<br/>filed / earnings release only / not yet reported]
    C --> P[Plan: one model call<br/>answer periods, filings to read, ≤3 web searches]
    P --> S[SEC evidence, free<br/>release, 10-Q/10-K and 8-K passages,<br/>XBRL facts for every answer period]
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

| Component | Why it's there |
|---|---|
| **DeepSeek V4.1 Flash instead of Kimi K2.6** | The quickest improvement is often a better, cheaper model. On Artificial Analysis it scores 39 against 27 on the Intelligence Index, generates 214 tokens/s against 71, and costs about a third as much. Here, the starter's own design gained 11 answers on Exact50 (14 → 25) and halved its latency (26 s → 12 s). Cheap reasoning makes the context the lever, which is what the rest of this table works on. |
| **Company resolution against SEC's ticker list** (`company.py`) | **Wrong-entity errors:** Facebook vs. Meta, share classes, spin-offs. The model only names companies, so it can never invent an identifier. |
| **Reporting calendar from each company's own filings** (`fiscal.py`) | **Fiscal-period errors:** confusing fiscal and calendar periods caused 63% of the best model's errors in Daloopa's benchmark. The calendar gives fiscal labels with exact dates, handles start-year naming and irregular 16-week quarters, and gives each period's reporting status as of the question date, which drives both refusals and point-in-time answers. |
| **One planning call, validated in code** (`planner.py`) | Scales effort to the question (Anthropic's guidance; OpenAI's `financial_research_agent`). It can't pick a period the company hasn't reported, and it plans at most 3 searches. |
| **SEC-first evidence:** ranked passages from releases and 10-Q/10-K filings, plus XBRL facts | Primary, exact numbers at no cost. In Daloopa's benchmark, structured filings data took agents from 20–71% accuracy to about 90%. Always including the core income-statement lines fixed missing-revenue gaps. |
| **Tavily for what filings lack, plus one gap-filling round** | News, earnings-call guidance, and companies that don't file with the SEC. Added after dev failures where guidance existed only on the call. Settings were measured on the web dev set with plans replayed: basic search plus one extract scored 8/10 at 3.9 credits per question; advanced depth (7/10, 5.6), company sites first (6/10, 6.4), `topic="finance"` (4/10, 6.6) and `auto_parameters` (2/10, 8.0) cost more and scored lower. |
| **Claims and cells with verbatim quotes; code checks; calculations in code** (`writer.py`) | **Hallucinated or mis-computed numbers:** a quote must exist in its source, every number must appear in a quote, and arithmetic (growth, TTM, fiscal Q4 = full year minus nine months) is evaluated by code, never by the model. |
| **Verifier pass, one revision, withhold what still fails** | **Meaning errors code can't see:** wrong metric (net sales vs. revenue), GAAP vs. non-GAAP, actual vs. guidance. This follows OpenAI's verifier pattern and Bloomberg's post-generation checks. |
| **Tables** | Comps and trend tables are what analysts build daily, and where per-cell provenance matters most. |
| **Langfuse tracing (OpenTelemetry) and an eval harness** | Every run is inspectable step by step, with scores attached, in development and from the deployed app. The traces located the failures fixed in §5 and show where time goes. Tests replay cached Tavily responses, so most runs spend no credits. |
| **Reasoning effort set per step** | Halved median latency without changing quality on the dev set. A per-question effort selector (Jev) was tried on a branch and not merged, to keep the design simple. |
| **CI/CD to AWS, kanban, PRs** | GitHub Actions tests every push and `main` deploys itself, so it is always live. The chat has a shared password (from SSM, not the code) and answers one question at a time. Keys were never read by the coding agent: loaded in code, copied to SSM by a script that doesn't print them. |

All production code is generic: a unit test fails if any evaluation-set company name appears in `agents/`.

## 4. Final results vs. the base agent

**Exact50** is 50 of the 74 held-out questions, chosen by fixed rules (`evals/exact50_selection.md`):
- all 16 edge-case and ambiguous requests
- all 10 web-dependent questions
- 16 date traps
- 4 actual-versus-guidance questions
- 4 cross-calendar comparisons

Plain single-figure lookups, which every configuration answers, were dropped. Each column is one fresh run, graded by `gpt-6-luna` (OpenAI, high reasoning, a different family from the agents; 8 of 10 agreement with the user's grades), with three votes per answer. The middle column runs the starter's design on our model, DeepSeek V4.1 Flash, to separate the architecture's contribution from the model's.

| Exact50 | Starter (as shipped) | Starter design, our model | **Our agent** |
|---|---|---|---|
| Fully correct | 14/50 | 25/50 | **32/50** |
| **Verified-correct** (correct, every cited claim supported, every number cited) | 2/50 | 0/50 | **18/50** |
| Cited claims supported by the cited source | 66% | 69% | **94%** |
| Primary-source citations | 15% | 26% | **73%** |
| Edge-case and ambiguous requests correct | 1/16 | 1/16 | **11/16** |
| Web-dependent questions correct | 3/10 | **7/10** | 3/10 |
| Tavily credits (50 questions)\* | 373 | 338 | **115** |
| Cost per question (model + Tavily)\*\* | $0.126 | $0.074 | **$0.049** |
| Median latency | 26 s | **12 s** | 45 s |

\* Our agent's credits are Tavily's own per-call usage. The starters' are counted from their successful searches, because their LangChain tool doesn't report usage.
\*\* Nebius list prices for the model tokens; Tavily credits at $0.008 (pay-as-you-go).

**How it compares.** The gain is trust and cost, paid for in speed: for factual research, an answer that needn't be re-checked is worth the wait.
- **Against what was shipped:**
  - fully correct rises from 14 to 32 of 50, and verified-correct from 2 to 18
  - supported citations rise from 66% to 94%, and primary sources from 15% to 73%
  - it uses about a third of the credits and costs $0.049 per question against $0.126
  - it is slower: 45 s against 26 s. Langfuse step timings (29 traces) put most of it in writing and verification (median 24 s); the planner takes 5 s
- **Against the starter's design on the same model:**
  - fully correct rises from 25 to 32, mostly on ambiguous and edge-case requests (1 → 11 of 16)
  - every trust measure is higher, and it uses about a third of the credits
  - it is weaker on web-dependent questions (3 against 7 of 10) and about 4× slower
- **Caveats:**
  - one run per column
  - Exact50's rules were written after earlier results on these questions were known
  - the final agent's fixes came from diagnosing held-out failures (§5), so this is not a clean held-out test

Full tables: [`results/final/exact50.md`](results/final/exact50.md). The earlier full held-out results (older agent, Nemotron judge, before the grading fixes; its citation check also saw quotes attached to sources that didn't contain them, which may have flattered our agent's supported-claim rate there; the Exact50 grading strips them) are in [`results/final/results.md`](results/final/results.md). On those mostly single-figure questions, the starter's design on our model was about as accurate as our agent (94% against 99% fully correct), and the architecture's gain was in trust and cost.

## 5. How the result was reached

1. **A first implementation was rebuilt.** It reached 21/25 on the dev set but was overfit: named-company rules and one prompt rule per test question. It was also unstable, ranging from 11 to 21 out of 25 across runs. It was replaced by the generic pipeline above, about 1,400 lines instead of about 5,700.
2. **Two more held-out sets were added.** On the first held-out set, the starter's design on our model and our agent both scored near the ceiling, so I added the harder set and the table set to test where the architecture matters. They were built blind from SEC filings, without seeing either agent's outputs.
3. **The as-shipped starter is the headline baseline.** It was run on the held-out sets once the comparison was framed as "what was shipped vs. what we built". The same-model runs stay as the architecture-only comparison.
4. **Changes came only from dev failures, until the review.** Until 2026-10-05, agent changes were driven by dev-set failures only. Two known held-out issues remain unfixed and are reported: a unit mismatch in one table calculation, and an over-strict verifier rule.
5. **Budget.** Most of the Tavily credits went to the starter runs, which is why the as-shipped starter has two runs on held-out sets 1 and 2 and none on the table set. Tavily's usage endpoint reported 1,884 credits used against the 1,500-credit plan; the 384 over were billed pay-as-you-go.

6. **The evaluation was reviewed (2026-10-05).** A full rerun looked wrong: the starter's design on our model was ahead on correctness. The review found problems in the harness first:
   - answers scored 0 because the judge's verdict contradicted its own per-point marks
   - one run graded by the agents' own model
   - a citation check cut to the first 60,000 characters of everything retrieved, which hid support for long baseline retrievals
   - many questions that every configuration answers

   The grading was fixed (verdict from the required rubric points, cited sources shown in full), and Exact50 was built from the held-out sets by rules written down first. The judge stayed a different family from the agents: GLM-5.3-Flash on Nebius was tried first, but it was throttled in the first smoke runs (no grade for 5 of 24 answers), so Exact50 was graded by OpenAI's GPT-6 Luna through the OpenAI API.
7. **Generic fixes from the diagnosis.** The run records and Langfuse traces showed where held-out answers broke. The causes:
   - a number check that read "Margin 29.4%" as a date
   - zero-width spaces in SEC tables breaking quote matching
   - SEC's tagged financial data lagging two companies' July 10-Qs
   - calculations that couldn't chain
   - web results about other companies passing the relevance filter

   These were fixed in code. The planner and writer prompts were rewritten to teach a way of working through a question rather than rules for particular questions, and the writer's reasoning effort was raised. That moved Exact50 from 24 to 32 fully correct.

Details: [`README.md`](README.md), [`results/final/exact50.md`](results/final/exact50.md), [`PLAN.md`](PLAN.md).
