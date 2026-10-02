"""M3 benchmark: 30 questions, saved SEC inputs, live Nebius, zero Tavily calls.

Only the question/as-of date are passed to production code. Golden company/lens/
period metadata is read exclusively after planning to score the output.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

import httpx

from agents.company import resolve
from agents.edgar import EdgarClient
from agents.models import SMALL_MODEL
from agents.planner import plan


@contextmanager
def nebius_only_network():
    """Fail closed if this benchmark attempts retrieval or another external API."""
    counts = Counter()
    originals = []
    def check(request):
        host = request.url.host
        if host not in {"api.tokenfactory.nebius.com", "api.studio.nebius.ai"}:
            raise AssertionError(f"M3 benchmark forbids network requests to {host}")
        counts[host] += 1
    # The installed OpenAI SDK uses httpx2; the SEC client uses httpx. Cover
    # both transports so the allowlist also measures actual inference requests.
    import importlib
    for module_name in ("httpx", "httpx2"):
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            continue
        for cls, is_async in ((module.Client, False), (module.AsyncClient, True)):
            original = cls.send
            if any(c is cls for c, _ in originals):
                continue
            if is_async:
                async def send_async(client, request, *args, _original=original, **kwargs):
                    check(request)
                    return await _original(client, request, *args, **kwargs)
                cls.send = send_async
            else:
                def send(client, request, *args, _original=original, **kwargs):
                    check(request)
                    return _original(client, request, *args, **kwargs)
                cls.send = send
            originals.append((cls, original))
    try:
        yield counts
    finally:
        for cls, original in originals:
            cls.send = original


def period_identity(label: str) -> str:
    """Exact fiscal identity, excluding human display descriptors/company prefixes.

    Preserve fiscal vs calendar, quarter/year, and implied/actual aggregate basis.
    Company identity is checked independently; dates are compared without tolerance.
    """
    text = label.lower().replace(" ", "")
    if "nexttwelve" in text or "next12" in text:
        return "next12"
    match = re.search(r"(?:(ttm).*?)?((?:q[1-4]|[369]m)?fy\d{4}|q[1-4]\d{4})", text)
    if match:
        identity = (match.group(1) or "") + match.group(2)
        if re.match(r"[369]m", identity):
            identity += ":implied" if "implied" in text else ":actual"
        return identity
    if "calendar" in text:
        return "calendar" + (re.search(r"\d{4}", text).group() if re.search(r"\d{4}", text) else "")
    return text


def score(row: dict, output: dict, index: dict) -> dict:
    companies = row["company"].split(" — not ")[0]
    expected_tickers = {t for t in re.findall(r"\b[A-Z]{1,5}\b", companies) if t in index}
    expected_ciks = {str(index[t]["cik_str"]).zfill(10) for t in expected_tickers}
    actual = output["resolution"]["entities"]
    actual_ciks = {e["cik"] for e in actual if e["status"] == "resolved"}
    company_ok = actual_ciks == expected_ciks
    if not expected_ciks:
        company_ok = len(actual) == 1 and actual[0]["status"] == "unresolved" and "cargill" in actual[0]["requested_name"].lower()
    else:
        company_ok &= not any(e["status"] == "unresolved" for e in actual)
        client = EdgarClient("tests/fixtures/edgar", offline=True)
        company_ok &= all(e["company_name"] == client.submissions(e["cik"])["name"]
                          and e["fiscal_year_end"] == client.submissions(e["cik"])["fiscalYearEnd"] for e in actual if e["status"] == "resolved")
    actual_periods = output["plan"]["periods"]
    expected = sorted((period_identity(p["label"]), p["start"], p["end"]) for p in row["expected_periods"])
    got = sorted((period_identity(p["label"]), p["start"], p["end"]) for p in actual_periods)
    required = set(row["lens"] if isinstance(row["lens"], list) else [row["lens"]])
    chosen = {s["researcher"] for s in output["plan"]["searches"]}
    searches = output["plan"]["searches"]
    credits = sum(2 if s["search_depth"] == "advanced" else 1 for s in searches)
    return {"company_exact": bool(company_ok), "periods_exact": expected == got,
            "required_researchers": required <= chosen, "extra_researchers": sorted(chosen-required),
            "researcher_count": len(chosen), "missing_researchers": sorted(required-chosen),
            "budget_ok": credits <= output["plan"]["search_budget"] and len(searches) <= 8,
            "queries_ok": all(len(s["query"]) < 400 for s in searches),
            "unreported_ok": row["id"] != "G11" or output["plan"]["brief"]["may_be_unreported"],
            "expected_periods": expected, "actual_periods": got, "planned_search_credits": credits}


def run_one(row, model, index):
    start = time.perf_counter()
    try:
        client = EdgarClient("tests/fixtures/edgar", offline=True)
        today = date.fromisoformat(row["as_of"][:10])
        resolution = resolve(row["question"], client=client, model=model)
        result = plan(row["question"], resolution, today, 16, client=client, model=model)
        output = {"id": row["id"], "resolution": resolution.model_dump(), "plan": result.model_dump(mode="json")}
        output["scores"] = score(row, output, index)
    except Exception as exc:
        import traceback
        output = {"id": row["id"], "error": type(exc).__name__,
                  "error_detail": str(exc)[:500],
                  "error_frames": [f"{f.filename}:{f.lineno} {f.name}" for f in traceback.extract_tb(exc.__traceback__)[-4:]]}
    output["latency_s"] = round(time.perf_counter()-start, 2)
    return output


def report(outputs, rows, model, path, network_counts=None):
    scores = [o["scores"] for o in outputs if "scores" in o]
    fixed_ids = {r["id"] for r in rows if r["time_sensitivity"] == "static"}
    fixed = [o for o in outputs if o["id"] in fixed_ids]
    def count(key): return sum(s[key] for s in scores)
    lines = [f"# M3 company lookup and planner: {path.stem}", "",
             f"Model: `{model}`. Saved SEC inputs; live Nebius extraction + one planning call. **Tavily calls/credits: 0/0.**", "",
             "Golden answers, evidence, company fields, lens and expected periods are never supplied to the model.", "",
             "| Acceptance check | Result |", "|---|---|",
             f"| Company identity, CIK, name and fiscal year end | {count('company_exact')}/{len(rows)} |",
             f"| Fixed-question fiscal identities and dates | {sum(o.get('scores',{}).get('periods_exact',False) for o in fixed)}/{len(fixed)} |",
             f"| Required researchers included | {count('required_researchers')}/{len(rows)} |",
             f"| Search budget respected | {count('budget_ok')}/{len(rows)} |",
             f"| Queries under 400 characters | {count('queries_ok')}/{len(rows)} |",
             f"| G11 potentially unreported | {next((str(o.get('scores',{}).get('unreported_ok',False)) for o in outputs if o['id']=='G11'), 'not run')} |",
             f"| Errors | {sum('error' in o for o in outputs)} |", "",
             f"Average researchers per successful plan: {sum(s['researcher_count'] for s in scores)/max(len(scores),1):.2f}.", "",
             "Period comparison preserves fiscal/calendar identity, year/quarter and implied/actual aggregate basis; display descriptors and company-name prefixes are excluded. Start/end dates have zero tolerance. Multi-company period ownership is tested separately in unit tests.", "",
             "| ID | Company | Periods | Researchers | Extras / error |", "|---|---|---|---|---|"]
    for o in sorted(outputs,key=lambda o:o['id']):
        s=o.get('scores',{})
        lines.append(f"| {o['id']} | {s.get('company_exact',False)} | {s.get('periods_exact',False)} | {s.get('required_researchers',False)} | {o.get('error') or ', '.join(s.get('extra_researchers',[])) or 'none'} |")
    import statistics
    successful = [o for o in outputs if 'scores' in o]
    tokens = [sum(o['resolution']['tokens'].values())+sum(o['plan']['tokens'].values()) for o in successful]
    latency = [o['latency_s'] for o in successful]
    lines.extend(["", "## Operations", "",
                  f"Median resolution + planning latency: {statistics.median(latency):.2f} s." if latency else "No successful plans.",
                  f"Mean model tokens per successful question: {statistics.mean(tokens):,.0f}." if tokens else "",
                  f"Mean planned search credits (not spent): {statistics.mean(s['planned_search_credits'] for s in scores):.2f}." if scores else "",
                  f"Network requests: `{dict(network_counts)}`. Other HTTPX hosts are blocked." if network_counts is not None else ""])
    path.write_text("\n".join(lines)+"\n")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=SMALL_MODEL)
    parser.add_argument("--name", default="planner_m3_r1")
    parser.add_argument("--ids", nargs="*")
    parser.add_argument("--workers",type=int,default=4)
    args=parser.parse_args()
    rows=[json.loads(l) for l in Path("evals/golden.jsonl").read_text().splitlines() if l.strip()]
    if args.ids: rows=[r for r in rows if r['id'] in args.ids]
    index={r['ticker']:r for r in EdgarClient("tests/fixtures/edgar",offline=True).tickers().values()}
    outputs=[]
    raw=Path(f"results/raw/{args.name}.jsonl")
    raw.parent.mkdir(parents=True,exist_ok=True)
    with nebius_only_network() as network_counts, ThreadPoolExecutor(max_workers=args.workers) as pool, raw.open('w') as f:
        for future in as_completed([pool.submit(run_one,r,args.model,index) for r in rows]):
            output=future.result()
            outputs.append(output)
            f.write(json.dumps(output)+"\n"); f.flush()
            print(output['id'],output.get('scores') and {k:v for k,v in output['scores'].items() if k.endswith('_exact') or k.endswith('_ok') or k=='missing_researchers'} or output.get('error'),flush=True)
    path=Path(f"results/{args.name}.md")
    report(outputs,rows,args.model,path,network_counts)
    print(path)
    failures=any('error' in o or not all(o['scores'][k] for k in ('company_exact','required_researchers','budget_ok','queries_ok','unreported_ok'))
                 or (o['id'] in {r['id'] for r in rows if r['time_sensitivity']=='static'} and not o['scores']['periods_exact']) for o in outputs)
    raise SystemExit(1 if failures else 0)


if __name__=="__main__": main()
