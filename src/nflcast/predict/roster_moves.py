"""Display only (user request 2026-10-29): each team's roster moves this season, as of a game's week.

Neither model line knows about trades, releases or signings: both rate teams from their games (QB changes are the
exception, handled by the QB module). This lists what the lines may be missing, from nflverse weekly rosters (team and
status per player per week; the nflverse trades file is not updated during the season) and PFR snap counts:
  * departures: players who took a meaningful share of a unit's snaps for the team this season (before this week) and
    are no longer on its active roster: now with another team, released, reserve list (IR, suspension, PUP), practice
    squad;
  * arrivals: players now on the active roster who were active for another team earlier this season;
  * kicker / punter changes.
Snap share = the player's snaps / the team's snaps for that unit over the team's games before this week. Roster files
only list teams playing that week (byes are missing) and often lack PFR ids, so players are matched by gsis id through
the nflverse players table and each player's status is his latest roster row up to the game's week.
"""

from __future__ import annotations

import polars as pl

from nflcast.data.games import franchise

MIN_SHARE = 0.20                       # departures / arrivals shown from this share of a unit's snaps
SPECIALISTS = ("K", "P")
ACTIVE = ("ACT", "INA")                 # on the active roster (INA = inactive for a game, still on the roster)
STATUS_TEXT = {"RES": "Reserve list (IR, suspension or PUP)", "CUT": "Released", "DEV": "Practice squad",
               "EXE": "Exempt list", "RET": "Retired"}
OFF_ROSTER = "Not on the active roster"          # any other status code (never shown raw on the site)


def prepare(rosters: pl.DataFrame, snaps: pl.DataFrame, players: pl.DataFrame, season: int) -> dict:
    """Season tables shared by every game: weekly roster rows and per-player snaps with gsis ids."""
    r = (rosters.filter(pl.col("season") == season)
         .select("week", franchise(pl.col("team")).alias("team"), "gsis_id", "full_name", pl.col("position").alias("pos"),
                 "status")
         .drop_nulls("gsis_id").unique(["week", "gsis_id"], keep="last"))
    ids = players.select("gsis_id", "pfr_id").drop_nulls().unique("pfr_id")
    s = (snaps.filter((pl.col("season") == season) & (pl.col("game_type") == "REG"))
         .select("week", franchise(pl.col("team")).alias("team"), pl.col("pfr_player_id").alias("pfr_id"), "player",
                 "offense_snaps", "offense_pct", "defense_snaps", "defense_pct")
         .join(ids, on="pfr_id", how="left"))
    unit = (s.with_columns(
        o=pl.when(pl.col("offense_pct") > 0).then(pl.col("offense_snaps") / pl.col("offense_pct")),
        d=pl.when(pl.col("defense_pct") > 0).then(pl.col("defense_snaps") / pl.col("defense_pct")))
        .group_by("team", "week").agg(team_off=pl.col("o").median(), team_def=pl.col("d").median()))
    return {"r": r, "s": s, "unit": unit}


def _shares(P: dict, team: str, before_week: int) -> pl.DataFrame:
    s = P["s"].filter((pl.col("team") == team) & (pl.col("week") < before_week))
    u = P["unit"].filter((pl.col("team") == team) & (pl.col("week") < before_week))
    schema = {"gsis_id": pl.Utf8, "player": pl.Utf8, "share": pl.Float64, "unit": pl.Utf8, "games": pl.UInt32}
    if s.height == 0 or u.height == 0:
        return pl.DataFrame(schema=schema)
    to, td = max(float(u["team_off"].fill_null(0).sum()), 1.0), max(float(u["team_def"].fill_null(0).sum()), 1.0)
    g = (s.drop_nulls("gsis_id").group_by("gsis_id")
         .agg(player=pl.col("player").last(), off=pl.col("offense_snaps").sum(), deff=pl.col("defense_snaps").sum(),
              games=pl.len()))
    return g.with_columns(share=pl.max_horizontal(pl.col("off") / to, pl.col("deff") / td),
                          unit=pl.when(pl.col("off") / to >= pl.col("deff") / td).then(pl.lit("offence"))
                          .otherwise(pl.lit("defence"))).select(list(schema))


def _latest(P: dict, week: int) -> pl.DataFrame:
    """Each player's latest roster row up to `week`."""
    return P["r"].filter(pl.col("week") <= week).sort("week").group_by("gsis_id").last()


def team_moves(P: dict, team: str, week: int) -> dict:
    r = P["r"]
    tw = r.filter((pl.col("team") == team) & (pl.col("week") <= week))["week"].max()
    if tw is None:
        return {"departures": [], "arrivals": [], "specialists": []}
    latest = {x["gsis_id"]: x for x in _latest(P, week).iter_rows(named=True)}
    mine = r.filter((pl.col("team") == team) & (pl.col("week") == tw) & pl.col("status").is_in(ACTIVE))
    on_team = {g for g in mine["gsis_id"].to_list() if latest.get(g, {}).get("team") == team}
    earlier = r.filter(pl.col("week") < week)
    deps = []
    for x in _shares(P, team, week).filter(pl.col("share") >= MIN_SHARE).iter_rows(named=True):
        gid = x["gsis_id"]
        if gid in on_team:
            continue
        cur = latest.get(gid)
        hist = earlier.filter((pl.col("gsis_id") == gid) & (pl.col("team") == team) & pl.col("status").is_in(ACTIVE))
        last = int(hist["week"].max()) if hist.height else None
        if cur is None or (cur["team"] == team and cur["status"] in ACTIVE):
            move = "Released"               # active for the team before, no longer on its roster
        elif cur["team"] != team:
            move = f"Now with {cur['team']}" + ("" if cur["status"] in ACTIVE
                                                 else f" ({STATUS_TEXT.get(cur['status'], OFF_ROSTER)})")
        else:
            move = STATUS_TEXT.get(cur["status"], OFF_ROSTER)
        deps.append({"player": (cur or {}).get("full_name") or x["player"], "pos": (cur or {}).get("pos"),
                     "move": move, "last_active_week": last, "share": round(float(x["share"]), 3), "unit": x["unit"],
                     "games": int(x["games"])})
    arrs = []
    for x in mine.filter(pl.col("gsis_id").is_in(list(on_team))).iter_rows(named=True):
        prev = earlier.filter((pl.col("gsis_id") == x["gsis_id"]) & (pl.col("team") != team) & pl.col("status").is_in(ACTIVE))
        if prev.height == 0:
            continue
        old = prev.sort("week")["team"][-1]
        here = earlier.filter((pl.col("gsis_id") == x["gsis_id"]) & (pl.col("team") == team))
        sh = _shares(P, old, week).filter(pl.col("gsis_id") == x["gsis_id"])
        share = float(sh["share"][0]) if sh.height else 0.0
        if share < MIN_SHARE and x["pos"] not in SPECIALISTS + ("QB",):
            continue
        arrs.append({"player": x["full_name"], "pos": x["pos"], "from": old,
                     "since_week": int(here["week"].min()) if here.height else int(tw), "share_with_old_team": round(share, 3)})
    spec = []
    for pos in SPECIALISTS:
        cur = mine.filter((pl.col("pos") == pos) & (pl.col("status") == "ACT"))["full_name"].to_list()
        before = (earlier.filter((pl.col("team") == team) & (pl.col("pos") == pos) & (pl.col("status") == "ACT"))
                  .group_by("full_name").agg(first=pl.col("week").min(), last=pl.col("week").max()).sort("first"))
        olds = [b for b in before.iter_rows(named=True) if b["full_name"] not in cur]
        since = earlier.filter((pl.col("team") == team) & (pl.col("pos") == pos) & pl.col("full_name").is_in(cur))
        since_week = int(since["week"].min()) if since.height else int(tw)
        first_week = earlier.filter(pl.col("team") == team)["week"].min()
        # a change only if the current specialist joined after the team's first week (a stand-in who left is not one)
        if cur and olds and first_week is not None and since_week > first_week:
            spec.append({"pos": pos, "now": cur[0], "since_week": since_week,
                         "before": [{"player": b["full_name"], "weeks": [int(b["first"]), int(b["last"])]} for b in olds]})
    deps.sort(key=lambda d: -d["share"])
    return {"departures": deps, "arrivals": arrs, "specialists": spec}


def game_moves(P: dict, game: dict) -> dict:
    """{"away": {...}, "home": {...}} for one game (game: away_id, home_id, week)."""
    return {side: team_moves(P, game[f"{side}_id"], int(game["week"])) for side in ("away", "home")}
