"""Luck and regression watch for the Team ratings page (display only; never a model input).

Results vs play quality, season to date, from our own nflverse play-by-play aggregates:
  * expected wins: per game, P(win | net EPA per play) from a logistic fit on completed regular-season games of earlier
    seasons (ties excluded); summed over the team's games. Wins above it = results ahead of play (regression risk),
    below it = results behind play (likely to improve);
  * one-score record (final margin <= 8), turnover margin, and the share of all fumbles in the team's games that the team
    recovered (about 50% in the long run; far from it is mostly luck).
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import polars as pl
from sklearn.linear_model import LogisticRegression

LUCKY, UNLUCKY = 1.0, -1.0          # wins above / below expected that get a label


def _games(tg: pl.DataFrame) -> pl.DataFrame:
    """One row per team-game with the opponent's numbers and net EPA per play."""
    opp = tg.select("game_id", pl.col("team").alias("opp"), o_epa=pl.col("epa_play_sum"), o_plays=pl.col("plays"),
                    o_ints=pl.col("ints"), o_fl=pl.col("fumbles_lost"))
    g = tg.join(opp, on=["game_id", "opp"])
    return g.with_columns(net_epa=pl.col("epa_play_sum") / pl.col("plays") - pl.col("o_epa") / pl.col("o_plays"),
                          margin=pl.col("points") - pl.col("points_allowed"))


def win_model(tg: pl.DataFrame, season: int) -> LogisticRegression:
    g = _games(tg).filter((pl.col("season") < season) & (pl.col("game_type") == "REG") & (pl.col("margin") != 0))
    return LogisticRegression().fit(g["net_epa"].to_numpy().reshape(-1, 1), (g["margin"] > 0).to_numpy())


def fumble_share(pbp: pl.DataFrame) -> dict[str, tuple[int, int]]:
    """{team: (fumbles recovered by the team, all fumbles in its games)} from plays with a fumble."""
    f = pbp.filter(pl.col("fumble") == 1).select("game_id", "posteam", "defteam", "fumble_lost").drop_nulls(["posteam", "defteam"])
    out: dict[str, list[int]] = {}
    for r in f.iter_rows(named=True):
        lost = int(r["fumble_lost"] or 0)
        for team, recovered in ((r["posteam"], 1 - lost), (r["defteam"], lost)):
            s = out.setdefault(team, [0, 0])
            s[0] += recovered
            s[1] += 1
    return {k: (v[0], v[1]) for k, v in out.items()}


def team_luck(tg: pl.DataFrame, pbp: pl.DataFrame | None, season: int, now: datetime) -> list[dict]:
    m = win_model(tg, season)
    g = _games(tg).filter((pl.col("season") == season) & (pl.col("kickoff_utc") < now))
    if g.height == 0:
        return []
    g = g.with_columns(p=pl.Series(m.predict_proba(g["net_epa"].to_numpy().reshape(-1, 1))[:, 1]))
    fum = fumble_share(pbp) if pbp is not None else {}
    rows = []
    for team, t in g.group_by("team"):
        w, l, ties = int((t["margin"] > 0).sum()), int((t["margin"] < 0).sum()), int((t["margin"] == 0).sum())
        xw = float(t["p"].sum())
        luck = w + 0.5 * ties - xw
        close = t.filter(pl.col("margin").abs() <= 8)
        rec, tot = fum.get(team[0], (0, 0))
        rows.append({
            "team": team[0], "games": t.height, "wins": w, "losses": l, "ties": ties, "expected_wins": xw, "luck": luck,
            "one_score": [int((close["margin"] > 0).sum()), int((close["margin"] < 0).sum())],
            "turnover_margin": int((t["o_ints"] + t["o_fl"]).sum() - (t["ints"] + t["fumbles_lost"]).sum()),
            "fumbles_recovered": rec, "fumbles_total": tot,
            "net_epa_play": float(np.average(t["net_epa"].to_numpy())),
            "read": "ahead" if luck >= LUCKY else "behind" if luck <= UNLUCKY else "in_line"})
    return sorted(rows, key=lambda r: -r["luck"])
