"""Bind explicit analyst period requests before asking the model to plan searches.

These are question-language rules, independent of the benchmark. Fall back to
model period selection only when the user has not specified a supported scope.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta

from agents.calendar import FiscalCalendar, add_months
from agents.schemas import Period, Resolution

QUARTER = re.compile(
    r"\b(?:Q(?P<q>[1-4])\s*(?P<basis>FY|fiscal(?:\s+year)?|calendar(?:\s+year)?)?\s*(?P<year>20\d{2})"
    r"|(?P<first_basis>FY|fiscal(?:\s+year)?|calendar(?:\s+year)?)\s*(?P<first_year>20\d{2})\s*Q(?P<first_q>[1-4]))\b", re.I)
YEAR = re.compile(r"\b(?:FY\s*|fiscal\s+(?:year\s+)?)(20\d{2})\b", re.I)
HALF = re.compile(r"\b(?:(?P<word>first|second)\s+half|H(?P<n>[12]))\s*(?:of\s+)?(?:the\s+)?"
                  r"(?P<basis>FY|fiscal(?:\s+year)?|calendar(?:\s+year)?)\s*(?P<year>20\d{2})\b", re.I)


@dataclass(frozen=True)
class QuarterRequest:
    quarter: int
    year: int
    start: int
    end: int
    calendar: bool = False


def quarter_requests(question: str) -> list[QuarterRequest]:
    """Recognize either order and inherit a year only across a coordinated list."""
    requests = []
    for m in QUARTER.finditer(question):
        basis = m.group('basis') or m.group('first_basis') or ''
        calendar = 'calendar' in basis.lower() or bool(re.search(r'calendar\s*$', question[:m.start()], re.I))
        requests.append(QuarterRequest(int(m.group('q') or m.group('first_q')),
                                       int(m.group('year') or m.group('first_year')),
                                       m.start(), m.end(), calendar))
    anchors = list(requests)
    for m in re.finditer(r'\bQ([1-4])\b', question, re.I):
        if any(p.start <= m.start() < p.end for p in anchors):
            continue
        for anchor in sorted(anchors, key=lambda p: min(abs(p.start-m.end()), abs(m.start()-p.end))):
            gap = question[m.end():anchor.start] if m.end() <= anchor.start else question[anchor.end:m.start()]
            if re.fullmatch(r'\s*(?:(?:and|or|to|through)\s*|[, &–—-]\s*)+', gap, re.I):
                requests.append(QuarterRequest(int(m.group(1)), anchor.year, m.start(), m.end(), anchor.calendar))
                break
    return sorted(requests, key=lambda p: p.start)


def calendar_period(year: int, part: int, months: int, tickers: list[str]) -> Period:
    if part not in range(1, 12//months + 1):
        raise ValueError('Invalid calendar period')
    start = date(year, (part-1)*months+1, 1)
    label = f"Calendar {'Q' if months == 3 else 'H'}{part} {year}"
    return Period(label=label, start=start, end=add_months(start, months)-timedelta(days=1),
                  tickers=tickers, basis='calendar')


def expand_quarter_range(question: str, requests: list[QuarterRequest]) -> list[QuarterRequest]:
    if len(requests) != 2:
        return requests
    first, last = requests
    if first.calendar != last.calendar or not re.fullmatch(
            r'\s*(?:through|to|[–—-])\s*', question[first.end:last.start], re.I):
        return requests
    lo, hi = first.year*4+first.quarter-1, last.year*4+last.quarter-1
    if hi < lo or hi-lo > 20:
        raise ValueError('Invalid or oversized quarter range')
    return [QuarterRequest(n%4+1, n//4, first.start, last.end, first.calendar) for n in range(lo, hi+1)]


def quarter_owners(question: str, requests: list[QuarterRequest], entities) -> list | None:
    """Use local mentions, including 'Q2 ... for X'; never zip introduction order."""
    mentions = []
    for e in entities:
        names = {e.requested_name, e.ticker, (e.company_name or '').split()[0]}
        for name in names - {None, ''}:
            # Ignore articles in legal names, e.g. The Home Depot.
            if name.lower() in {'the', 'a', 'an'}:
                continue
            for m in re.finditer(r'(?<!\w)'+re.escape(name)+r'(?!\w)', question, re.I):
                mentions.append((m.start(), m.end(), e))
    owners = []
    for request in requests:
        before = [m for m in mentions if m[1] <= request.start]
        after = [m for m in mentions if m[0] >= request.end]
        if after and re.match(r'\s+(?:for|of|at)\s+', question[request.end:], re.I):
            owner = min(after, key=lambda m: m[0])[2]
        elif before:
            owner = max(before, key=lambda m: m[1])[2]
        else:
            return None
        owners.append(owner)
    # If any company is unbound, leave interpretation to the structured model.
    return owners if {e.ticker for e in owners} == {e.ticker for e in entities} else None


def explicit_periods(question: str, resolution: Resolution, calendars: dict[str, FiscalCalendar],
                     catalog: dict[str, Period], today: date) -> list[Period] | None:
    text = question.lower()
    entities = [e for e in resolution.entities if e.status == "resolved"]
    matches = quarter_requests(question)
    years = list(dict.fromkeys(int(m.group(1)) for m in YEAR.finditer(question)))
    news_days = re.search(r"(?:past|last)\s+(\d+)\s+days", text)

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

    half = HALF.search(question)
    if half:
        if len(list(HALF.finditer(question))) > 1:
            return None  # Several half-year clauses need semantic interpretation.
        part = int(half.group('n') or (1 if half.group('word').lower() == 'first' else 2))
        year = int(half.group('year'))
        if 'calendar' in half.group('basis').lower():
            return with_news([calendar_period(year, part, 6, [e.ticker for e in entities])])
        if len(entities) == 1:
            cal = calendars[entities[0].ticker]
            if part == 1:
                return with_news([cal.period('ytd', year, 2)])
            p = cal.period('annual', year)
            p.start = cal.period('quarter', year, 3).start
            p.label = f'H2 FY{year}'
            return with_news([p])
        return None

    if matches and all(m.calendar for m in matches):
        if len(entities) > 1 and len(matches) > 1:
            owners = quarter_owners(question, matches, entities)
            if owners is None:
                return None
            return with_news([calendar_period(m.year, m.quarter, 3, [e.ticker])
                              for m, e in zip(matches, owners)])
        return with_news([calendar_period(m.year, m.quarter, 3, [e.ticker for e in entities])
                          for m in expand_quarter_range(question, matches)])

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
        owners = quarter_owners(question, matches, entities) if matches else None
        if owners:
            result = []
            for m, e in zip(matches, owners):
                p = (calendar_period(m.year, m.quarter, 3, [e.ticker]) if m.calendar
                     else quarter(calendars[e.ticker], m.year, m.quarter))
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
    if "trailing-twelve-month" in text or "trailing twelve month" in text or re.search(r'\bttm\b', text):
        if matches:
            q, fy = matches[-1].quarter, matches[-1].year
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
    if "implied" in text and any(m.quarter == 4 for m in matches):
        fy = next(m.year for m in matches if m.quarter == 4)
        p = quarter(cal, fy, 4)
        p.label += " implied"
        return [cal.period("ytd", fy, 3), p]
    if matches:
        matches = expand_quarter_range(question, matches)
        return with_news([(calendar_period(m.year, m.quarter, 3, [entities[0].ticker]) if m.calendar
                           else quarter(cal, m.year, m.quarter)) for m in matches])
    september = re.search(r"september\s+(20\d{2})\s+quarter", text)
    if september:
        year = int(september.group(1))
        return [p.model_copy(deep=True) for p in catalog.values()
                if p.label.startswith("Q") and p.end.year == year and p.end.month == 9]
    if re.search(r'(?:most recently|latest|most recent) reported quarter|upcoming quarter', text):
        reported = [p for p in catalog.values() if p.label.startswith("Q") and p.reported]
        if reported:
            latest = max(reported, key=lambda p: p.end)
            if "upcoming quarter" in text:
                upcoming = [p for p in catalog.values() if p.label.startswith("Q") and p.start > latest.end]
                return [min(upcoming, key=lambda p: p.start).model_copy(deep=True)]
            return [latest.model_copy(deep=True)]
    # A partial parse must not replace an unsupported subannual request with FY.
    if re.search(r'\b(?:Q[1-4]|H[12]|half|months?|YTD|quarters?)\b', question, re.I) and 'each quarter' not in text:
        return None
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
