"""Small deterministic synthetic fixtures (CI fixture, NOT research data)."""

from datetime import datetime, timedelta, timezone

import numpy as np
import polars as pl
import pytest

from nflcast.features.asof import METRICS

TEAMS = ["AAA", "BBB", "CCC", "DDD"]


def make_team_games(n_weeks: int = 6, seasons=(2020, 2021), seed: int = 0) -> pl.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    start = datetime(2020, 9, 13, 17, 0, tzinfo=timezone.utc)
    num_cols = sorted({m[1] for m in METRICS} | {m[2] for m in METRICS if m[2]})
    gi = 0
    for si, season in enumerate(seasons):
        for w in range(1, n_weeks + 1):
            ko = start + timedelta(days=365 * si + 7 * (w - 1))
            pairs = [("AAA", "BBB"), ("CCC", "DDD")] if w % 2 else [("AAA", "CCC"), ("BBB", "DDD")]
            for home, away in pairs:
                gid = f"{season}_{w:02d}_{away}_{home}"
                gi += 1
                for team, opp, is_home in ((home, away, True), (away, home, False)):
                    r = {"game_id": gid, "season": season, "week": w, "kickoff_utc": ko, "team": team, "opp": opp,
                         "is_home": is_home, "neutral_site": False}
                    for c in num_cols:
                        r[c] = float(rng.integers(1, 60))
                    rows.append(r)
    return pl.DataFrame(rows).with_columns(pl.col("kickoff_utc").dt.cast_time_unit("us"))


@pytest.fixture
def team_games():
    return make_team_games()
