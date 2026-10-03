"""A company's reporting calendar, built from its own SEC filings as of a given date.

Every period gets the company's fiscal label, exact start/end dates and its reporting
status: filed in a 10-Q/10-K, announced only in an earnings release (8-K item 2.02),
or not yet reported. Fiscal-year naming (by the year a fiscal year ends or starts) is
read from the company's annual-report XBRL, because conventions differ by company.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from agents.edgar import ARCHIVES, EdgarClient

PERIODIC = {"10-K": "annual", "20-F": "annual", "40-F": "annual", "10-Q": "quarterly"}


@dataclass
class Filing:
    form: str
    filed: date
    accession: str
    url: str           # primary document
    report_date: date | None
    items: str = ""    # 8-K item numbers, e.g. "2.02,9.01"


@dataclass
class Period:
    label: str                 # e.g. "Q2 FY2027", "FY2026"
    start: date
    end: date
    status: str                # "filed", "earnings release only", "not yet reported"
    report: Filing | None = None              # 10-Q / 10-K / 20-F
    earnings_releases: list[Filing] = field(default_factory=list)  # 8-K item 2.02 filed after the period
    projected: bool = False    # dates inferred from the company's calendar pattern

    def describe(self) -> str:
        source = ""
        if self.report:
            source = f"; {self.report.form} filed {self.report.filed}"
        if self.earnings_releases:
            source += f"; earnings release 8-K filed {self.earnings_releases[0].filed}"
        approx = " (projected dates)" if self.projected else ""
        return f"{self.label}: {self.start} to {self.end}{approx} — {self.status}{source}"


def filings_as_of(client: EdgarClient, cik: str, today: date) -> list[Filing]:
    recent = client.submissions(cik).get("filings", {}).get("recent", {})
    out = []
    for i, form in enumerate(recent.get("form", [])):
        filed = date.fromisoformat(recent["filingDate"][i])
        if filed > today:
            continue
        acc = recent["accessionNumber"][i]
        report = recent["reportDate"][i]
        out.append(Filing(form=form, filed=filed, accession=acc,
                          url=f"{ARCHIVES}/{int(cik)}/{acc.replace('-', '')}/{recent['primaryDocument'][i]}",
                          report_date=date.fromisoformat(report) if report else None,
                          items=recent.get("items", [""] * len(recent["form"]))[i] or ""))
    return out


def _naming_offset(client: EdgarClient, cik: str, annual: list[Filing]) -> int:
    """0 if fiscal years are named for the calendar year they end in, -1 if for the year they start in."""
    accessions = {f.accession: f.report_date for f in annual}
    for namespace in client.companyfacts(cik).get("facts", {}).values():
        for concept in namespace.values():
            for unit in concept.get("units", {}).values():
                for fact in unit:
                    end = accessions.get(fact.get("accn"))
                    if end and fact.get("fp") == "FY" and fact.get("fy") and fact.get("end") == end.isoformat():
                        return int(fact["fy"]) - end.year
    return 0


def _step(end: date, month_end: bool, months: int) -> date:
    """Next period end: same day-of-month pattern for month-end calendars, else whole weeks."""
    if not month_end:
        return end + timedelta(weeks=13 * months // 3)
    y, m = divmod(end.month - 1 + months, 12)
    first_next = date(end.year + y + (m + 1) // 12, (m + 1) % 12 + 1, 1)
    return first_next - timedelta(days=1)


def calendar(client: EdgarClient, cik: str, today: date, years: int = 3) -> list[Period]:
    """Reported and next-expected periods for the last `years` fiscal years, oldest first."""
    filings = filings_as_of(client, cik, today)
    reports = sorted((f for f in filings if f.form in PERIODIC and f.report_date), key=lambda f: f.report_date)
    # Keep the original filing for each period end (amendments re-use the same report date).
    by_end: dict[date, Filing] = {}
    for f in reports:
        by_end.setdefault(f.report_date, f)
    annual = [f for f in by_end.values() if PERIODIC[f.form] == "annual"]
    if not annual:
        return []
    offset = _naming_offset(client, cik, annual)
    month_end = all((e + timedelta(days=1)).day == 1 for e in by_end)
    releases = sorted((f for f in filings if f.form in ("8-K", "6-K") and "2.02" in f.items), key=lambda f: f.filed)

    # Fiscal-year ends: reported ones, then projected ones until the fiscal year containing today.
    fy_ends = sorted(f.report_date for f in annual)
    while fy_ends[-1] < today:
        fy_ends.append(_step(fy_ends[-1], month_end, 12))
    has_quarters = any(f.form == "10-Q" for f in by_end.values())

    periods: list[Period] = []
    previous_quarter_ends: list[date] = []
    for prev_end, fy_end in zip(fy_ends, fy_ends[1:]):
        fy_label = f"FY{fy_end.year + offset}"
        fy_start = prev_end + timedelta(days=1)
        filed_quarters = sorted(e for e, f in by_end.items() if fy_start <= e < fy_end and f.form == "10-Q")
        # Quarters are numbered by order within the fiscal year. Missing ones are projected from
        # the same quarter a year earlier, which preserves irregular lengths (e.g. 12/12/12/16 weeks).
        quarter_ends = []
        for q in range(3):
            if q < len(filed_quarters):
                quarter_ends.append((filed_quarters[q], False))
            elif len(previous_quarter_ends) == 3:
                quarter_ends.append((previous_quarter_ends[q] + (fy_end - prev_end), True))
            else:
                quarter_ends.append((_step(prev_end, month_end, 3 * (q + 1)), True))
        previous_quarter_ends = [e for e, _ in quarter_ends]
        if fy_end.year < today.year - years:
            continue
        if has_quarters:
            start = fy_start
            for q, (end, projected) in enumerate(quarter_ends + [(fy_end, fy_end not in by_end)], start=1):
                periods.append(_period(f"Q{q} {fy_label}", start, end, projected, by_end, releases, today))
                start = end + timedelta(days=1)
        periods.append(_period(fy_label, fy_start, fy_end, fy_end not in by_end, by_end, releases, today))
    return [p for p in periods if p.start <= today]


def _period(label, start, end, projected, by_end, releases, today) -> Period:
    report = by_end.get(end)
    window_end = end + timedelta(days=100)
    matched = [r for r in releases if end < r.filed <= window_end]
    if report:
        status = "filed"
    elif matched:
        status = "earnings release only (periodic report not yet filed)"
    elif end >= today:
        status = "not yet reported (period still in progress)"
    else:
        status = "not yet reported (period ended, results not yet released)"
    return Period(label=label, start=start, end=end, status=status, report=report,
                  earnings_releases=matched[:1], projected=projected and not report)
