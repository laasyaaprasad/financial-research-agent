"""Fiscal period boundaries from XBRL contexts and an inferred calendar rule.

XBRL 'fy'/'fp' describe the filing context, including comparative prior-year
facts, so dates determine period identity. Week-based years are inferred from
historical annual endpoints; projections are explicitly marked, never reported.
"""

from __future__ import annotations

import calendar
from collections import Counter
from datetime import date, timedelta

from agents.edgar import EdgarClient, filings
from agents.schemas import Entity, Period

DAY = timedelta(days=1)


def month_end(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


def add_months(value: date, months: int) -> date:
    total = value.year * 12 + value.month - 1 + months
    year, month = divmod(total, 12)
    return date(year, month + 1, min(value.day, calendar.monthrange(year, month + 1)[1]))


def contexts(facts: dict, today: date) -> list[dict]:
    unique = {}
    for namespace in facts.get("facts", {}).values():
        for concept in namespace.values():
            for unit in concept.get("units", {}).values():
                for fact in unit:
                    if (not fact.get("start") or fact.get("filed", "9999") > today.isoformat()
                            or fact.get("form") not in ("10-K", "10-Q", "20-F", "40-F", "8-K", "6-K")):
                        continue
                    key = tuple(fact.get(k) for k in ("start", "end", "accn", "fy", "fp", "form", "filed"))
                    unique[key] = fact
    return list(unique.values())


class FiscalCalendar:
    def __init__(self, entity: Entity, client: EdgarClient, today: date):
        self.entity, self.today = entity, today
        self.facts_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{entity.cik}.json"
        self.sub_url = f"https://data.sec.gov/submissions/CIK{entity.cik}.json"
        self.rows = contexts(client.companyfacts(entity.cik), today)
        self.filings = filings(client.submissions(entity.cik), today)
        self.ends = {f["reportDate"] for f in self.filings
                     if f.get("form") in ("10-Q", "10-K", "20-F", "40-F")}
        self.annuals = {}
        own_reports = {f.get("accessionNumber"): f.get("reportDate") for f in self.filings}
        fiscal_labels = {r["end"]: int(r["fy"]) for r in self.rows
                         if r["form"] in ("10-K", "20-F", "40-F") and r.get("fy")
                         and own_reports.get(r.get("accn")) == r["end"] and r.get("fp") == "FY"}
        pairs = Counter((r["start"], r["end"]) for r in self.rows
                        if r["form"] in ("10-K", "20-F", "40-F")
                        and 330 <= (date.fromisoformat(r["end"]) - date.fromisoformat(r["start"])).days <= 380)
        for (start, end), count in pairs.most_common():
            end_date = date.fromisoformat(end)
            fy = fiscal_labels.get(end, end_date.year)
            self.annuals.setdefault(fy, (date.fromisoformat(start), end_date))
        recent = sorted(self.annuals.items())[-5:]
        if not recent:
            raise ValueError(f"No annual XBRL duration contexts for {entity.ticker}")
        self.weekly = all((end - start).days + 1 in (364, 371) for _, (start, end) in recent)
        self.year_offset = Counter(end.year - fy for fy, (_, end) in recent).most_common(1)[0][0]
        self.rule = self._infer_week_rule(recent) if self.weekly else None

    def _infer_week_rule(self, recent):
        weekday = Counter(end.weekday() for _, (_, end) in recent).most_common(1)[0][0]
        nominal_month = int(self.entity.fiscal_year_end[:2])
        candidates = []
        for month in {nominal_month, *(end.month for _, (_, end) in recent)}:
            for mode in ("last", "nearest"):
                for day in (31, 28, 15):
                    rule = (month, weekday, mode, day)
                    matches = sum(self._weekly_end(fy + self.year_offset, rule) == end for fy, (_, end) in recent)
                    candidates.append((matches, mode == "last", day == 31, rule))
        best = max(candidates, key=lambda c: c[:3])
        if best[0] != len(recent):
            # Some filers schedule the extra week rather than follow a fixed
            # nearest/last-weekday rule. Roll 52 weeks from the last filed year;
            # mark these estimates projected, including their 53-week uncertainty.
            return None
        return best[3]

    @staticmethod
    def _weekly_end(fy, rule):
        month, weekday, mode, day = rule
        anchor = date(fy, month, min(day, calendar.monthrange(fy, month)[1]))
        if mode == "last":
            return anchor - timedelta(days=(anchor.weekday() - weekday) % 7)
        offset = (weekday - anchor.weekday()) % 7
        return anchor + timedelta(days=offset if offset <= 3 else offset - 7)

    def annual_range(self, fy: int) -> tuple[date, date, str]:
        if fy in self.annuals:
            start, end = self.annuals[fy]
            return start, end, "filing"
        if self.weekly:
            if self.rule:
                end = self._weekly_end(fy + self.year_offset, self.rule)
                start = self._weekly_end(fy - 1 + self.year_offset, self.rule) + DAY
            else:
                anchor_year = min(self.annuals, key=lambda y: abs(y - fy))
                anchor_end = self.annuals[anchor_year][1]
                end = anchor_end + timedelta(weeks=52 * (fy - anchor_year))
                start = end - timedelta(weeks=52) + DAY
        else:
            month, day = int(self.entity.fiscal_year_end[:2]), int(self.entity.fiscal_year_end[2:])
            end = date(fy + self.year_offset, month, min(day, calendar.monthrange(fy + self.year_offset, month)[1]))
            start = date(fy - 1 + self.year_offset, month, min(day, calendar.monthrange(fy - 1 + self.year_offset, month)[1])) + DAY
        return start, end, "projected"

    def quarter_range(self, fy: int, quarter: int) -> tuple[date, date, str]:
        start, end, basis = self.annual_range(fy)
        if self.weekly:
            # Infer quarter lengths from historical first-quarter durations. Costco
            # uses 12/12/12/16 weeks; other covered week-based filers use 13-week Qs.
            lengths = []
            for r in self.rows:
                rs, re = date.fromisoformat(r["start"]), date.fromisoformat(r["end"])
                if any(rs == s for s, _ in self.annuals.values()) and 75 <= (re-rs).days <= 100:
                    lengths.append((re-rs).days + 1)
            weeks = Counter(lengths).most_common(1)[0][0] // 7 if lengths else 13
            qs = start + timedelta(weeks=weeks * (quarter - 1))
            qe = end if quarter == 4 else start + timedelta(weeks=weeks * quarter) - DAY
        else:
            qs = add_months(start, 3 * (quarter - 1))
            qe = add_months(start, 3 * quarter) - DAY
        # Exact reported quarter contexts take precedence over projections.
        candidates = Counter((r["start"], r["end"]) for r in self.rows
                             if abs((date.fromisoformat(r["end"]) - qe).days) <= 7
                             and 70 <= (date.fromisoformat(r["end"]) - date.fromisoformat(r["start"])).days <= 119)
        if candidates:
            exact = next((pair for pair, _ in candidates.most_common() if pair[0] == qs.isoformat()), None)
            if exact:
                qs, qe = map(date.fromisoformat, exact)
                basis = "filing"
        return qs, qe, basis

    def period(self, kind: str, fy: int, quarter: int | None = None) -> Period:
        if kind == "quarter":
            start, end, basis = self.quarter_range(fy, quarter)
            label = f"Q{quarter} FY{fy}" if self.entity.fiscal_year_end != "1231" else f"Q{quarter} {fy}"
        elif kind == "ytd":
            start, _, _ = self.annual_range(fy)
            _, end, basis = self.quarter_range(fy, quarter)
            label = f"{quarter * 3}M FY{fy}"
        else:
            start, end, basis = self.annual_range(fy)
            label = f"FY{fy}"
        earnings = any(f.get("form") == "8-K" and "2.02" in f.get("items", "")
                       and end <= date.fromisoformat(f["filingDate"]) <= end + timedelta(days=65)
                       for f in self.filings)
        return Period(label=label, start=start, end=end, tickers=[self.entity.ticker], basis=basis,
                      source_urls=[self.facts_url, self.sub_url],
                      reported=(end.isoformat() in self.ends or earnings) and end <= self.today)

    def catalog(self) -> list[Period]:
        periods = []
        for year in range(self.today.year - 4, self.today.year + 3):
            periods.append(self.period("annual", year))
            for q in range(1, 5):
                periods.append(self.period("quarter", year, q))
                if q in (2, 3):
                    periods.append(self.period("ytd", year, q))
        return periods
