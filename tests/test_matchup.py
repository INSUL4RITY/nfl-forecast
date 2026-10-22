"""Matchup detail (display only): definitions on a hand-built play-by-play, as-of cut-offs, ranks, edges, QB labels."""

from datetime import datetime, timedelta, timezone

import polars as pl

from nflcast.predict import matchup as MU

KO1 = datetime(2026, 9, 10, 17, 0, tzinfo=timezone.utc)


def play(pid, off, de, **k):
    base = {"game_id": "g1", "play_id": pid, "posteam": off, "defteam": de, "play_type": "pass", "qb_dropback": 1,
            "qb_scramble": 0, "rush": 0, "sack": 0, "qb_kneel": 0, "qb_spike": 0, "two_point_attempt": 0, "epa": 0.0,
            "yards_gained": 5, "down": 1, "first_down_rush": 0, "first_down_pass": 0, "touchdown": 0, "td_team": None,
            "yardline_100": 60, "fixed_drive": 1, "qtr": 1, "wp": 0.5, "game_seconds_remaining": 3600 - pid,
            "extra_point_result": None, "two_point_conv_result": None, "field_goal_result": None,
            "incomplete_pass": 0, "out_of_bounds": 0}
    base.update(k)
    return base


def pbp_one_game():
    rows = [
        # drive 1 (A): dropback +1.0 (20-yd pass, explosive), designed run -0.5, scramble 12 yds +0.4 (explosive run),
        # 3rd down: conversion by penalty only (not a conversion), then a 3rd-down pass that converts, TD + XP (7 pts)
        play(1, "A", "B", epa=1.0, yards_gained=20, game_seconds_remaining=3590),
        play(2, "A", "B", play_type="run", qb_dropback=0, rush=1, epa=-0.5, yards_gained=2, game_seconds_remaining=3560),
        play(3, "A", "B", play_type="run", qb_scramble=1, epa=0.4, yards_gained=12, game_seconds_remaining=3530),
        play(4, "A", "B", down=3, epa=0.2, yards_gained=3, first_down_pass=0, game_seconds_remaining=3500),  # penalty 1st down
        play(5, "A", "B", down=3, epa=0.8, yards_gained=15, first_down_pass=1, yardline_100=15, game_seconds_remaining=3490,
             incomplete_pass=0),
        play(6, "A", "B", epa=2.0, yards_gained=15, touchdown=1, td_team="A", yardline_100=15, game_seconds_remaining=3480),
        play(7, "A", "B", play_type="extra_point", qb_dropback=0, epa=0.0, extra_point_result="good", game_seconds_remaining=3480),
        # excluded plays: kneel, penalty no-play, two-point try
        play(8, "A", "B", play_type="qb_kneel", qb_dropback=0, rush=1, qb_kneel=1, epa=-0.1, fixed_drive=3),
        play(9, "A", "B", play_type="no_play", epa=0.3, fixed_drive=3),
        play(10, "A", "B", two_point_attempt=1, epa=0.5, fixed_drive=3),
        # drive 2 (B): sack -1.5, then an incomplete pass, then a FG (3 pts); a red-zone trip without a TD
        play(11, "B", "A", sack=1, epa=-1.5, yards_gained=-7, fixed_drive=2, yardline_100=18, game_seconds_remaining=3400),
        play(12, "B", "A", epa=-0.3, yards_gained=0, incomplete_pass=1, fixed_drive=2, yardline_100=25, game_seconds_remaining=3395),
        play(13, "B", "A", epa=0.1, yards_gained=6, fixed_drive=2, yardline_100=19, game_seconds_remaining=3392),
        play(14, "B", "A", play_type="field_goal", qb_dropback=0, epa=0.0, field_goal_result="made", fixed_drive=2,
             game_seconds_remaining=3360),
    ]
    return pl.DataFrame(rows)


def games_one():
    return pl.DataFrame({"game_id": ["g1"], "season": [2026], "week": [1], "game_type": ["REG"], "status": ["final"],
                         "kickoff_utc": [KO1], "home_team": ["A"], "away_team": ["B"], "home_score": [7], "away_score": [3]})


def test_definitions_on_a_hand_built_game():
    tg = MU.team_games(pbp_one_game(), games_one())
    a = tg.filter(pl.col("team") == "A").row(0, named=True)
    assert a["plays"] == 6                              # kneel, no-play and two-point try are excluded
    assert abs(a["epa_sum"] - 3.9) < 1e-9 and a["succ"] == 5
    assert a["db"] == 5 and a["rush_n"] == 1            # the scramble counts as a dropback, not a designed run
    assert a["expl"] == 2                               # 20-yd pass + 12-yd scramble; the 15-yd 3rd-down pass is not
    assert a["third_att"] == 2 and a["third_conv"] == 1  # a first down by penalty is not a conversion
    assert a["drives"] == 1 and a["drive_pts"] == 7 and a["rz_trips"] == 1 and a["rz_tds"] == 1
    b = tg.filter(pl.col("team") == "B").row(0, named=True)
    assert b["sacks"] == 1 and b["drives"] == 1 and b["drive_pts"] == 3 and b["rz_trips"] == 1 and b["rz_tds"] == 0
    assert a["d_sacks"] == 1 and b["d_sacks"] == 0 and a["d_drive_pts"] == 3   # defence = the opponent's offence
    # tempo: gaps after a play that left the clock running only (none after B's incompletion)
    assert a["tempo_n"] == 3 and abs(a["tempo_sum"] - (30 + 30 + 10)) < 1e-9     # 3rd downs are not neutral
    assert b["tempo_n"] == 1 and abs(b["tempo_sum"] - 5) < 1e-9


def _two_games():
    g1 = pbp_one_game()
    g2 = g1.with_columns(game_id=pl.lit("g2"),
                         posteam=pl.when(pl.col("posteam") == "A").then(pl.lit("C")).otherwise(pl.lit("A")),
                         defteam=pl.when(pl.col("defteam") == "A").then(pl.lit("C")).otherwise(pl.lit("A")),
                         td_team=pl.when(pl.col("td_team") == "A").then(pl.lit("C")).otherwise(pl.col("td_team")))
    games = pl.concat([games_one(), pl.DataFrame({
        "game_id": ["g2"], "season": [2026], "week": [2], "game_type": ["REG"], "status": ["final"],
        "kickoff_utc": [KO1 + timedelta(days=7)], "home_team": ["C"], "away_team": ["A"], "home_score": [7], "away_score": [3]})])
    return pl.concat([g1, g2]), games


def test_as_of_cutoff_ranks_edges_and_qb_labels():
    pbp, games = _two_games()
    tg = MU.team_games(pbp, games)
    # before week 2's kickoff only week 1 counts: A has 1 game, C has none -> not available for an A-vs-C game
    wk2 = {"game_id": "g2", "season": 2026, "kickoff_utc": KO1 + timedelta(days=7), "home_team": "C", "away_team": "A"}
    assert MU.game_detail(tg, wk2, {}, None)["available"] is False
    later = {**wk2, "game_id": "g3", "kickoff_utc": KO1 + timedelta(days=14)}
    starters = {("g1", "A"): "QB One", ("g2", "A"): "QB Two", ("g2", "C"): "QB C"}
    d = MU.game_detail(tg, later, starters, {"away": "QB One", "home": "QB C"})
    assert d["available"] and d["teams"]["away"]["games"] == 2 and d["teams"]["home"]["games"] == 1
    log = d["log"]["away"]
    assert [x["qb"] for x in log] == ["QB One", "QB Two"] and [x["other_qb"] for x in log] == [False, True]
    assert d["teams"]["away"]["qb_starts"] == [{"qb": "QB One", "games": 1}, {"qb": "QB Two", "games": 1}]
    S = MU.season_to_date(tg, 2026, later["kickoff_utc"])
    best_off = S.sort("off_epa", descending=True)["team"][0]
    assert S.filter(pl.col("team") == best_off)["off_epa_rank"][0] == 1
    low_sack = S.sort("sack_rate")["team"][0]
    assert S.filter(pl.col("team") == low_sack)["sack_rate_rank"][0] == 1      # fewer sacks taken ranks better
    hi_rush = S.sort("def_sack_rate", descending=True)["team"][0]
    assert S.filter(pl.col("team") == hi_rush)["def_sack_rate_rank"][0] == 1   # more sacks generated ranks better
    assert MU._edge(2, 20) == "offence" and MU._edge(20, 2) == "defence" and MU._edge(5, 9) == "even"
    assert MU._edge(None, 3) == "none"
