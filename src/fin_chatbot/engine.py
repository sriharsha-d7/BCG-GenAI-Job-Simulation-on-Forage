"""Answer a parsed query from the data. Every number in a reply is computed from `financials.csv`."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from . import data
from .parser import Query, parse


@dataclass
class Answer:
    text: str
    intent: str
    ok: bool = True
    rows: list[dict] = field(default_factory=list)  # the exact figures behind the text


def _label(metric: str) -> str:
    return data.METRICS[metric][0]


def _fy(company: str, year: int) -> str:
    end = data.load().loc[(company, year), "period_end"]
    return f"{company} FY{year} (year ended {end:%b %d, %Y})"


def _years_or_default(q: Query) -> tuple[list[int] | None, str | None]:
    avail = data.years()
    bad = [y for y in q.years if y not in avail]
    if bad:
        return None, f"I only have fiscal years {avail[0]}-{avail[-1]}; {', '.join(map(str, bad))} isn't covered."
    return (q.years or [max(avail)]), None


def answer_query(q: Query) -> Answer:
    if q.unknown_companies:
        return Answer(f"I don't have data for '{q.unknown_companies[0]}'. I cover {', '.join(data.COMPANIES)} "
                      f"for fiscal years {data.years()[0]}-{data.years()[-1]}.", q.intent, ok=False)
    if q.intent == "unknown" or q.metric is None:
        return Answer("I can answer questions about revenue, net income, total assets, total liabilities and operating cash flow "
                      "(plus net margin, liabilities-to-assets and equity) for Apple, Microsoft and Tesla, "
                      f"fiscal years {data.years()[0]}-{data.years()[-1]}. Try: 'What was Tesla's net income in 2023?'", "unknown", ok=False)
    m, name = q.metric, _label(q.metric)
    years, err = _years_or_default(q)
    if err:
        return Answer(err, q.intent, ok=False)

    if q.intent == "lookup":
        c, y = q.companies[0], years[0]
        v = data.value(c, y, m)
        return Answer(f"{_fy(c, y)} reported {name} of {data.fmt(m, v)}.", "lookup", rows=[{"company": c, "year": y, "metric": m, "value": v}])

    if q.intent == "trend":
        c = q.companies[0]
        rows = [{"company": c, "year": y, "metric": m, "value": data.value(c, y, m)} for y in data.years()]
        lines = "\n".join(f"  FY{r['year']}: {data.fmt(m, r['value'])}" for r in rows)
        return Answer(f"{c} {name}:\n{lines}", "trend", rows=rows)

    if q.intent == "compare":
        y = years[-1]
        cos = q.companies or list(data.COMPANIES)
        rows = [{"company": c, "year": y, "metric": m, "value": data.value(c, y, m)} for c in cos]
        lines = "\n".join(f"  {_fy(r['company'], y)}: {data.fmt(m, r['value'])}" for r in rows)
        top = max(rows, key=lambda r: r["value"])
        return Answer(f"{name.capitalize()}, fiscal {y}:\n{lines}\nHighest: {top['company']}.", "compare", rows=rows)

    if q.intent == "rank":
        y = years[-1]
        rows = sorted(({"company": c, "year": y, "metric": m, "value": data.value(c, y, m)} for c in data.COMPANIES),
                      key=lambda r: r["value"], reverse=(q.rank_order == "high"))
        w = rows[0]
        word = "highest" if q.rank_order == "high" else "lowest"
        return Answer(f"{w['company']} had the {word} {name} in fiscal {y}: {data.fmt(m, w['value'])}.", "rank", rows=rows)

    if q.intent == "growth":
        y = years[-1]
        if y - 1 not in data.years():
            return Answer(f"Growth needs the prior year, and I have no data before FY{data.years()[0]}.", "growth", ok=False)
        if m in data.PERCENT:
            return Answer(f"'Growth' isn't meaningful for a ratio; ask for the {name} by year instead.", "growth", ok=False)
        rows, lines = [], []
        for c in q.companies:
            a, b = data.value(c, y - 1, m), data.value(c, y, m)
            g = (b - a) / abs(a)
            rows.append({"company": c, "year": y, "metric": m, "value": b, "prior": a, "growth": g})
            lines.append(f"  {c}: {data.fmt(m, a)} -> {data.fmt(m, b)} ({g:+.1%})")
        return Answer(f"{name.capitalize()} change, FY{y - 1} to FY{y}:\n" + "\n".join(lines), "growth", rows=rows)

    return Answer("Sorry, I couldn't work out that question.", "unknown", ok=False)


def answer(text: str) -> Answer:
    return answer_query(parse(text))
