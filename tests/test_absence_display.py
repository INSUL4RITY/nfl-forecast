"""Who is missing (predict/absence_display.py; display only, user authorisation 2026-11-20, item B1)."""

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import polars as pl

from nflcast.features import injury_versions as IV
from nflcast.predict import absence_display as AD

KO = datetime(2026, 11, 20, 1, 15, tzinfo=timezone.utc)


def _inj(rows):
    return pl.DataFrame(rows, schema={"week": pl.Int32, "team": pl.Utf8, "gsis_id": pl.Utf8, "full_name": pl.Utf8,
                                      "position": pl.Utf8, "report_status": pl.Utf8, "practice_status": pl.Utf8})


def _fake_tables(monkeypatch, shares):
    monkeypatch.setattr(AD.RL, "_share", lambda s, u, team, gid, weeks: {"share": shares.get(gid, 0.0)})
    monkeypatch.setattr(AD.RL, "team_list", lambda P, team, week: {"players": [
        {"player": "Res Player", "pos": "LB", "list": "Injured reserve", "specialist": False,
         "this_season": {"share": 0.9}, "last_season": None},
        {"player": "Listed Too", "pos": "LB", "list": "Injured reserve, designated to return", "specialist": False,
         "this_season": {"share": 0.7}, "last_season": None}]})
    monkeypatch.setattr(AD.RM, "team_moves", lambda P, team, week: {"departures": [
        {"player": "Traded Guy", "pos": "WR", "move": "Now with KC", "share": 0.7},
        {"player": "PS Guy", "pos": "WR", "move": "Practice squad", "share": 0.3}], "arrivals": [], "specialists": []})
    return {"s": None, "unit": None}, {"r": None}


def test_game_statuses_listed_practice_rows_only_before_statuses(monkeypatch):
    rl, rm = _fake_tables(monkeypatch, {"a": 0.9, "b": 0.8, "c": 0.1, "d": 0.6, "q": 0.95, "e": 0.5})
    inj = _inj([
        {"week": 11, "team": "IND", "gsis_id": "a", "full_name": "A Tackle", "position": "T", "report_status": "Out", "practice_status": "Did Not Participate In Practice"},
        {"week": 11, "team": "IND", "gsis_id": "b", "full_name": "B Corner", "position": "CB", "report_status": "Questionable", "practice_status": "Limited Participation in Practice"},
        {"week": 11, "team": "IND", "gsis_id": "c", "full_name": "C Backup", "position": "G", "report_status": "Out", "practice_status": None},
        {"week": 11, "team": "IND", "gsis_id": "d", "full_name": "D Healthy", "position": "WR", "report_status": None, "practice_status": "Full Participation in Practice"},
        {"week": 11, "team": "IND", "gsis_id": "q", "full_name": "Q Back", "position": "QB", "report_status": "Out", "practice_status": None},
        {"week": 11, "team": "IND", "gsis_id": "e", "full_name": "Listed Too", "position": "LB", "report_status": "Questionable", "practice_status": None},
    ])
    t = AD.team_absences("IND", 11, inj, rl, rm)
    names = [p["player"] for p in t["players"]]
    assert names[:2] == ["A Tackle", "B Corner"]              # report rows first, by share
    assert "C Backup" not in names and t["others"] >= 1        # under 20% of snaps: counted, not listed
    assert "D Healthy" not in names                            # no game status once statuses exist
    assert "Q Back" not in names                               # quarterbacks are covered elsewhere
    assert names.count("Listed Too") == 1                      # on the report and a reserve list: shown once
    assert "Traded Guy" in names and "PS Guy" not in names     # traded/released only
    assert {p["unit"] for p in t["players"]} <= set(AD.UNIT_TEXT.values())


def test_practice_rows_shown_while_no_game_statuses(monkeypatch):
    rl, rm = _fake_tables(monkeypatch, {"a": 0.9, "d": 0.6})
    inj = _inj([
        {"week": 11, "team": "IND", "gsis_id": "a", "full_name": "A Tackle", "position": "T", "report_status": None, "practice_status": "Did Not Participate In Practice"},
        {"week": 11, "team": "IND", "gsis_id": "d", "full_name": "D Healthy", "position": "WR", "report_status": None, "practice_status": "Full Participation in Practice"},
    ])
    t = AD.team_absences("IND", 11, inj, rl, rm)
    rep = [p for p in t["players"] if p["kind"] == "injury report"]
    assert [(p["player"], p["status"]) for p in rep] == [("A Tackle", "Did not practise (no game status yet)")]


def test_only_big_gap_games(monkeypatch):
    lp = {"line_home_spread": -12.5, "stats_only": {"margin": 10.0}, "generated_at": (KO - timedelta(days=1)).isoformat()}
    assert AD.game_absences({"season": 2026, "week": 11, "kickoff_utc": KO, "home_id": "HOU", "away_id": "IND"},
                            lp, KO, {}, {}, {}) is None          # gap 2.5: not a Big gap
    assert AD.gap_of({"line_home_spread": -12.5, "stats_only": {"margin": 7.71}}) == 7.71 - 12.5


def test_final_statuses_at_lock(monkeypatch):
    early = _inj([{"week": 11, "team": "IND", "gsis_id": "a", "full_name": "A", "position": "T", "report_status": None, "practice_status": "Did Not Participate In Practice"}])
    late = _inj([{"week": 11, "team": "IND", "gsis_id": "a", "full_name": "A", "position": "T", "report_status": "Out", "practice_status": "Did Not Participate In Practice"}])
    lock = KO - timedelta(hours=29)
    monkeypatch.setattr("nflcast.data.sources.snapshot_asof", lambda src, season, t: ((early if t <= lock else late), {}))
    assert IV.final_statuses_at(2026, 11, "IND", lock, KO) is False      # statuses arrived after the lock
    assert IV.final_statuses_at(2026, 11, "IND", KO, KO) is True
    monkeypatch.setattr("nflcast.data.sources.snapshot_asof", lambda src, season, t: (early, {}))
    assert IV.final_statuses_at(2026, 11, "IND", lock, KO) is False      # none in the data yet


def test_no_codes_or_ids_and_export_only(monkeypatch):
    rl, rm = _fake_tables(monkeypatch, {"a": 0.9})
    inj = _inj([{"week": 11, "team": "IND", "gsis_id": "00-0012345", "full_name": "A Tackle", "position": "T",
                 "report_status": "Out", "practice_status": None}])
    monkeypatch.setattr(AD.RL, "_share", lambda s, u, team, gid, weeks: {"share": 0.9})
    out = str(AD.team_absences("IND", 11, inj, rl, rm))
    assert not re.search(r"00-00\d+|\b[A-Z]\d{2}\b|\bRES\b|gsis|pfr", out)
    src = Path(__file__).resolve().parents[1] / "src" / "nflcast" / "predict"
    assert "absence_display" not in (src / "release.py").read_text(encoding="utf-8")
    assert "absence_display" in (src / "export_web.py").read_text(encoding="utf-8-sig")
