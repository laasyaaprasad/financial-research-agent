# Financial research agent (Tavily FDE take-home)

A cited company-research agent for financial analysts, built on Tavily (retrieval), SEC EDGAR (filings data) and Nebius (LLM inference), with an offline evaluation harness. See `PLAN.md` for milestones and acceptance criteria.

## Secrets: strict rule, no exceptions

API keys live in `.env` (`TAVILY_API_KEY`, `NEBIUS_API_KEY`, plus any added later).

- **Never read `.env` or any `.env.*` file.** Not with the Read tool, and not with `cat`, `head`, `tail`, `less`, `grep`, `sed`, `awk`, `diff`, `source` + `echo`, editors, or any other command or tool.
- **Only access keys programmatically** inside project code: `load_dotenv()` then `os.getenv("NAME")`.
- **Never display key values.** No `printenv`, `env`, `echo $VAR`, `set`, or printing/logging `os.environ`. To check a key, report presence only (e.g. `bool(os.getenv("TAVILY_API_KEY"))`).
- **Never copy key values anywhere**: not into code, other files, command-line arguments, URLs, logs, traces, eval results, commits, or chat.
- Checking that the file exists (`test -f .env`) is allowed; inspecting its contents is not.
- If a key seems missing or wrong, ask the user to fix `.env`. Do not inspect it.
- `.env` must stay in `.gitignore`. Before any commit, confirm no key material (e.g. `tvly-`) appears in tracked files or `results/`.

## Project conventions

- Python ≥ 3.11, run everything with `uv run`.
- `starter_agent.py` is reference only: it must never be committed (keep it in `.gitignore`).
- SEC EDGAR requests need a `User-Agent` with contact info; read it from the `SEC_USER_AGENT` environment variable, never hardcode it.
- Every milestone must pass its acceptance criteria in `PLAN.md` before the next starts. Report eval numbers as measured; don't round up or omit failures.
- Claims from research that were not verified (vendor benchmarks, unconfirmed API behaviour such as `topic="finance"`) must be tested or caveated before they appear in the README or technical statement.
