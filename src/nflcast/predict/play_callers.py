"""Display only (user request 2026-11-11): who calls the plays for each team, shown on game pages.

Source: Sam Hoppen's play-caller dataset (github.com/samhoppen/NFL_public, data/all_playcallers.csv, with Arif Hasan):
offensive play caller, defensive play caller and head coach per team and game, 1999 on. No licence is stated, so the file
is kept in data/raw/playcallers/<retrieved>/ (local and the private backup, with meta.json: commit, time, sha256) and
credited on the site; only the names shown per game reach the public site data.

The file already lists the rest of 2026 (future weeks are assumptions, and it says nothing about when a change was
announced), so only rows for games that are FINAL in our schedule are used: a finished game shows its own row, an
upcoming game the team's latest finished game of the season. "Since week N" marks a caller who took over during the
season (after the team's first game). Not a model input: the frozen models do not use coaching data (B19 in
docs/research_2027.md is the 2027 test).
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from nflcast.config import ROOT

SRC_DIR = ROOT / "data" / "raw" / "playcallers"
FILE = "all_playcallers.csv"
ROLES = (("offence", "off_play_caller"), ("defence", "def_play_caller"))


def latest_file(src_dir: Path = SRC_DIR) -> Path | None:
    c = sorted(src_dir.glob(f"*/{FILE}"))
    return c[-1] if c else None


def load(src_dir: Path = SRC_DIR) -> pl.DataFrame | None:
    f = latest_file(src_dir)
    if f is None:
        return None
    return pl.read_csv(f, infer_schema_length=0, encoding="utf8").select(
        pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32), "team", "game_id",
        "off_play_caller", "def_play_caller", "head_coach")


def prepare(pc: pl.DataFrame, games: pl.DataFrame) -> dict:
    """{(team, season): [rows of FINISHED games, oldest first]} with kickoff times from our schedule."""
    fin = games.filter(pl.col("status") == "final").select("game_id", "kickoff_utc")
    rows = pc.join(fin, on="game_id", how="inner").sort("kickoff_utc")
    out: dict = {}
    for r in rows.iter_rows(named=True):
        out.setdefault((r["team"], int(r["season"])), []).append(r)
    return out


def for_game(P: dict, team: str, season: int, game_id: str, kickoff) -> dict | None:
    """Play callers for one team in one game, from finished games only (this game's own row once it is final)."""
    played = [r for r in P.get((team, season), []) if r["kickoff_utc"] <= kickoff]
    if not played:
        return None
    cur = played[-1]
    out = {"based_on": "this_game" if cur["game_id"] == game_id else "last_game", "as_of_week": int(cur["week"])}
    for role, col in ROLES:
        name = (cur[col] or "").strip() or None
        i = len(played) - 1
        while i > 0 and played[i - 1][col] == cur[col]:
            i -= 1
        out[role] = {"name": name, "head_coach": bool(name and name == (cur["head_coach"] or "").strip()),
                     "since_week": int(played[i]["week"]) if i > 0 else None,
                     "replaced": ((played[i - 1][col] or "").strip() or None) if i > 0 else None}
    return out
