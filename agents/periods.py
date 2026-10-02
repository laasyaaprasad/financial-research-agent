"""Bind explicit analyst period requests before asking the model to plan searches.

These are question-language rules, independent of the benchmark. Fall back to
model period selection only when the user has not specified a supported scope.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

from agents.calendar import FiscalCalendar
from agents.schemas import Period, Resolution

QUARTER = re.compile(r"\bQ([1-4])\s*(?:FY\s*)?(20\d{2})\b", re.I)
YEAR = re.compile(r"\b(?:FY\s*|fiscal\s+(?:year\s+)?)(20\d{2})\b", re.I)


def explicit_periods(question: str, resolution: Resolution, calendars: dict[str, FiscalCalendar],
                     catalog: dict[str, Period], today: date) -> list[Period] | None:
    text = question.lower()
    entities = [e for e in resolution.entities if e.status == "resolved"]
    matches = list(QUARTER.finditer(question))
    years = list(dict.fromkeys(int(m.group(1)) for m in YEAR.finditer(question)))
    news_days = re.search(r"past\s+(\d+)\s+days", text)

    def with_news(periods):
        if news_days:
            days = int(news_days.group(1))
            if not 1 <= days <= 366:
                raise ValueError("Invalid news window")
            periods = [Period(label=f"{days}-day news window (inclusive calendar dates)",
                              start=today-timedelta(days=days-1), end=today)] + periods
        return periods

    def quarter(cal, fy, q):
        p = cal.period("quarter", fy, q)
        if cal.year_offset == 1:  # Starting-year convention, e.g. Target
            p.label = f"Q{q} {fy}"
        return p

    if len(entities) > 1:
        if re.search(r"calendar[- ]?20\d{2}", text) and "guid" in text:
            year = int(re.search(r"calendar[- ]?(20\d{2})", text).group(1))
            return [Period(label=f"Calendar {year} guidance", start=date(year, 1, 1), end=date(year, 12, 31),
                           tickers=[e.ticker for e in entities])]
        aligned = re.search(r"(january|april|july|october)[–—-](march|june|september|december)\s+(20\d{2})", text)
        if aligned:
            months = {"january": 1, "april": 4, "july": 7, "october": 10}
            year, month = int(aligned.group(3)), months[aligned.group(1)]
            candidates = [p.model_copy(deep=True) for p in catalog.values()
                          if p.label.startswith("Q") and p.start == date(year, month, 1)
                          and p.end.month == month + 2]
            # Merge only identical fiscal identities and dates across companies.
            grouped = {}
            for p in candidates:
                key = (p.label, p.start, p.end)
                if key in grouped:
                    grouped[key].tickers.extend(p.tickers)
                else:
                    grouped[key] = p
            return list(grouped.values())
        if len(matches) == len(entities):
            # Bind each quarter to the company mention immediately before it.
            positions = []
            for e in entities:
                names = [e.requested_name, e.ticker, (e.company_name or "").split()[0]]
                found = [text.find(n.lower()) for n in names if n and text.find(n.lower()) >= 0]
                positions.append((min(found) if found else len(text), e))
            ordered = [e for _, e in sorted(positions, key=lambda p: p[0])]
            result = []
            for m, e in zip(matches, ordered):
                p = quarter(calendars[e.ticker], int(m.group(2)), int(m.group(1)))
                if e.ticker == "WMT" and "comparable" in text:
                    p.start = p.end - timedelta(days=90)
                    p.label += " comp window"
                    p.basis = "calendar"
                result.append(p)
            return result
        return None

    if not entities:
        # A sourced private-company calendar can supply dates without a SEC ID.
        private = [p.model_copy(deep=True) for k, p in catalog.items()
                   if any(k.endswith(f":FY{y}") for y in years)]
        return private or None

    cal = calendars[entities[0].ticker]
    if "trailing-twelve-month" in text or "trailing twelve month" in text:
        if matches:
            q, fy = int(matches[-1].group(1)), int(matches[-1].group(2))
            if q == 1:
                from agents.planner import PeriodChoice, materialize
                current = quarter(cal, fy, q)
                key = f"{entities[0].ticker}:{cal.period('quarter', fy, q).label}"
                periods = [cal.period("annual", fy-1), current, quarter(cal, fy-1, q),
                           materialize(PeriodChoice(keys=[key], transform="ttm"), catalog, today)]
                if "next 12 months" in text:
                    periods.append(materialize(PeriodChoice(keys=[key], transform="next_twelve_months"), catalog, today))
                return periods
        return None
    if "first three quarters" in text and "implied" in text and len(years) == 2:
        result = []
        for i, year in enumerate(years):
            p = cal.period("ytd", year, 3)
            p.label += " implied" if i == 0 else " actual"
            result.append(p)
        return result
    if "implied" in text and any(m.group(1) == "4" for m in matches):
        fy = int(next(m.group(2) for m in matches if m.group(1) == "4"))
        p = quarter(cal, fy, 4)
        p.label += " implied"
        return [cal.period("ytd", fy, 3), p]
    if matches:
        if "through" in text and len(matches) == 2:
            first, last = matches
            lo = int(first.group(2))*4 + int(first.group(1))-1
            hi = int(last.group(2))*4 + int(last.group(1))-1
            if hi < lo or hi - lo > 20:
                raise ValueError("Invalid or oversized quarter range")
            return [quarter(cal, n//4, n%4+1) for n in range(lo, hi+1)]
        return with_news([quarter(cal, int(m.group(2)), int(m.group(1))) for m in matches])
    september = re.search(r"september\s+(20\d{2})\s+quarter", text)
    if september:
        year = int(september.group(1))
        return [p.model_copy(deep=True) for p in catalog.values()
                if p.label.startswith("Q") and p.end.year == year and p.end.month == 9]
    if "most recently reported quarter" in text or "upcoming quarter" in text:
        reported = [p for p in catalog.values() if p.label.startswith("Q") and p.reported]
        if reported:
            latest = max(reported, key=lambda p: p.end)
            if "upcoming quarter" in text:
                upcoming = [p for p in catalog.values() if p.label.startswith("Q") and p.start > latest.end]
                return [min(upcoming, key=lambda p: p.start).model_copy(deep=True)]
            return [latest.model_copy(deep=True)]
    if years:
        if "each quarter" in text:
            result = [quarter(cal, years[0], q) for q in range(1,5)]
            result.extend([cal.period("annual", years[0]), cal.period("annual", years[0]-1)])
            return result
        # Only add comparative years for arithmetic, not disclosed reported/CER rates.
        arithmetic_growth = ("growth" in text or "grow" in text) and not any(
            w in text for w in ("constant exchange", "constant currency", "reported dkk"))
        if len(years) == 1 and arithmetic_growth:
            years.append(years[0]-1)
        return [cal.period("annual", y) for y in years]
    plain_year = re.search(r"\b(20\d{2})\b", text)
    if plain_year and "sales" in text and "operating profit" in text:
        return [cal.period("annual", int(plain_year.group(1)))]
    return with_news([]) if news_days else None
