import polars as pl
import pytest

from nflcast.data.policy import BannedMarketColumnError, assert_no_banned, banned_columns, strip_banned
from nflcast.models.core import TEAM_FEATS, OPP_FEATS, CONTEXT


def test_schedule_price_columns_are_banned():
    cols = ["game_id", "spread_line", "total_line", "away_moneyline", "home_moneyline", "away_spread_odds",
            "home_spread_odds", "under_odds", "over_odds", "vegas_wp", "vegas_home_wpa"]
    assert set(banned_columns(cols)) == {"away_moneyline", "home_moneyline", "away_spread_odds", "home_spread_odds",
                                         "under_odds", "over_odds", "vegas_wp", "vegas_home_wpa"}


def test_spread_and_total_are_allowed():
    assert banned_columns(["home_spread", "total", "spread_line", "total_line", "market_snapshot_at"]) == []


def test_strip_and_assert():
    df = pl.DataFrame({"game_id": ["x"], "home_moneyline": [-150], "total_line": [44.5]})
    clean, dropped = strip_banned(df)
    assert dropped == ["home_moneyline"] and clean.columns == ["game_id", "total_line"]
    with pytest.raises(BannedMarketColumnError):
        assert_no_banned(df.columns)


def test_football_only_features_contain_no_market_inputs():
    names = TEAM_FEATS + OPP_FEATS + CONTEXT
    assert_no_banned(names)
    assert not any(k in n for n in names for k in ("spread", "total_line", "market"))
