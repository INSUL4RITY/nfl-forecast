"""A2: build the candidate absence inputs exactly as pre-registered (absences_v1_preregistration_2026-11-21.md, section 1).

build(raw, target_seasons) -> (team inputs per game and arm, player rows). `raw` holds the source tables (so the leakage
test can pass corrupted copies): games, team_games, snaps, injuries, rosters, players.
Arms: AV1 (primary), AV1-inj, AV1-b8, AV1-split (subset inputs lost_edge, lost_cb on top of AV1).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import numpy as np  # noqa: E402
import polars as pl  # noqa: E402

from nflcast.config import PROCESSED_DIR  # noqa: E402
from nflcast.data import sources as S  # noqa: E402
from nflcast.data.games import franchise  # noqa: E402
from nflcast.features import personnel as P  # noqa: E402

HL, CARRY, WIN = 8.0, 0.6, 48
M_SHRINK = 50.0
UNITS = ["ol", "skill", "front", "db"]
EDGE_POS, CB_POS = {"DE", "OLB", "EDGE"}, {"CB"}
UNIT_MAP = P.UNIT_OF_POSITION


def load_raw(first: int = 2012, last: int = 2026) -> dict:
    games = pl.read_parquet(PROCESSED_DIR / "games.parquet")
    tg = (pl.read_parquet(PROCESSED_DIR / "team_games.parquet").select("game_id", "team", "kickoff_utc")
          .join(games.select("game_id", "season", "week"), on="game_id"))
    players = S.fetch("players").select("gsis_id", "pfr_id").drop_nulls()
    snaps = pl.concat([S.fetch("snap_counts", s).select(
        "game_id", franchise(pl.col("team")).alias("team"), pl.col("pfr_player_id").alias("pfr"), "position",
        pl.col("offense_pct").fill_null(0.0).cast(pl.Float64), pl.col("defense_pct").fill_null(0.0).cast(pl.Float64))
        for s in range(first, last + 1)], how="vertical_relaxed")
    inj = pl.concat([S.fetch("injuries", s).select(
        pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32), franchise(pl.col("team")).alias("team"), "gsis_id",
        P._status_key(pl.col("report_status")).alias("status"), pl.col("practice_status").fill_null(""))
        for s in range(first, last + 1)], how="vertical_relaxed").unique(["season", "week", "team", "gsis_id"], keep="last")
    ros = pl.concat([S.fetch("rosters_weekly", s).select(
        pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32), franchise(pl.col("team")).alias("team"),
        "gsis_id", "status") for s in range(max(first, 2016), last + 1)], how="vertical_relaxed").drop_nulls("gsis_id")
    ros = ros.unique(["season", "week", "team", "gsis_id"], keep="last")
    return {"games": games, "tg": tg, "snaps": snaps, "inj": inj, "ros": ros, "players": players}


def _practice(e: pl.Expr) -> pl.Expr:
    return (pl.when(e.str.contains("(?i)did not")).then(pl.lit("DNP")).when(e.str.contains("(?i)limited")).then(pl.lit("Limited"))
            .when(e.str.contains("(?i)full")).then(pl.lit("Full")).otherwise(pl.lit("none")))


def _band(e: pl.Expr) -> pl.Expr:
    return (pl.when(e < 0.2).then(pl.lit("a")).when(e < 0.5).then(pl.lit("b")).when(e < 0.8).then(pl.lit("c")).otherwise(pl.lit("d")))


def _snap_rows(raw: dict) -> pl.DataFrame:
    p2g = raw["players"].unique("pfr_id").rename({"pfr_id": "pfr"})
    s = (raw["snaps"].with_columns(unit=pl.col("position").replace_strict(UNIT_MAP, default=None))
         .filter(pl.col("unit").is_not_null())
         .with_columns(s=pl.when(pl.col("unit").is_in(["ol", "skill"])).then(pl.col("offense_pct")).otherwise(pl.col("defense_pct")))
         .join(p2g, on="pfr", how="left")
         .with_columns(edge=pl.col("position").is_in(list(EDGE_POS)), cb=pl.col("position").is_in(list(CB_POS))))
    return s.select("game_id", "team", "pfr", "gsis_id", "unit", "s", "edge", "cb")


def player_rows(raw: dict, target_seasons: list[int]) -> pl.DataFrame:
    """One row per (target team-game, player): window quantities, status, roster status, played in target."""
    tg = raw["tg"].sort("kickoff_utc", "game_id").with_columns(idx=pl.int_range(pl.len()).over("team"))
    sn = _snap_rows(raw)
    return pl.concat([_season_rows(raw, tg, sn, Y) for Y in target_seasons], how="diagonal_relaxed")


def _season_rows(raw: dict, tg: pl.DataFrame, sn: pl.DataFrame, Y: int) -> pl.DataFrame:
    tgt = tg.filter(pl.col("season") == Y).rename({"game_id": "tgame", "idx": "tidx", "season": "tseason",
                                                                     "week": "tweek", "kickoff_utc": "tko"})
    win = (tgt.with_columns(pidx=pl.int_ranges(pl.col("tidx") - WIN, pl.col("tidx"))).explode("pidx")
           .filter(pl.col("pidx") >= 0)
           .join(tg.select(pl.col("game_id").alias("g"), "team", pl.col("idx").alias("pidx"), pl.col("season").alias("gseason")),
                 on=["team", "pidx"]))
    win = win.with_columns(w=0.5 ** ((pl.col("tidx") - 1 - pl.col("pidx")) / HL) * CARRY ** (pl.col("tseason") - pl.col("gseason")).clip(0),
                           last=pl.col("pidx") == pl.col("tidx") - 1, rec6=pl.col("pidx") >= pl.col("tidx") - 6)
    WT = win.group_by("tgame", "team").agg(WT=pl.col("w").sum())
    pw = (win.join(sn.rename({"game_id": "g"}), on=["g", "team"], how="inner")
          .group_by("tgame", "team", "pfr").agg(
              gsis_id=pl.col("gsis_id").drop_nulls().last(), unit=pl.col("unit").last(), edge=pl.col("edge").last(), cb=pl.col("cb").last(),
              num=(pl.col("w") * pl.col("s")).sum(), pw=(pl.col("w") * (pl.col("s") > 0)).sum(),
              played_last=((pl.col("s") > 0) & pl.col("last")).any(), rec6=(pl.col("s") * pl.col("rec6")).sum() / 6.0)
          .filter(pl.col("pw") > 0)
          .join(WT, on=["tgame", "team"]).join(tgt.select("tgame", "team", "tseason", "tweek", "tko"), on=["tgame", "team"])
          .with_columns(r=pl.col("num") / pl.col("WT"), b=pl.col("num") / pl.col("pw"), kind=pl.lit("window")))
    # roster file for the previous game week (week 1: week-1 file)
    ros = raw["ros"]
    rw = ros.select("season", "team", "week").unique().sort("season", "team", "week")
    tkey = (tgt.select("tgame", "team", "tseason", "tweek")
            .with_columns(key=pl.when(pl.col("tweek") <= 1).then(1).otherwise(pl.col("tweek") - 1).cast(pl.Int32))
            .sort("key"))
    fw = tkey.join_asof(rw.rename({"season": "tseason", "week": "fweek"}).with_columns(key=pl.col("fweek")).sort("key"),
                        on="key", by=["tseason", "team"], strategy="backward").select("tgame", "team", "tseason", "fweek")
    on_file = ros.rename({"season": "tseason", "week": "fweek", "status": "rstatus"})
    pw = pw.join(fw.drop("tseason"), on=["tgame", "team"], how="left").join(on_file, on=["tseason", "fweek", "team", "gsis_id"], how="left")
    pw = pw.with_columns(roster=pl.when(pl.col("fweek").is_null() | pl.col("gsis_id").is_null()).then(pl.lit("unknown"))
                         .when(pl.col("rstatus") == "RES").then(pl.lit("reserve"))
                         .when(pl.col("rstatus").is_in(["ACT", "INA"])).then(pl.lit("active"))
                         .otherwise(pl.lit("departed")))
    # arrivals: active on T's file, no window play for T, with earlier plays for other teams (his own last 48 games)
    act = (fw.join(on_file.filter(pl.col("rstatus").is_in(["ACT", "INA"])), on=["tseason", "fweek", "team"], how="inner")
           .join(tgt.select("tgame", "team", "tko"), on=["tgame", "team"]))
    known = pw.select("tgame", "team", "gsis_id").drop_nulls()
    act = act.join(known, on=["tgame", "team", "gsis_id"], how="anti").select("tgame", "team", "gsis_id", "tseason", "tko", "fweek")
    hist = (sn.drop_nulls("gsis_id").filter(pl.col("gsis_id").is_in(act["gsis_id"].unique().to_list())).join(raw["tg"].select("game_id", "team", "kickoff_utc", pl.col("season").alias("gseason")),
                                          on=["game_id", "team"]))
    arr = (act.join(hist.rename({"team": "oteam"}), on="gsis_id", how="inner")
           .filter((pl.col("kickoff_utc") < pl.col("tko")) & (pl.col("oteam") != pl.col("team")))
           .sort("kickoff_utc").group_by("tgame", "team", "gsis_id", maintain_order=True).tail(WIN))
    if arr.height:
        key = ["tgame", "team", "gsis_id"]
        arr = (arr.with_columns(k=pl.len().over(key) - 1 - pl.int_range(pl.len()).over(key))
               .with_columns(w=0.5 ** (pl.col("k") / HL) * CARRY ** (pl.col("tseason") - pl.col("gseason")).clip(0))
               .group_by("tgame", "team", "gsis_id").agg(
                   unit=pl.col("unit").last(), edge=pl.col("edge").last(), cb=pl.col("cb").last(), pfr=pl.col("pfr").last(),
                   num=(pl.col("w") * pl.col("s")).sum(), pw=(pl.col("w") * (pl.col("s") > 0)).sum(),
                   tseason=pl.col("tseason").first(), tko=pl.col("tko").first(), fweek=pl.col("fweek").first())
               .filter(pl.col("pw") > 0)
               .with_columns(b=pl.col("num") / pl.col("pw"), r=pl.lit(0.0), kind=pl.lit("arrival"), roster=pl.lit("active"),
                             played_last=pl.lit(False), rec6=pl.lit(0.0)))
        arr = arr.join(tgt.select("tgame", "team", "tweek"), on=["tgame", "team"])
    rows = pl.concat([pw, arr], how="diagonal_relaxed") if arr.height else pw
    # injury report for the target week (final weekly report)
    inj = raw["inj"].rename({"season": "tseason", "week": "tweek"}).with_columns(practice=_practice(pl.col("practice_status")))
    rows = rows.join(inj.select("tseason", "tweek", "team", "gsis_id", "status", "practice"), on=["tseason", "tweek", "team", "gsis_id"], how="left")
    # listed players with no window play and not an arrival (e.g. rookies without snaps) carry no share: not needed.
    # participation in the target game (for the rate tables of LATER seasons only)
    tsn = sn.select(pl.col("game_id").alias("tgame"), "team", "pfr", ts="s")
    rows = (rows.join(tsn, on=["tgame", "team", "pfr"], how="left")
            .with_columns(played_t=(pl.col("ts").fill_null(0.0) > 0).cast(pl.Float64),
                          band=_band(pl.col("b")), band6=_band(pl.col("rec6")), listed=pl.col("status").is_not_null()))
    return rows


def rates(rows: pl.DataFrame, season: int) -> dict:
    """As-of rate tables for games of `season` (5 earlier seasons; P_unl from 2016 on, 2016 uses itself)."""
    L = rows.filter(pl.col("listed") & pl.col("tseason").is_between(season - 5, season - 1))
    st = L.group_by("status", "band").agg(k=pl.col("played_t").sum(), n=pl.len())
    cell = L.group_by("status", "practice", "band").agg(k=pl.col("played_t").sum(), n=pl.len())
    cell = cell.join(st.select("status", "band", p0=pl.col("k") / pl.col("n")), on=["status", "band"], how="left")
    cell = cell.with_columns(p=(pl.col("k") + M_SHRINK * pl.col("p0")) / (pl.col("n") + M_SHRINK))
    st6 = L.group_by("status", "band6").agg(k=pl.col("played_t").sum(), n=pl.len())
    cell6 = L.group_by("status", "practice", "band6").agg(k=pl.col("played_t").sum(), n=pl.len())
    cell6 = cell6.join(st6.select("status", "band6", p0=pl.col("k") / pl.col("n")), on=["status", "band6"], how="left")
    cell6 = cell6.with_columns(p=(pl.col("k") + M_SHRINK * pl.col("p0")) / (pl.col("n") + M_SHRINK))
    lo, hi = (season, season) if season <= 2016 else (max(2016, season - 5), season - 1)
    U = rows.filter(~pl.col("listed") & (pl.col("roster") == "active") & (pl.col("kind") == "window")
                    & pl.col("tseason").is_between(lo, hi))
    unl = U.group_by("band", "played_last").agg(p=pl.col("played_t").mean(), n=pl.len())
    stat = {r["status"]: r["k"] / r["n"] for r in L.group_by("status").agg(k=pl.col("played_t").sum(), n=pl.len()).iter_rows(named=True)}
    return {"list": cell.select("status", "practice", "band", "p"), "list6": cell6.select("status", "practice", "band6", "p"),
            "list_status_band": st.select("status", "band", p_sb=pl.col("k") / pl.col("n")),
            "list6_status_band": st6.select("status", "band6", p_sb6=pl.col("k") / pl.col("n")),
            "status": stat, "unl": unl.select("band", "played_last", p_unl="p"), "n_list": L.height, "n_unl": U.height}


def team_inputs(rows: pl.DataFrame, target_seasons: list[int]) -> tuple[pl.DataFrame, dict]:
    out, rep = [], {}
    for Y in target_seasons:
        R = rows.filter(pl.col("tseason") == Y)
        rt = rates(rows, Y)
        rep[Y] = {"n_list_rows": rt["n_list"], "n_unl_rows": rt["n_unl"],
                  "p_unl": rt["unl"].sort("band", "played_last").to_dicts()}
        R = (R.join(rt["list"], on=["status", "practice", "band"], how="left")
             .join(rt["list_status_band"], on=["status", "band"], how="left")
             .join(rt["list6"].rename({"p": "p6"}), on=["status", "practice", "band6"], how="left")
             .join(rt["list6_status_band"], on=["status", "band6"], how="left")
             .join(rt["unl"], on=["band", "played_last"], how="left"))
        fb = pl.col("status").replace_strict(rt["status"], default=None)
        R = R.with_columns(p_list=pl.coalesce("p", "p_sb", fb), p_list6=pl.coalesce("p6", "p_sb6", fb))
        R = R.with_columns(P=pl.when(pl.col("listed")).then(pl.col("p_list"))
                           .when(pl.col("roster").is_in(["reserve", "departed"])).then(0.0)
                           .otherwise(pl.col("p_unl"))).with_columns(pl.col("P").fill_null(1.0))
        R = R.with_columns(d_av1=pl.col("r") - pl.col("b") * pl.col("P"),
                           d_inj=pl.when(pl.col("listed")).then(pl.col("r") - pl.col("b") * pl.col("p_list")).otherwise(0.0),
                           d_b8=pl.when(pl.col("listed")).then(pl.col("rec6") * (1 - pl.col("p_list6"))).otherwise(0.0))
        agg = []
        for arm, col in (("AV1", "d_av1"), ("AV1-inj", "d_inj"), ("AV1-b8", "d_b8")):
            agg += [pl.col(col).filter(pl.col("unit") == u).sum().alias(f"{arm}|lost_{u}") for u in UNITS]
        agg += [pl.col("d_av1").filter(pl.col("edge")).sum().alias("AV1|lost_edge"),
                pl.col("d_av1").filter(pl.col("cb")).sum().alias("AV1|lost_cb")]
        out.append(R.group_by("tgame", "team").agg(agg).rename({"tgame": "game_id"}))
    return pl.concat(out), rep


def build(raw: dict, target_seasons: list[int], rate_seasons_back: int = 5) -> tuple[pl.DataFrame, pl.DataFrame, dict]:
    need = sorted(set(range(min(target_seasons) - rate_seasons_back, max(target_seasons) + 1)) & set(range(2013, 2027)))
    rows = player_rows(raw, need)
    T, rep = team_inputs(rows, target_seasons)
    return T, rows, rep
