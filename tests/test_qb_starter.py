from datetime import datetime, timezone

import polars as pl

from nflcast.features import personnel as P

KO = datetime(2026, 11, 6, 0, 15, tzinfo=timezone.utc)
GAMES = pl.DataFrame({"game_id": ["G"], "season": [2026], "week": [9], "kickoff_utc": [KO]})


def _pbp(passers: list[str]) -> pl.DataFrame:
    n = len(passers)
    return pl.DataFrame({"game_id": ["G"] * n, "posteam": ["BAL"] * n, "play_id": list(range(1, n + 1)),
                         "qb_dropback": [1] * n, "qb_spike": [0] * n, "passer_id": passers,
                         "play_type": ["pass"] * n, "epa": [0.1] * n})


def _starter(qbg: pl.DataFrame) -> str:
    return qbg.filter(pl.col("is_starter"))["qb_id"].to_list()


def test_trick_play_pass_by_a_running_back_is_not_the_starter():
    qbg = P.qb_games(_pbp(["henry"] + ["fagnano"] * 20), GAMES, {"henry": "RB", "fagnano": "QB"})
    assert _starter(qbg) == ["fagnano"]
    assert qbg.filter(pl.col("qb_id") == "henry")["db"].to_list() == [1]      # his dropback still counts as his


def test_non_qb_who_really_played_quarterback_is_still_the_starter():
    qbg = P.qb_games(_pbp(["hill"] * 11 + ["winston"] * 3), GAMES, {"hill": "TE", "winston": "QB"})
    assert _starter(qbg) == ["hill"]


def test_injured_qb_with_few_dropbacks_keeps_the_start_and_fallback_when_nobody_is_eligible():
    assert _starter(P.qb_games(_pbp(["qb1"] * 2 + ["qb2"] * 30), GAMES, {"qb1": "QB", "qb2": "QB"})) == ["qb1"]
    assert _starter(P.qb_games(_pbp(["wr"] * 2 + ["rb"] * 1), GAMES, {"wr": "WR", "rb": "RB"})) == ["wr"]


def test_qb_change_feature_uses_the_real_starter():
    """The QB-change input compares the expected starter with the previous game's starter (QBModel.previous_starter)."""
    qbg = P.qb_games(_pbp(["henry"] + ["fagnano"] * 20), GAMES, {"henry": "RB", "fagnano": "QB"})
    qbm = P.QBModel(qbg)
    later = int(datetime(2026, 11, 13, tzinfo=timezone.utc).timestamp() * 1_000_000)
    assert qbm.previous_starter("BAL", later) == "fagnano"
