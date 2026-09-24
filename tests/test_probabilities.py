import numpy as np
import polars as pl

from nflcast.models.probability import IntervalModel, OutcomeModel


def _oof(n=600, seed=3):
    rng = np.random.default_rng(seed)
    pm = rng.normal(0, 6, n)
    margin = np.round(pm + rng.normal(0, 13, n))
    margin[:2] = 0  # a couple of ties
    return pl.DataFrame({"season": np.repeat([2019, 2020, 2021], n // 3), "pred_margin": pm, "margin": margin})


def _games():
    return pl.DataFrame({"game_type": ["REG"] * 400, "status": ["final"] * 400, "season": [2019] * 400,
                         "margin": [0.0] * 2 + [3.0] * 398})


def test_probabilities_sum_to_one_and_playoff_tie_zero():
    om = OutcomeModel().fit(_oof(), _games())
    pm = np.linspace(-20, 20, 41)
    playoff = np.array([i % 2 == 0 for i in range(41)])
    p = om.predict(pm, playoff)
    total = p["p_home"] + p["p_away"] + p["p_tie"]
    assert np.allclose(total, 1.0)
    assert (p["p_tie"][playoff] == 0).all() and (p["p_tie"][~playoff] > 0).all()
    assert ((p["p_home"] >= 0) & (p["p_home"] <= 1)).all()
    # monotone in the predicted margin
    reg = ~playoff
    assert np.all(np.diff(p["p_home"][reg]) > 0)


def test_interval_ordering_and_nesting():
    rng = np.random.default_rng(0)
    pred = rng.normal(44, 4, 800)
    actual = pred + rng.normal(0, 13, 800)
    for method in ("residual", "quantile"):
        im = IntervalModel(method, (0.8, 0.95)).fit(pred, actual)
        out = im.predict(pred)
        lo80, hi80 = out[0.8]
        lo95, hi95 = out[0.95]
        assert (lo80 <= hi80).all() and (lo95 <= hi95).all()
        assert (lo95 <= lo80 + 1e-9).all() and (hi95 >= hi80 - 1e-9).all()
