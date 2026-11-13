import math

import polars as pl
import pytest

from nflcast.predict import score as SC


def _row(margin, total, p=(0.6, 0.39, 0.01), fb_p=(0.5, 0.49, 0.01), m80=(-5, 5), m95=(-10, 10), fb_m80=(0, 20)):
    r = {"horizon_type": "final_pregame", "margin": margin, "total_points": total, "pred_margin": 2.0, "pred_total": 44.0,
         "mkt_margin": 2.5, "mkt_total": 44.5, "fb_margin": 1.0}
    for pre, (ph, pa, pt) in (("", p), ("fb_", fb_p)):
        r.update({f"{pre}p_home": ph, f"{pre}p_away": pa, f"{pre}p_tie": pt})
        for k, (lo80, hi80), (lo95, hi95) in (("m", m80 if pre == "" else fb_m80, m95), ("t", (40, 50), (30, 60))):
            r.update({f"{pre}{k}80_lo": lo80, f"{pre}{k}80_hi": hi80, f"{pre}{k}95_lo": lo95, f"{pre}{k}95_hi": hi95})
    return r


def test_brier_log_loss_and_coverage_for_headline_and_stats_only():
    ev = SC.evaluate(pl.DataFrame([_row(3, 45), _row(-7, 41)]))
    # home win: Brier = (0.6-1)^2 + 0.39^2 + 0.01^2 ; away win: 0.6^2 + (0.39-1)^2 + 0.01^2
    assert ev["brier"].to_list() == pytest.approx([0.16 + 0.1521 + 0.0001, 0.36 + 0.3721 + 0.0001])
    assert ev["fb_brier"].to_list() == pytest.approx([0.25 + 0.2401 + 0.0001, 0.25 + 0.2601 + 0.0001])
    assert ev["log_loss"].to_list() == pytest.approx([-math.log(0.6), -math.log(0.39)])
    assert ev["fb_log_loss"].to_list() == pytest.approx([-math.log(0.5), -math.log(0.49)])
    assert ev["in_m80"].to_list() == [True, False] and ev["in_m95"].to_list() == [True, True]
    assert ev["fb_in_m80"].to_list() == [True, False]


def test_tie_scores_the_tie_probability_and_summary_reports_the_new_fields():
    ev = SC.evaluate(pl.DataFrame([_row(0, 40), _row(3, 45)]))
    assert ev["log_loss"][0] == pytest.approx(-math.log(0.01))
    s = SC._summary(ev)[0]
    assert s["n"] == 2 and s["n_stats_only"] == 2
    for k in ("brier", "stats_only_brier", "stats_only_log_loss", "cover_m95", "stats_only_cover_m80", "stats_only_cover_t95"):
        assert k in s and s[k] is not None


def test_missing_stats_only_block_is_not_scored():
    r = _row(3, 45)
    r.update({"fb_p_home": None, "fb_p_away": None, "fb_p_tie": None})
    ev = SC.evaluate(pl.DataFrame([r, _row(-3, 45)], strict=False))
    assert ev["fb_log_loss"][0] is None and SC._summary(ev)[0]["n_stats_only"] == 1
