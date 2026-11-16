"""v3-C leverage weight (research only; evaluation/qb_v3_eval.py)."""

import polars as pl

from nflcast.evaluation.qb_v3_eval import leverage_weight, weighted_qbg


def test_leverage_weight_curve():
    wp = pl.DataFrame({"wp": [0.5, 0.3, 0.15, 0.05, 0.0, 0.97, None]})
    w = wp.select(leverage_weight(pl.col("wp"), 0.10, 0.25).alias("w"))["w"].to_list()
    assert w[:3] == [1.0, 1.0, 1.0]                       # competitive: full weight
    assert abs(w[3] - (0.25 + 0.75 * 0.5)) < 1e-12        # halfway to the floor
    assert w[4] == 0.25 and abs(w[5] - (0.25 + 0.75 * 0.3)) < 1e-9
    assert w[6] == 1.0                                     # missing wp: full weight
    assert wp.select(leverage_weight(pl.col("wp"), 0.3, 1.0).alias("w"))["w"].to_list() == [1.0] * 7   # f = 1: unchanged (missing wp too)


def test_weighted_qb_games_with_unit_weights_reproduce_the_original():
    qbg = pl.DataFrame({"game_id": ["g1", "g1"], "team": ["AAA", "AAA"], "qb_id": ["q1", "q2"], "db": [3, 1],
                        "epa": [0.6, -0.2], "is_starter": [True, False]})
    db = pl.DataFrame({"game_id": ["g1"] * 4, "team": ["AAA"] * 4, "qb_id": ["q1", "q1", "q1", "q2"],
                       "epa": [0.5, 0.3, -0.2, -0.2], "wp": [0.5, 0.02, 0.6, 0.5]})
    same = weighted_qbg(qbg, db, 0.1, 1.0)
    assert same["db"].to_list() == [3.0, 1.0] and [round(x, 9) for x in same["epa"].to_list()] == [0.6, -0.2]
    low = weighted_qbg(qbg, db, 0.1, 0.0)                  # the wp 0.02 dropback counts 0.2
    assert abs(low["db"][0] - 2.2) < 1e-9 and abs(low["epa"][0] - (0.5 + 0.2 * 0.3 - 0.2)) < 1e-9
