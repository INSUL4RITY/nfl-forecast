"""Team analytics: the matchup calibration only ever pulls expectations towards the league average."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "team_analytics"))
import backtest_matchups as B  # noqa: E402
import compute as cp  # noqa: E402

C = json.loads(cp.CAL_FILE.read_text(encoding="utf-8"))


def test_every_matchup_measure_has_a_factor_between_0_and_1():
    assert set(C["factor"]) == {m[0] for m in cp.MATCHUP_METRICS}
    for by_week in C["factor"].values():
        v = [by_week[str(w)] for w in range(1, 19)]
        assert all(0.0 <= x <= 1.0 for x in v)
        assert all(b >= a for a, b in zip(v, v[1:]))            # more of a team's record is kept as the season goes on


def test_weeks_outside_the_file_use_the_nearest_week():
    lo, _ = cp.calibration_factors(-3)
    hi, _ = cp.calibration_factors(40)
    assert lo["epa_play"] == C["factor"]["epa_play"]["1"] and hi["epa_play"] == C["factor"]["epa_play"]["18"]


def test_factor_is_clipped():
    assert float(B.factor(0.2, 0.05, 30)) == 1.0 and float(B.factor(0.2, 0.05, 4, k=0.0)) == 0.0
    assert abs(float(B.factor(0.2, 0.05, 6)) - 0.5) < 1e-12


def test_fit_recovers_a_known_week_pattern():
    rng = np.random.default_rng(0)
    rows = []
    for m, k in (("a", 1.0), ("b", 0.5)):
        for w in range(4, 17):
            shr = rng.normal(0, 1, 400)
            rows.append(pd.DataFrame({"metric": m, "W": w, "n": 60, "shr": shr, "actual": k * (0.2 + 0.05 * w) * shr + rng.normal(0, 0.5, 400)}))
    a, b, ks = B.fit(pd.concat(rows, ignore_index=True))
    assert abs(ks["b"] / ks["a"] - 0.5) < 0.05
    assert abs(float(B.factor(a, b, 10, ks["a"])) - 0.7) < 0.05


def test_out_of_sample_check_is_recorded():
    assert C["improved"] <= C["measures"] == len(C["leave_one_season_out"])
    assert all(v["error_after"] <= v["error_before"] + 1e-9 for v in C["leave_one_season_out"].values()) == (C["improved"] == C["measures"])
