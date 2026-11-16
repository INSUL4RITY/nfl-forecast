"""Team analytics: blitz outcomes, hot/cold verdicts and the depleted-line flag (added for the week 11 build)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "team_analytics"))
import compute as cp  # noqa: E402


# ---- blitz outcomes
def test_blitz_outcomes_add_up_and_classify():
    rows = [  # defteam D blitzes on all four: sack, completion of 25, incompletion, scramble of 6; one non-blitz interception
        {"defteam": "D", "posteam": "O", "blitz": True, "sack": 1, "qb_scramble": 0, "interception": 0, "complete_pass": 0, "success": 0, "yards_gained": -7, "epa": -2.0},
        {"defteam": "D", "posteam": "O", "blitz": True, "sack": 0, "qb_scramble": 0, "interception": 0, "complete_pass": 1, "success": 1, "yards_gained": 25, "epa": 1.8},
        {"defteam": "D", "posteam": "O", "blitz": True, "sack": 0, "qb_scramble": 0, "interception": 0, "complete_pass": 0, "success": 0, "yards_gained": 0, "epa": -0.5},
        {"defteam": "D", "posteam": "O", "blitz": True, "sack": 0, "qb_scramble": 1, "interception": 0, "complete_pass": 0, "success": 1, "yards_gained": 6, "epa": 0.3},
        {"defteam": "D", "posteam": "O", "blitz": False, "sack": 0, "qb_scramble": 0, "interception": 1, "complete_pass": 0, "success": 0, "yards_gained": 0, "epa": -3.0},
    ]
    T = pd.DataFrame(index=["D", "O"])
    cp.blitz_outcomes(pd.DataFrame(rows), T)
    r = T.loc["D"]
    assert r.def_out_sack_blitz == 0.25 and r.def_out_cmp_blitz == 0.25 and r.def_out_inc_blitz == 0.25 and r.def_out_scr_blitz == 0.25
    assert sum(r[f"def_out_{o}_blitz"] for o in cp.BLITZ_OUTCOMES) == 1.0
    assert r.def_out_expl_blitz == 0.25 and r.def_out_succ_blitz == 0.5
    assert r.def_out_int_noblitz == 1.0
    assert abs(r.def_blitz_epa_gain - ((-2.0 + 1.8 - 0.5 + 0.3) / 4 - (-3.0))) < 1e-12
    assert T.loc["O"].off_out_sack_blitz == 0.25                          # the offence's view of the same plays
