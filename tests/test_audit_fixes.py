"""Team analytics: fixes from the November 2026 audit (one block per item)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "team_analytics"))
import build_html as bh  # noqa: E402
import reliability as rel  # noqa: E402


# ---- item 1: player tables rank on usage only; efficiency carries a reliability badge
def test_reliability_levels():
    assert rel.level(0.6) == "High" and rel.level(0.5) == "High"
    assert rel.level(0.3) == "Medium" and rel.level(0.2) == "Medium"
    assert rel.level(0.05) == "Low" and rel.level(None) is None and rel.level(float("nan")) is None


def test_player_efficiency_is_low_on_small_samples():
    assert rel.player_kept("carry", 10) < 0.05 and rel.level(rel.player_kept("carry", 10)) == "Low"
    assert rel.player_kept("carry", 10) < rel.player_kept("carry", 80) < rel.player_kept("carry", 250)
    assert rel.player_kept("target_TE", 80) == rel.player_kept("target_WR", 80)     # thin TE fit replaced by the WR fit
    assert rel.player_kept("carry", 0) is None


def test_player_tables_rank_usage_only():
    eff = bh.player_col_rule({"k": "epa_car", "l": "EPA/carry", "f": "epa", "d": 1, "t": ""})
    assert eff["d"] == 0 and eff["b"] == "rel_car"
    tgt = bh.player_col_rule({"k": "yac_pr", "l": "YAC/rec.", "f": "n1", "d": 1, "t": ""})
    assert tgt["d"] == 0 and tgt["b"] == "rel_tgt"
    prod = bh.player_col_rule({"k": "rush_yds", "l": "Rush yds", "f": "int", "d": 1, "t": ""})
    assert prod["d"] == 0 and "b" not in prod
    use = bh.player_col_rule({"k": "car_share", "l": "Carry share", "f": "pct", "d": 1, "t": ""})
    assert use["d"] == 1 and "b" not in use
