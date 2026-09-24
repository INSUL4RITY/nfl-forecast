"""Milestone 3: expected quarterback and player availability features.

Quarterbacks
------------
* QB ability: exponentially weighted EPA per dropback over the QB's own games (follows the player across
  teams), shrunk toward an as-of "newcomer prior" (league mean + learned offset for inexperienced QBs).
* Expected starter at the cutoff:
    - early horizon: depth-chart QB1 (weekly charts 2016-2024 have no timestamp -> week-level
      approximation; 2025+ daily snapshots taken at or before the cutoff), falling back to the team's
      previous-game starter.
    - final horizon (60 min): the actual starter (first dropback passer). Starting QBs are normally
      known from inactives ~90 min before kickoff; this is labelled an approximation of final-pregame
      knowledge, not a strict as-of reconstruction.
* qb_delta = expected-starter rating minus the rating of the QBs represented in the team's weighted
  history. This measures change relative to the baseline already in the team statistics, so a QB
  absence is not counted twice.

Non-QB availability (final horizon only)
----------------------------------------
From the final weekly injury report (the only version retained historically). For each listed player:
expected lost snap share = P(miss | report status) x the player's recent snap share, where P(miss | status)
is estimated from earlier seasons only, and snap share includes zeros for games missed (so absences
already reflected in recent team statistics shrink the player's baseline share). Aggregated by unit.
Units are "player-equivalents of snaps", NOT points: the model learns any relationship.
"""

from __future__ import annotations

from datetime import timedelta

import numpy as np
import polars as pl

from nflcast.config import settings
from nflcast.data import sources as S
from nflcast.data.games import franchise

QB_HALF_LIFE_GAMES = 16.0
QB_SEASON_CARRY = 0.8
QB_SHRINK_DROPBACKS = 250.0
NEWCOMER_CAREER_DB = 200


# ------------------------------------------------------------------ QB game table
def qb_games(pbp: pl.DataFrame, games: pl.DataFrame) -> pl.DataFrame:
    """One row per (game, team, dropback player): dropbacks, EPA sum, starter flag."""
    p = pbp.filter((pl.col("qb_dropback") == 1) & (pl.col("qb_spike").fill_null(0) == 0)
                   & pl.col("passer_id").is_not_null() & (pl.col("play_type") != "no_play")).with_columns(
        team=franchise(pl.col("posteam")))
    first = p.sort("play_id").group_by(["game_id", "team"]).agg(starter_id=pl.col("passer_id").first())
    agg = p.group_by(["game_id", "team", "passer_id"]).agg(db=pl.len(), epa=pl.col("epa").fill_null(0).sum())
    out = agg.join(first, on=["game_id", "team"]).with_columns(is_starter=pl.col("passer_id") == pl.col("starter_id"))
    g = games.select("game_id", "season", "week", "kickoff_utc")
    return out.join(g, on="game_id").rename({"passer_id": "qb_id"}).drop("starter_id").sort(["kickoff_utc", "game_id"])


class QBModel:
    def __init__(self, qbg: pl.DataFrame):
        lag = timedelta(hours=settings()["pbp_available_after_kickoff_hours"])
        q = qbg.with_columns(avail=(pl.col("kickoff_utc") + lag).dt.epoch("us")).sort("avail")
        # career dropbacks before each game (within available history, starting 2011)
        q = q.with_columns(career_before=pl.col("db").cum_sum().over("qb_id") - pl.col("db"))
        self.q = q
        self.by_qb = {k[0]: (d["avail"].to_numpy(), d["season"].to_numpy(), d["db"].to_numpy().astype(float),
                             d["epa"].to_numpy()) for k, d in q.group_by(["qb_id"])}
        self.avail_all = q["avail"].to_numpy()
        self.cum_db = np.concatenate([[0.0], np.cumsum(q["db"].to_numpy())])
        self.cum_epa = np.concatenate([[0.0], np.cumsum(q["epa"].to_numpy())])
        newc = (q["career_before"] < NEWCOMER_CAREER_DB).to_numpy()
        self.cum_db_new = np.concatenate([[0.0], np.cumsum(q["db"].to_numpy() * newc)])
        self.cum_epa_new = np.concatenate([[0.0], np.cumsum(q["epa"].to_numpy() * newc)])
        starters = q.filter(pl.col("is_starter"))
        self.team_starts = {k[0]: (d["avail"].to_numpy(), d["qb_id"].to_list(), d["game_id"].to_list())
                            for k, d in starters.group_by(["team"])}
        self.starter_by_game = {(r[0], r[1]): r[2] for r in starters.select("game_id", "team", "qb_id").iter_rows()}

    def prior(self, cutoff_us: int) -> float:
        """As-of prior for a QB with no history: league EPA/db + newcomer offset (last ~3 seasons)."""
        n = int(np.searchsorted(self.avail_all, cutoff_us, side="right"))
        lo = max(0, n - 3 * 32 * 18)
        db = self.cum_db[n] - self.cum_db[lo]
        league = (self.cum_epa[n] - self.cum_epa[lo]) / db if db > 0 else 0.0
        dbn = self.cum_db_new[n] - self.cum_db_new[lo]
        newc = (self.cum_epa_new[n] - self.cum_epa_new[lo]) / dbn if dbn > 500 else league - 0.1
        return float(newc)

    def rating(self, qb_id: str | None, cutoff_us: int, season: int) -> tuple[float, float]:
        """(shrunk EPA/dropback, weighted dropbacks of evidence) as of the cutoff."""
        pr = self.prior(cutoff_us)
        if qb_id is None or qb_id not in self.by_qb:
            return pr, 0.0
        av, se, db, ep = self.by_qb[qb_id]
        n = int(np.searchsorted(av, cutoff_us, side="right"))
        if n == 0:
            return pr, 0.0
        k = np.arange(n)[::-1]
        w = 0.5 ** (k / QB_HALF_LIFE_GAMES) * QB_SEASON_CARRY ** np.clip(season - se[:n], 0, None)
        wdb = float((w * db[:n]).sum())
        return float(((w * ep[:n]).sum() + QB_SHRINK_DROPBACKS * pr) / (wdb + QB_SHRINK_DROPBACKS)), wdb

    def previous_starter(self, team: str, cutoff_us: int) -> str | None:
        if team not in self.team_starts:
            return None
        av, ids, _ = self.team_starts[team]
        n = int(np.searchsorted(av, cutoff_us, side="right"))
        return ids[n - 1] if n else None

    def baseline_rating(self, team: str, cutoff_us: int, season: int, half_life: float, carry: float, max_games: int = 48) -> float:
        """Rating of the QBs represented in the team's weighted history (same weights as team form)."""
        if team not in self.team_starts:
            return self.prior(cutoff_us)
        av, ids, gids = self.team_starts[team]
        n = int(np.searchsorted(av, cutoff_us, side="right"))
        lo = max(0, n - max_games)
        if n == 0:
            return self.prior(cutoff_us)
        seasons = np.array([int(g[:4]) for g in gids[lo:n]])
        k = np.arange(n - lo)[::-1]
        w = 0.5 ** (k / half_life) * carry ** np.clip(season - seasons, 0, None)
        cache: dict[str, float] = {}
        r = []
        for qid in ids[lo:n]:
            if qid not in cache:
                cache[qid] = self.rating(qid, cutoff_us, season)[0]
            r.append(cache[qid])
        return float((w * np.array(r)).sum() / w.sum())


# ------------------------------------------------------------------ depth charts
def depth_chart_qb1(seasons: list[int]) -> pl.DataFrame:
    """QB1 by team and week (weekly charts) or by snapshot time (daily charts, 2025+).

    Returns columns: team, season, week (nullable), dt_us (nullable), qb_id.
    """
    frames = []
    for s in seasons:
        try:
            dc = S.fetch("depth_charts", s)
        except Exception:  # noqa: BLE001
            continue
        if "dt" in dc.columns:
            q = (dc.filter((pl.col("pos_abb") == "QB") & (pl.col("pos_rank") == 1) & pl.col("gsis_id").is_not_null())
                 .select(franchise(pl.col("team")).alias("team"), pl.lit(s).alias("season"), pl.lit(None, pl.Int32).alias("week"),
                         pl.col("dt").str.to_datetime(time_zone="UTC").dt.epoch("us").alias("dt_us"), pl.col("gsis_id").alias("qb_id"))
                 .unique(["team", "dt_us"], keep="first"))
        else:
            q = (dc.filter((pl.col("position") == "QB") & (pl.col("depth_team") == "1") & pl.col("gsis_id").is_not_null())
                 .select(franchise(pl.col("club_code")).alias("team"), pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32),
                         pl.lit(None, pl.Int64).alias("dt_us"), pl.col("gsis_id").alias("qb_id"))
                 .unique(["team", "season", "week"], keep="first"))
        frames.append(q)
    return pl.concat(frames, how="vertical_relaxed") if frames else pl.DataFrame()


class DepthCharts:
    def __init__(self, qb1: pl.DataFrame):
        weekly = qb1.filter(pl.col("week").is_not_null())
        self.weekly = {(r[0], r[1], r[2]): r[3] for r in weekly.select("team", "season", "week", "qb_id").iter_rows()}
        daily = qb1.filter(pl.col("dt_us").is_not_null()).sort("dt_us")
        self.daily = {k[0]: (d["dt_us"].to_numpy(), d["qb_id"].to_list()) for k, d in daily.group_by(["team"])}

    def qb1(self, team: str, season: int, week: int, cutoff_us: int) -> tuple[str | None, str]:
        if team in self.daily:
            dts, ids = self.daily[team]
            n = int(np.searchsorted(dts, cutoff_us, side="right"))
            # only trust a daily snapshot from within ~10 days of the cutoff
            if n and cutoff_us - dts[n - 1] <= 10 * 86400 * 1_000_000:
                return ids[n - 1], "depth_chart_daily"
        q = self.weekly.get((team, season, week))
        return (q, "depth_chart_weekly") if q else (None, "none")


# ------------------------------------------------------------------ injuries / availability
UNIT_OF_POSITION = {
    "T": "ol", "OT": "ol", "G": "ol", "OG": "ol", "C": "ol", "OL": "ol",
    "WR": "skill", "TE": "skill", "RB": "skill", "FB": "skill", "HB": "skill",
    "DE": "front", "DT": "front", "NT": "front", "DL": "front", "LB": "front", "OLB": "front", "ILB": "front", "MLB": "front", "EDGE": "front",
    "CB": "db", "S": "db", "SS": "db", "FS": "db", "DB": "db", "SAF": "db",
}
UNITS = ["ol", "skill", "front", "db"]


def _status_key(expr: pl.Expr) -> pl.Expr:
    return expr.fill_null("None").str.strip_chars().replace({"": "None", "Note": "None"})


def injury_player_weeks(seasons: list[int], games: pl.DataFrame) -> pl.DataFrame:
    """Final weekly report rows joined to whether the player actually played (snap counts)."""
    idmap = S.fetch("players").select("gsis_id", pl.col("pfr_id").alias("pfr_player_id")).drop_nulls().unique("gsis_id")
    frames = []
    for s in seasons:
        inj = S.fetch("injuries", s).select(
            pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32), franchise(pl.col("team")).alias("team"),
            "gsis_id", "position", _status_key(pl.col("report_status")).alias("status"))
        frames.append(inj)
    inj = pl.concat(frames).unique(["season", "week", "team", "gsis_id"], keep="last").join(idmap, on="gsis_id", how="left")
    inj = inj.with_columns(unit=pl.col("position").replace_strict(UNIT_OF_POSITION, default=None))
    # attach the team's game that week
    g = pl.concat([
        games.select("game_id", "season", "week", pl.col("home_id").alias("team"), "kickoff_utc"),
        games.select("game_id", "season", "week", pl.col("away_id").alias("team"), "kickoff_utc")])
    return inj.join(g.with_columns(pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32)),
                    on=["season", "week", "team"], how="inner")


def snap_shares(seasons: list[int], games: pl.DataFrame) -> pl.DataFrame:
    """Per (team game, player): offense/defense snap share (0 rows for games not played are added later)."""
    frames = [S.fetch("snap_counts", s).select(
        "game_id", franchise(pl.col("team")).alias("team"), "pfr_player_id", "offense_pct", "defense_pct") for s in seasons]
    sc = pl.concat(frames).with_columns(share=pl.max_horizontal(pl.col("offense_pct").fill_null(0), pl.col("defense_pct").fill_null(0)))
    return sc.join(games.select("game_id", "kickoff_utc", "season"), on="game_id").select(
        "game_id", "team", "pfr_player_id", "share", "kickoff_utc", "season")


class Availability:
    """Expected lost snap share by unit from the final injury report (final horizon)."""

    def __init__(self, inj: pl.DataFrame, snaps: pl.DataFrame, team_games: pl.DataFrame):
        self.inj = inj
        played = snaps.filter(pl.col("share") > 0).select("game_id", "pfr_player_id").with_columns(played=pl.lit(1))
        self.hist = inj.join(played, on=["game_id", "pfr_player_id"], how="left").with_columns(pl.col("played").fill_null(0))
        self.snaps = snaps
        # team game sequence to build share histories with zeros for missed games
        self.team_games = team_games.select("game_id", "team", "kickoff_utc").unique().sort("kickoff_utc")
        self._p_cache: dict[int, dict] = {}

    def p_play(self, season: int) -> dict[str, float]:
        """P(played | status) from seasons before `season` (as-of; falls back to pooled if too few)."""
        if season not in self._p_cache:
            h = self.hist.filter((pl.col("season") < season) & (pl.col("season") >= season - 5))
            if h.height < 500:
                h = self.hist.filter(pl.col("season") < season)
            tab = h.group_by("status").agg(p=pl.col("played").mean(), n=pl.len())
            self._p_cache[season] = {r["status"]: r["p"] for r in tab.iter_rows(named=True) if r["n"] >= 30}
        return self._p_cache[season]

    def unit_losses(self, game_ids: list[str], seasons: list[int]) -> pl.DataFrame:
        """Rows per (game_id, team): lost_<unit> for UNITS plus inj_listed count. Uses only prior games for shares."""
        rep = self.inj.filter(pl.col("game_id").is_in(game_ids) & pl.col("unit").is_not_null() & pl.col("pfr_player_id").is_not_null())
        if rep.height == 0:
            return pl.DataFrame(schema={"game_id": pl.Utf8, "team": pl.Utf8, **{f"lost_{u}": pl.Float64 for u in UNITS}})
        # player recent share: mean over the team's previous 6 games (0 when absent)
        tg = self.team_games.with_columns(idx=pl.int_range(pl.len()).over("team"))
        cur = rep.select("game_id", "team", "pfr_player_id", "status", "unit", "season").join(
            tg.select("game_id", "team", "idx"), on=["game_id", "team"])
        prev = (cur.select("game_id", "team", "pfr_player_id", "idx")
                .with_columns(pidx=pl.int_ranges(pl.col("idx") - 6, pl.col("idx"))).explode("pidx")
                .filter(pl.col("pidx") >= 0)
                .join(tg.select(pl.col("game_id").alias("pg"), "team", pl.col("idx").alias("pidx")), on=["team", "pidx"]))
        prev = prev.join(self.snaps.select(pl.col("game_id").alias("pg"), "pfr_player_id", "team", "share"),
                         on=["pg", "pfr_player_id", "team"], how="left").with_columns(pl.col("share").fill_null(0.0))
        share = prev.group_by(["game_id", "team", "pfr_player_id"]).agg(recent_share=pl.col("share").mean())
        cur = cur.join(share, on=["game_id", "team", "pfr_player_id"], how="left").with_columns(pl.col("recent_share").fill_null(0.0))
        pmap = {s: self.p_play(s) for s in cur["season"].unique().to_list()}
        pm = [1.0 - pmap[s].get(st, pmap[s].get("None", 0.9)) for s, st in zip(cur["season"], cur["status"])]
        cur = cur.with_columns(p_miss=pl.Series(pm)).with_columns(lost=pl.col("p_miss") * pl.col("recent_share"))
        wide = cur.group_by(["game_id", "team"]).agg([pl.col("lost").filter(pl.col("unit") == u).sum().alias(f"lost_{u}") for u in UNITS])
        return wide


# ------------------------------------------------------------------ assemble personnel features
def add_personnel_features(feats: pl.DataFrame, games: pl.DataFrame, qbm: QBModel, dcs: DepthCharts,
                           avail: Availability | None) -> pl.DataFrame:
    """Add QB and availability features to a feature_snapshots frame (one row per game x horizon)."""
    cfg = settings()["features"]
    hl, carry = float(cfg["half_life_games"]), float(cfg["season_carryover"])
    g = games.select("game_id", "status")
    rows = []
    for r in feats.join(g, on="game_id", how="left").iter_rows(named=True):
        c_us = int(r["cutoff_utc"].timestamp() * 1_000_000)
        rec = {"game_id": r["game_id"], "horizon": r["horizon"]}
        for side in ("home", "away"):
            team = r[f"{side}_id"]
            prev = qbm.previous_starter(team, c_us)
            if r["horizon"] == "final" and r["status"] == "final" and (r["game_id"], team) in qbm.starter_by_game:
                qb, src = qbm.starter_by_game[(r["game_id"], team)], "actual_starter_final_horizon"
            else:
                qb, src = dcs.qb1(team, r["season"], r["week"], c_us)
                if qb is None:
                    qb, src = prev, "previous_game_starter"
            rating, wdb = qbm.rating(qb, c_us, r["season"])
            base = qbm.baseline_rating(team, c_us, r["season"], hl, carry)
            rec.update({f"{side}_qb_id": qb, f"{side}_qb_source": src, f"{side}_qb_rating": rating,
                        f"{side}_qb_log_db": float(np.log1p(wdb)), f"{side}_qb_delta": rating - base,
                        f"{side}_qb_change": float(qb is not None and prev is not None and qb != prev)})
        rows.append(rec)
    out = feats.join(pl.DataFrame(rows), on=["game_id", "horizon"], how="left")
    ctx = games.select("game_id", "roof", "home_rest", "away_rest")
    out = out.join(ctx, on="game_id", how="left").with_columns(
        dome=pl.col("roof").is_in(["dome", "closed"]).cast(pl.Float64),
        home_off_bye=(pl.col("home_rest") >= 13).cast(pl.Float64), away_off_bye=(pl.col("away_rest") >= 13).cast(pl.Float64),
        home_short_week=(pl.col("home_rest") <= 5).cast(pl.Float64), away_short_week=(pl.col("away_rest") <= 5).cast(pl.Float64),
    ).drop("roof", "home_rest", "away_rest")
    # injuries: final horizon only (only the final weekly report survives historically)
    lost_cols = [f"lost_{u}" for u in UNITS]
    if avail is not None:
        fin_ids = out.filter(pl.col("horizon") == "final")["game_id"].unique().to_list()
        seasons = out["season"].unique().to_list()
        L = avail.unit_losses(fin_ids, seasons)
        for side in ("home", "away"):
            Ls = L.rename({"team": f"{side}_id", **{c: f"{side}_{c}" for c in lost_cols}})
            out = out.join(Ls.with_columns(horizon=pl.lit("final")), on=["game_id", f"{side}_id", "horizon"], how="left")
        # A final-horizon game with no report rows means no listed injuries (0), not missing data.
        out = out.with_columns([pl.when(pl.col("horizon") == "final").then(pl.col(f"{s}_{c}").fill_null(0.0))
                                .otherwise(None).alias(f"{s}_{c}") for s in ("home", "away") for c in lost_cols])
    return out
