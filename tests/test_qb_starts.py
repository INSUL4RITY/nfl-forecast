"""Team analytics: the starting quarterback is the passer of the first dropback, not the one with the most."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "team_analytics"))
import context as ctx  # noqa: E402


def plays(game, week, seq):
    """seq: passer ids in play order for team A."""
    return [{"game_id": game, "week": week, "play_id": i, "posteam": "A", "passer_id": q, "db": True} for i, q in enumerate(seq)]


def test_starter_hurt_early_keeps_the_start():
    p = pd.DataFrame(plays("g1", 1, ["starter"] * 30) + plays("g2", 2, ["starter"] + ["backup"] * 25))
    s = ctx.qb_starts(p)
    assert s.passer_id.tolist() == ["starter", "starter"] and s.week.tolist() == [1, 2]


def test_trick_play_passer_is_not_a_starter():
    p = pd.DataFrame(plays("g1", 1, ["receiver"] + ["starter"] * 20))
    assert ctx.qb_starts(p).passer_id.tolist() == ["starter"]


def test_one_row_per_team_game():
    p = pd.DataFrame(plays("g1", 1, ["a"] * 10) + plays("g2", 2, ["b"] * 10) + plays("g3", 3, ["a"] * 10))
    s = ctx.qb_starts(p)
    assert len(s) == 3 and s.groupby("passer_id").size().to_dict() == {"a": 2, "b": 1}
