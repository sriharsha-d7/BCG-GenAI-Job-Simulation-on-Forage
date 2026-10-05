"""Optional GenAI front end: an LLM turns the question into a structured `Query`; the *engine* computes the answer.

The model never writes a number into a reply, so it cannot hallucinate a financial figure: the worst a bad parse
can do is ask for the wrong (verified) row. Anything the model returns is validated, and an invalid or failed
call falls back to the rule-based parser.

Requires ``pip install anthropic`` and ``ANTHROPIC_API_KEY``. The client is injectable so the logic is unit-tested
without network access; it has not been exercised against the live API in this repository's CI.
"""

from __future__ import annotations

import os

from . import data
from .engine import Answer, answer_query
from .parser import Query, parse

DEFAULT_MODEL = os.environ.get("FIN_CHATBOT_MODEL", "claude-sonnet-5-5")
INTENTS = ["lookup", "trend", "compare", "growth", "rank"]

TOOL = {
    "name": "query_financials",
    "description": ("Translate a user's question about Apple, Microsoft or Tesla annual financials (FY2022-2024) into a "
                    "structured query. Do not answer the question; only describe what data is needed."),
    "input_schema": {
        "type": "object",
        "properties": {
            "intent": {"type": "string", "enum": INTENTS},
            "metric": {"type": "string", "enum": list(data.METRICS)},
            "companies": {"type": "array", "items": {"type": "string", "enum": list(data.COMPANIES)}},
            "years": {"type": "array", "items": {"type": "integer"}},
            "rank_order": {"type": "string", "enum": ["high", "low"]},
        },
        "required": ["intent", "metric"],
    },
}


def parse_with_llm(text: str, client=None, model: str = DEFAULT_MODEL) -> Query:
    if client is None:
        import anthropic  # optional dependency

        client = anthropic.Anthropic()
    try:
        resp = client.messages.create(
            model=model, max_tokens=300, tools=[TOOL], tool_choice={"type": "tool", "name": TOOL["name"]},
            messages=[{"role": "user", "content": text}],
        )
        block = next(b for b in resp.content if getattr(b, "type", None) == "tool_use")
        args = dict(block.input)
        q = Query(
            intent=args["intent"], metric=args["metric"],
            companies=[c for c in args.get("companies", []) if c in data.COMPANIES],
            years=[int(y) for y in args.get("years", [])],
            rank_order=args.get("rank_order"),
        )
        _validate(q)
        return q
    except Exception:  # network error, refusal, malformed output: never fail the user's question
        return parse(text)


def _validate(q: Query) -> None:
    if q.intent not in INTENTS or q.metric not in data.METRICS:
        raise ValueError("invalid intent/metric")
    if q.intent in {"lookup", "trend", "growth"} and not q.companies:
        raise ValueError("needs a company")
    if q.intent == "rank" and q.rank_order not in {"high", "low"}:
        raise ValueError("rank needs an order")


def answer_with_llm(text: str, client=None, model: str = DEFAULT_MODEL) -> Answer:
    return answer_query(parse_with_llm(text, client, model))
