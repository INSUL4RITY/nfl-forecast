"""Market-data policy: only point spread and total may be used as numerical market inputs.

Moneylines, American/decimal prices, juice/vig, implied probabilities, betting splits and any
return/stake/profit fields are rejected. The check is applied at ingestion (price columns are
dropped before anything is written to disk) and again on every model feature matrix.
"""

from __future__ import annotations

import re

import polars as pl

# Column-name patterns that indicate betting prices or betting-derived quantities.
# Tokens are matched between underscores/ends so that ordinary words are not caught by accident.
# `vegas` covers nflfastR's vegas_wp / vegas_home_wp, which are probabilities derived from the spread.
_TOKENS = [
    "moneyline", "ml", "odds", "price", "prices", "implied", "vig", "juice", "handle", "tickets",
    "stake", "stakes", "units", "profit", "roi", "parlay", "payout", "vegas", "overround",
]
BANNED_PATTERNS = [rf"(^|_){t}(_|$)" for t in _TOKENS] + [r"bet_pct", r"expected_return", r"betting_split"]
_BANNED = re.compile("|".join(BANNED_PATTERNS), re.IGNORECASE)

# Market-derived columns permitted in feature tables (numbers) plus metadata columns.
ALLOWED_MARKET_NUMERIC = {"home_spread", "total", "market_margin", "market_total", "market_home_pts", "market_away_pts"}
ALLOWED_MARKET_META = {"market_source", "market_snapshot_at", "market_timing", "market_available", "market_source_count"}


class BannedMarketColumnError(ValueError):
    pass


def banned_columns(columns: list[str]) -> list[str]:
    return [c for c in columns if _BANNED.search(c)]


def strip_banned(df: pl.DataFrame) -> tuple[pl.DataFrame, list[str]]:
    """Drop price-type columns. Returns (clean frame, dropped column names)."""
    bad = banned_columns(df.columns)
    return df.drop(bad), bad


def assert_no_banned(columns: list[str], context: str = "") -> None:
    bad = banned_columns(list(columns))
    if bad:
        raise BannedMarketColumnError(f"Banned market-price columns present {context}: {bad}")
