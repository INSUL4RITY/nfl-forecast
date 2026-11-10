"""Team analytics: the opponent adjustment recovers known team effects from simulated plays."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "team_analytics"))
import compute as cp  # noqa: E402


def simulate(seed=0, n_per_game=400):
    rng = np.random.default_rng(seed)
    teams = [f"T{i}" for i in range(8)]
    off = pd.Series(np.linspace(-0.15, 0.15, 8), index=teams)
    de = pd.Series(np.linspace(0.10, -0.10, 8), index=teams)
    off -= off.mean(); de -= de.mean()
    rows = []
    for i, h in enumerate(teams):                      # an unbalanced schedule: each team hosts three others
        for a in (teams[(i + 1) % 8], teams[(i + 2) % 8], teams[(i + 3) % 8]):
            for o, d, home in ((h, a, 1), (a, h, -1)):
                y = 0.02 + 0.03 * home + off[o] + de[d] + rng.normal(0, 0.3, n_per_game)
                rows.append(pd.DataFrame({"posteam": o, "defteam": d, "is_home": home, "y": y}))
    return pd.concat(rows, ignore_index=True), teams, off, de


def test_adjust_recovers_effects_and_home():
    d, teams, off, de = simulate()
    a = cp.adjust(d, "y", teams)
    assert abs(a["home"] - 0.03) < 0.01
    assert np.abs(a["off_eff"] - off).max() < 0.03 and np.abs(a["def_eff"] - de).max() < 0.03
    assert abs(a["off_eff"].sum()) < 1e-6 and abs(a["def_eff"].sum()) < 1e-6      # sum-to-zero effects


def test_adjust_beats_raw_averages_on_an_unbalanced_schedule():
    d, teams, off, de = simulate(seed=1)
    a = cp.adjust(d, "y", teams)
    raw = d.groupby("posteam").y.mean() - d.y.mean()
    assert np.abs(a["off_eff"] - off).mean() < np.abs(raw.reindex(teams) - off).mean()
