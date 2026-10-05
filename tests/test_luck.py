"""Luck table (display only): fumble recovery shares count every fumble in a team's games once for each side."""

import polars as pl

from nflcast.predict.luck import fumble_share


def test_fumble_share_counts_both_teams():
    pbp = pl.DataFrame({"game_id": ["g"] * 4, "posteam": ["PHI", "PHI", "LA", "LA"], "defteam": ["LA", "LA", "PHI", "PHI"],
                        "fumble": [1, 1, 1, 0], "fumble_lost": [1, 0, 1, 0]})
    # PHI fumbled twice (lost one), LA fumbled once (lost it): 3 fumbles; PHI recovered 2, LA recovered 1
    assert fumble_share(pbp) == {"PHI": (2, 3), "LA": (1, 3)}
