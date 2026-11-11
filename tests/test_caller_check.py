"""Team analytics: the play-caller cross-check (no network)."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "team_analytics"))
import caller_check as cc  # noqa: E402

CFG = {"teams": {
    "AAA": {"hc": "Head One", "off": {"caller": "Off One", "conf": "confirmed"}, "def": {"caller": "New Dc", "conf": "confirmed",
            "changes": [{"from_week": 3, "caller": "New Dc", "previous": "Old Dc"}]}},
    "LA": {"hc": "Head Two Jr.", "off": {"caller": "Off Two", "conf": "confirmed"}, "def": {"caller": "X or Y", "conf": "unclear"}},
}}


def data(aaa_def=("Old Dc", "Old Dc", "New Dc", "New Dc"), weeks=4):
    rows = []
    for w in range(1, weeks + 1):
        rows.append({"season": 2026, "week": w, "team": "AAA", "off_play_caller": "Off One", "def_play_caller": aaa_def[w - 1], "head_coach": "Head One"})
        rows.append({"season": 2026, "week": w, "team": "LAR", "off_play_caller": "Off Two", "def_play_caller": "Y", "head_coach": "Head Two"})
    return pd.DataFrame(rows)


def test_changes_apply_from_their_first_week():
    c = CFG["teams"]["AAA"]
    assert [cc.ours_at(c, "def", w) for w in (1, 2, 3, 4)] == ["Old Dc", "Old Dc", "New Dc", "New Dc"]


def test_agreement_with_suffix_and_team_code_differences():
    r = cc.compare(CFG, data(), 2026, 4)
    assert r["differences"] == [] and r["teams_missing"] == []
    assert r["checked"] == 4 * 3 + 4 * 2                       # the unclear entry is not counted
    assert r["unclear"] == [{"team": "LA", "side": "defence", "file": "X or Y", "dataset": "Y"}]
    assert "entries agree" in cc.qc_line(r, 4, "now") and "Marked unclear" in cc.qc_line(r, 4, "now")


def test_a_missed_change_is_reported_with_its_weeks():
    r = cc.compare(CFG, data(aaa_def=("Old Dc", "Old Dc", "New Dc", "Third Dc")), 2026, 4)
    assert r["differences"] == [{"team": "AAA", "side": "defence", "weeks": [4], "file": "New Dc", "dataset": "Third Dc"}]
    assert "1 difference" in cc.qc_line(r, 4, "now") and "AAA defence week 4: file New Dc, dataset Third Dc" in cc.qc_line(r, 4, "now")


def test_future_weeks_are_ignored():
    r = cc.compare(CFG, data(aaa_def=("Old Dc", "Old Dc", "New Dc", "Third Dc")), 2026, 3)
    assert r["differences"] == []


def test_failed_download_never_raises():
    def boom(*a, **k):
        raise OSError("down")
    res, line = cc.run(2026, 9, get=boom)
    assert res is None and line.startswith("Play-caller check: not checked")
