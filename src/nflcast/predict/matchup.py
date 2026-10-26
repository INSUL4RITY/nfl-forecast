"""Matchup detail for game pages (display only; user request 2026-10-22). Not a model input; the frozen model and the
picks are untouched.

For every game of the current season: both teams' season-to-date unit statistics AS OF THAT GAME'S KICKOFF (completed
regular-season games before it), 32-team ranks, offence-vs-defence matchups with an edge label, play style in neutral
situations, and a game log with each game's starting quarterback. Computed from nflverse play-by-play with the standard
nflfastR definitions:

  plays          scrimmage snaps: dropbacks (incl. sacks and scrambles) and designed runs; no kneels, spikes,
                 no-plays (penalties) or two-point tries; EPA must be present
  EPA / play     mean EPA on those plays; a defence's figure is the EPA its opponents gained (lower is better)
  passing        EPA per dropback;  rushing: EPA per designed run (scrambles count as dropbacks)
  success        share of plays with EPA > 0
  explosive      share of plays that were a pass attempt gaining 20+ yards or a run (scrambles included) gaining 10+
  sack rate      sacks per dropback (offence: lower is better; defence: higher is better)
  third down     share of third-down plays that gained a first down by rush or pass, or a touchdown (first downs
                 by penalty are not conversions)
  red zone       share of drives reaching the opponent's 20 that ended in an offensive touchdown
  points/drive   offensive points (touchdowns, conversions, field goals) per drive with at least one scrimmage play
  neutral        1st or 2nd down, quarters 1-3, the offence's win probability between 20% and 80%
  adjusted       opponent-adjusted EPA per play: a team's offensive EPA minus how much easier than average its
                 opponents' defences have been (their season EPA allowed vs the league average), and the same for
                 defence; one pass, season to date
  tempo          game-clock seconds from the previous snap to this one, in neutral situations, counted only when the
                 previous play left the clock running (same drive and quarter; not after an incompletion or a play
                 out of bounds; gaps over 60 s, e.g. timeouts or reviews, are left out)
"""

from __future__ import annotations

from datetime import datetime

import polars as pl

EDGE_RANKS = 8          # a matchup row is an "edge" when one side ranks at least this many places better

# (key, label, unit, offence column, defence column, higher-is-better for the OFFENCE)
UNIT_ROWS = [
    ("passing", "Passing efficiency", "EPA per dropback", "db_epa", "def_db_epa", True),
    ("rushing", "Rushing efficiency", "EPA per designed run", "rush_epa", "def_rush_epa", True),
    ("success", "Play success", "Share of plays with positive EPA", "success", "def_success", True),
    ("explosive", "Explosive plays", "20+ yard passes, 10+ yard runs", "explosive", "def_explosive", True),
    ("sacks", "Protection vs pass rush", "Sacks per dropback", "sack_rate", "def_sack_rate", False),
    ("third", "Third down", "Conversion rate", "third", "def_third", True),
    ("redzone", "Red zone", "Drives inside the 20 ending in a touchdown", "redzone", "def_redzone", True),
    ("ppd", "Points per drive", "Offensive points per drive", "ppd", "def_ppd", True),
]
# columns where a LOWER value is better for the team the column describes
LOWER_BETTER = {"sack_rate", "def_epa", "def_db_epa", "def_rush_epa", "def_success", "def_explosive", "def_third",
                "def_redzone", "def_ppd"}


def plays_frame(pbp: pl.DataFrame) -> pl.DataFrame:
    """Scrimmage plays with the flags used below (one row per play, offence = posteam)."""
    p = pbp.filter(pl.col("posteam").is_not_null() & pl.col("defteam").is_not_null()).sort("game_id", "play_id")
    scrim = (((pl.col("qb_dropback") == 1) | (pl.col("rush") == 1)) & (pl.col("qb_kneel").fill_null(0) == 0)
             & (pl.col("qb_spike").fill_null(0) == 0) & (pl.col("play_type") != "no_play")
             & (pl.col("two_point_attempt").fill_null(0) == 0) & pl.col("epa").is_not_null())
    own_td = (pl.col("touchdown").fill_null(0) == 1) & (pl.col("td_team") == pl.col("posteam"))
    p = p.with_columns(
        is_play=scrim,
        is_db=scrim & (pl.col("qb_dropback") == 1),
        is_rush=scrim & (pl.col("qb_dropback").fill_null(0) == 0) & (pl.col("rush") == 1),
        own_td=own_td,
        pts=(own_td.cast(pl.Int32) * 6 + (pl.col("extra_point_result") == "good").fill_null(False).cast(pl.Int32)
             + (pl.col("two_point_conv_result") == "success").fill_null(False).cast(pl.Int32) * 2
             + (pl.col("field_goal_result") == "made").fill_null(False).cast(pl.Int32) * 3),
        neutral=(pl.col("down").is_in([1, 2]) & (pl.col("qtr") <= 3) & pl.col("wp").is_between(0.2, 0.8)).fill_null(False),
    )
    # tempo: seconds since the previous snap (scrimmage or penalty) of the same drive and quarter, only when that
    # previous play left the clock running
    snaps = p.filter(pl.col("play_type").is_in(["pass", "run", "no_play"]))
    w = ["game_id", "fixed_drive", "qtr"]
    snaps = snaps.with_columns(
        gap=(pl.col("game_seconds_remaining").shift(1) - pl.col("game_seconds_remaining")).over(w),
        prev_stopped=((pl.col("incomplete_pass").fill_null(0) == 1) | (pl.col("out_of_bounds").fill_null(0) == 1)).shift(1).over(w))
    snaps = snaps.with_columns(gap=pl.when(pl.col("prev_stopped").fill_null(True)).then(None).otherwise(pl.col("gap")))
    p = p.join(snaps.select("game_id", "play_id", "gap"), on=["game_id", "play_id"], how="left")
    return p


def team_games(pbp: pl.DataFrame, games: pl.DataFrame) -> pl.DataFrame:
    """One row per (game_id, team) with offensive sums and the opponent's offensive sums as defensive sums.
    games: game_id, season, week, game_type, kickoff_utc, home_team, away_team (final games of the season)."""
    p = plays_frame(pbp)
    g = p.filter(pl.col("is_play"))
    off = g.group_by("game_id", "posteam").agg(
        plays=pl.len(), epa_sum=pl.col("epa").sum(), succ=(pl.col("epa") > 0).sum(),
        db=pl.col("is_db").sum(), db_epa_sum=pl.col("epa").filter(pl.col("is_db")).sum(),
        rush_n=pl.col("is_rush").sum(), rush_epa_sum=pl.col("epa").filter(pl.col("is_rush")).sum(),
        expl=(((pl.col("yards_gained") >= 20) & pl.col("is_db") & (pl.col("sack").fill_null(0) == 0)
               & (pl.col("qb_scramble").fill_null(0) == 0))
              | ((pl.col("yards_gained") >= 10) & (pl.col("is_rush") | (pl.col("qb_scramble").fill_null(0) == 1)))).sum(),
        sacks=(pl.col("sack").fill_null(0) == 1).sum(),
        third_att=(pl.col("down") == 3).sum(),
        third_conv=((pl.col("down") == 3) & ((pl.col("first_down_rush").fill_null(0) == 1)
                     | (pl.col("first_down_pass").fill_null(0) == 1) | pl.col("own_td"))).sum(),
        n_db=(pl.col("neutral") & pl.col("is_db")).sum(), n_rush=(pl.col("neutral") & pl.col("is_rush")).sum(),
        tempo_sum=pl.col("gap").filter(pl.col("neutral") & pl.col("gap").is_between(1, 60)).sum(),
        tempo_n=pl.col("gap").filter(pl.col("neutral") & pl.col("gap").is_between(1, 60)).len(),
    )
    # drives: those with at least one scrimmage play; points include conversions and field goals
    dp = p.filter(pl.col("fixed_drive").is_not_null()).group_by("game_id", "posteam", "fixed_drive").agg(
        has_play=pl.col("is_play").any(), pts=pl.col("pts").sum(), td=pl.col("own_td").any(),
        rz=(pl.col("is_play") & (pl.col("yardline_100") <= 20)).any())
    dp = dp.filter(pl.col("has_play")).group_by("game_id", "posteam").agg(
        drives=pl.len(), drive_pts=pl.col("pts").sum(), rz_trips=pl.col("rz").sum(), rz_tds=(pl.col("rz") & pl.col("td")).sum())
    off = off.join(dp, on=["game_id", "posteam"], how="left").rename({"posteam": "team"}).with_columns(
        pl.col("drives", "drive_pts", "rz_trips", "rz_tds").fill_null(0))
    sums = [c for c in off.columns if c not in ("game_id", "team")]
    gm = pl.concat([
        games.select("game_id", "season", "week", "kickoff_utc", pl.col("home_team").alias("team"), pl.col("away_team").alias("opp"),
                     pl.lit(True).alias("is_home"), pl.col("home_score").alias("pf"), pl.col("away_score").alias("pa")),
        games.select("game_id", "season", "week", "kickoff_utc", pl.col("away_team").alias("team"), pl.col("home_team").alias("opp"),
                     pl.lit(False).alias("is_home"), pl.col("away_score").alias("pf"), pl.col("home_score").alias("pa"))])
    out = gm.join(off, on=["game_id", "team"], how="inner")
    opp = off.rename({c: f"d_{c}" for c in sums}).rename({"team": "opp"})
    return out.join(opp, on=["game_id", "opp"], how="inner")


def _rates(df: pl.DataFrame) -> pl.DataFrame:
    """Season-to-date rates per team from summed per-game rows."""
    ids = {"game_id", "team", "opp", "season", "week", "kickoff_utc", "is_home"}
    s = df.group_by("team").agg(games=pl.len(), *[pl.col(c).sum() for c in df.columns if c not in ids])

    def r(a: str, b: str) -> pl.Expr:
        return pl.when(pl.col(b) > 0).then(pl.col(a) / pl.col(b)).otherwise(None)
    s = s.with_columns(
        off_epa=r("epa_sum", "plays"), def_epa=r("d_epa_sum", "d_plays"),
        db_epa=r("db_epa_sum", "db"), def_db_epa=r("d_db_epa_sum", "d_db"),
        rush_epa=r("rush_epa_sum", "rush_n"), def_rush_epa=r("d_rush_epa_sum", "d_rush_n"),
        success=r("succ", "plays"), def_success=r("d_succ", "d_plays"),
        explosive=r("expl", "plays"), def_explosive=r("d_expl", "d_plays"),
        sack_rate=r("sacks", "db"), def_sack_rate=r("d_sacks", "d_db"),
        third=r("third_conv", "third_att"), def_third=r("d_third_conv", "d_third_att"),
        redzone=r("rz_tds", "rz_trips"), def_redzone=r("d_rz_tds", "d_rz_trips"),
        ppd=r("drive_pts", "drives"), def_ppd=r("d_drive_pts", "d_drives"),
        neutral_db=pl.when((pl.col("n_db") + pl.col("n_rush")) > 0).then(pl.col("n_db") / (pl.col("n_db") + pl.col("n_rush"))),
        tempo=r("tempo_sum", "tempo_n"),
    ).with_columns(net_epa=pl.col("off_epa") - pl.col("def_epa"))
    return s


RANKED = ["net_epa", "adj_net_epa", "off_epa", "def_epa", "db_epa", "def_db_epa", "rush_epa", "def_rush_epa", "success", "def_success",
          "explosive", "def_explosive", "sack_rate", "def_sack_rate", "third", "def_third", "redzone", "def_redzone",
          "ppd", "def_ppd"]


def season_to_date(tg: pl.DataFrame, season: int, cutoff: datetime) -> pl.DataFrame:
    """Rates and 1-based ranks (1 = best) for every team with at least one game before `cutoff` in `season`."""
    played = tg.filter((pl.col("season") == season) & (pl.col("kickoff_utc") < cutoff))
    s = _rates(played)
    if s.height == 0:
        return s
    # opponent adjustment: average quality of the units each team has faced (game-weighted), relative to the league
    lo, ld = s["off_epa"].mean(), s["def_epa"].mean()
    opp = played.select("team", "opp").join(s.select(pl.col("team").alias("opp"), pl.col("off_epa").alias("o_off"),
                                                     pl.col("def_epa").alias("o_def")), on="opp", how="left")
    faced = opp.group_by("team").agg(faced_def=pl.col("o_def").mean(), faced_off=pl.col("o_off").mean())
    s = s.join(faced, on="team", how="left").with_columns(
        adj_off_epa=pl.col("off_epa") - (pl.col("faced_def") - ld),
        adj_def_epa=pl.col("def_epa") - (pl.col("faced_off") - lo),
    ).with_columns(adj_net_epa=pl.col("adj_off_epa") - pl.col("adj_def_epa"))
    ranks = []
    for c in RANKED:
        desc = c not in LOWER_BETTER and c != "sack_rate"
        if c == "def_sack_rate":
            desc = True
        ranks.append(pl.col(c).rank(method="min", descending=desc).cast(pl.Int32).alias(f"{c}_rank"))
    return s.with_columns(ranks)


def _edge(off_rank: int | None, def_rank: int | None) -> str:
    if off_rank is None or def_rank is None:
        return "none"
    if def_rank - off_rank >= EDGE_RANKS:
        return "offence"
    if off_rank - def_rank >= EDGE_RANKS:
        return "defence"
    return "even"


def _r(x, n=4):
    return None if x is None else round(float(x), n)


def game_detail(tg: pl.DataFrame, game: dict, starters: dict, expected_qb: dict | None) -> dict | None:
    """The matchup detail for one game: `game` has game_id, season, kickoff_utc (datetime), home_team, away_team.
    `starters`: {(game_id, team): qb name}; `expected_qb`: {"home": name, "away": name} from the forecast (or None)."""
    ko = game["kickoff_utc"]
    S = season_to_date(tg, game["season"], ko)
    teams = {"home": game["home_team"], "away": game["away_team"]}
    if S.height == 0 or any(S.filter(pl.col("team") == t).height == 0 for t in teams.values()):
        return {"available": False, "n_teams": S.height}
    row = {side: S.filter(pl.col("team") == t).row(0, named=True) for side, t in teams.items()}
    league = {c: _r(S[c].mean()) for c in RANKED + ["neutral_db", "tempo"]}
    hist = tg.filter((pl.col("season") == game["season"]) & (pl.col("kickoff_utc") < ko)).sort("kickoff_utc")
    out = {"available": True, "n_teams": S.height, "league": league, "teams": {}, "units": {}, "log": {}}
    for side, t in teams.items():
        r = row[side]
        games_t = hist.filter(pl.col("team") == t)
        last3 = games_t.tail(3)
        l3 = ((last3["epa_sum"].sum() / last3["plays"].sum()) - (last3["d_epa_sum"].sum() / last3["d_plays"].sum())
              if last3.height else None)
        log = []
        for gr in games_t.iter_rows(named=True):
            qb = starters.get((gr["game_id"], t))
            exp = (expected_qb or {}).get(side)
            log.append({"week": gr["week"], "opp": gr["opp"], "home": gr["is_home"],
                        "net_epa": _r(gr["epa_sum"] / gr["plays"] - gr["d_epa_sum"] / gr["d_plays"]),
                        "margin": int(gr["pf"] - gr["pa"]), "pf": int(gr["pf"]), "pa": int(gr["pa"]),
                        "qb": qb, "other_qb": bool(qb and exp and qb != exp)})
        starts: dict[str, int] = {}
        for x in log:
            if x["qb"]:
                starts[x["qb"]] = starts.get(x["qb"], 0) + 1
        out["teams"][side] = {
            "team": t, "games": int(r["games"]), "record": [int((games_t["pf"] > games_t["pa"]).sum()),
                                                            int((games_t["pf"] < games_t["pa"]).sum()),
                                                            int((games_t["pf"] == games_t["pa"]).sum())],
            "net_epa": _r(r["net_epa"]), "off_epa": _r(r["off_epa"]), "def_epa": _r(r["def_epa"]), "ppd": _r(r["ppd"], 3),
            "adj_net_epa": _r(r["adj_net_epa"]), "adj_off_epa": _r(r["adj_off_epa"]), "adj_def_epa": _r(r["adj_def_epa"]),
            "def_ppd": _r(r["def_ppd"], 3), "last3_net_epa": _r(l3),
            "ranks": {c: r[f"{c}_rank"] for c in RANKED},
            "neutral_db": _r(r["neutral_db"]), "tempo": _r(r["tempo"], 2),
            "qb_starts": sorted(({"qb": k, "games": v} for k, v in starts.items()), key=lambda x: -x["games"]),
            "expected_qb": (expected_qb or {}).get(side),
        }
        out["log"][side] = log
    for off_side, def_side in (("away", "home"), ("home", "away")):
        rows = []
        for key, label, unit, oc, dc, _hb in UNIT_ROWS:
            o, d = row[off_side], row[def_side]
            orank, drank = o[f"{oc}_rank"], d[f"{dc}_rank"]
            rows.append({"key": key, "label": label, "unit": unit, "off_value": _r(o[oc]), "off_rank": orank,
                         "def_value": _r(d[dc]), "def_rank": drank, "edge": _edge(orank, drank)})
        out["units"][f"{off_side}_offence"] = rows
    return out


def build(season: int, games: pl.DataFrame, pbp: pl.DataFrame, qb_games: pl.DataFrame, names: dict) -> tuple[pl.DataFrame, dict]:
    """Per-team-game table for `season` (completed games, playoffs included: a playoff game's season to date is every
    earlier game) and {(game_id, team): starting QB name}."""
    done = games.filter((pl.col("season") == season) & (pl.col("status") == "final"))
    tg = team_games(pbp.filter(pl.col("game_id").is_in(done["game_id"].to_list())), done)
    st = qb_games.filter(pl.col("is_starter") == True)  # noqa: E712
    starters = {(r["game_id"], r["team"]): names.get(r["qb_id"]) for r in st.iter_rows(named=True)}   # never show an ID
    return tg, starters
