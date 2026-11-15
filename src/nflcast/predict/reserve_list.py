"""Display only (user request 2026-11-15): players on reserve lists (injured reserve, PUP, suspension, ...) per team.

Players on a reserve list are not on the weekly injury report, so a long-term absence can be invisible on the game page.
This lists them from the nflverse weekly roster snapshot that each cycle already downloads (status "RES" plus
status_description_abbr), at export time only: never in the release JSON, never a model input, never in "notable".

Reserve types were read from the data (2021-2026 weekly rosters), not assumed:
  R01  follows an active week, often after injury-report entries; ends in R48 or back on the active roster -> injured reserve
  R48  always follows R01 and usually ends on the active roster                -> injured reserve, designated to return
  R04  starts in week 1 (99%), no injury-report entries, then active           -> physically unable to perform (PUP)
  R05  starts in week 1 (83%), long spells (e.g. an off-field accident)        -> non-football injury
  R27  injury-report notes such as "not injury related - personal matter", illness -> non-football illness
  R47 / R49  only ever follow R05 / R27                                        -> non-football list, designated to return
  R40  short spells between active weeks (known league suspensions, e.g. three or four games) -> suspended
  R30  season-long spells (known indefinite league suspensions)                -> suspended
  R33  one-week spells between active weeks (known club suspensions)          -> suspended by the team
  R03 did not report, R06 left the team, R59 one-week spells in 2021-22 (COVID-19 list), R23 future contracts after
  the season: shown as "Other reserve list". W03 under RES (waived, then reverted to IR in week 1) counts as injured
  reserve. A01 under RES is the first week of a move whose type is not in the data yet (it becomes R01 the next week
  in every 2026 case) and is shown as "Reserve list (type not yet given)". Codes are never shown on the site.

Two snap shares (offensive or defensive snaps / the team's snaps for that unit), because either alone misleads (a
starter hurt early in his first game looks like a backup this season; last season's role can be out of date):
  * this season: with this team, over the team's games up to his last game before he went on the list (None if he
    did not play for the team this season before the list, e.g. hurt in training camp);
  * last season: regular season, with the team he played most for (named when it is another team).
A player is listed when either share is at least MIN_SHARE, and kickers / punters whenever they kicked in either
period; the rest are counted. The roster file for a week lags the transactions, so each team's list carries the
roster week it comes from (its latest file up to the game's week; byes have no file).
"""

from __future__ import annotations

import polars as pl

from nflcast.data.games import franchise

MIN_SHARE = 0.20                       # listed from this share of a unit's snaps (same as Roster moves)
SPECIALISTS = ("K", "P")               # kickers / punters listed whenever they kicked for a team in the period
INJURED = "Injured reserve"
KIND = {  # status_description_abbr under status RES -> (group, public label)
    "R01": ("injured", INJURED), "W03": ("injured", INJURED),
    "R48": ("injured", "Injured reserve, designated to return"),
    "R04": ("pup", "Physically unable to perform"),
    "R05": ("nfi", "Non-football injury"), "R47": ("nfi", "Non-football injury, designated to return"),
    "R27": ("nfi", "Non-football illness"), "R49": ("nfi", "Non-football illness, designated to return"),
    "R40": ("suspended", "Suspended"), "R30": ("suspended", "Suspended"), "R33": ("suspended", "Suspended by the team"),
    "R03": ("other", "Did not report"), "R06": ("other", "Left the team"),
    "A01": ("pending", "Reserve list (type not yet given)"),
}
OTHER = ("other", "Other reserve list")


def kind(code: str | None) -> tuple[str, str]:
    """(group, plain-English label) for a reserve code; unknown codes never reach the page raw."""
    return KIND.get(code or "", OTHER)


def _unit_snaps(snaps: pl.DataFrame) -> pl.DataFrame:
    """Team snaps per game and unit, recovered from each player's snaps / pct (median over the team's players)."""
    return (snaps.with_columns(
        o=pl.when(pl.col("offense_pct") > 0).then(pl.col("offense_snaps") / pl.col("offense_pct")),
        d=pl.when(pl.col("defense_pct") > 0).then(pl.col("defense_snaps") / pl.col("defense_pct")))
        .group_by("team", "week").agg(team_off=pl.col("o").median(), team_def=pl.col("d").median()))


def _snaps(snaps: pl.DataFrame, ids: pl.DataFrame, season: int) -> pl.DataFrame:
    cols = ["offense_snaps", "offense_pct", "defense_snaps", "defense_pct"]
    st = [pl.col("st_snaps").fill_null(0).alias("st_snaps")] if "st_snaps" in snaps.columns else [pl.lit(0).alias("st_snaps")]
    return (snaps.filter((pl.col("season") == season) & (pl.col("game_type") == "REG"))
            .select("week", franchise(pl.col("team")).alias("team"), pl.col("pfr_player_id").alias("pfr_id"),
                    *[pl.col(c).fill_null(0) for c in cols], *st)
            .join(ids, on="pfr_id", how="inner"))


def prepare(rosters: pl.DataFrame, snaps: pl.DataFrame, players: pl.DataFrame, season: int,
            prev_snaps: pl.DataFrame | None = None) -> dict:
    """Season tables shared by every game: weekly roster rows and per-player snaps (this season and last) by gsis id."""
    code = (pl.col("status_description_abbr") if "status_description_abbr" in rosters.columns
            else pl.lit(None, dtype=pl.Utf8))
    r = (rosters.filter(pl.col("season") == season)
         .select(pl.col("week").cast(pl.Int32), franchise(pl.col("team")).alias("team"), "gsis_id", "full_name",
                 pl.col("position").alias("pos"), "status", code.alias("code"))
         .drop_nulls("gsis_id").unique(["week", "gsis_id"], keep="last"))
    ids = players.select("gsis_id", "pfr_id").drop_nulls().unique("pfr_id")
    s = _snaps(snaps, ids, season)
    p = _snaps(prev_snaps, ids, season - 1) if prev_snaps is not None and prev_snaps.height else None
    return {"r": r, "s": s, "unit": _unit_snaps(s), "prev": p, "prev_unit": _unit_snaps(p) if p is not None else None}


def _share(s: pl.DataFrame, unit: pl.DataFrame, team: str, gid: str, weeks: tuple[int, int] | None) -> dict | None:
    """Player's share of the team's unit snaps over the team's games in [w0, w1] (None: no games in range)."""
    ts = s.filter(pl.col("team") == team)
    tu = unit.filter(pl.col("team") == team)
    if weeks is not None:
        ts = ts.filter(pl.col("week").is_between(*weeks))
        tu = tu.filter(pl.col("week").is_between(*weeks))
    me = ts.filter(pl.col("gsis_id") == gid)
    if tu.height == 0 or me.height == 0:
        return None
    to, td = max(float(tu["team_off"].fill_null(0).sum()), 1.0), max(float(tu["team_def"].fill_null(0).sum()), 1.0)
    o, d = float(me["offense_snaps"].sum()) / to, float(me["defense_snaps"].sum()) / td
    played = me.filter((pl.col("offense_snaps") + pl.col("defense_snaps") + pl.col("st_snaps")) > 0)
    return {"share": max(o, d), "unit": "offence" if o >= d else "defence", "games": played.height,
            "kicked": played.filter(pl.col("st_snaps") > 0).height}


def team_list(P: dict, team: str, week: int, min_share: float = MIN_SHARE) -> dict:
    """Reserve-list players of `team` in its latest roster file up to `week` (the game's week)."""
    r = P["r"]
    tw = r.filter((pl.col("team") == team) & (pl.col("week") <= week))["week"].max()
    if tw is None:
        return {"roster_week": None, "players": [], "others": 0}
    mine = r.filter((pl.col("team") == team) & (pl.col("week") == tw) & (pl.col("status") == "RES"))
    hist = r.filter((pl.col("team") == team) & (pl.col("week") <= tw)).sort("week")
    team_weeks = sorted(set(hist["week"].to_list()))
    out, others = [], 0
    for x in mine.iter_rows(named=True):
        gid = x["gsis_id"]
        h = {w: st for w, st in hist.filter(pl.col("gsis_id") == gid).select("week", "status").iter_rows()}
        since = tw
        for w in reversed(team_weeks):            # start of the current spell (team weeks without a row break it)
            if h.get(w) != "RES":
                break
            since = w
        this = None                              # this season, with this team, up to his last game before the list
        if since > 1:
            played = P["s"].filter((pl.col("team") == team) & (pl.col("gsis_id") == gid) & (pl.col("week") < since)
                                   & ((pl.col("offense_snaps") + pl.col("defense_snaps") + pl.col("st_snaps")) > 0))
            if played.height:
                this = _share(P["s"], P["unit"], team, gid, (1, int(played["week"].max())))
        last = None                              # last regular season, with the team he played most for
        if P.get("prev") is not None:
            for t in P["prev"].filter(pl.col("gsis_id") == gid)["team"].unique().sort().to_list():
                c = _share(P["prev"], P["prev_unit"], t, gid, None)
                if c and c["games"] and (last is None or (c["share"], c["kicked"]) > (last["share"], last["kicked"])):
                    last = {**c, "team": t}
        group, label = kind(x["code"])
        kicked = any(s is not None and s["kicked"] > 0 for s in (this, last))
        specialist = x["pos"] in SPECIALISTS and kicked
        top = max([s["share"] for s in (this, last) if s is not None], default=None)
        if not specialist and (top is None or top < min_share):
            others += 1
            continue
        side = lambda s: None if s is None else {"share": round(float(s["share"]), 3), "unit": s["unit"],
                                                  "games": int(s["games"])}
        out.append({"player": x["full_name"], "pos": x["pos"], "list": label, "group": group, "since_week": int(since),
                    "specialist": specialist, "this_season": side(this),
                    "last_season": None if last is None else {**side(last),
                                                              "team": last["team"] if last["team"] != team else None}})
    key = lambda d: (d["specialist"], -max(s["share"] for s in (d["this_season"], d["last_season"]) if s is not None))
    out.sort(key=key)
    return {"roster_week": int(tw), "players": out, "others": others}


def game_list(P: dict, game: dict, min_share: float = MIN_SHARE) -> dict:
    """{"min_share", "away": {...}, "home": {...}} for one game (game: away_id, home_id, week)."""
    return {"min_share": min_share,
            **{side: team_list(P, game[f"{side}_id"], int(game["week"]), min_share) for side in ("away", "home")}}
