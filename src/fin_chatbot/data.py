"""Verified financial data (USD millions) and metric metadata."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parents[2] / "data" / "financials.csv"

# metric key -> (display name, synonyms; longest phrases are matched first)
METRICS = {
    "revenue": ("total revenue", ["total revenue", "revenue", "revenues", "sales", "top line", "turnover"]),
    "net_income": ("net income", ["net income", "net profit", "profit", "earnings", "bottom line"]),
    "total_assets": ("total assets", ["total assets", "assets"]),
    "total_liabilities": ("total liabilities", ["total liabilities", "liabilities"]),
    "operating_cash_flow": ("operating cash flow", ["operating cash flow", "cash flow from operating activities", "operating cash",
                                                     "cash from operations", "cash flow", "cfo"]),
    # derived
    "net_margin": ("net margin", ["net margin", "profit margin", "net profit margin"]),
    "leverage": ("liabilities-to-assets ratio", ["liabilities to assets", "liabilities-to-assets", "leverage", "debt ratio"]),
    "equity": ("equity (assets minus liabilities)", ["shareholders equity", "stockholders equity", "equity", "net worth", "book value"]),
}
DERIVED = {"net_margin", "leverage", "equity"}
PERCENT = {"net_margin", "leverage"}

COMPANIES = {"Apple": ["apple", "aapl"], "Microsoft": ["microsoft", "msft"], "Tesla": ["tesla", "tsla"]}


@lru_cache(maxsize=1)
def load() -> pd.DataFrame:
    df = pd.read_csv(DATA, parse_dates=["period_end"])
    df["net_margin"] = df["net_income"] / df["revenue"]
    df["leverage"] = df["total_liabilities"] / df["total_assets"]
    df["equity"] = df["total_assets"] - df["total_liabilities"]
    return df.set_index(["company", "fiscal_year"]).sort_index()


def years() -> list[int]:
    return sorted(load().index.get_level_values("fiscal_year").unique())


def value(company: str, year: int, metric: str) -> float:
    return float(load().loc[(company, year), metric])


def fmt(metric: str, v: float) -> str:
    if metric in PERCENT:
        return f"{v:.1%}"
    return f"${v:,.0f} million (${v / 1000:,.1f} billion)"
