"""Display-only split of the football-only margin into groups (predict/breakdown.py)."""
import numpy as np
import polars as pl

from nflcast.models.core import FootballRidge, feature_set
from nflcast.predict import breakdown as BD


def _frame(n: int, seed: int) -> pl.DataFrame:
    rng = np.random.default_rng(seed)
    fs = feature_set("core_qb")
    cols = {}
    for side in ("home", "away"):
        for f in set(fs["team"]) | set(fs["opp"]) | {"games_this_season"}:
            cols[f"{side}_{f}"] = rng.normal(size=n)
    cols.update(neutral_site=rng.random(n) < 0.1, rest_diff=rng.integers(-7, 8, n).astype(float),
                is_playoff=np.zeros(n, bool), dome=(rng.random(n) < 0.3).astype(float),
                home_score=rng.normal(24, 9, n).clip(0), away_score=rng.normal(21, 9, n).clip(0))
    return pl.DataFrame(cols)


def test_groups_add_up_to_the_scenario_weighted_football_margin():
    m = FootballRidge(alpha=10.0, feature_set=feature_set("core_qb")).fit(_frame(400, 0))
    df = _frame(3, 1)                                  # one game, three QB scenarios
    p = m.predict(df)
    w = np.array([0.6, 0.3, 0.1])
    margin = float((w * p["home_pts"]).sum() - (w * p["away_pts"]).sum())
    per, names = BD.per_feature(m, df)
    b = BD.football_breakdown(per, names, np.arange(3), w, margin)
    assert b is not None and abs(sum(g["margin_points"] for g in b["groups"]) - margin) < 1e-9
    assert [g["group"] for g in b["groups"]] == [k for k, _ in BD.GROUPS]
    assert BD.football_breakdown(per, names, np.arange(3), w, margin + 0.01) is None    # mismatch: not shown


def test_every_feature_has_a_named_group():
    fs = feature_set("core_qb")
    names = [f"team_{f}" for f in fs["team"]] + [f"opp_{f}" for f in fs["opp"]]
    groups = {n: BD.group_of(n) for n in names}
    assert all(g != "other" for g in groups.values()), {n: g for n, g in groups.items() if g == "other"}
    assert BD.group_of("venue") == "home_field" and BD.group_of("rest_adv") == "rest"
    assert BD.group_of("team_off_bye") == "rest" and BD.group_of("opp_short_week") == "rest"
    assert BD.group_of("team_qb_rating") == "qb" and BD.group_of("opp_def_epa_db") == "passing"
    assert BD.group_of("team_adj_off_pts") == "scoring" and BD.group_of("opp_adj_def_epa") == "efficiency"
