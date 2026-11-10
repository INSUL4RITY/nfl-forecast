"""Team analytics EP-scale check: flags only the revised nflfastR EP valuation (PR 618)."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "team_analytics"))
import ep_scale  # noqa: E402


def frame(n_kick=250, ep=1.98, kick_epa=0.24, tp=0.4735):
    rows = [{"play_type": "kickoff", "ep": ep, "epa": kick_epa, "two_point_conversion_prob": 0.0} for _ in range(n_kick)]
    rows += [{"play_type": "pass", "ep": ep, "epa": 0.05, "two_point_conversion_prob": tp} for _ in range(50)]
    return pd.DataFrame(rows)


def test_old_scale_is_quiet():
    assert ep_scale.problem(frame()) is None
    warn, qc = ep_scale.check({2025: frame(), 2026: frame()})
    assert warn is None and qc.startswith("EP scale: play-by-play 2025-2026")


def test_each_marker_flags_the_revised_scale():
    assert "two-point" in ep_scale.problem(frame(tp=0.49))
    assert "mean EP" in ep_scale.problem(frame(ep=1.58))
    assert "kickoff EPA" in ep_scale.problem(frame(kick_epa=-0.07))


def test_kickoff_marker_only_under_the_dynamic_kickoff():
    old_rules = frame(kick_epa=0.0)            # 2021-23 kickoffs were worth about 0 EPA on the original scale
    assert ep_scale.problem(old_rules, 2022) is None
    assert "kickoff EPA" in ep_scale.problem(old_rules, 2025)


def test_too_few_kickoffs_to_judge():
    assert ep_scale.problem(frame(n_kick=20, kick_epa=-0.5)) is None


def test_warning_names_the_season():
    warn, qc = ep_scale.check({2025: frame(), 2026: frame(tp=0.49)})
    assert "2026 (two-point" in warn and "2025" not in warn.split("for ")[1].split(".")[0]
    assert qc.startswith("EP scale: WARNING")
