"""Rule-based natural-language understanding: text -> structured `Query`."""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field

from . import data


@dataclass
class Query:
    intent: str  # lookup | trend | compare | growth | rank | unknown
    metric: str | None = None
    companies: list[str] = field(default_factory=list)
    years: list[int] = field(default_factory=list)
    rank_order: str | None = None  # "high" | "low"
    unknown_companies: list[str] = field(default_factory=list)
    note: str | None = None


_GROWTH = r"\b(growth|grew|grow|change[d]?|increase[d]?|decrease[d]?|decline[d]?|yoy|year[- ]over[- ]year|up|down)\b"
_COMPARE = r"\b(compare|comparison|versus|vs\.?|against|between|both|difference)\b"
_HIGH = r"\b(highest|largest|biggest|most|greatest|top|best|max(imum)?)\b"
_LOW = r"\b(lowest|smallest|least|fewest|worst|min(imum)?)\b"
_TREND = r"\b(trend|over time|history|historical|each year|all years|every year|by year)\b"
_STOP = set("what was is the for in of a an and tell me show give how much did does do were are their its s fy fiscal year "
            "which company had has have with to than total revenue sales net income profit assets liabilities cash flow".split())


def _find_metric(text: str) -> str | None:
    best, best_len = None, 0
    for key, (_, syns) in data.METRICS.items():
        for s in syns:
            if re.search(rf"\b{re.escape(s)}\b", text) and len(s) > best_len:
                best, best_len = key, len(s)
    return best


def _find_companies(text: str) -> tuple[list[str], list[str]]:
    found = []
    for name, aliases in data.COMPANIES.items():
        if any(re.search(rf"\b{a}\b", text) for a in aliases):
            found.append(name)
    # tolerate typos ("microsft") via fuzzy match on remaining word tokens
    all_aliases = {a: n for n, al in data.COMPANIES.items() for a in al if len(a) > 4}
    for tok in re.findall(r"[a-z]{5,}", text):
        m = difflib.get_close_matches(tok, list(all_aliases), n=1, cutoff=0.8)
        if m and all_aliases[m[0]] not in found and tok not in all_aliases:
            found.append(all_aliases[m[0]])
    order = {c: text.find(a) for c, al in data.COMPANIES.items() for a in al if a in text}
    found.sort(key=lambda c: order.get(c, 10**6))
    return found, []


def _find_years(text: str) -> list[int]:
    ys = [int(y) for y in re.findall(r"(?<!\d)(20\d{2})(?!\d)", text)]  # "2024" and "fy2024"
    ys += [2000 + int(y) for y in re.findall(r"\bfy\s?'?(\d{2})(?!\d)", text)]  # "fy24"
    if re.search(r"\b(latest|most recent|last year|current)\b", text):
        ys.append(max(data.years()))
    return list(dict.fromkeys(ys))


_PREPOSITION = r"\b(?:for|of|about|at|does|did|is|was|by)\s+([a-z][a-z&.\-]{2,})(?:'s)?\b"
_VOCAB = set(re.findall(r"[a-z]+", " ".join(
    [_GROWTH, _COMPARE, _HIGH, _LOW, _TREND]
    + [s for _, (_, syns) in data.METRICS.items() for s in syns]
    + [a for al in data.COMPANIES.values() for a in al]
    + list(_STOP)
    + ["company", "companies", "all", "each", "every", "latest", "recent", "last", "current", "year", "years", "fiscal", "the"]
)))


def _unknown_company(text: str) -> list[str]:
    """A word right after 'for/of/about/...' that is not part of our vocabulary is probably a company we do not cover."""
    out = []
    for w in re.findall(_PREPOSITION, text):
        if w not in _VOCAB and not difflib.get_close_matches(w, [a for al in data.COMPANIES.values() for a in al], n=1, cutoff=0.8):
            out.append(w)
    return out


def parse(text: str) -> Query:
    t = text.lower().strip()
    t = t.replace("’", "'")
    metric = _find_metric(t)
    companies, _ = _find_companies(t)
    years = _find_years(t)

    q = Query("unknown", metric, companies, years)
    q.unknown_companies = _unknown_company(t)

    high, low = re.search(_HIGH, t), re.search(_LOW, t)
    if (high or low) and not companies and metric:
        q.intent, q.rank_order = "rank", "high" if (high and (not low or high.start() < low.start())) else "low"
        return q
    if not metric:
        return q
    if re.search(_GROWTH, t) and len(companies) >= 1:
        q.intent = "growth"
    elif len(companies) >= 2 or re.search(_COMPARE, t) or (not companies and not (high or low)):
        q.intent = "compare"
        if not companies:
            q.companies = list(data.COMPANIES)
    elif len(companies) == 1 and (re.search(_TREND, t) or not years):
        q.intent = "trend"
    elif len(companies) == 1:
        q.intent = "lookup"
    return q
