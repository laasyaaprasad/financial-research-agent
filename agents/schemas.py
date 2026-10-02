"""Validated inputs and outputs for company resolution and the one-pass planner."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Researcher = Literal["financials", "news", "company", "industry"]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Entity(Record):
    requested_name: str
    status: Literal["resolved", "unresolved"]
    ticker: str | None = None
    cik: str | None = None
    company_name: str | None = None
    fiscal_year_end: str | None = None  # SEC MMDD, not an exact week-based year end
    tickers: list[str] = Field(default_factory=list)
    annual_form: Literal["10-K", "20-F", "40-F"] | None = None
    calendar_source_urls: list[str] = Field(default_factory=list)
    reason: str | None = None


class Resolution(Record):
    entities: list[Entity]
    tokens: dict[str, int] = Field(default_factory=dict)


class Period(Record):
    label: str
    start: date
    end: date
    tickers: list[str] = Field(default_factory=list)
    basis: Literal["filing", "calendar", "projected", "unresolved"] = "calendar"
    source_urls: list[str] = Field(default_factory=list)
    reported: bool = False

    @model_validator(mode="after")
    def valid_dates(self):
        if self.start > self.end:
            raise ValueError("Period start must not follow its end")
        return self


class Search(Record):
    researcher: Researcher
    reason: str
    query: str = Field(min_length=1, max_length=399)
    topic: Literal["general", "news", "finance"] = "general"
    search_depth: Literal["basic", "fast", "advanced"] = "advanced"
    start_date: date | None = None
    end_date: date | None = None
    preferred_domains: list[str] = Field(default_factory=list)

    @property
    def credits(self) -> int:
        return 2 if self.search_depth == "advanced" else 1


class EdgarFetch(Record):
    ticker: str
    cik: str
    form: Literal["10-K", "10-Q", "8-K", "20-F", "40-F", "6-K"]
    period_end: date
    item: str


class Brief(Record):
    metrics: list[str]
    answer_type: Literal["number", "text", "list"]
    may_be_unreported: bool


class ResearchPlan(Record):
    brief: Brief
    periods: list[Period]
    edgar_fetches: list[EdgarFetch]
    searches: list[Search] = Field(max_length=8)
    warnings: list[str] = Field(default_factory=list)
    search_budget: int = Field(ge=0)
    model: str
    tokens: dict[str, int] = Field(default_factory=dict)

    @model_validator(mode="after")
    def within_budget(self):
        if sum(s.credits for s in self.searches) > self.search_budget:
            raise ValueError("Searches exceed the Tavily credit budget")
        return self
