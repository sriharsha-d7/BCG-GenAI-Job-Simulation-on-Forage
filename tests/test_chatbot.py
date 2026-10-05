from types import SimpleNamespace

import pandas as pd
import pytest

from fin_chatbot import answer, data
from fin_chatbot.llm import answer_with_llm, parse_with_llm
from fin_chatbot.parser import parse


# ---------- data integrity ----------
def test_dataset_is_complete_and_consistent():
    df = data.load().reset_index()
    assert len(df) == 9 and not df.duplicated(["company", "fiscal_year"]).any()
    assert set(df.company) == set(data.COMPANIES) and sorted(df.fiscal_year.unique()) == [2022, 2023, 2024]
    assert (df.total_assets > df.total_liabilities).all()
    assert df.drop(columns=["period_end", "company"]).notna().all().all()


def test_fiscal_year_end_months_match_each_company():
    df = data.load().reset_index()
    months = df.groupby("company").period_end.apply(lambda s: set(s.dt.month)).to_dict()
    assert months == {"Apple": {9}, "Microsoft": {6}, "Tesla": {12}}


# ---------- answers the previous hard-coded bot got wrong ----------
@pytest.mark.parametrize("q,expected", [
    ("What was Tesla's net income in 2023?", "14,997"),         # was 14,974
    ("tesla total liabilities in 2023", "43,009"),               # was 77,000
    ("microsoft total assets 2024", "512,163"),                  # was 450,000
    ("apple revenue 2023", "383,285"),
    ("microsoft revenue 2023", "211,915"),
    ("apple revenue in 2022", "394,328"),
])
def test_known_facts(q, expected):
    a = answer(q)
    assert a.ok and expected in a.text


def test_every_stored_value_is_returned_by_the_bot():
    names = {"revenue": "revenue", "net_income": "net income", "total_assets": "total assets",
             "total_liabilities": "total liabilities", "operating_cash_flow": "operating cash flow"}
    for (company, year), row in data.load().iterrows():
        for key, phrase in names.items():
            a = answer(f"{company} {phrase} in {year}")
            assert a.ok and a.rows[0]["value"] == row[key], (company, year, key)


# ---------- behaviours ----------
def test_year_shorthand_and_typos():
    assert answer("apple revenue fy24").rows[0]["year"] == 2024
    assert answer("apple total assets in fy2023").rows[0]["year"] == 2023
    assert answer("microsft revenue 2022").rows[0]["company"] == "Microsoft"


def test_compare_and_rank():
    c = answer("compare apple and microsoft revenue in 2024")
    assert c.intent == "compare" and [r["company"] for r in c.rows] == ["Apple", "Microsoft"]
    r = answer("which company had the lowest net income in 2024")
    assert r.intent == "rank" and r.rows[0]["company"] == "Tesla"


def test_growth_is_computed_not_recalled():
    a = answer("tesla revenue growth 2024")
    assert a.rows[0]["growth"] == pytest.approx(97690 / 96773 - 1)
    assert not answer("apple revenue growth 2022").ok  # no prior year


def test_derived_metrics():
    assert answer("apple net margin 2024").rows[0]["value"] == pytest.approx(93736 / 391035)
    assert answer("tesla equity 2023").rows[0]["value"] == 106618 - 43009


def test_refuses_instead_of_inventing():
    assert not answer("what is google's revenue in 2023").ok
    assert "google" in answer("what is google's revenue in 2023").text
    assert not answer("apple revenue in 2019").ok
    assert not answer("hello").ok
    assert not answer("tesla leverage growth 2024").ok


# ---------- LLM front end (fake client, no network) ----------
def _fake(args=None, raises=False):
    def create(**kw):
        if raises:
            raise RuntimeError("api down")
        return SimpleNamespace(content=[SimpleNamespace(type="tool_use", input=args)])
    return SimpleNamespace(messages=SimpleNamespace(create=create))


def test_llm_parse_is_used_but_numbers_come_from_data():
    c = _fake({"intent": "lookup", "metric": "revenue", "companies": ["Tesla"], "years": [2024]})
    a = answer_with_llm("how much did elon's car company bring in last year?", client=c)
    assert a.ok and a.rows[0]["value"] == 97690


def test_llm_garbage_or_failure_falls_back_to_rules():
    bad = _fake({"intent": "lookup", "metric": "vibes", "companies": ["Tesla"]})
    assert parse_with_llm("tesla revenue 2023", client=bad).metric == "revenue"
    down = _fake(raises=True)
    assert answer_with_llm("tesla revenue 2023", client=down).rows[0]["value"] == 96773


def test_llm_cannot_inject_unknown_company():
    c = _fake({"intent": "compare", "metric": "revenue", "companies": ["Enron", "Apple"], "years": [2023]})
    q = parse_with_llm("x", client=c)
    assert q.companies == ["Apple"]
