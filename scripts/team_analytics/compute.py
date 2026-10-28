"""Team performance analytics entering a given week, from nflverse / nflfastR data.

Stand-alone analysis: it does not read or change the frozen forecasting model and uses no market data
(spread, total, moneyline and price columns are dropped on load).

    .venv\\Scripts\\python.exe scripts\\team_analytics\\compute.py --season 2026 --through-week 7

Downloads into data/cache/team_analytics/ (git-ignored) with a retrieval manifest, and writes CSV tables
plus bundle.json to reports/team_analytics/<season>_week<NN>/. Historical seasons (2021 to season-1)
are used only for (a) the prior-season stabilisation, (b) the empirically weighted composites, (c) the
EPA-to-win, field-goal, fumble-recovery and fourth-down reference models. Definitions are in METHOD below
and are repeated on the report's Method section.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from scipy.optimize import nnls
from sklearn.linear_model import LogisticRegression
import warnings

warnings.simplefilter("ignore", pd.errors.PerformanceWarning)

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from nflcast.data.policy import banned_columns  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import context as ctx  # noqa: E402
import callers  # noqa: E402

BASE = "https://github.com/nflverse/nflverse-data/releases/download/"
CACHE = ROOT / "data" / "cache" / "team_analytics"
MANIFEST: list[dict] = []
MARKET_COLS = {"spread_line", "total_line", "home_spread_odds", "away_spread_odds", "over_odds", "under_odds"}

EXPL_PASS, EXPL_RUN = 20, 10          # explosive thresholds (yards)
PYTH_EXP = 2.37                       # Pythagorean exponent for the NFL (Football Outsiders' published value)
ONE_SCORE = 8
MIN_QB_DROPBACKS = 100


# ----------------------------------------------------------------------------------------------- data
def fetch(rel: str, refresh: bool = False) -> pd.DataFrame:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / rel.replace("/", "__")
    meta_path = path.with_suffix(".meta.json")
    if refresh or not path.exists():
        r = requests.get(BASE + rel, timeout=600)
        r.raise_for_status()
        path.write_bytes(r.content)
        meta_path.write_text(json.dumps({
            "url": BASE + rel,
            "retrieved_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "http_last_modified": r.headers.get("Last-Modified"),
            "sha256": hashlib.sha256(r.content).hexdigest(),
            "bytes": len(r.content),
        }, indent=1))
    MANIFEST.append(json.loads(meta_path.read_text()))
    df = pd.read_parquet(path)
    drop = set(banned_columns(list(df.columns))) | (MARKET_COLS & set(df.columns))
    return df.drop(columns=sorted(drop))


PBP_COLS = [
    "play_id", "game_id", "home_team", "away_team", "season_type", "week", "posteam", "defteam", "yardline_100",
    "half_seconds_remaining", "game_seconds_remaining", "game_half", "qtr", "down", "goal_to_go", "ydstogo",
    "ydsnet", "desc", "play_type", "yards_gained", "qb_dropback", "qb_kneel", "qb_spike", "qb_scramble",
    "air_yards", "yards_after_catch", "field_goal_result", "kick_distance", "extra_point_result",
    "two_point_conv_result", "timeout", "timeout_team", "td_team", "posteam_score", "defteam_score",
    "score_differential", "total_home_score", "total_away_score", "ep", "epa", "wp", "first_down_rush",
    "first_down_pass", "first_down_penalty", "third_down_converted", "third_down_failed", "fourth_down_converted",
    "fourth_down_failed", "interception", "punt_blocked", "punt_inside_twenty", "touchback", "fumble_forced",
    "fumble_not_forced", "fumble_out_of_bounds", "safety", "penalty", "fumble_lost", "qb_hit", "rush_attempt",
    "pass_attempt", "sack", "touchdown", "pass_touchdown", "rush_touchdown", "return_touchdown",
    "extra_point_attempt", "two_point_attempt", "field_goal_attempt", "kickoff_attempt", "punt_attempt", "fumble",
    "complete_pass", "passer_player_id", "passing_yards", "rusher_player_id", "fumbled_1_team",
    "fumble_recovery_1_team", "return_team", "return_yards", "penalty_team", "penalty_yards", "penalty_type",
    "season", "cpoe", "special_teams_play", "fixed_drive", "fixed_drive_result", "drive_play_count",
    "drive_time_of_possession", "drive_start_transition", "home_score", "away_score", "location", "result",
    "success", "passer_id", "passer", "rusher_id", "pass", "rush", "first_down", "xyac_mean_yardage", "pass_oe",
    "kickoff_inside_twenty", "kickoff_in_endzone", "drive_first_downs", "series", "series_success", "time_of_day",
    "run_location", "run_gap",
]


def load_pbp(season: int, through_week: int | None = None) -> pd.DataFrame:
    p = fetch(f"pbp/play_by_play_{season}.parquet")
    p = p[[c for c in PBP_COLS if c in p.columns]]
    p = p[p.season_type == "REG"].copy()
    if through_week is not None:
        p = p[p.week <= through_week]
    return prep(p)


def prep(p: pd.DataFrame) -> pd.DataFrame:
    p = p.sort_values(["game_id", "play_id"]).reset_index(drop=True)
    p["is_home"] = np.where(p.location == "Neutral", 0, np.where(p.posteam == p.home_team, 1, -1))
    p["sc"] = (((p["pass"] == 1) | (p["rush"] == 1)) & p.epa.notna() & p.down.notna() & p.posteam.notna()
               & (p.qb_kneel != 1) & (p.qb_spike != 1))
    live = p.play_type.isin(["pass", "run"])
    p["live"] = live
    p["db"] = p.sc & (p["pass"] == 1)
    p["drush"] = p.sc & (p["rush"] == 1)                       # designed rush: nflfastR `rush` excludes scrambles
    p["drush_live"] = p.drush & (p.play_type == "run")
    p["scr"] = p.sc & (p.qb_scramble == 1)
    p["att"] = p.sc & (p.play_type == "pass") & (p.sack != 1) & (p.qb_scramble != 1)
    p["sackp"] = p.sc & (p.sack == 1)
    p["early"] = p.sc & (p.down <= 2)
    p["d3"] = p.sc & (p.down == 3)
    p["rz"] = p.sc & (p.yardline_100 <= 20)
    p["expl_pass"] = p.att & (p.yards_gained >= EXPL_PASS)
    p["expl_run"] = p.drush_live & (p.yards_gained >= EXPL_RUN)
    p["expl_scr"] = p.scr & live & (p.yards_gained >= EXPL_RUN)
    p["explosive"] = p.expl_pass | p.expl_run | p.expl_scr
    p["int_"] = p.sc & live & (p.interception == 1)
    p["fl"] = p.sc & live & (p.fumble_lost == 1)
    p["to"] = p.int_ | p.fl
    p["passing_yards"] = p.passing_yards.fillna(0)
    p["neutral"] = p.sc & p.wp.between(0.10, 0.90)
    # pre-play score of each team (total_*_score is the post-play score)
    g = p.groupby("game_id")
    p["home_pre"] = g.total_home_score.shift(1).fillna(0)
    p["away_pre"] = g.total_away_score.shift(1).fillna(0)
    # quarterbacks: anyone with >= 5 dropbacks as passer in the data window
    qb_ids = p[p.db].groupby("passer_id").size()
    qb_ids = set(qb_ids[qb_ids >= 5].index)
    p["qb_drun"] = p.drush & p.rusher_player_id.isin(qb_ids)
    p["rb_drun"] = p.drush & ~p.qb_drun
    return p


def ag(df: pd.DataFrame, by: str, specs: dict) -> pd.DataFrame:
    """specs: name -> (value column or None, mask column or None, 'mean' | 'sum' | 'count')."""
    out = {}
    key = df[by]
    for name, (val, mask, how) in specs.items():
        m = df[mask].astype(bool) if mask else pd.Series(True, index=df.index)
        if how == "count":
            out[name] = m.groupby(key).sum()
        else:
            v = df[val].astype(float)
            out[name] = (v.where(m, 0).groupby(key).sum() if how == "sum" else v.where(m).groupby(key).mean())
    return pd.DataFrame(out)


# ------------------------------------------------------------------------------ opponent adjustment
def adjust(df: pd.DataFrame, y: str, teams: list[str]) -> dict:
    """Least squares y ~ intercept + home + offence(team) + defence(team), sum-to-zero team effects, no
    shrinkage. Returns per-team adjusted values on the raw scale (league mean + effect), opponent strength
    faced and the home coefficient."""
    d = df[df[y].notna()]
    idx = {t: i for i, t in enumerate(teams)}
    n, T = len(d), len(teams)
    X = np.zeros((n + 2, 2 + 2 * T))
    X[:n, 0] = 1
    X[:n, 1] = d.is_home.values
    X[np.arange(n), 2 + d.posteam.map(idx).values] = 1
    X[np.arange(n), 2 + T + d.defteam.map(idx).values] = 1
    X[n, 2:2 + T] = 1e3
    X[n + 1, 2 + T:] = 1e3
    yv = np.concatenate([d[y].astype(float).values, [0, 0]])
    coef, *_ = np.linalg.lstsq(X, yv, rcond=None)
    off = pd.Series(coef[2:2 + T], index=teams)
    de = pd.Series(coef[2 + T:], index=teams)
    resid = yv[:n] - X[:n] @ coef
    mean = float(d[y].mean())
    sos_off = d.defteam.map(de).groupby(d.posteam).mean()     # >0: faced defences that allow more (easier)
    sos_def = d.posteam.map(off).groupby(d.defteam).mean()    # >0: faced offences that produce more (harder)
    return {"off": mean + off, "def": mean + de, "off_eff": off, "def_eff": de, "home": float(coef[1]),
            "sos_off": sos_off, "sos_def": sos_def, "resid_var": float(resid.var()), "mean": mean}


# --------------------------------------------------------------------------------------- drives
def top_seconds(s):
    if not isinstance(s, str) or ":" not in s:
        return np.nan
    m, sec = s.split(":")[:2]
    return int(m) * 60 + int(sec)


def build_drives(p: pd.DataFrame) -> pd.DataFrame:
    d = p[p.fixed_drive.notna() & p.posteam.notna()].copy()
    d["scrim"] = d.down.notna() & d.play_type.isin(["pass", "run", "punt", "field_goal", "no_play", "qb_kneel",
                                                     "qb_spike"])
    d["kneel"] = d.play_type == "qb_kneel"
    d["off_play"] = d.sc
    key = ["game_id", "fixed_drive"]
    first = d.groupby(key).head(1).set_index(key)
    scr = d[d.scrim]
    fs = scr.groupby(key).head(1).set_index(key)
    agg = scr.groupby(key).agg(n_scrim=("scrim", "size"), n_kneel=("kneel", "sum"), min_yl=("yardline_100", "min"),
                               g2g=("goal_to_go", "max"), n_off=("off_play", "sum"))
    dr = pd.DataFrame({
        "game_id": [k[0] for k in fs.index], "fixed_drive": [k[1] for k in fs.index],
        "week": fs.week.values, "posteam": fs.posteam.values, "defteam": fs.defteam.values,
        "home_team": fs.home_team.values, "start_yl": fs.yardline_100.values, "ep_start": fs.ep.values,
        "start_half_sec": fs.half_seconds_remaining.values, "qtr": fs.qtr.values, "game_half": fs.game_half.values,
        "result": first.loc[fs.index, "fixed_drive_result"].values,
        "transition": first.loc[fs.index, "drive_start_transition"].values,
        "plays": first.loc[fs.index, "drive_play_count"].values, "yards": first.loc[fs.index, "ydsnet"].values,
        "top_sec": [top_seconds(x) for x in first.loc[fs.index, "drive_time_of_possession"].values],
        "home_pre": first.loc[fs.index, "home_pre"].values, "away_pre": first.loc[fs.index, "away_pre"].values,
        "first_downs": first.loc[fs.index, "drive_first_downs"].values,
        "start_wall": first.loc[fs.index, "time_of_day"].values,
        "end_wall": d.groupby(key).time_of_day.last().reindex(fs.index).values,
    })
    dr = dr.join(agg, on=key)
    dr = dr.sort_values(key).reset_index(drop=True)
    # score at the start of the next drive in the game (final score after the last drive)
    finals = p.groupby("game_id")[["total_home_score", "total_away_score"]].max()
    nxt_h = dr.groupby("game_id").home_pre.shift(-1)
    nxt_a = dr.groupby("game_id").away_pre.shift(-1)
    dr["home_end"] = nxt_h.fillna(dr.game_id.map(finals.total_home_score))
    dr["away_end"] = nxt_a.fillna(dr.game_id.map(finals.total_away_score))
    is_home = dr.posteam == dr.home_team
    dr["pts"] = np.where(is_home, dr.home_end - dr.home_pre, dr.away_end - dr.away_pre)       # offence points
    dr["opp_pts_during"] = np.where(is_home, dr.away_end - dr.away_pre, dr.home_end - dr.home_pre)  # return TDs, safeties
    dr["pts"] = dr.pts.clip(lower=0)
    dr["td"] = (dr.result == "Touchdown").astype(int)
    dr["fg"] = (dr.result == "Field goal").astype(int)
    dr["punt"] = (dr.result == "Punt").astype(int)
    dr["turnover"] = dr.result.isin(["Turnover", "Opp touchdown"]).astype(int)
    dr["downs"] = (dr.result == "Turnover on downs").astype(int)
    dr["rz_trip"] = (dr.min_yl <= 20).astype(int)
    dr["g2g_trip"] = (dr.g2g == 1).astype(int)
    dr["rz_td"] = dr.rz_trip * dr.td
    dr["g2g_td"] = dr.g2g_trip * dr.td
    dr["pts_over_ep"] = dr.pts - dr.ep_start
    dr["excluded"] = ((dr.n_kneel == dr.n_scrim) | (dr.start_half_sec <= 30) | (dr.n_off == 0) & (dr.n_kneel > 0))
    return dr


def drive_table(dr: pd.DataFrame, side: str) -> pd.DataFrame:
    key = "posteam" if side == "off" else "defteam"
    d = dr[~dr.excluded]
    g = d.groupby(key)
    t = pd.DataFrame({
        "drives": g.size(), "ppd": g.pts.mean(), "td_pd": g.td.mean(), "fg_pd": g.fg.mean(), "punt_pd": g.punt.mean(),
        "to_pd": g.turnover.mean(), "downs_pd": g.downs.mean(), "start_yl": g.start_yl.mean(),
        "start_own": 100 - g.start_yl.mean(), "plays_pd": g.plays.mean(), "yards_pd": g.yards.mean(),
        "top_pd": g.top_sec.mean(), "ep_start": g.ep_start.mean(), "pts_over_ep": g.pts_over_ep.mean(),
        "rz_trips": g.rz_trip.sum(), "rz_td_rate": g.rz_td.sum() / g.rz_trip.sum(),
        "rz_trips_pd": g.rz_trip.mean(), "g2g_trips": g.g2g_trip.sum(), "g2g_td_rate": g.g2g_td.sum() / g.g2g_trip.sum(),
        "pts_per_rz_trip": d[d.rz_trip == 1].groupby(key).pts.mean(),
    })
    t["excluded_drives"] = dr[dr.excluded].groupby(key).size().reindex(t.index).fillna(0)
    return t.add_prefix(f"{side}_")


# ------------------------------------------------------------------------------------- unit metrics
UNIT_SPECS = {
    "plays": (None, "sc", "count"), "epa_play": ("epa", "sc", "mean"), "sr": ("success", "sc", "mean"),
    "epa_play_neutral": ("epa", "neutral", "mean"),
    "dropbacks": (None, "db", "count"), "epa_db": ("epa", "db", "mean"), "sr_db": ("success", "db", "mean"),
    "rushes": (None, "drush", "count"), "epa_rush": ("epa", "drush", "mean"), "sr_rush": ("success", "drush", "mean"),
    "early_epa": ("epa", "early", "mean"), "early_sr": ("success", "early", "mean"),
    "d3_epa": ("epa", "d3", "mean"), "rz_epa": ("epa", "rz", "mean"),
    "expl_rate": ("explosive", "sc", "mean"), "expl_pass_rate": ("expl_pass", "att", "mean"),
    "expl_run_rate": ("expl_run", "drush_live", "mean"), "n_expl_pass": (None, "expl_pass", "count"),
    "n_expl_run": (None, "expl_run", "count"), "n_explosive": (None, "explosive", "count"),
    "epa_on_explosive": ("epa", "explosive", "sum"), "epa_total": ("epa", "sc", "sum"), "epa_pos": ("epa_pos", "sc", "sum"),
    "to_epa_sum": ("epa", "to", "sum"), "n_int": (None, "int_", "count"), "n_fl_scrim": (None, "fl", "count"),
    "attempts": (None, "att", "count"), "sacks": (None, "sackp", "count"), "cpoe": ("cpoe", "att", "mean"),
    "pass_yds": ("passing_yards", "att", "sum"), "pass_fd": ("first_down_pass", "db", "mean"),
    "pass_td": ("pass_touchdown", "att", "sum"), "adot": ("air_yards", "att", "mean"),
    "scrambles": (None, "scr", "count"), "epa_scr": ("epa", "scr", "mean"),
    "qb_runs": (None, "qb_drun", "count"), "epa_qb_run": ("epa", "qb_drun", "mean"),
    "rb_runs": (None, "rb_drun", "count"), "epa_rb_run": ("epa", "rb_drun", "mean"), "sr_rb_run": ("success", "rb_drun", "mean"),
    "ypc": ("yards_gained", "drush_live", "mean"), "rush_fd": ("first_down", "drush", "mean"),
    "early_db_epa": ("epa", "early_db", "mean"), "early_rush_epa": ("epa", "early_rush", "mean"),
    "stuff_rate": ("stuffed", "drush_live", "mean"), "sy_conv": ("conv", "sy_rush", "mean"), "sy_n": (None, "sy_rush", "count"),
    "gl_td": ("rush_touchdown", "gl_rush", "mean"), "gl_n": (None, "gl_rush", "count"),
    "d3_conv": ("third_down_converted", "d3_flag", "mean"), "d3_n": (None, "d3_flag", "count"),
    "d4_conv": ("fourth_down_converted", "d4_flag", "mean"), "d4_n": (None, "d4_flag", "count"),
    "hit_or_sack_rate": ("hit_sack", "db", "mean"), "epa_db_clean": ("epa", "db_clean", "mean"),
    "epa_db_hit": ("epa", "db_hit", "mean"), "d3_db_epa": ("epa", "d3_db", "mean"), "rz_db_epa": ("epa", "rz_db", "mean"),
    "yacoe": ("yacoe", "comp", "mean"),
    "expl_td": ("touchdown", "explosive", "sum"), "deep_att": (None, "deep", "count"), "deep_epa": ("epa", "deep", "mean"),
    "deep_comp": ("complete_pass", "deep", "mean"),
}


def add_unit_flags(p: pd.DataFrame) -> pd.DataFrame:
    p["early_db"] = p.early & p.db
    p["early_rush"] = p.early & p.drush
    p["d3_db"] = p.d3 & p.db
    p["rz_db"] = p.rz & p.db
    p["stuffed"] = (p.yards_gained <= 0).astype(float)
    p["sy_rush"] = p.drush & p.down.isin([3, 4]) & (p.ydstogo <= 2)
    p["conv"] = ((p.first_down == 1) | (p.touchdown == 1)).astype(float)
    p["gl_rush"] = p.drush & (p.yardline_100 <= 3)
    p["d3_flag"] = p.sc & ((p.third_down_converted == 1) | (p.third_down_failed == 1))
    p["d4_flag"] = p.sc & ((p.fourth_down_converted == 1) | (p.fourth_down_failed == 1))
    p["hit_sack"] = ((p.qb_hit == 1) | (p.sack == 1)).astype(float)
    p["db_clean"] = p.db & (p.hit_sack == 0)
    p["db_hit"] = p.db & (p.hit_sack == 1)
    p["comp"] = p.att & (p.complete_pass == 1) & p.xyac_mean_yardage.notna()
    p["yacoe"] = p.yards_after_catch - p.xyac_mean_yardage
    p["deep"] = p.att & (p.air_yards >= 20)
    p["epa_pos"] = p.epa.clip(lower=0)
    return p


def unit_table(p: pd.DataFrame, side: str) -> pd.DataFrame:
    key = "posteam" if side == "off" else "defteam"
    t = ag(p, key, UNIT_SPECS)
    t["sack_rate"] = t.sacks / t.dropbacks
    t["int_rate"] = t.n_int / t.attempts
    t["ypa"] = t.pass_yds / t.attempts
    sack_yds = p[p.sackp].groupby(key).yards_gained.sum()
    t["nya"] = (t.pass_yds + sack_yds.reindex(t.index).fillna(0)) / (t.attempts + t.sacks)
    t["scr_rate"] = t.scrambles / t.dropbacks
    t["pass_rate"] = t.dropbacks / t.plays
    t["expl_epa_share"] = t.epa_on_explosive / t.epa_pos          # share of all positive EPA that came on explosive plays
    t["epa_nonexpl"] = (t.epa_total - t.epa_on_explosive) / (t.plays - t.n_explosive)
    t["to_epa_play"] = t.to_epa_sum / t.plays
    t["epa_nonto"] = (t.epa_total - t.to_epa_sum) / (t.plays - t.n_int - t.n_fl_scrim)
    nonexpl = p[p.sc & ~p.explosive]
    t["sr_nonexpl"] = nonexpl.groupby(key).success.mean()
    return t.add_prefix(f"{side}_")


# ---------------------------------------------------------------------------- historical references
def season_summary(p: pd.DataFrame, teams: list[str]) -> dict:
    """Adjusted offence/defence EPA per play and success rate for one season window."""
    sc = p[p.sc]
    a_epa = adjust(sc, "epa", teams)
    a_sr = adjust(sc, "success", teams)
    dr = build_drives(p)
    ppd_o = dr[~dr.excluded].groupby("posteam").pts.mean()
    ppd_d = dr[~dr.excluded].groupby("defteam").pts.mean()
    return {"a_epa": a_epa, "a_sr": a_sr, "ppd_o": ppd_o, "ppd_d": ppd_d, "n_off": sc.groupby("posteam").size(),
            "n_def": sc.groupby("defteam").size()}


def zs(s: pd.Series) -> pd.Series:
    return (s - s.mean()) / s.std(ddof=0)


def history(seasons: list[int], early_weeks: int) -> dict:
    rows, prior_pairs, games, fg, fourth, fum = [], [], [], [], [], []
    full = {}
    for s in seasons:
        p = add_unit_flags(load_pbp(s))
        teams = sorted(p.posteam.dropna().unique())
        e = season_summary(p[p.week <= early_weeks], teams)
        late = p[p.week > early_weeks]
        l_epa = adjust(late[late.sc], "epa", teams)
        f = season_summary(p, teams)
        full[s] = f
        for t in teams:
            rows.append({"season": s, "team": t,
                         "o_epa": e["a_epa"]["off"][t], "o_sr": e["a_sr"]["off"][t], "o_ppd": e["ppd_o"].get(t),
                         "d_epa": e["a_epa"]["def"][t], "d_sr": e["a_sr"]["def"][t], "d_ppd": e["ppd_d"].get(t),
                         "o_late": l_epa["off"][t], "d_late": l_epa["def"][t],
                         "o_full": f["a_epa"]["off"][t], "d_full": f["a_epa"]["def"][t],
                         "n_off_full": f["n_off"][t], "n_def_full": f["n_def"][t]})
        # game-level net EPA (scrimmage + special teams) vs result
        games.append(game_net_epa(p).assign(season=s))
        fga = p[(p.field_goal_attempt == 1) & p.kick_distance.notna()]
        fg.append(pd.DataFrame({"dist": fga.kick_distance, "made": (fga.field_goal_result == "made").astype(int),
                                "season": s}))
        fd = p[(p.down == 4) & p.play_type.isin(["pass", "run", "punt", "field_goal"]) & p.epa.notna()
               & p.wp.between(0.2, 0.8) & (p.half_seconds_remaining > 120) & (p.qb_kneel != 1)]
        fourth.append(fd[["ydstogo", "yardline_100", "play_type", "ep", "epa"]])
        fb = p[p.sc & p.live & (p.fumble == 1) & (p.fumble_out_of_bounds != 1) & p.fumble_recovery_1_team.notna()]
        fum.append(pd.DataFrame({"lost": (fb.fumble_recovery_1_team != fb.fumbled_1_team).astype(int)}))
    H = pd.DataFrame(rows)
    return {"teams": H, "games": pd.concat(games), "fg": pd.concat(fg), "fourth": pd.concat(fourth),
            "fum_lost_rate": float(pd.concat(fum).lost.mean()), "full": full}


def st_mask(p):
    return p.play_type.isin(["kickoff", "punt", "field_goal", "extra_point"]) & p.epa.notna() & p.posteam.notna()


def game_net_epa(p: pd.DataFrame) -> pd.DataFrame:
    sc = p[p.sc]
    st = p[st_mask(p)]
    off = sc.groupby(["game_id", "posteam"]).epa.sum()
    st_o = st.groupby(["game_id", "posteam"]).epa.sum()
    gm = p.groupby("game_id").agg(home=("home_team", "first"), away=("away_team", "first"),
                                  hs=("home_score", "first"), as_=("away_score", "first"))
    out = []
    for gid, r in gm.iterrows():
        for team, opp, pf, pa in [(r.home, r.away, r.hs, r.as_), (r.away, r.home, r.as_, r.hs)]:
            net = off.get((gid, team), 0) - off.get((gid, opp), 0) + st_o.get((gid, team), 0) - st_o.get((gid, opp), 0)
            out.append({"game_id": gid, "team": team, "opp": opp, "net_epa": net, "pf": pf, "pa": pa,
                        "win": 1.0 if pf > pa else (0.0 if pf < pa else 0.5)})
    return pd.DataFrame(out)


def fit_composite(H: pd.DataFrame, side: str) -> dict:
    cols = [f"{side}_epa", f"{side}_sr", f"{side}_ppd"]
    sign = 1 if side == "o" else -1
    Z = H.groupby("season")[cols].transform(zs) * sign
    y = H.groupby("season")[f"{side}_late"].transform(zs) * sign
    w, _ = nnls(Z.values, y.values)
    pred = Z.values @ w
    r2 = 1 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    single = {c: float(np.corrcoef(Z[c], y)[0, 1] ** 2) for c in cols}
    return {"weights": dict(zip(cols, (w / w.sum()).round(3))), "raw_coef": dict(zip(cols, w.round(3))),
            "r2": float(r2), "single_r2": single, "n": int(len(H))}


def fit_prior(H: pd.DataFrame, side: str, play_var: float) -> dict:
    x = H.pivot(index="team", columns="season", values=f"{side}_full")
    n = H.pivot(index="team", columns="season", values=f"n_{'off' if side == 'o' else 'def'}_full")
    xs, ys, noise = [], [], []
    seasons = sorted(x.columns)
    for a, b in zip(seasons[:-1], seasons[1:]):
        xa, xb = x[a] - x[a].mean(), x[b] - x[b].mean()
        xs.append(xa)
        ys.append(xb)
        noise.append(play_var / n[b])
    X, Y, N = pd.concat(xs), pd.concat(ys), pd.concat(noise)
    slope = float((X * Y).sum() / (X * X).sum())
    resid_var = float(((Y - slope * X) ** 2).mean())
    tau2 = max(resid_var - float(N.mean()), 1e-5)
    return {"slope": slope, "resid_var": resid_var, "tau2": tau2, "pairs": len(X)}


# ------------------------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, default=2026)
    ap.add_argument("--through-week", type=int, default=7)
    ap.add_argument("--first-history", type=int, default=2021)
    args = ap.parse_args()
    S, W = args.season, args.through_week
    out_dir = ROOT / "reports" / "team_analytics" / f"{S}_week{W + 1:02d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    qc: list[str] = []

    p = add_unit_flags(load_pbp(S, W))
    teams = sorted(p.posteam.dropna().unique())
    assert len(teams) == 32, teams
    sched = fetch("schedules/games.parquet")
    sched = sched[(sched.season == S) & (sched.game_type == "REG")]
    played = sched[(sched.week <= W)]
    n_games_sched = len(played)
    n_games_pbp = p.game_id.nunique()
    qc.append(f"Schedule lists {n_games_sched} regular-season games in weeks 1-{W}; play-by-play contains "
              f"{n_games_pbp}; {int(played.result.notna().sum())} have final scores.")
    if n_games_pbp != n_games_sched:
        qc.append("WARNING: play-by-play game count differs from the schedule.")

    # ---- history
    hist_seasons = list(range(args.first_history, S))
    print("history", hist_seasons, flush=True)
    H = history(hist_seasons, W)
    comp_o = fit_composite(H["teams"], "o")
    comp_d = fit_composite(H["teams"], "d")

    # ---- units, adjustment
    sc = p[p.sc]
    off, de = unit_table(p, "off"), unit_table(p, "def")
    T = pd.DataFrame(index=teams).join(off).join(de)
    adj = {}
    for name, mask, y in [("epa", "sc", "epa"), ("sr", "sc", "success"), ("epa_db", "db", "epa"),
                          ("epa_rush", "drush", "epa"), ("sr_db", "db", "success"), ("sr_rush", "drush", "success"),
                          ("early_epa", "early", "epa")]:
        a = adjust(p[p[mask]], y, teams)
        adj[name] = a
        T[f"off_adj_{name}"] = a["off"]
        T[f"def_adj_{name}"] = a["def"]
    T["sos_off"] = adj["epa"]["sos_off"]
    T["sos_def"] = adj["epa"]["sos_def"]
    net_eff = adj["epa"]["off_eff"] - adj["epa"]["def_eff"]          # EPA/play net strength of each team
    T["adj_net_epa"] = T.off_adj_epa - T.def_adj_epa
    T["raw_net_epa"] = T.off_epa_play - T.def_epa_play
    home_coef = adj["epa"]["home"]
    qc.append(f"Opponent adjustment: home-field coefficient {home_coef:+.3f} EPA/play for the offence "
              f"(half the home/away gap); play-level residual variance {adj['epa']['resid_var']:.3f}.")

    # ---- drives
    dr = build_drives(p)
    T = T.join(drive_table(dr, "off")).join(drive_table(dr, "def"))
    drive_pts = dr.groupby("game_id").pts.sum() + dr.groupby("game_id").opp_pts_during.sum()
    finals = played.set_index("game_id")
    tot = (finals.home_score + finals.away_score).reindex(drive_pts.index)
    mism = (drive_pts - tot).abs()
    qc.append(f"Drive points reconcile with final scores in {int((mism < 0.5).sum())} of {len(mism)} games "
              f"(max gap {mism.max():.0f} pts; gaps come from scores on plays outside a scrimmage drive).")
    qc.append(f"Drives: {len(dr)} built, {int(dr.excluded.sum())} excluded (kneel-only, or started with 30 s or "
              f"less left in a half).")

    # ---- records / luck
    rec = []
    for t in teams:
        g = played[(played.home_team == t) | (played.away_team == t)].copy()
        home = g.home_team == t
        pf = np.where(home, g.home_score, g.away_score)
        pa = np.where(home, g.away_score, g.home_score)
        opp = np.where(home, g.away_team, g.home_team)
        margin = pf - pa
        ot = g.overtime.fillna(0).astype(int).values == 1
        rec.append({"team": t, "games": len(g), "w": int((margin > 0).sum()), "l": int((margin < 0).sum()),
                    "t": int((margin == 0).sum()), "pf": int(pf.sum()), "pa": int(pa.sum()),
                    "one_w": int(((margin > 0) & (abs(margin) <= ONE_SCORE)).sum()),
                    "one_l": int(((margin < 0) & (abs(margin) <= ONE_SCORE)).sum()),
                    "three_w": int(((margin > 0) & (abs(margin) <= 3)).sum()),
                    "three_l": int(((margin < 0) & (abs(margin) <= 3)).sum()),
                    "ot_w": int(((margin > 0) & ot).sum()), "ot_l": int(((margin < 0) & ot).sum()),
                    "home_w": int(((margin > 0) & home.values).sum()), "home_g": int(home.sum()),
                    "opp_list": list(opp), "margins": list(map(int, margin))})
    R = pd.DataFrame(rec).set_index("team")
    R["win_pct"] = (R.w + 0.5 * R.t) / R.games
    R["pyth_xw"] = R.games * R.pf ** PYTH_EXP / (R.pf ** PYTH_EXP + R.pa ** PYTH_EXP)
    R["pt_diff_pg"] = (R.pf - R.pa) / R.games
    G = game_net_epa(p)
    hg = H["games"][H["games"].win != 0.5]
    lr = LogisticRegression(fit_intercept=False, C=1e6).fit(hg[["net_epa"]], hg.win)
    G["xwin"] = lr.predict_proba(G[["net_epa"]])[:, 1]
    R["eff_xw"] = G.groupby("team").xwin.sum()
    R["w_minus_pyth"] = R.w + 0.5 * R.t - R.pyth_xw
    R["w_minus_eff"] = R.w + 0.5 * R.t - R.eff_xw
    R["luck_index"] = (R.w_minus_pyth + R.w_minus_eff) / 2
    epa_win_coef = float(lr.coef_[0][0])
    # strength of schedule (average opponent net adjusted EPA/play, game-weighted)
    R["sos_net"] = [np.mean([net_eff[o] for o in R.loc[t, "opp_list"]]) for t in teams]
    R["opp_record_pct"] = [np.mean([R.loc[o, "win_pct"] for o in R.loc[t, "opp_list"]]) for t in teams]
    T = T.join(R.drop(columns=["opp_list", "margins"]))

    # opponent tiers (terciles of net adjusted EPA/play) and home/away, wins vs winning teams
    tiers = pd.qcut(net_eff.rank(method="first"), 3, labels=["weak", "average", "strong"])
    G["opp_tier"] = G.opp.map(tiers)
    G["off_epa_play"] = [sc[(sc.game_id == g) & (sc.posteam == t)].epa.mean() for g, t in zip(G.game_id, G.team)]
    G["def_epa_play"] = [sc[(sc.game_id == g) & (sc.defteam == t)].epa.mean() for g, t in zip(G.game_id, G.team)]
    G["net_epa_play"] = G.off_epa_play - G.def_epa_play
    G["week"] = G.game_id.str[5:7].astype(int)
    G["home"] = [played.set_index("game_id").loc[g, "home_team"] == t for g, t in zip(G.game_id, G.team)]
    G["opp_winning"] = G.opp.map(R.win_pct > 0.5)
    for tier in ["strong", "average", "weak"]:
        sub = G[G.opp_tier == tier]
        T[f"net_vs_{tier}"] = sub.groupby("team").net_epa_play.mean()
        T[f"g_vs_{tier}"] = sub.groupby("team").size()
        T[f"w_vs_{tier}"] = sub.groupby("team").win.sum()
    T["net_home"] = G[G.home].groupby("team").net_epa_play.mean()
    T["net_away"] = G[~G.home].groupby("team").net_epa_play.mean()
    T["w_vs_winning"] = G[G.opp_winning].groupby("team").win.sum()
    T["g_vs_winning"] = G[G.opp_winning].groupby("team").size()
    T["net_sd"] = G.groupby("team").net_epa_play.std()
    T["off_sd"] = G.groupby("team").off_epa_play.std()
    T["def_sd"] = G.groupby("team").def_epa_play.std()
    T["opp_net_beaten"] = G[G.win == 1].groupby("team").opp.apply(lambda s: np.mean([net_eff[o] for o in s]))
    T["opp_net_lost"] = G[G.win == 0].groupby("team").opp.apply(lambda s: np.mean([net_eff[o] for o in s]))

    # close-game / high-leverage plays: Q4 or OT with score within one score
    close = sc[(sc.qtr >= 4) & (sc.score_differential.abs() <= ONE_SCORE)]
    T["close_off_epa"] = close.groupby("posteam").epa.mean()
    T["close_def_epa"] = close.groupby("defteam").epa.mean()
    T["close_n"] = close.groupby("posteam").size() + close.groupby("defteam").size()

    # ---- special teams
    st = p[st_mask(p)]
    st_for = st.groupby("posteam").epa.sum() - st.groupby("defteam").epa.sum()
    T["st_epa_pg"] = st_for / T.games
    for kind in ["kickoff", "punt", "field_goal", "extra_point"]:
        s2 = st[st.play_type == kind]
        T[f"st_{kind}_epa_pg"] = (s2.groupby("posteam").epa.sum().reindex(teams).fillna(0)
                                  - s2.groupby("defteam").epa.sum().reindex(teams).fillna(0)) / T.games
    fgh = H["fg"][H["fg"].season >= S - 3]
    fg_lr = LogisticRegression(C=1e6).fit(fgh[["dist"]], fgh.made)
    fga = p[(p.field_goal_attempt == 1) & p.kick_distance.notna()].copy()
    fga["p"] = fg_lr.predict_proba(fga[["kick_distance"]].rename(columns={"kick_distance": "dist"}))[:, 1]
    fga["made"] = (fga.field_goal_result == "made").astype(int)
    fga["band"] = pd.cut(fga.kick_distance, [0, 39, 49, 99], labels=["u40", "40_49", "50p"])
    g = fga.groupby("posteam")
    T["fg_att"], T["fg_made"] = g.size(), g.made.sum()
    T["fg_pct"] = T.fg_made / T.fg_att
    T["fg_pts_oe"] = 3 * (g.made.sum() - g.p.sum())
    T["fg_pts_oe_against"] = 3 * (fga.groupby("defteam").made.sum() - fga.groupby("defteam").p.sum())
    for b in ["u40", "40_49", "50p"]:
        sb = fga[fga.band == b].groupby("posteam")
        T[f"fg_{b}"] = sb.made.sum().astype(int).astype(str) + "/" + sb.size().astype(str)
    xp = p[p.extra_point_attempt == 1]
    T["xp_att"] = xp.groupby("posteam").size()
    T["xp_pct"] = (xp.extra_point_result == "good").groupby(xp.posteam).mean()
    pu = p[(p.punt_attempt == 1) & (p.play_type == "punt")].copy()
    pu["net"] = pu.kick_distance.fillna(0) - pu.return_yards.fillna(0) - 20 * pu.touchback.fillna(0)
    T["punts"] = pu.groupby("posteam").size()
    T["punt_gross"] = pu.groupby("posteam").kick_distance.mean()
    T["punt_net"] = pu.groupby("posteam").net.mean()
    T["punt_in20"] = pu.groupby("posteam").punt_inside_twenty.mean()
    T["opp_punt_net"] = pu.groupby("defteam").net.mean()
    T["punt_ret_avg"] = pu[pu.return_yards > 0].groupby("defteam").return_yards.mean()
    ko = p[(p.kickoff_attempt == 1) & (p.play_type == "kickoff")]
    T["ko_tb_rate"] = ko.groupby("defteam").touchback.mean()           # kicking team = defteam on kickoffs
    T["ko_ret_avg"] = ko[ko.return_yards > 0].groupby("posteam").return_yards.mean()
    T["ko_ret_avg_allowed"] = ko[ko.return_yards > 0].groupby("defteam").return_yards.mean()
    kd = dr[dr.transition == "KICKOFF"]
    T["start_after_ko"] = 100 - kd.groupby("posteam").start_yl.mean()
    T["opp_start_after_ko"] = 100 - kd.groupby("defteam").start_yl.mean()
    pdv = dr[dr.transition == "PUNT"]
    T["start_after_punt"] = 100 - pdv.groupby("posteam").start_yl.mean()
    T["st_td"] = p[(p.return_touchdown == 1) & p.play_type.isin(["kickoff", "punt"])].groupby("td_team").size()
    T["st_td_allowed"] = (p[(p.return_touchdown == 1) & p.play_type.isin(["kickoff", "punt"])]
                          .assign(opp=lambda x: np.where(x.td_team == x.posteam, x.defteam, x.posteam))
                          .groupby("opp").size())
    blocks = p[(p.punt_blocked == 1) | (p.field_goal_result == "blocked") | (p.extra_point_result == "blocked")]
    T["blocks_made"] = blocks.groupby("defteam").size()
    T["blocks_allowed"] = blocks.groupby("posteam").size()

    # ---- combined team rating (points per game scale)
    plays_pg = float(sc.groupby(["game_id", "posteam"]).size().mean())
    T["rating_off_pg"] = (T.off_adj_epa - adj["epa"]["mean"]) * plays_pg
    T["rating_def_pg"] = (adj["epa"]["mean"] - T.def_adj_epa) * plays_pg
    T["rating_pg"] = T.rating_off_pg + T.rating_def_pg + T.st_epa_pg

    # ---- prior-season stabilisation
    play_var = adj["epa"]["resid_var"]
    pri_o, pri_d = fit_prior(H["teams"], "o", play_var), fit_prior(H["teams"], "d", play_var)
    last = H["teams"][H["teams"].season == S - 1].set_index("team")
    for side, pri, col, ncol in [("off", pri_o, "o_full", "off_plays"), ("def", pri_d, "d_full", "def_plays")]:
        x26 = T[f"{side}_adj_epa"]
        m26 = adj["epa"]["mean"]
        prior = m26 + pri["slope"] * (last[col] - last[col].mean())
        w = pri["tau2"] / (pri["tau2"] + play_var / T[ncol])
        T[f"{side}_prior_2025"] = prior
        T[f"{side}_w2026"] = w
        T[f"{side}_stab_epa"] = w * x26 + (1 - w) * prior
    T["stab_rating_pg"] = ((T.off_stab_epa - adj["epa"]["mean"]) + (adj["epa"]["mean"] - T.def_stab_epa)) * plays_pg + T.st_epa_pg

    # ---- composites (weights fitted on history, applied to 2026 z-scores)
    def comp(side, wts):
        s = 1 if side == "off" else -1
        parts = {f"{'o' if side == 'off' else 'd'}_epa": T[f"{side}_adj_epa"], f"{'o' if side == 'off' else 'd'}_sr": T[f"{side}_adj_sr"],
                 f"{'o' if side == 'off' else 'd'}_ppd": T[f"{side}_ppd"]}
        return sum(wts[k] * zs(v) * s for k, v in parts.items())
    T["off_composite"] = comp("off", comp_o["weights"])
    T["def_composite"] = comp("def", comp_d["weights"])
    # situational: late-down conversion (3rd+4th) and red-zone TD rate, equal weight
    T["off_late_conv"] = (p[p.d3_flag | p.d4_flag].assign(c=lambda x: ((x.third_down_converted == 1) | (x.fourth_down_converted == 1)).astype(int))
                          .groupby("posteam").c.mean())
    T["def_late_conv"] = (p[p.d3_flag | p.d4_flag].assign(c=lambda x: ((x.third_down_converted == 1) | (x.fourth_down_converted == 1)).astype(int))
                          .groupby("defteam").c.mean())
    T["off_situational"] = (zs(T.off_late_conv) + zs(T.off_rz_td_rate)) / 2
    T["def_situational"] = (-zs(T.def_late_conv) - zs(T.def_rz_td_rate)) / 2

    # ---- turnovers
    to_rows = p[p.live & p.epa.notna() & ((p.interception == 1) | ((p.fumble == 1) & p.fumble_recovery_1_team.notna()))].copy()
    to_rows["int_by"] = np.where(to_rows.interception == 1, to_rows.defteam, None)
    fumb = p[(p.fumble == 1) & p.fumbled_1_team.notna() & p.fumble_recovery_1_team.notna()
             & (p.play_type != "no_play")]
    fumb_lost = fumb[fumb.fumble_recovery_1_team != fumb.fumbled_1_team]
    ints = p[(p.interception == 1) & (p.play_type == "pass")]
    T["int_thrown"] = ints.groupby("posteam").size()
    T["int_made"] = ints.groupby("defteam").size()
    T["fum_lost"] = fumb_lost.groupby("fumbled_1_team").size()
    T["fum_taken"] = fumb_lost.groupby("fumble_recovery_1_team").size()
    T = T.fillna({c: 0 for c in ["int_thrown", "int_made", "fum_lost", "fum_taken", "st_td", "st_td_allowed",
                                 "blocks_made", "blocks_allowed"]})
    T["giveaways"] = T.int_thrown + T.fum_lost
    T["takeaways"] = T.int_made + T.fum_taken
    T["to_margin"] = T.takeaways - T.giveaways
    T["to_margin_pg"] = T.to_margin / T.games
    T["to_margin_pd"] = T.to_margin / ((T.off_drives + T.def_drives) / 2)
    T["giveaway_rate"] = T.giveaways / T.off_plays
    T["takeaway_rate"] = T.takeaways / T.def_plays
    fb_all = fumb[fumb.fumble_out_of_bounds != 1]
    own = fb_all.groupby("fumbled_1_team").size()
    own_rec = fb_all[fb_all.fumble_recovery_1_team == fb_all.fumbled_1_team].groupby("fumbled_1_team").size()
    opp_f = fb_all.assign(opp=np.where(fb_all.fumbled_1_team == fb_all.posteam, fb_all.defteam, fb_all.posteam))
    opp_n = opp_f.groupby("opp").size()
    opp_rec = opp_f[opp_f.fumble_recovery_1_team == opp_f.opp].groupby("opp").size()
    T["fumbles_total"] = (own.reindex(teams).fillna(0) + opp_n.reindex(teams).fillna(0))
    T["fumbles_recovered"] = own_rec.reindex(teams).fillna(0) + opp_rec.reindex(teams).fillna(0)
    T["fum_rec_pct"] = T.fumbles_recovered / T.fumbles_total
    T["own_fumbles"] = own.reindex(teams).fillna(0)
    T["opp_fumbles"] = opp_n.reindex(teams).fillna(0)
    # expected interceptions from FTN charting (interception-worthy throws), expected fumbles lost
    ftn = fetch(f"ftn_charting/ftn_charting_{S}.parquet")
    ftn = ftn[ftn.week <= W]
    pf = p.merge(ftn[["nflverse_game_id", "nflverse_play_id", "is_interception_worthy", "n_blitzers", "n_pass_rushers",
                      "is_play_action", "is_screen_pass", "is_qb_out_of_pocket", "is_drop", "is_catchable_ball",
                      "is_throw_away"]],
                 left_on=["game_id", "play_id"], right_on=["nflverse_game_id", "nflverse_play_id"], how="left")
    att = pf[pf.att & pf.is_interception_worthy.notna()]
    p_w = att[att.is_interception_worthy == True].int_.mean()
    p_nw = att[att.is_interception_worthy == False].int_.mean()
    p_all = pf[pf.att].int_.mean()
    pf["x_int"] = np.where(pf.is_interception_worthy.isna(), p_all, np.where(pf.is_interception_worthy == True, p_w, p_nw))
    pf.loc[~pf.att, "x_int"] = 0
    T["int_worthy"] = pf[pf.att].groupby("posteam").is_interception_worthy.sum()
    T["int_worthy_rate"] = pf[pf.att & pf.is_interception_worthy.notna()].groupby("posteam").is_interception_worthy.mean()
    T["def_int_worthy_rate"] = pf[pf.att & pf.is_interception_worthy.notna()].groupby("defteam").is_interception_worthy.mean()
    T["x_int_thrown"] = pf.groupby("posteam").x_int.sum()
    T["x_int_made"] = pf.groupby("defteam").x_int.sum()
    flr = H["fum_lost_rate"]
    T["x_fum_lost"] = T.own_fumbles * flr
    T["x_fum_taken"] = T.opp_fumbles * flr
    T["x_to_margin"] = (T.x_int_made + T.x_fum_taken) - (T.x_int_thrown + T.x_fum_lost)
    T["to_luck"] = T.to_margin - T.x_to_margin
    qc.append(f"FTN charting: {pf[pf.att].is_interception_worthy.notna().mean():.1%} of 2026 pass attempts charted "
              f"(missing: {', '.join(sorted(set(p.game_id) - set(ftn.nflverse_game_id))) or 'none'}). "
              f"League P(INT | interception-worthy) = {p_w:.3f}; P(INT | not) = {p_nw:.4f}. Historical own-fumble loss "
              f"rate {flr:.3f} ({hist_seasons[0]}-{hist_seasons[-1]}).")
    # points off turnovers (scrimmage turnovers ending a drive) and turnover EPA
    drs = dr.sort_values(["game_id", "fixed_drive"]).reset_index(drop=True)
    drs["next_pos"] = drs.groupby("game_id").posteam.shift(-1)
    drs["next_pts"] = drs.groupby("game_id").pts.shift(-1)
    tdr = drs[drs.turnover == 1].copy()
    tdr["pts_after"] = np.where(tdr.result == "Opp touchdown", tdr.opp_pts_during,
                                np.where(tdr.next_pos == tdr.defteam, tdr.next_pts.fillna(0), 0))
    T["pts_off_takeaways"] = tdr.groupby("defteam").pts_after.sum()
    T["pts_after_giveaways"] = tdr.groupby("posteam").pts_after.sum()
    T["def_return_td"] = (tdr.result == "Opp touchdown").groupby(tdr.defteam).sum()
    T["to_epa_off"] = p[p.to].groupby("posteam").epa.sum()
    T["to_epa_def"] = -p[p.to].groupby("defteam").epa.sum()
    gv = p[p.to]
    T["giveaways_opp_terr"] = gv[gv.yardline_100 < 50].groupby("posteam").size()
    T["giveaways_rz"] = gv[gv.yardline_100 <= 20].groupby("posteam").size()
    T["takeaways_own_terr"] = gv[gv.yardline_100 >= 50].groupby("defteam").size()

    # ---- pressure, blitz (FTN play-level counts; PFR game-level pressure)
    dbf = pf[pf.db & pf.n_pass_rushers.notna() & (pf.n_pass_rushers > 0)].copy()
    dbf["blitz"] = dbf.n_blitzers > 0
    dbf["rush5"] = dbf.n_pass_rushers >= 5
    for side, key in [("def", "defteam"), ("off", "posteam")]:
        g = dbf.groupby(key)
        T[f"{side}_blitz_rate"] = g.blitz.mean()
        T[f"{side}_rush5_rate"] = g.rush5.mean()
        T[f"{side}_charted_db"] = g.size()
        for lab, m in [("blitz", dbf.blitz), ("noblitz", ~dbf.blitz), ("r4", dbf.n_pass_rushers <= 4), ("r5", dbf.rush5)]:
            s2 = dbf[m].groupby(key)
            T[f"{side}_epa_{lab}"] = s2.epa.mean()
            T[f"{side}_sack_{lab}"] = s2.sackp.mean()
            T[f"{side}_hs_{lab}"] = s2.hit_sack.mean()
            T[f"{side}_n_{lab}"] = s2.size()
        T[f"{side}_pa_rate"] = pf[pf.db & pf.is_play_action.notna()].groupby(key).is_play_action.mean()
        T[f"{side}_epa_pa"] = pf[pf.db & (pf.is_play_action == True)].groupby(key).epa.mean()
        T[f"{side}_epa_nopa"] = pf[pf.db & (pf.is_play_action == False)].groupby(key).epa.mean()
        T[f"{side}_epa_screen"] = pf[pf.db & (pf.is_screen_pass == True)].groupby(key).epa.mean()
        T[f"{side}_epa_oop"] = pf[pf.db & (pf.is_qb_out_of_pocket == True)].groupby(key).epa.mean()
        T[f"{side}_oop_rate"] = pf[pf.db & pf.is_qb_out_of_pocket.notna()].groupby(key).is_qb_out_of_pocket.mean()
    T["def_d3_sack_rate"] = p[p.d3_db].groupby("defteam").sackp.mean()
    T["off_drop_rate"] = (pf[pf.att & (pf.is_catchable_ball == True)].groupby("posteam").is_drop.mean())
    pfr = fetch(f"pfr_advstats/advstats_week_pass_{S}.parquet")
    pfr = pfr[(pfr.week <= W) & (pfr.game_type == "REG")]
    tg = pfr.groupby(["game_id", "team"]).agg(pressured=("times_pressured", "sum"), blitzed=("times_blitzed", "sum"),
                                             hurried=("times_hurried", "sum"), hit=("times_hit", "sum"),
                                             sacked=("times_sacked", "sum"), opp=("opponent", "first")).reset_index()
    dbg = p[p.db].groupby(["game_id", "posteam"]).size().rename("db").reset_index()
    tg = tg.merge(dbg, left_on=["game_id", "team"], right_on=["game_id", "posteam"], how="left")
    qc.append(f"PFR advanced passing: {len(tg)} of {2 * n_games_pbp} team-games available "
              f"({tg.game_id.nunique()} games); pressure and PFR-blitz rates use only those games.")
    for side, key in [("off", "team"), ("def", "opp")]:
        g = tg.groupby(key)
        T[f"{side}_pressure_rate"] = g.pressured.sum() / g.db.sum()
        T[f"{side}_pfr_blitz_rate"] = g.blitzed.sum() / g.db.sum()
        T[f"{side}_hurry_rate"] = g.hurried.sum() / g.db.sum()
        T[f"{side}_qbhit_rate"] = g.hit.sum() / g.db.sum()
        T[f"{side}_pressure_to_sack"] = g.sacked.sum() / g.pressured.sum()
        T[f"{side}_pfr_games"] = g.size()
    pdf = fetch(f"pfr_advstats/advstats_week_def_{S}.parquet")
    pdf = pdf[(pdf.week <= W) & (pdf.game_type == "REG")]
    T["def_missed_tackles_pg"] = pdf.groupby("team").def_missed_tackles.sum() / pdf.groupby("team").game_id.nunique()
    T["def_missed_tackle_pct"] = pdf.groupby("team").def_missed_tackles.sum() / (
        pdf.groupby("team").def_missed_tackles.sum() + pdf.groupby("team").def_tackles_combined.sum())
    prr = fetch(f"pfr_advstats/advstats_week_rush_{S}.parquet")
    prr = prr[(prr.week <= W) & (prr.game_type == "REG")]
    g = prr.groupby("team")
    T["ybc_per_att"] = g.rushing_yards_before_contact.sum() / g.carries.sum()
    T["yac_per_att"] = g.rushing_yards_after_contact.sum() / g.carries.sum()
    T["rush_broken_tackles_pg"] = g.rushing_broken_tackles.sum() / g.game_id.nunique()
    g = prr.groupby("opponent")
    T["def_ybc_allowed"] = g.rushing_yards_before_contact.sum() / g.carries.sum()
    T["def_yac_allowed"] = g.rushing_yards_after_contact.sum() / g.carries.sum()
    ngs_r = fetch("nextgen_stats/ngs_rushing.parquet")
    ngs_r = ngs_r[(ngs_r.season == S) & (ngs_r.week.between(1, W)) & (ngs_r.season_type == "REG")].copy()
    ngs_r["team"] = ngs_r.team_abbr.replace({"LAR": "LA"})
    g = ngs_r.groupby("team")
    T["ryoe_per_att"] = g.rush_yards_over_expected.sum() / g.rush_attempts.sum()
    T["ngs_rush_att_share"] = g.rush_attempts.sum() / T.off_rushes
    ngs_p = fetch("nextgen_stats/ngs_passing.parquet")
    ngs_p = ngs_p[(ngs_p.season == S) & (ngs_p.week.between(1, W)) & (ngs_p.season_type == "REG")].copy()
    ngs_p["team"] = ngs_p.team_abbr.replace({"LAR": "LA"})
    ngs_p["ttt_x"] = ngs_p.avg_time_to_throw * ngs_p.attempts
    T["time_to_throw"] = ngs_p.groupby("team").ttt_x.sum() / ngs_p.groupby("team").attempts.sum()
    ngs_p["opp"] = [_opp_of(played, t, w) for t, w in zip(ngs_p.team, ngs_p.week)]
    T["def_time_to_throw"] = ngs_p.groupby("opp").ttt_x.sum() / ngs_p.groupby("opp").attempts.sum()

    # raw volume per game (context only: depends on pace and game script)
    live_sc = p[p.sc & p.live]
    for side, key in [("off", "posteam"), ("def", "defteam")]:
        rush_y = live_sc[live_sc["rush"] == 1].groupby(key).yards_gained.sum() + live_sc[live_sc.scr].groupby(key).yards_gained.sum()
        pass_y = live_sc[live_sc.att].groupby(key).passing_yards.sum() + live_sc[live_sc.sackp].groupby(key).yards_gained.sum()
        T[f"{side}_rush_yds_pg"] = rush_y / T.games
        T[f"{side}_pass_yds_pg"] = pass_y / T.games
        T[f"{side}_yds_pg"] = (rush_y + pass_y) / T.games
    T["off_pts_pg"] = T.pf / T.games
    T["def_pts_pg"] = T.pa / T.games

    # defence vs offensive styles: opponents' neutral pass rate over expected
    proe = p[p.neutral & p.early & p.pass_oe.notna()].groupby("posteam").pass_oe.mean()
    T["off_proe"] = proe
    pass_heavy = proe >= proe.median()
    sc2 = sc.assign(opp_pass_heavy=sc.posteam.map(pass_heavy))
    T["def_epa_vs_pass_heavy"] = sc2[sc2.opp_pass_heavy].groupby("defteam").epa.mean()
    T["def_epa_vs_run_heavy"] = sc2[~sc2.opp_pass_heavy].groupby("defteam").epa.mean()
    T["def_qb_run_epa"] = p[p.qb_drun].groupby("defteam").epa.mean()
    T["def_qb_runs"] = p[p.qb_drun].groupby("defteam").size()
    T["def_scr_epa"] = p[p.scr].groupby("defteam").epa.mean()

    # ---- penalties
    pen, pen_tables = penalties(p, teams)
    T = T.join(pen)

    # ---- coaching / game management
    T = T.join(coaching(p, sc, dr, H["fourth"], teams))
    byes = bye_effect(sched, G, teams, W)
    T = T.join(byes)

    # ---- personnel
    pers, ol_tbl, absences = personnel(S, W, p, teams)
    T = T.join(pers)

    # ---- QBs
    Q = qb_table(p, pf, adj, S, W, pfr)

    # starting quarterbacks (most dropbacks in each team-game) and change from last season's primary passer
    st_qb = (p[p.db].groupby(["posteam", "game_id", "passer_id"]).size().reset_index(name="n")
             .sort_values("n", ascending=False).drop_duplicates(["posteam", "game_id"]))
    qn = Q.set_index("passer_id").name_full.to_dict()
    T["qb_starters_n"] = st_qb.groupby("posteam").passer_id.nunique()
    T["qb_starts"] = st_qb.groupby("posteam").passer_id.apply(
        lambda s: ", ".join(f"{qn.get(i, i)} {c}" for i, c in s.value_counts().items()))
    prev = load_pbp(S - 1)
    prev_qb = prev[prev.db].groupby(["posteam", "passer_id"]).size().reset_index(name="n").sort_values("n").drop_duplicates("posteam", keep="last").set_index("posteam").passer_id
    cur_qb = st_qb.groupby("posteam").passer_id.agg(lambda s: s.value_counts().index[0])
    T["qb_changed_since_prior"] = [prev_qb.get(t) != cur_qb.get(t) for t in teams]

    # ---- week 8 slate
    nxt = sched[sched.week == W + 1][["game_id", "gameday", "weekday", "gametime", "away_team", "home_team", "location",
                                       "roof", "surface", "stadium", "away_coach", "home_coach", "away_rest", "home_rest",
                                       "away_score", "home_score", "div_game"]]
    MM = matchup_models(p, dr, tg, teams)

    # ---- matchup context: workload, fatigue, travel, penalties, QB scenarios, run style
    snaps = fetch(f"snap_counts/snap_counts_{S}.parquet")
    wl, dq = ctx.workload(p, dr, snaps, teams, W)
    T = T.join(wl)
    T["pts_per_min_poss"] = T.pf / (T.off_top_pg * T.games)
    T = T.join(ctx.fatigue_descriptives(p, dq, teams))
    pdet, pen_by_type, pen_groups, pen_rows = ctx.penalty_detail(p, teams)
    T = T.join(pdet)
    rzp = ctx.rz_penalty_effect(dr, pen_rows)
    T["rz_td_with_off_pen"] = rzp[("mean", True)] if ("mean", True) in rzp else np.nan
    T["rz_td_without_off_pen"] = rzp[("mean", False)] if ("mean", False) in rzp else np.nan
    T["rz_trips_with_off_pen"] = rzp[("size", True)] if ("size", True) in rzp else np.nan
    T = T.join(ctx.run_style(p, teams))
    ros = fetch(f"weekly_rosters/roster_weekly_{S}.parquet")
    ros_cur = ros[ros.week == ros.groupby("team").week.transform("max")]     # teams on a bye may lack the newest week
    inj = fetch(f"injuries/injuries_{S}.parquet")
    inj_last = inj[inj.week == inj.groupby("team").week.transform("max")]
    qbs = ctx.qb_scenarios(p, Q, ros_cur, inj_last, teams)
    print("fatigue study", flush=True)
    seasons_pbp = {s: H_p for s, H_p in ((s, add_unit_flags(load_pbp(s))) for s in hist_seasons)}
    seasons_pbp[S] = p
    fat = ctx.fatigue_study(seasons_pbp, build_drives)
    del seasons_pbp
    print("travel study", flush=True)
    sched_all = fetch("schedules/games.parquet")
    trv = ctx.travel_study(sched_all, 2002, S - 1)
    wk_trv = ctx.week_travel(sched[sched.season == S], W + 1, trv)
    pen_by_type.to_csv(out_dir / "penalties_by_type.csv", index=False)
    wk_trv.to_csv(out_dir / "travel_next_week.csv", index=False)
    (out_dir / "context.json").write_text(json.dumps({"fatigue": fat, "travel": trv, "qb": qbs, "penalty_groups": pen_groups},
                                                     indent=1, default=str))
    # play-caller attribution (hand-kept names with sources; stats split where a caller changed mid-season)
    (out_dir / "callers.json").write_text(json.dumps(callers.build(p, pf, S, W), indent=1), encoding="utf-8")

    # ---- output
    T.index.name = "team"
    tm = fetch("teams/teams_colors_logos.parquet")
    names = tm.set_index("team_abbr").team_name.to_dict()
    T.insert(0, "team_name", [names.get(t, t) for t in T.index])
    T.to_csv(out_dir / "team_metrics.csv", float_format="%.5f")
    Q.to_csv(out_dir / "quarterbacks.csv", index=False, float_format="%.5f")
    G.to_csv(out_dir / "team_games.csv", index=False, float_format="%.5f")
    dr.to_csv(out_dir / "drives.csv", index=False, float_format="%.4f")
    pen_tables.to_csv(out_dir / "penalty_types.csv")
    ol_tbl.to_csv(out_dir / "offensive_line.csv", index=False)
    absences.to_csv(out_dir / "absences.csv", index=False)
    nxt.to_csv(out_dir / "next_week_schedule.csv", index=False)
    (out_dir / "matchup_models.json").write_text(json.dumps(MM, indent=1))
    meta = {
        "season": S, "through_week": W, "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "games": n_games_pbp, "plays": int(p.sc.sum()), "drives": int((~dr.excluded).sum()),
        "history_seasons": hist_seasons, "composite_off": comp_o, "composite_def": comp_d,
        "prior_off": pri_o, "prior_def": pri_d, "epa_win_coef": epa_win_coef, "plays_per_game": plays_pg,
        "home_coef": home_coef, "league_epa_play": adj["epa"]["mean"],
        "league": {k: float(v) for k, v in {
            "sr": sc.success.mean(), "epa_db": p[p.db].epa.mean(), "epa_rush": p[p.drush].epa.mean(),
            "ppd": dr[~dr.excluded].pts.mean(), "expl_rate": sc.explosive.mean(), "sack_rate": p[p.db].sackp.mean(),
            "fg_pct": fga.made.mean(), "rz_td": dr[~dr.excluded & (dr.rz_trip == 1)].td.mean(),
            "d3_conv": p[p.d3_flag].third_down_converted.mean(), "blitz_rate": dbf.blitz.mean(),
            "pressure_rate": tg.pressured.sum() / tg.db.sum(), "p_int_worthy": p_w, "p_int_not": p_nw}.items()},
        "fum_lost_rate": flr, "qc": qc, "sources": MANIFEST,
        "tiers": {t: str(tiers[t]) for t in teams}, "net_eff": net_eff.to_dict(),
    }
    (out_dir / "bundle_meta.json").write_text(json.dumps(meta, indent=1, default=str))
    print("\n".join(qc))
    print("wrote", out_dir)


# ------------------------------------------------------------------------------------- matchup models
MATCHUP_METRICS = [
    # name, frame, mask column, y column
    ("epa_play", "plays", "sc", "epa"), ("sr", "plays", "sc", "success"),
    ("epa_db", "plays", "db", "epa"), ("sr_db", "plays", "db", "success"), ("ypa", "plays", "att", "passing_yards"),
    ("sack_rate", "plays", "db", "sackp"), ("expl_pass", "plays", "att", "expl_pass"),
    ("epa_rush", "plays", "drush", "epa"), ("sr_rush", "plays", "drush", "success"),
    ("ypc", "plays", "drush_live", "yards_gained"), ("expl_run", "plays", "drush_live", "expl_run"),
    ("stuff", "plays", "drush_live", "stuffed"), ("d3_conv", "plays", "d3_flag", "third_down_converted"),
    ("ppd", "drives", None, "pts"), ("rz_td", "drives", "rz_trip", "td"), ("to_pd", "drives", None, "turnover"),
    ("pressure", "pfr", None, "rate"),
]


def matchup_models(p, dr, tg, teams):
    """Additive offence + defence + home models with empirical-Bayes shrinkage of each team effect.

    Shrinkage weight w = tau2 / (tau2 + resid_var / n), with tau2 the between-team variance of the
    unshrunk effects minus their average sampling variance (method of moments). Small samples are
    pulled towards the league average; nothing from earlier seasons is used here."""
    frames = {"plays": p, "drives": dr[~dr.excluded].assign(
        is_home=lambda x: np.where(x.posteam == x.home_team, 1, -1)),
        "pfr": tg.dropna(subset=["db"]).assign(posteam=lambda x: x.team, defteam=lambda x: x.opp,
                                               rate=lambda x: x.pressured / x.db)}
    homes = p.groupby("game_id").agg(home=("home_team", "first"), loc=("location", "first"))
    frames["pfr"]["is_home"] = [0 if homes.loc[g, "loc"] == "Neutral" else (1 if homes.loc[g, "home"] == t else -1)
                                for g, t in zip(frames["pfr"].game_id, frames["pfr"].team)]
    out = {}
    for name, fr, mask, y in MATCHUP_METRICS:
        d = frames[fr]
        if mask:
            d = d[d[mask].astype(bool)]
        d = d[d[y].notna()].copy()
        d[y] = d[y].astype(float)
        a = adjust(d, y, teams)
        res = {"mean": a["mean"], "home": a["home"], "resid_var": a["resid_var"]}
        for side, key, eff in [("off", "posteam", "off_eff"), ("def", "defteam", "def_eff")]:
            n = d.groupby(key).size().reindex(teams).fillna(0)
            if fr == "pfr":      # one row per team-game: use dropbacks as the sample size
                n = d.groupby(key).db.sum().reindex(teams).fillna(0)
                noise = (a["mean"] * (1 - a["mean"])) / n
            else:
                noise = a["resid_var"] / n
            e = a[eff].reindex(teams)
            tau2 = max(float(e.var(ddof=1) - noise.mean()), 1e-9)
            w = tau2 / (tau2 + noise)
            res[side] = {"eff": e.round(5).to_dict(), "w": w.round(3).to_dict(), "n": n.astype(int).to_dict(),
                         "tau2": tau2}
        out[name] = res
    return out


def _opp_of(played, team, week):
    g = played[(played.week == week) & ((played.home_team == team) | (played.away_team == team))]
    if g.empty:
        return None
    r = g.iloc[0]
    return r.away_team if r.home_team == team else r.home_team


# ------------------------------------------------------------------------------------------ penalties
PRESNAP = {"False Start", "Delay of Game", "Encroachment", "Neutral Zone Infraction", "Illegal Formation",
           "Illegal Shift", "Illegal Motion", "Defensive Too Many Men on Field", "Offensive Too Many Men on Field",
           "Illegal Substitution", "Defensive Delay of Game", "Defensive Offside", "Offensive Offside"}
UNCONTROLLABLE_HINT = {"Defensive Pass Interference", "Offensive Pass Interference", "Illegal Contact",
                       "Defensive Holding", "Roughing the Passer"}


def penalties(p: pd.DataFrame, teams: list[str]):
    x = p[(p.penalty == 1) & p.penalty_team.notna() & p.posteam.notna()].copy()
    desc = x.desc.fillna("")
    # declined/offsetting: nflfastR records the first penalty on the play; flag declined when its text says so
    x["declined"] = desc.str.contains(r"PENALTY on [^,]+, [^,]+, declined", case=False, regex=True)
    x["offsetting"] = desc.str.contains("offsetting", case=False)
    x["accepted"] = ~x.declined & ~x.offsetting
    st_types = {"kickoff", "punt", "field_goal", "extra_point"}
    x["phase"] = np.where((x.special_teams_play == 1) | x.play_type.isin(st_types), "st",
                          np.where(x.penalty_team == x.posteam, "off", "def"))
    x["presnap"] = x.penalty_type.isin(PRESNAP)
    x["auto_fd"] = (x.phase == "def") & (x.first_down_penalty == 1)
    pre = desc.str.split("PENALTY").str[0]
    yds = pre.str.extract(r"for (-?\d+) yards?")[0].astype(float)
    is_pass = pre.str.contains(" pass ") & ~pre.str.contains("incomplete")
    x["negated_td"] = (x.play_type == "no_play") & desc.str.contains("TOUCHDOWN NULLIFIED") & (x.phase == "off")
    x["negated_expl"] = ((x.play_type == "no_play") & (x.phase == "off") &
                         ((is_pass & (yds >= EXPL_PASS)) | (~is_pass & (yds >= EXPL_RUN)) | x.negated_td))
    x["negated_takeaway"] = ((x.play_type == "no_play") & (x.phase == "def") &
                             desc.str.contains(r"INTERCEPTED|RECOVERED by", regex=True))
    # EPA of the penalty outcome where the whole result is the penalty (no-play); offence perspective
    x["np_epa"] = np.where(x.play_type == "no_play", x.epa, np.nan)
    a = x[x.accepted]
    out = pd.DataFrame(index=teams)
    games = p.groupby("posteam").game_id.nunique()
    offp = p[p.sc | ((p.play_type == "no_play") & (p.special_teams_play != 1))]
    off_snaps = offp.groupby("posteam").size()
    def_snaps = offp.groupby("defteam").size()
    for ph, snaps in [("off", off_snaps), ("def", def_snaps)]:
        s = a[a.phase == ph].groupby("penalty_team")
        out[f"pen_{ph}_n"] = s.size()
        out[f"pen_{ph}_yds"] = s.penalty_yards.sum()
        out[f"pen_{ph}_pg"] = out[f"pen_{ph}_n"] / games
        out[f"pen_{ph}_yds_pg"] = out[f"pen_{ph}_yds"] / games
        out[f"pen_{ph}_per100"] = 100 * out[f"pen_{ph}_n"] / snaps
        out[f"pen_{ph}_presnap"] = a[(a.phase == ph) & a.presnap].groupby("penalty_team").size()
        out[f"pen_{ph}_d3"] = a[(a.phase == ph) & (a.down == 3)].groupby("penalty_team").size()
        out[f"pen_{ph}_rz"] = a[(a.phase == ph) & (a.yardline_100 <= 20)].groupby("penalty_team").size()
        sign = 1 if ph == "def" else -1        # cost to the penalised team, EPA
        out[f"pen_{ph}_np_epa_cost"] = sign * a[a.phase == ph].groupby("penalty_team").np_epa.sum()
    out["pen_st_n"] = a[a.phase == "st"].groupby("penalty_team").size()
    out["pen_st_yds"] = a[a.phase == "st"].groupby("penalty_team").penalty_yards.sum()
    for lab, types in [("false_start", ["False Start"]), ("off_holding", ["Offensive Holding"]),
                       ("dpi", ["Defensive Pass Interference"]), ("def_hold_contact", ["Defensive Holding", "Illegal Contact"]),
                       ("rtp", ["Roughing the Passer"]),
                       ("personal_foul", ["Unnecessary Roughness", "Face Mask", "Unsportsmanlike Conduct", "Taunting",
                                          "Lowering the Head to Make Forcible Contact", "Horse Collar Tackle"])]:
        out[f"pen_{lab}"] = a[a.penalty_type.isin(types)].groupby("penalty_team").size()
    out["pen_auto_fd"] = a[a.auto_fd].groupby("penalty_team").size()
    out["pen_auto_fd_drawn"] = a[a.auto_fd].groupby("posteam").size()
    out["pen_negated_expl"] = x[x.negated_expl & x.accepted].groupby("penalty_team").size()
    out["pen_negated_td"] = x[x.negated_td & x.accepted].groupby("penalty_team").size()
    out["pen_negated_takeaway"] = x[x.negated_takeaway & x.accepted].groupby("penalty_team").size()
    out["pen_declined"] = x[x.declined].groupby("penalty_team").size()
    out["pen_offsetting"] = x[x.offsetting].groupby("penalty_team").size()
    out["pen_drawn_def"] = a[a.phase == "def"].groupby("posteam").size()     # opponents' defensive penalties
    out["pen_drawn_off"] = a[a.phase == "off"].groupby("defteam").size()
    out["pen_total"] = a.groupby("penalty_team").size()
    out["pen_total_yds"] = a.groupby("penalty_team").penalty_yards.sum()
    out["pen_def_aggr_share"] = a[(a.phase == "def") & a.penalty_type.isin(UNCONTROLLABLE_HINT)].groupby("penalty_team").size() / out.pen_def_n
    out = out.fillna({c: 0 for c in out.columns if not c.endswith("share")})
    types = a.pivot_table(index="penalty_team", columns="penalty_type", values="play_id", aggfunc="count", fill_value=0)
    return out, types


# ------------------------------------------------------------------------------------- game management
def coaching(p, sc, dr, fourth_hist, teams):
    out = pd.DataFrame(index=teams)
    # fourth-down decisions: bucket values (expected points after the play) from history
    def buckets(d):
        yb = pd.cut(d.ydstogo, [0, 1, 2, 3, 5, 9, 99], labels=["1", "2", "3", "4-5", "6-9", "10+"])
        fb = (d.yardline_100 // 10).clip(0, 9).astype(int)
        opt = np.where(d.play_type.isin(["pass", "run"]), "go", d.play_type)
        return yb.astype(str) + "|" + fb.astype(str), opt
    hb, ho = buckets(fourth_hist)
    ref = (fourth_hist.assign(b=hb, opt=ho, post=fourth_hist.ep + fourth_hist.epa)
           .groupby(["b", "opt"]).post.agg(["mean", "size"]))
    ref = ref[ref["size"] >= 20]["mean"].unstack()
    f4 = p[(p.down == 4) & p.play_type.isin(["pass", "run", "punt", "field_goal"]) & p.epa.notna()
           & p.wp.between(0.2, 0.8) & (p.half_seconds_remaining > 120) & (p.qb_kneel != 1)].copy()
    b, o = buckets(f4)
    f4["b"], f4["opt"] = b, o
    vals = ref.reindex(f4.b)
    vals.index = f4.index
    f4["best"] = vals.idxmax(axis=1)
    f4["best_val"] = vals.max(axis=1)
    f4["chosen_val"] = [vals.at[i, c] if c in vals.columns else np.nan for i, c in zip(f4.index, f4.opt)]
    kick = vals.drop(columns=["go"], errors="ignore").max(axis=1)
    f4["go_margin"] = vals.get("go") - kick
    f4["ep_lost"] = f4.best_val - f4.chosen_val
    g = f4.groupby("posteam")
    out["fd_decisions"] = g.size()
    out["fd_go_rate"] = g.opt.apply(lambda s: (s == "go").mean())
    out["fd_agree_rate"] = (f4.opt == f4.best).groupby(f4.posteam).mean()
    cg = f4[f4.go_margin >= 0.5]
    out["fd_clear_go_n"] = cg.groupby("posteam").size()
    out["fd_clear_go_rate"] = (cg.opt == "go").groupby(cg.posteam).mean()
    out["fd_ep_lost_per"] = g.ep_lost.mean()
    out["fd_ep_lost_total"] = g.ep_lost.sum()
    # pace (median seconds between consecutive offensive snaps of a drive, neutral situations), PROE
    s = sc.sort_values(["game_id", "play_id"]).copy()
    s["gap"] = s.groupby(["game_id", "fixed_drive"]).game_seconds_remaining.diff(-1)
    s["gap"] = s.gap.where(s.gap.between(1, 60))
    out["pace_sec"] = s[s.wp.between(0.2, 0.8) & (s.qtr <= 3)].groupby("posteam").gap.median()
    neu = p[p.sc & p.wp.between(0.2, 0.8) & p.early & (p.half_seconds_remaining > 120)]
    out["neutral_early_pass_rate"] = neu.groupby("posteam").db.mean()
    out["neutral_proe"] = neu[neu.pass_oe.notna()].groupby("posteam").pass_oe.mean()
    # halves, score state
    out["off_epa_h1"] = sc[sc.game_half == "Half1"].groupby("posteam").epa.mean()
    out["off_epa_h2"] = sc[sc.game_half == "Half2"].groupby("posteam").epa.mean()
    out["def_epa_h1"] = sc[sc.game_half == "Half1"].groupby("defteam").epa.mean()
    out["def_epa_h2"] = sc[sc.game_half == "Half2"].groupby("defteam").epa.mean()
    out["net_h2_minus_h1"] = (out.off_epa_h2 - out.def_epa_h2) - (out.off_epa_h1 - out.def_epa_h1)
    for lab, m in [("leading", sc.score_differential >= 9), ("close", sc.score_differential.abs() <= 8),
                   ("trailing", sc.score_differential <= -9)]:
        out[f"off_epa_{lab}"] = sc[m].groupby("posteam").epa.mean()
        out[f"off_plays_{lab}"] = sc[m].groupby("posteam").size()
    # end-of-first-half drives (started inside the final 2:00 of the half)
    eoh = dr[(dr.game_half == "Half1") & (dr.start_half_sec <= 120) & ~dr.excluded]
    out["eoh_drives"] = eoh.groupby("posteam").size()
    out["eoh_ppd"] = eoh.groupby("posteam").pts.mean()
    # timeouts: second-half timeouts left unused at the end of games the team lost by one score
    return out


def bye_effect(sched, G, teams, W):
    out = pd.DataFrame(index=teams)
    rows = []
    for t in teams:
        wk = set(sched[((sched.home_team == t) | (sched.away_team == t)) & (sched.week <= W)].week)
        bye = [w for w in range(1, W + 1) if w not in wk]
        rows.append({"team": t, "bye_week": bye[0] if bye else np.nan})
    b = pd.DataFrame(rows).set_index("team")
    out["bye_week"] = b.bye_week
    post = G.merge(b, left_on="team", right_index=True)
    post = post[post.week == post.bye_week + 1]
    out["net_after_bye"] = post.set_index("team").net_epa_play
    return out


# ------------------------------------------------------------------------------------------ personnel
OL_POS = {"T", "G", "C", "OL", "OT", "OG"}


def personnel(S, W, p, teams):
    snaps = fetch(f"snap_counts/snap_counts_{S}.parquet")
    snaps = snaps[(snaps.week <= W) & (snaps.game_type == "REG")].copy()
    snaps["team"] = snaps.team.replace({"LAR": "LA"})
    ros = fetch(f"weekly_rosters/roster_weekly_{S}.parquet")
    ros["team"] = ros.team.replace({"LAR": "LA"})
    cur_week = int(ros.week.max())
    cur = ros[ros.week == cur_week]
    inj = fetch(f"injuries/injuries_{S}.parquet")
    inj["team"] = inj.team.replace({"LAR": "LA"})
    inj_week = int(inj.week.max())
    last_inj = inj[inj.week == inj.groupby("team").week.transform("max")]      # each team's latest report
    out = pd.DataFrame(index=teams)
    # offensive line continuity: top-5 OL by offensive snaps per game
    ol = snaps[snaps.position.isin(OL_POS)].sort_values("offense_snaps", ascending=False)
    top5 = ol.groupby(["team", "game_id"]).head(5)
    combos = top5.groupby(["team", "game_id"]).pfr_player_id.apply(lambda s: tuple(sorted(s)))
    out["ol_starters_used"] = top5.groupby("team").pfr_player_id.nunique()
    out["ol_combos"] = combos.groupby("team").nunique()
    first_wk = top5.merge(top5.groupby("team").week.min().rename("w1"), left_on="team", right_index=True)
    w1 = first_wk[first_wk.week == first_wk.w1].groupby("team").pfr_player_id.apply(set)
    lastwk = top5.merge(top5.groupby("team").week.max().rename("wl"), left_on="team", right_index=True)
    wl = lastwk[lastwk.week == lastwk.wl].groupby("team").pfr_player_id.apply(set)
    out["ol_w1_starters_in_last"] = [len(w1[t] & wl[t]) if t in w1 and t in wl else np.nan for t in teams]
    ol_tbl = top5.groupby("team").agg(players=("player", lambda s: ", ".join(sorted(set(s)))))
    ol_tbl = ol_tbl.reset_index()
    # regulars: >= 50% offence or defence snap share in the games they played, at least 2 games
    snaps["share"] = snaps[["offense_pct", "defense_pct"]].max(axis=1)
    snaps["unit"] = np.where(snaps.offense_pct >= snaps.defense_pct, "off", "def")
    reg = snaps.groupby(["team", "pfr_player_id", "player", "position"]).agg(
        games=("game_id", "nunique"), share=("share", "mean"), unit=("unit", "first"), last_week=("week", "max")).reset_index()
    reg = reg[(reg.games >= 2) & (reg.share >= 0.5)]
    team_last = snaps.groupby("team").week.max()
    # current status from the latest weekly roster (pfr_id link) and the latest injury report (gsis link)
    link = ros.drop_duplicates("pfr_id").set_index("pfr_id")
    reg["gsis_id"] = reg.pfr_player_id.map(link.gsis_id)
    reg["roster_status"] = reg.pfr_player_id.map(cur.drop_duplicates("pfr_id").set_index("pfr_id").status)
    reg["roster_team_now"] = reg.pfr_player_id.map(cur.drop_duplicates("pfr_id").set_index("pfr_id").team)
    reg["status_abbr"] = reg.pfr_player_id.map(cur.drop_duplicates("pfr_id").set_index("pfr_id").status_description_abbr)
    rep = last_inj.drop_duplicates("gsis_id").set_index("gsis_id")
    reg["last_report_status"] = reg.gsis_id.map(rep.report_status)
    reg["last_practice_status"] = reg.gsis_id.map(rep.practice_status)
    reg["last_report_week"] = reg.gsis_id.map(rep.week)
    reg["last_report_injury"] = reg.gsis_id.map(rep.report_primary_injury)
    reg["missed_last_game"] = reg.last_week < reg.team.map(team_last)
    reg["group"] = reg.position.map(POS_GROUP).fillna("other")
    reg["on_reserve"] = reg.roster_status.eq("RES") & reg.roster_team_now.eq(reg.team)
    reg["left_team"] = reg.roster_team_now.notna() & reg.roster_team_now.ne(reg.team)
    reg["out_or_doubtful"] = reg.last_report_status.isin(["Out", "Doubtful"])
    reg["questionable"] = reg.last_report_status.eq("Questionable")
    # midweek reports carry practice participation but no game status until the final report
    reg["dnp"] = (reg.last_report_status.isna() & reg.last_practice_status.fillna("").str.startswith("Did Not"))
    reg["limited"] = (reg.last_report_status.isna() & reg.last_practice_status.fillna("").str.startswith("Limited"))
    unconfirmed = reg.missed_last_game & ~reg.left_team & reg.position.ne("QB")
    ab = reg[reg.on_reserve | reg.out_or_doubtful | reg.questionable | reg.dnp | reg.limited | unconfirmed].copy()
    ab["status_class"] = np.where(ab.on_reserve, "confirmed: reserve list",
                                  np.where(ab.out_or_doubtful, "listed Out/Doubtful",
                                           np.where(ab.questionable, "listed Questionable",
                                                    np.where(ab.dnp, "did not practise",
                                                             np.where(ab.limited, "limited in practice", "unconfirmed")))))
    wk = "week " + ab.last_report_week.astype("Int64").astype(str) + " report: "
    ab["reason"] = np.where(ab.on_reserve, "reserve list (week " + str(cur_week) + " roster)",
                            np.where(ab.out_or_doubtful | ab.questionable, wk + ab.last_report_status.fillna(""),
                                     np.where(ab.dnp | ab.limited, wk + ab.last_practice_status.fillna("") + " (no game status yet)",
                                              "did not play in the team's latest game; no injury designation")))
    conf = ab[ab.status_class.isin(["confirmed: reserve list", "listed Out/Doubtful"])]
    out["regulars"] = reg.groupby("team").size()
    out["reg_on_reserve"] = reg[reg.on_reserve].groupby("team").size()
    out["reg_on_reserve_share_sum"] = reg[reg.on_reserve].groupby("team").share.sum()
    for grp in ["QB", "OL", "WR/TE", "RB", "DL/EDGE", "LB", "DB"]:
        out[f"absent_{grp}"] = conf[conf.group == grp].groupby("team").size()
    out["absent_snap_weighted"] = conf.groupby("team").share.sum()
    out["absent_n"] = conf.groupby("team").size()
    out["questionable_n"] = ab[ab.status_class == "listed Questionable"].groupby("team").size()
    out["practice_concern_n"] = ab[ab.status_class.isin(["did not practise", "limited in practice"])].groupby("team").size()
    out["unconfirmed_n"] = ab[ab.status_class == "unconfirmed"].groupby("team").size()
    out = out.fillna({c: 0 for c in out.columns if c.startswith(("absent_", "reg_on", "questionable", "unconfirmed", "practice_concern"))})
    # concentration
    tgt = p[p.att & p.passer_id.notna()]
    rec_col = "receiver_player_id" if "receiver_player_id" in p.columns else None
    rush = p[p.rb_drun]
    out["top_rb_carry_share"] = rush.groupby("posteam").rusher_player_id.apply(lambda s: s.value_counts(normalize=True).iloc[0])
    dsn = snaps[snaps.defense_snaps > 0].groupby(["team", "pfr_player_id"]).defense_snaps.sum().reset_index()
    out["def_top11_snap_share"] = dsn.groupby("team").defense_snaps.apply(lambda s: s.nlargest(11).sum() / s.sum())
    out["def_players_25pct"] = snaps[snaps.defense_pct >= 0.25].groupby("team").pfr_player_id.nunique()
    out["snap_week"] = cur_week
    ab_out = ab[["team", "player", "position", "group", "unit", "games", "share", "status_class", "reason",
                 "last_report_injury", "last_practice_status", "last_report_week"]]
    ab_out.attrs["roster_week"] = cur_week
    return out, ol_tbl, ab_out.sort_values(["team", "share"], ascending=[True, False])


POS_GROUP = {"QB": "QB", "T": "OL", "G": "OL", "C": "OL", "OL": "OL", "WR": "WR/TE", "TE": "WR/TE", "RB": "RB",
             "FB": "RB", "DE": "DL/EDGE", "DT": "DL/EDGE", "NT": "DL/EDGE", "DL": "DL/EDGE", "OLB": "DL/EDGE",
             "LB": "LB", "ILB": "LB", "MLB": "LB", "CB": "DB", "S": "DB", "FS": "DB", "SS": "DB", "DB": "DB"}


# ---------------------------------------------------------------------------------------- quarterbacks
def qb_table(p, pf, adj, S, W, pfr):
    d = pf[pf.db & pf.passer_id.notna()].copy()
    g = d.groupby("passer_id")
    q = pd.DataFrame({"name": g.passer.agg(lambda s: s.mode().iloc[0]),
                      "team": g.posteam.agg(lambda s: s.value_counts().index[0]),
                      "teams": g.posteam.agg(lambda s: "/".join(sorted(s.unique()))),
                      "games": g.game_id.nunique(), "dropbacks": g.size(), "epa_db": g.epa.mean(),
                      "sr": g.success.mean()})
    # opponent adjustment: subtract the dropback-defence effect of each opponent faced
    d["opp_eff"] = d.defteam.map(adj["epa_db"]["def_eff"])
    q["adj_epa_db"] = q.epa_db - d.groupby("passer_id").opp_eff.mean()
    a = d[d.att]
    q["attempts"] = a.groupby("passer_id").size()
    q["cpoe"] = a.groupby("passer_id").cpoe.mean()
    q["ypa"] = a.groupby("passer_id").passing_yards.sum() / q.attempts
    q["adot"] = a.groupby("passer_id").air_yards.mean()
    q["sack_rate"] = d.groupby("passer_id").sackp.mean()
    q["int_rate"] = a.groupby("passer_id").int_.mean()
    q["int_worthy_rate"] = a[a.is_interception_worthy.notna()].groupby("passer_id").is_interception_worthy.mean()
    q["fd_td_rate"] = ((d.first_down == 1) | (d.touchdown == 1)).groupby(d.passer_id).mean()
    q["scr_rate"] = d.groupby("passer_id").scr.mean()
    q["epa_scr"] = d[d.scr].groupby("passer_id").epa.mean()
    runs = p[p.qb_drun]
    q["designed_runs"] = runs.groupby("rusher_player_id").size().reindex(q.index).fillna(0)
    q["epa_designed_run"] = runs.groupby("rusher_player_id").epa.mean()
    q["epa_early"] = d[d.early].groupby("passer_id").epa.mean()
    q["epa_d3"] = d[d.d3].groupby("passer_id").epa.mean()
    q["epa_rz"] = d[d.rz].groupby("passer_id").epa.mean()
    q["epa_clean"] = d[d.hit_sack == 0].groupby("passer_id").epa.mean()
    q["epa_hit_sack"] = d[d.hit_sack == 1].groupby("passer_id").epa.mean()
    q["hit_sack_rate"] = d.groupby("passer_id").hit_sack.mean()
    ch = d[d.n_pass_rushers.notna() & (d.n_pass_rushers > 0)]
    q["epa_vs_blitz"] = ch[ch.n_blitzers > 0].groupby("passer_id").epa.mean()
    q["epa_no_blitz"] = ch[ch.n_blitzers == 0].groupby("passer_id").epa.mean()
    q["blitzed_rate"] = (ch.n_blitzers > 0).groupby(ch.passer_id).mean()
    q["yacoe"] = d[d.comp].groupby("passer_id").yacoe.mean()
    q["drop_rate"] = a[a.is_catchable_ball == True].groupby("passer_id").is_drop.mean()
    gm = d.groupby(["passer_id", "game_id"]).epa.agg(["mean", "size"])
    gm = gm[gm["size"] >= 15]
    q["game_sd"] = gm.groupby("passer_id")["mean"].std()
    q["games_15db"] = gm.groupby("passer_id").size()
    # PFR pressure faced (QB-level weekly rows; join by name+team, the only shared key)
    # PFR pressure faced: PFR ids linked to gsis ids through the weekly roster; dropbacks from pbp in the
    # same games (PFR coverage is incomplete)
    ros = fetch(f"weekly_rosters/roster_weekly_{S}.parquet").dropna(subset=["pfr_id", "gsis_id"])
    pfr2 = pfr.assign(gsis=pfr.pfr_player_id.map(ros.drop_duplicates("pfr_id").set_index("pfr_id").gsis_id))
    pr = pfr2.groupby("gsis").agg(pressured=("times_pressured", "sum"), sacked=("times_sacked", "sum"))
    pfr_games = set(zip(pfr2.game_id, pfr2.gsis))
    dpf = d[[(g, i) in pfr_games for g, i in zip(d.game_id, d.passer_id)]]
    pr["db_pfr"] = dpf.groupby("passer_id").size()
    q["pressure_rate"] = (pr.pressured / pr.db_pfr).reindex(q.index)
    q["p2s"] = (pr.sacked / pr.pressured).reindex(q.index)
    q["name_full"] = q.index.map(ros.drop_duplicates("gsis_id").set_index("gsis_id").full_name)
    # NGS time to throw
    ngs = fetch("nextgen_stats/ngs_passing.parquet")
    ngs = ngs[(ngs.season == S) & ngs.week.between(1, W) & (ngs.season_type == "REG")].copy()
    ngs["x"] = ngs.avg_time_to_throw * ngs.attempts
    tt = ngs.groupby("player_gsis_id").x.sum() / ngs.groupby("player_gsis_id").attempts.sum()
    q["time_to_throw"] = tt.reindex(q.index)
    q["team_pressure_allowed"] = q.team.map(pfr_team_pressure(pfr, p))
    q = q.reset_index().rename(columns={"index": "passer_id"})
    qual = q[q.dropbacks >= MIN_QB_DROPBACKS]
    q["qualified"] = q.dropbacks >= MIN_QB_DROPBACKS
    zcols = {"adj_epa_db": 0.5, "cpoe": 0.3, "int_worthy_rate": -0.2}
    score = 0
    for c, w in zcols.items():
        score = score + w * (q[c] - qual[c].mean()) / qual[c].std()
    q["qb_composite"] = score
    # share of the team's dropbacks
    tdb = d.groupby("posteam").size()
    q["team_db_share"] = q.dropbacks / q.team.map(tdb)
    last = d[d.week == d.groupby("posteam").week.transform("max")]
    latest = last.groupby("posteam").passer_id.agg(lambda s: s.value_counts().index[0])
    q["latest_starter"] = q.passer_id.isin(set(latest.values))
    return q.sort_values("qb_composite", ascending=False)


def pfr_team_pressure(pfr, p):
    g = pfr.groupby(["game_id", "team"]).times_pressured.sum().reset_index()
    g["team"] = g.team.replace({"LAR": "LA"})
    dbg = p[p.db].groupby(["game_id", "posteam"]).size()
    g["db"] = [dbg.get((a, b), np.nan) for a, b in zip(g.game_id, g.team)]
    s = g.groupby("team")
    return s.times_pressured.sum() / s.db.sum()


if __name__ == "__main__":
    main()
