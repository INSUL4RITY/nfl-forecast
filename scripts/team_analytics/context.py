"""Matchup context for the team analytics report: workload, fatigue evidence, rest and travel (including
body-clock kickoff times), detailed penalties, quarterback scenarios and run style.

Called from compute.py. Every function takes already-loaded frames; nothing here reads market data.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ET = ZoneInfo("America/New_York")

# home stadium location and time zone (relocated franchises included for the historical study)
TEAM_GEO = {
    "ARI": (33.53, -112.26, "America/Phoenix"), "ATL": (33.76, -84.40, "America/New_York"),
    "BAL": (39.28, -76.62, "America/New_York"), "BUF": (42.77, -78.79, "America/New_York"),
    "CAR": (35.23, -80.85, "America/New_York"), "CHI": (41.86, -87.62, "America/Chicago"),
    "CIN": (39.10, -84.52, "America/New_York"), "CLE": (41.51, -81.70, "America/New_York"),
    "DAL": (32.75, -97.09, "America/Chicago"), "DEN": (39.74, -105.02, "America/Denver"),
    "DET": (42.34, -83.05, "America/Detroit"), "GB": (44.50, -88.06, "America/Chicago"),
    "HOU": (29.68, -95.41, "America/Chicago"), "IND": (39.76, -86.16, "America/Indiana/Indianapolis"),
    "JAX": (30.32, -81.64, "America/New_York"), "KC": (39.05, -94.48, "America/Chicago"),
    "LA": (33.95, -118.34, "America/Los_Angeles"), "LAC": (33.95, -118.34, "America/Los_Angeles"),
    "LV": (36.09, -115.18, "America/Los_Angeles"), "MIA": (25.96, -80.24, "America/New_York"),
    "MIN": (44.97, -93.26, "America/Chicago"), "NE": (42.09, -71.26, "America/New_York"),
    "NO": (29.95, -90.08, "America/Chicago"), "NYG": (40.81, -74.07, "America/New_York"),
    "NYJ": (40.81, -74.07, "America/New_York"), "OAK": (37.75, -122.20, "America/Los_Angeles"),
    "PHI": (39.90, -75.17, "America/New_York"), "PIT": (40.45, -80.02, "America/New_York"),
    "SD": (32.78, -117.12, "America/Los_Angeles"), "SEA": (47.60, -122.33, "America/Los_Angeles"),
    "SF": (37.40, -121.97, "America/Los_Angeles"), "STL": (38.63, -90.19, "America/Chicago"),
    "TB": (27.98, -82.50, "America/New_York"), "TEN": (36.17, -86.77, "America/Chicago"),
    "WAS": (38.91, -76.86, "America/New_York"),
}
INTL_VENUES = [  # keyword in nflverse stadium name -> location
    ("Wembley", (51.56, -0.28, "Europe/London")), ("Tottenham", (51.60, -0.07, "Europe/London")),
    ("Twickenham", (51.46, -0.34, "Europe/London")), ("Allianz", (48.22, 11.62, "Europe/Berlin")),
    ("Bayern", (48.22, 11.62, "Europe/Berlin")), ("Frankfurt", (50.07, 8.65, "Europe/Berlin")),
    ("Deutsche Bank", (50.07, 8.65, "Europe/Berlin")), ("Olympiastadion", (52.51, 13.24, "Europe/Berlin")),
    ("Azteca", (19.30, -99.15, "America/Mexico_City")), ("Banorte", (19.30, -99.15, "America/Mexico_City")),
    ("Corinthians", (-23.55, -46.47, "America/Sao_Paulo")), ("Sao Paulo", (-23.55, -46.47, "America/Sao_Paulo")),
    ("Maracana", (-22.91, -43.23, "America/Sao_Paulo")), ("Melbourne", (-37.82, 144.98, "Australia/Melbourne")),
    ("Stade de France", (48.92, 2.36, "Europe/Paris")), ("Bernabeu", (40.45, -3.69, "Europe/Madrid")),
    ("Croke", (53.36, -6.25, "Europe/Dublin")), ("Rogers Centre", (43.64, -79.39, "America/Toronto")),
]


def venue_geo(row):
    if str(row.location) == "Neutral":
        for key, geo in INTL_VENUES:
            if key.lower() in str(row.stadium).lower():
                return geo + (True,)
        return (np.nan, np.nan, None, True)
    lat, lon, tz = TEAM_GEO.get(row.home_team, (np.nan, np.nan, None))
    return (lat, lon, tz, False)


def haversine_km(a_lat, a_lon, b_lat, b_lon):
    r = 6371.0
    p1, p2 = np.radians(a_lat), np.radians(b_lat)
    dphi, dl = p2 - p1, np.radians(b_lon - a_lon)
    h = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(h))


def kickoff(row):
    try:
        d = dt.datetime.strptime(f"{row.gameday} {row.gametime}", "%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return None
    return d.replace(tzinfo=ET)


def tz_hours(tz, when):
    return when.astimezone(ZoneInfo(tz)).utcoffset().total_seconds() / 3600


def slot_of(k):
    h = k.hour + k.minute / 60
    return "early" if h < 15 else ("late" if h < 19 else "night")


def travel_rows(sched: pd.DataFrame) -> pd.DataFrame:
    """One row per team per game with venue, distance, time-zone change and body-clock kickoff."""
    rows = []
    for r in sched.itertuples():
        k = kickoff(r)
        vlat, vlon, vtz, neutral = venue_geo(r)
        for team, side in [(r.home_team, "home"), (r.away_team, "away")]:
            lat, lon, htz = TEAM_GEO.get(team, (np.nan, np.nan, None))
            rec = {"game_id": r.game_id, "season": r.season, "week": r.week, "team": team, "side": side,
                   "opp": r.away_team if side == "home" else r.home_team, "neutral": neutral,
                   "intl": bool(neutral and vtz is not None),         # every listed neutral venue is outside the US
                   "rest": r.home_rest if side == "home" else r.away_rest, "weekday": r.weekday,
                   "gametime": r.gametime, "gameday": r.gameday, "stadium": r.stadium}
            if k is not None and vtz and htz:
                rec["tz_diff"] = tz_hours(vtz, k) - tz_hours(htz, k)       # + = travelled east
                rec["body_clock"] = k.astimezone(ZoneInfo(htz)).strftime("%H:%M")
                rec["body_hour"] = k.astimezone(ZoneInfo(htz)).hour + k.astimezone(ZoneInfo(htz)).minute / 60
                rec["local_time"] = k.astimezone(ZoneInfo(vtz)).strftime("%H:%M")
                rec["slot"] = slot_of(k)
                rec["km"] = float(haversine_km(lat, lon, vlat, vlon)) if not np.isnan(vlat) else np.nan
            rows.append(rec)
    return pd.DataFrame(rows)


def direction(d):
    if pd.isna(d):
        return None
    return "east 2+" if d >= 2 else ("west 2+" if d <= -2 else ("one zone" if abs(d) >= 1 else "same zone"))


# ------------------------------------------------------------------------------ travel / body clock study
def loo_residuals(g: pd.DataFrame) -> pd.Series:
    """Leave-one-game-out residual of home margin against a season team-strength fit."""
    teams = sorted(set(g.home_team) | set(g.away_team))
    idx = {t: i for i, t in enumerate(teams)}
    n, T = len(g), len(teams)
    X = np.zeros((n + 1, T + 1))
    X[:n, 0] = (g.location != "Neutral").astype(float).values
    X[np.arange(n), 1 + g.home_team.map(idx).values] += 1
    X[np.arange(n), 1 + g.away_team.map(idx).values] -= 1
    X[n, 1:] = 1.0
    y = np.concatenate([(g.home_score - g.away_score).astype(float).values, [0.0]])
    XtX_inv = np.linalg.pinv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    e = y[:n] - X[:n] @ beta
    h = np.einsum("ij,jk,ik->i", X[:n], XtX_inv, X[:n])
    return pd.Series(e / np.clip(1 - h, 0.05, None), index=g.index)


def travel_study(sched_all: pd.DataFrame, first=2002, last=2025) -> dict:
    s = sched_all[(sched_all.game_type == "REG") & sched_all.season.between(first, last) & sched_all.result.notna()].copy()
    s["resid_home"] = pd.concat([loo_residuals(g) for _, g in s.groupby("season")])
    tr = travel_rows(s)
    away = tr[(tr.side == "away") & ~tr.neutral].merge(s[["game_id", "resid_home", "home_rest", "away_rest"]], on="game_id")
    away["resid"] = -away.resid_home                          # + = away team did better than its strength implies
    away["dir"] = away.tz_diff.map(direction)
    away["rest_diff"] = away.away_rest - away.home_rest
    def summarise(df, key):
        out = []
        base = df[df.dir == "same zone"].resid
        for k, g in df.groupby(key):
            m, se = g.resid.mean(), g.resid.std(ddof=1) / np.sqrt(len(g))
            d = m - base.mean()
            se_d = np.sqrt(se ** 2 + base.var(ddof=1) / len(base))
            out.append({"group": k if isinstance(k, str) else " / ".join(map(str, k)), "n": int(len(g)), "mean": float(m),
                        "lo": float(m - 1.96 * se), "hi": float(m + 1.96 * se), "vs_same": float(d),
                        "vs_lo": float(d - 1.96 * se_d), "vs_hi": float(d + 1.96 * se_d)})
        return out
    by_dir_slot = summarise(away.dropna(subset=["dir"]), ["dir", "slot"])
    away["body_bin"] = pd.cut(away.body_hour, [0, 11.99, 14.99, 17.99, 20.99, 24],
                              labels=["before noon", "noon-3pm", "3-6pm", "6-9pm", "9pm or later"]).astype(str)
    by_body = summarise(away.dropna(subset=["body_hour"]), "body_bin")
    # rest and road-trip effects (all games, both sides)
    tr2 = tr.merge(s[["game_id", "resid_home"]], on="game_id")
    tr2["resid"] = np.where(tr2.side == "home", tr2.resid_home, -tr2.resid_home)
    tr2 = tr2.sort_values(["team", "season", "week"])
    tr2["prev_side"] = tr2.groupby(["team", "season"]).side.shift(1)
    tr2["prev_neutral"] = tr2.groupby(["team", "season"]).neutral.shift(1)
    rest_rows = []
    for lab, m in [("short week (5 days or fewer)", tr2.rest <= 5), ("normal (6-8 days)", tr2.rest.between(6, 8)),
                   ("long (9-12 days)", tr2.rest.between(9, 12)), ("after bye (13+ days)", tr2.rest >= 13)]:
        g = tr2[m]
        rest_rows.append({"group": lab, "n": int(len(g)), "mean": float(g.resid.mean()),
                          "lo": float(g.resid.mean() - 1.96 * g.resid.std() / np.sqrt(len(g))),
                          "hi": float(g.resid.mean() + 1.96 * g.resid.std() / np.sqrt(len(g)))})
    for lab, m in [("second straight road game", (tr2.side == "away") & (tr2.prev_side == "away") & ~tr2.neutral),
                   ("road game after a home game", (tr2.side == "away") & (tr2.prev_side == "home") & ~tr2.neutral),
                   ("first game after an international game", tr2.prev_neutral.fillna(False).astype(bool) & ~tr2.neutral)]:
        g = tr2[m]
        rest_rows.append({"group": lab, "n": int(len(g)), "mean": float(g.resid.mean()),
                          "lo": float(g.resid.mean() - 1.96 * g.resid.std() / np.sqrt(len(g))),
                          "hi": float(g.resid.mean() + 1.96 * g.resid.std() / np.sqrt(len(g)))})
    return {"seasons": [first, last], "games": int(len(s)), "by_dir_slot": by_dir_slot, "by_body_clock": by_body,
            "rest": rest_rows, "resid_sd": float(away.resid.std())}


def week_travel(sched_season: pd.DataFrame, week: int, study: dict) -> pd.DataFrame:
    tr = travel_rows(sched_season[sched_season.week <= week]).sort_values(["team", "week"])
    tr["dir"] = tr.tz_diff.map(direction)
    tr["prev_week"] = tr.groupby("team").week.shift(1)
    tr["prev_weekday"] = tr.groupby("team").weekday.shift(1)
    tr["prev_side"] = tr.groupby("team").side.shift(1)
    tr["prev_intl"] = tr.groupby("team").intl.shift(1)
    tr["prev_stadium"] = tr.groupby("team").stadium.shift(1)
    tr["prev_tz_diff"] = tr.groupby("team").tz_diff.shift(1)
    road = []
    for t, g in tr.groupby("team"):
        streak = 0
        for r in g.itertuples():
            streak = streak + 1 if (r.side == "away" or r.neutral) else 0
            road.append(streak)
    tr["road_streak"] = road
    cur = tr[tr.week == week].copy()
    lookup = {g["group"]: g for g in study["by_dir_slot"]}
    cur["hist"] = [lookup.get(f"{d} / {s}") if ((side == "away" or n) and d) else None
                   for d, s, side, n in zip(cur.dir, cur.slot, cur.side, cur.neutral)]
    return cur


# ------------------------------------------------------------------------------------------ workload
def workload(p: pd.DataFrame, dr: pd.DataFrame, snaps: pd.DataFrame, teams: list[str], W: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    out = pd.DataFrame(index=teams)
    sn = snaps[(snaps.week <= W) & (snaps.game_type == "REG")].copy()
    sn["team"] = sn.team.replace({"LAR": "LA"})
    tg = sn.groupby(["team", "game_id", "week"]).agg(off_snaps=("offense_snaps", "max"), def_snaps=("defense_snaps", "max"),
                                                      st_snaps=("st_snaps", "max")).reset_index()
    g = tg.groupby("team")
    out["off_snaps_pg"], out["def_snaps_pg"], out["st_snaps_pg"] = g.off_snaps.mean(), g.def_snaps.mean(), g.st_snaps.mean()
    last = tg.sort_values("week").groupby("team").tail(1).set_index("team")
    out["def_snaps_last"], out["off_snaps_last"], out["last_week_played"] = last.def_snaps, last.off_snaps, last.week
    last2 = tg.sort_values("week").groupby("team").tail(2).groupby("team").def_snaps.mean()
    out["def_snaps_last2"] = last2
    out["def_snaps_max"] = g.def_snaps.max()
    d = dr[~dr.excluded].copy()
    d["no_fd"] = d.first_downs.fillna(0) == 0
    d["three_out"] = d.no_fd & (d.result == "Punt")
    d["no_fd_no_score"] = d.no_fd & ~d.result.isin(["Touchdown", "Field goal"])
    d["sustained"] = (d.plays >= 8) | (d.top_sec >= 240)
    d["short_poss"] = ((d.plays <= 3) | (d.top_sec <= 90)) & d.result.isin(["Punt", "Turnover", "Turnover on downs", "Opp touchdown"])
    d["stop"] = d.result.isin(["Punt", "Turnover", "Turnover on downs", "Missed field goal", "Opp touchdown"])
    games = d.groupby("posteam").game_id.nunique()
    for side, key in [("off", "posteam"), ("def", "defteam")]:
        gg = d.groupby(key)
        ng = d.groupby(key).game_id.nunique()
        out[f"{side}_top_pg"] = gg.top_sec.sum() / ng / 60            # minutes with the ball (off) / defending (def)
        out[f"{side}_drive_sec"] = gg.top_sec.mean()
        out[f"{side}_drives_pg"] = gg.size() / ng
        out[f"{side}_three_out_rate"] = gg.three_out.mean()
        out[f"{side}_no_fd_rate"] = gg.no_fd_no_score.mean()
        out[f"{side}_sustained_pg"] = gg.sustained.sum() / ng
        out[f"{side}_short_poss_pg"] = gg.short_poss.sum() / ng
        out[f"{side}_stops_pg"] = gg.stop.sum() / ng
    out["off_snaps_per_drive"] = out.off_snaps_pg / out.off_drives_pg
    out["def_snaps_per_drive"] = out.def_snaps_pg / out.def_drives_pg
    # drive success rate (share of series that earn a first down or touchdown)
    se = p[p.series.notna() & p.series_success.notna() & p.posteam.notna() & (p.down.notna())]
    se = se.drop_duplicates(["game_id", "posteam", "series"])
    out["off_series_success"] = se.groupby("posteam").series_success.mean()
    out["def_series_success"] = se.groupby("defteam").series_success.mean()
    # quick turnarounds: defensive drives that start after the team's own offence held the ball 3 plays or fewer
    # (or 90 s or less), and wall-clock rest between defensive drives
    d = d.sort_values(["game_id", "fixed_drive"])
    d["prev_plays"] = d.groupby("game_id").plays.shift(1)
    d["prev_top"] = d.groupby("game_id").top_sec.shift(1)
    d["prev_pos"] = d.groupby("game_id").posteam.shift(1)
    d["prev_result"] = d.groupby("game_id").result.shift(1)
    d["quick"] = (d.prev_pos == d.defteam) & ((d.prev_plays <= 3) | (d.prev_top <= 90))
    d["after_to"] = (d.prev_pos == d.defteam) & d.prev_result.isin(["Turnover", "Opp touchdown"])
    d["short_field"] = d.start_yl <= 50
    ng = d.groupby("defteam").game_id.nunique()
    out["def_quick_pg"] = d[d.quick].groupby("defteam").size().reindex(teams).fillna(0) / ng
    out["def_short_field_after_to_pg"] = d[d.after_to & d.short_field].groupby("defteam").size().reindex(teams).fillna(0) / ng
    out["def_short_field_pg"] = d[d.short_field].groupby("defteam").size().reindex(teams).fillna(0) / ng
    # wall-clock minutes between the end of one defensive drive and the start of the next (same half)
    d["start_t"], d["end_t"] = pd.to_datetime(d.start_wall, utc=True, errors="coerce"), pd.to_datetime(d.end_wall, utc=True, errors="coerce")
    d = d.sort_values(["game_id", "defteam", "fixed_drive"])
    d["prev_def_end"] = d.groupby(["game_id", "defteam", "game_half"]).end_t.shift(1)
    d["rest_min"] = (d.start_t - d.prev_def_end).dt.total_seconds() / 60
    d.loc[(d.rest_min < 0) | (d.rest_min > 40), "rest_min"] = np.nan
    out["def_rest_min_median"] = d.groupby("defteam").rest_min.median()
    out["def_rest_under8_share"] = (d.rest_min < 8).groupby(d.defteam).mean()
    # intensity: dropbacks faced and longest stretch of defensive plays with only short offensive drives between
    out["def_dropbacks_pg"] = p[p.db].groupby("defteam").size() / ng
    stretch = []
    gm = dr[~dr.excluded].sort_values(["game_id", "fixed_drive"])
    for gid, gdrv in gm.groupby("game_id"):
        for team in set(gdrv.posteam):
            run, best = 0, 0
            for r in gdrv.itertuples():
                if r.defteam == team:
                    run += r.plays if pd.notna(r.plays) else 0
                elif r.posteam == team and ((r.plays or 0) > 3 and (r.top_sec or 0) > 90):
                    run = 0
                best = max(best, run)
            stretch.append({"team": team, "game_id": gid, "stretch": best})
    st = pd.DataFrame(stretch)
    out["def_max_stretch_avg"] = st.groupby("team").stretch.mean()
    return out, d


# ------------------------------------------------------------------------------- fatigue: 2026 descriptives
def fatigue_descriptives(p: pd.DataFrame, dq: pd.DataFrame, teams: list[str]) -> pd.DataFrame:
    sc = p[p.sc]
    out = pd.DataFrame(index=teams)
    for q in [1, 2, 3, 4]:
        out[f"def_epa_q{q}"] = sc[sc.qtr == q].groupby("defteam").epa.mean()
        out[f"def_sr_q{q}"] = sc[sc.qtr == q].groupby("defteam").success.mean()
    close = sc[sc.score_differential.abs() <= 8]
    out["def_epa_close_h1"] = close[close.game_half == "Half1"].groupby("defteam").epa.mean()
    out["def_epa_close_h2"] = close[close.game_half == "Half2"].groupby("defteam").epa.mean()
    out["def_close_h2_minus_h1"] = out.def_epa_close_h2 - out.def_epa_close_h1
    h2 = sc[sc.game_half == "Half2"]
    out["def_expl_rate_h2"] = h2.groupby("defteam").explosive.mean()
    out["def_expl_rate_h1"] = sc[sc.game_half == "Half1"].groupby("defteam").explosive.mean()
    q4r = sc[(sc.qtr >= 4) & sc.drush]
    out["def_rush_epa_q4"] = q4r.groupby("defteam").epa.mean()
    out["def_ypc_q4"] = q4r[q4r.play_type == "run"].groupby("defteam").yards_gained.mean()
    out["def_rush_epa_h1"] = sc[(sc.game_half == "Half1") & sc.drush].groupby("defteam").epa.mean()
    out["def_hs_h1"] = sc[(sc.game_half == "Half1") & sc.db].groupby("defteam").hit_sack.mean()
    out["def_hs_h2"] = h2[h2.db].groupby("defteam").hit_sack.mean()
    # drive-level: after own three-and-outs / turnovers / quick turnarounds, short fields
    dd = dq.copy()
    dd["prev_three_out"] = (dd.prev_pos == dd.defteam) & (dd.prev_plays <= 4) & (dd.prev_result == "Punt")
    dplay = sc.merge(dd[["game_id", "fixed_drive", "quick", "after_to", "prev_three_out", "short_field"]],
                     on=["game_id", "fixed_drive"], how="left")
    for lab, col in [("after_three_out", "prev_three_out"), ("after_to", "after_to"), ("quick", "quick")]:
        m = dplay[col].fillna(False).astype(bool)
        out[f"def_epa_{lab}"] = dplay[m].groupby("defteam").epa.mean()
        out[f"def_epa_not_{lab}"] = dplay[~m].groupby("defteam").epa.mean()
        out[f"def_n_{lab}"] = dplay[m].groupby("defteam").size()
    sf = dd[dd.short_field]
    out["def_ppd_short_field"] = sf.groupby("defteam").pts.mean()
    out["def_ppd_long_field"] = dd[~dd.short_field].groupby("defteam").pts.mean()
    out["def_q4_pts_pg"] = dd[dd.qtr >= 4].groupby("defteam").pts.sum() / dd.groupby("defteam").game_id.nunique()
    return out


# ------------------------------------------------------------------------------- fatigue: regression study
def _twoway_demean(df, cols, g1, g2, iters=25):
    x = df[cols].astype(float).copy()
    for _ in range(iters):
        x = x - x.groupby(df[g1]).transform("mean")
        x = x - x.groupby(df[g2]).transform("mean")
    return x


def _ols_cluster(y, X, clusters):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ beta
    XtX_inv = np.linalg.pinv(X.T @ X)
    meat = np.zeros((X.shape[1], X.shape[1]))
    for _, idx in pd.Series(np.arange(len(y))).groupby(clusters).groups.items():
        idx = np.asarray(idx)
        s = X[idx].T @ e[idx]
        meat += np.outer(s, s)
    V = XtX_inv @ meat @ XtX_inv
    return beta, np.sqrt(np.diag(V))


def fatigue_study(seasons_pbp: dict[int, pd.DataFrame], build_drives) -> dict:
    """Does defensive workload predict defensive efficiency, beyond team quality, quarter and score?

    Play level: EPA allowed ~ defensive plays already faced this game (per 10) + quarter + score-state
    dummies, with defence-season and offence-season fixed effects (two-way demeaning), game-clustered SEs.
    Drive level: EPA/play allowed on a drive ~ quick turnaround / wall-clock rest. Game level: EPA/play
    allowed ~ defensive snaps in the previous game."""
    plays, drives, games = [], [], []
    for s, p in seasons_pbp.items():
        sc = p[p.sc].copy().sort_values(["game_id", "play_id"])
        sc["cum_def"] = sc.groupby(["game_id", "defteam"]).cumcount()
        sc["season"] = s
        plays.append(sc[["season", "game_id", "posteam", "defteam", "epa", "success", "qtr", "score_differential", "cum_def"]])
        dr = build_drives(p)
        d = dr[~dr.excluded].sort_values(["game_id", "fixed_drive"]).copy()
        d["prev_plays"] = d.groupby("game_id").plays.shift(1)
        d["prev_top"] = d.groupby("game_id").top_sec.shift(1)
        d["prev_pos"] = d.groupby("game_id").posteam.shift(1)
        d["quick"] = ((d.prev_pos == d.defteam) & ((d.prev_plays <= 3) | (d.prev_top <= 90))).astype(float)
        d["start_t"] = pd.to_datetime(d.start_wall, utc=True, errors="coerce")
        d["end_t"] = pd.to_datetime(d.end_wall, utc=True, errors="coerce")
        d = d.sort_values(["game_id", "defteam", "fixed_drive"])
        d["rest_min"] = (d.start_t - d.groupby(["game_id", "defteam", "game_half"]).end_t.shift(1)).dt.total_seconds() / 60
        dp = p[p.sc].groupby(["game_id", "fixed_drive"]).agg(epa=("epa", "mean"), n=("epa", "size"),
                                                              sd=("score_differential", "first")).reset_index()
        d = d.merge(dp, on=["game_id", "fixed_drive"], how="inner")
        d["season"] = s
        drives.append(d[["season", "game_id", "posteam", "defteam", "epa", "n", "sd", "qtr", "quick", "rest_min"]])
        gm = p[p.sc].groupby(["game_id", "defteam", "posteam"]).agg(epa=("epa", "mean"), plays=("epa", "size"),
                                                                    week=("week", "first")).reset_index()
        gm["season"] = s
        games.append(gm)
    P = pd.concat(plays, ignore_index=True)
    P["sd_bin"] = pd.cut(-P.score_differential, [-99, -17, -9, -1, 0, 8, 16, 99]).astype(str)   # defence perspective
    P["dfe"] = P.defteam + P.season.astype(str)
    P["ofe"] = P.posteam + P.season.astype(str)
    Xd = pd.get_dummies(P[["qtr", "sd_bin"]].astype(str), drop_first=True).astype(float)
    Xd.insert(0, "cum_def_10", P.cum_def / 10)
    res = {}
    for ycol in ["epa", "success"]:
        df = pd.concat([P[[ycol, "dfe", "ofe", "game_id"]], Xd], axis=1)
        dm = _twoway_demean(df, [ycol] + list(Xd.columns), "dfe", "ofe")
        b, se = _ols_cluster(dm[ycol].values, dm[list(Xd.columns)].values, df.game_id.values)
        res[f"play_{ycol}"] = {"coef": float(b[0]), "se": float(se[0]), "n": int(len(df))}
    # drive level
    D = pd.concat(drives, ignore_index=True).dropna(subset=["epa"])
    D["dfe"] = D.defteam + D.season.astype(str)
    D["ofe"] = D.posteam + D.season.astype(str)
    D["sd_bin"] = pd.cut(-D.sd, [-99, -17, -9, -1, 0, 8, 16, 99]).astype(str)
    D["rest_short"] = (D.rest_min < 8).astype(float)
    Xq = pd.get_dummies(D[["qtr", "sd_bin"]].astype(str), drop_first=True).astype(float)
    for lab, col in [("drive_quick", "quick"), ("drive_rest_under8", "rest_short")]:
        sub = D if col == "quick" else D[D.rest_min.between(0, 40)]
        Xs = pd.concat([sub[[col]], Xq.loc[sub.index]], axis=1)
        df = pd.concat([sub[["epa", "dfe", "ofe", "game_id", "n"]], Xs], axis=1)
        dm = _twoway_demean(df, ["epa"] + list(Xs.columns), "dfe", "ofe")
        w = np.sqrt(df.n.values)
        b, se = _ols_cluster(dm.epa.values * w, dm[list(Xs.columns)].values * w[:, None], df.game_id.values)
        res[lab] = {"coef": float(b[0]), "se": float(se[0]), "n": int(len(df)), "share": float(sub[col].mean())}
    # game level: previous game's defensive plays
    Gm = pd.concat(games, ignore_index=True).sort_values(["season", "defteam", "week"])
    Gm["prev_plays"] = Gm.groupby(["season", "defteam"]).plays.shift(1)
    Gm = Gm.dropna(subset=["prev_plays"])
    Gm["dfe"] = Gm.defteam + Gm.season.astype(str)
    Gm["ofe"] = Gm.posteam + Gm.season.astype(str)
    Gm["prev10"] = Gm.prev_plays / 10
    dm = _twoway_demean(Gm, ["epa", "prev10"], "dfe", "ofe")
    w = np.sqrt(Gm.plays.values)
    b, se = _ols_cluster(dm.epa.values * w, dm[["prev10"]].values * w[:, None], Gm.game_id.values)
    res["game_prev_plays"] = {"coef": float(b[0]), "se": float(se[0]), "n": int(len(Gm))}
    # raw quarter profile (league): EPA allowed by quarter, all plays and close-score plays
    P["close"] = P.score_differential.abs() <= 8
    res["by_quarter"] = [{"qtr": int(q), "epa_all": float(g.epa.mean()), "epa_close": float(g[g.close].epa.mean()),
                          "n": int(len(g))} for q, g in P[P.qtr <= 4].groupby("qtr")]
    res["seasons"] = sorted(seasons_pbp)
    return res


# ------------------------------------------------------------------------------------------ penalties
OFF_TYPES = {
    "False start": ["False Start"], "Offensive holding": ["Offensive Holding"], "OPI": ["Offensive Pass Interference"],
    "Illegal formation": ["Illegal Formation"], "Illegal shift/motion": ["Illegal Shift", "Illegal Motion"],
    "Delay of game": ["Delay of Game"], "Ineligible downfield": ["Ineligible Downfield Pass", "Illegal Touch Pass"],
    "Intentional grounding": ["Intentional Grounding"],
    "Personal foul": ["Unnecessary Roughness", "Face Mask", "Taunting", "Lowering the Head to Make Forcible Contact",
                      "Chop Block", "Clipping", "Low Block", "Tripping", "Illegal Crackback", "Illegal Peelback"],
    "Unsportsmanlike": ["Unsportsmanlike Conduct"],
    "Illegal block": ["Illegal Block Above the Waist", "Illegal Blindside Block", "Illegal Use of Hands"],
    "Other pre-snap": ["Offensive Offside", "Offensive Too Many Men on Field", "Illegal Substitution"],
}
DEF_TYPES = {
    "Neutral zone": ["Neutral Zone Infraction"], "Offside": ["Defensive Offside"], "Encroachment": ["Encroachment"],
    "Defensive holding": ["Defensive Holding"], "DPI": ["Defensive Pass Interference"], "Illegal contact": ["Illegal Contact"],
    "Roughing the passer": ["Roughing the Passer"], "Face mask": ["Face Mask"], "Unnecessary roughness": ["Unnecessary Roughness"],
    "Unsportsmanlike": ["Unsportsmanlike Conduct", "Taunting"], "Illegal substitution / 12 men": ["Defensive Too Many Men on Field", "Illegal Substitution"],
    "Illegal use of hands": ["Illegal Use of Hands"], "Other personal foul": ["Horse Collar Tackle", "Lowering the Head to Make Forcible Contact", "Tripping"],
    "Defensive delay": ["Defensive Delay of Game", "Delay of Game"],
    "Kicker contact": ["Roughing the Kicker", "Running Into the Kicker"],
}
ST_TYPES = {
    "Holding": ["Offensive Holding", "Defensive Holding"], "Block in the back / illegal block": ["Illegal Block Above the Waist", "Illegal Blindside Block", "Illegal Use of Hands", "Low Block", "Clipping"],
    "Offside on kick": ["Offside on Free Kick", "Defensive Offside", "Encroachment"],
    "Kicker contact": ["Running Into the Kicker", "Roughing the Kicker"],
    "Kick-catch interference": ["Fair Catch Interference", "Kick Catch Interference", "Invalid Fair Catch Signal"],
    "Kickoff rules": ["Kickoff Short of Landing Zone", "Kickoff Out of Bounds", "Illegal Kickoff Formation", "Illegal Formation"],
    "Out of bounds on kick": ["Player Out of Bounds on Kick"], "Personal foul": ["Unnecessary Roughness", "Face Mask", "Unsportsmanlike Conduct", "Taunting",
                                                               "Lowering the Head to Make Forcible Contact"],
}


def classify(phase, ptype):
    table = {"off": OFF_TYPES, "def": DEF_TYPES, "st": ST_TYPES}[phase]
    for cat, types in table.items():
        if ptype in types:
            return cat
    return "Other"


def penalty_detail(p: pd.DataFrame, teams: list[str], ep_yard: float = 0.07):
    """Per-penalty table with phase, category and situational flags, plus per-team aggregates."""
    x = p[(p.penalty == 1) & p.penalty_team.notna() & p.posteam.notna()].copy()
    desc = x.desc.fillna("")
    x["declined"] = desc.str.contains(r"PENALTY on [^,]+, [^,]+, declined", case=False, regex=True)
    x["offsetting"] = desc.str.contains("offsetting", case=False)
    x["multi"] = desc.str.count("PENALTY") >= 2
    x["accepted"] = ~x.declined & ~x.offsetting
    st_types = {"kickoff", "punt", "field_goal", "extra_point"}
    x["phase"] = np.where((x.special_teams_play == 1) | x.play_type.isin(st_types), "st",
                          np.where(x.penalty_team == x.posteam, "off", "def"))
    x["category"] = [classify(ph, t) for ph, t in zip(x.phase, x.penalty_type.fillna(""))]
    pre = desc.str.split("PENALTY").str[0]
    yds = pre.str.extract(r"for (-?\d+) yards?")[0].astype(float)
    noplay = x.play_type == "no_play"
    off = x.phase == "off"
    x["negated_fd"] = noplay & off & ((yds >= x.ydstogo) | desc.str.contains("TOUCHDOWN NULLIFIED"))
    need = np.where(x.down == 1, 0.4 * x.ydstogo, np.where(x.down == 2, 0.6 * x.ydstogo, x.ydstogo))
    x["negated_success"] = noplay & off & (yds >= need)
    x["out_of_fg_range"] = off & (x.yardline_100 <= 37) & (x.yardline_100 + x.penalty_yards.fillna(0) > 37) & (x.special_teams_play != 1)
    x["drive_extending"] = (x.phase == "def") & (x.first_down_penalty == 1) & x.down.isin([3, 4])
    x["high_leverage"] = (x.qtr >= 4) & (x.score_differential.abs() <= 8)
    pen_sd = np.where(x.penalty_team == x.posteam, x.score_differential, -x.score_differential)
    x["while_leading_late"] = (x.qtr >= 4) & (pen_sd >= 1) & (pen_sd <= 8)
    x["while_trailing_late"] = (x.qtr >= 4) & (pen_sd <= -1) & (pen_sd >= -8)
    # next scrimmage play's distance, for long-yardage situations created by offensive fouls
    nxt = p.groupby("game_id").ydstogo.shift(-1)
    x["next_ydstogo"] = nxt.reindex(x.index)
    x["created_long"] = off & noplay & (x.next_ydstogo >= 15)
    x["np_epa"] = np.where(noplay, x.epa, np.nan)
    # live-ball accepted penalties: approximate EPA of the yardage at a league EP-per-yard slope (documented)
    x["live_epa_est"] = np.where(~noplay & x.accepted, ep_yard * x.penalty_yards.fillna(0), np.nan)
    a = x[x.accepted]
    out = pd.DataFrame(index=teams)
    games = p.groupby("posteam").game_id.nunique()
    for ph in ["off", "def", "st"]:
        s = a[a.phase == ph].groupby("penalty_team")
        out[f"pd_{ph}_pg"] = s.size() / games
    out["pd_total_pg"] = a.groupby("penalty_team").size() / games
    out["pd_total_yds_pg"] = a.groupby("penalty_team").penalty_yards.sum() / games
    for col in ["negated_fd", "negated_success", "out_of_fg_range", "drive_extending", "high_leverage",
                "while_leading_late", "while_trailing_late", "created_long"]:
        out[f"pd_{col}"] = a[a[col]].groupby("penalty_team").size()
    out["pd_multi_plays"] = x[x.multi].groupby("penalty_team").size()
    out["pd_declined"] = x[x.declined].groupby("penalty_team").size()
    out["pd_offsetting"] = x[x.offsetting].groupby("penalty_team").size()
    out["pd_accepted"] = a.groupby("penalty_team").size()
    # drawn
    out["pd_drawn_def_pg"] = a[a.phase == "def"].groupby("posteam").size() / games
    db = p[p.db]
    out["pd_dpi_drawn_per100db"] = 100 * a[a.penalty_type == "Defensive Pass Interference"].groupby("posteam").size() / db.groupby("posteam").size()
    out["pd_cover_fouls_per100db"] = 100 * a[(a.phase == "def") & a.penalty_type.isin(
        ["Defensive Pass Interference", "Defensive Holding", "Illegal Contact"])].groupby("penalty_team").size() / db.groupby("defteam").size()
    out["pd_off_holding_per100db"] = 100 * a[(a.phase == "off") & (a.penalty_type == "Offensive Holding")].groupby("penalty_team").size() / db.groupby("posteam").size()
    out["pd_off_holding_drawn_per100db"] = 100 * a[(a.phase == "off") & (a.penalty_type == "Offensive Holding")].groupby("defteam").size() / db.groupby("defteam").size()
    out["pd_rtp_per100db"] = 100 * a[a.penalty_type == "Roughing the Passer"].groupby("penalty_team").size() / db.groupby("defteam").size()
    presnap_def = ["Neutral Zone Infraction", "Defensive Offside", "Encroachment"]
    plays_off = p[p.sc | ((p.play_type == "no_play") & (p.special_teams_play != 1))]
    n_off, n_def = plays_off.groupby("posteam").size(), plays_off.groupby("defteam").size()
    out["pd_def_jump_per100"] = 100 * a[a.penalty_type.isin(presnap_def) & (a.phase == "def")].groupby("penalty_team").size() / n_def
    out["pd_def_jump_drawn_per100"] = 100 * a[a.penalty_type.isin(presnap_def) & (a.phase == "def")].groupby("posteam").size() / n_off
    presnap_off = ["False Start", "Delay of Game", "Illegal Formation", "Illegal Shift", "Illegal Motion"]
    out["pd_off_presnap_per100"] = 100 * a[a.penalty_type.isin(presnap_off) & (a.phase == "off")].groupby("penalty_team").size() / n_off
    out["pd_off_presnap_drawn_per100"] = 100 * a[a.penalty_type.isin(presnap_off) & (a.phase == "off")].groupby("defteam").size() / n_def
    fs = a[(a.penalty_type == "False Start") & (a.phase == "off")].copy()
    fs["home"] = fs.penalty_team == fs.home_team
    ph = plays_off.assign(home=plays_off.posteam == plays_off.home_team)
    out["pd_fs_away_per100"] = 100 * fs[~fs.home].groupby("penalty_team").size().reindex(teams).fillna(0) / ph[~ph.home].groupby("posteam").size()
    out["pd_fs_home_per100"] = 100 * fs[fs.home].groupby("penalty_team").size().reindex(teams).fillna(0) / ph[ph.home].groupby("posteam").size()
    out["pd_off_yds_per_snap"] = a[a.phase == "off"].groupby("penalty_team").penalty_yards.sum() / n_off
    out["pd_def_yds_per_snap"] = a[a.phase == "def"].groupby("penalty_team").penalty_yards.sum() / n_def
    out["pd_np_epa_off"] = -a[(a.phase == "off")].groupby("penalty_team").np_epa.sum()
    out["pd_np_epa_def"] = a[(a.phase == "def")].groupby("penalty_team").np_epa.sum()
    out["pd_live_epa_est_off"] = a[(a.phase == "off")].groupby("penalty_team").live_epa_est.sum()
    out["pd_live_epa_est_def"] = a[(a.phase == "def")].groupby("penalty_team").live_epa_est.sum()
    out["pd_epa_cost_total"] = out[["pd_np_epa_off", "pd_np_epa_def", "pd_live_epa_est_off", "pd_live_epa_est_def"]].sum(axis=1) / games
    out = out.fillna(0)          # every rate here has a non-zero denominator, so a missing numerator means zero
    by_type = (a.groupby(["penalty_team", "phase", "category"]).agg(n=("play_id", "size"), yds=("penalty_yards", "sum"))
               .reset_index().rename(columns={"penalty_team": "team"}))
    by_type["per_game"] = by_type.n / by_type.team.map(games)
    raw_types = sorted(a.penalty_type.dropna().unique())
    grouping = {ph: {cat: [t for t in types if t in raw_types] for cat, types in tbl.items()}
                for ph, tbl in [("off", OFF_TYPES), ("def", DEF_TYPES), ("st", ST_TYPES)]}
    other = {ph: sorted(set(a[(a.phase == ph) & (a.category == "Other")].penalty_type.dropna())) for ph in ["off", "def", "st"]}
    return out, by_type, {"grouping": grouping, "other": other, "ep_yard": ep_yard}, x


def rz_penalty_effect(dr: pd.DataFrame, x: pd.DataFrame) -> pd.DataFrame:
    """Red-zone trips with and without an accepted offensive penalty inside the 20."""
    pen = x[x.accepted & (x.phase == "off") & (x.yardline_100 <= 20)]
    keys = set(zip(pen.game_id, pen.fixed_drive)) if "fixed_drive" in pen else set()
    d = dr[~dr.excluded & (dr.rz_trip == 1)].copy()
    d["rz_pen"] = [(g, f) in keys for g, f in zip(d.game_id, d.fixed_drive)]
    out = d.groupby(["posteam", "rz_pen"]).td.agg(["mean", "size"]).unstack()
    return out


# -------------------------------------------------------------------------------------- QB scenarios
TRICK_MAX = 5   # a passer with fewer season dropbacks than this is treated as a trick play, not a starter


def qb_starts(p: pd.DataFrame) -> pd.DataFrame:
    """The quarterback who started each team-game: the passer of the team's first dropback, skipping passers with
    fewer than TRICK_MAX season dropbacks. A starter hurt early still gets the start (the passer with the most
    dropbacks would not be him). One row per team-game: posteam, game_id, week, passer_id."""
    d = p[p.db & p.passer_id.notna()].sort_values(["game_id", "play_id"])
    d = d[d.passer_id.map(d.groupby("passer_id").size()) >= TRICK_MAX]
    return d.drop_duplicates(["posteam", "game_id"])[["posteam", "game_id", "week", "passer_id"]].reset_index(drop=True)


def one_quarter(g: pd.DataFrame) -> dict | None:
    """When a single quarter supplied more than half of a passer's total EPA (same sign as the total) and leaving it out
    moves his EPA per dropback by ONE_Q_SHIFT or more, that quarter and his average without it; else None. g = his dropbacks. Descriptive only: the backtest found that dropping the best
    quarter does not predict better than shrinkage, so it changes no number, it only warns."""
    if len(g) < 10 or g.epa.notna().sum() < 10:
        return None
    tot = float(g.epa.sum())
    q = g.assign(q=g.qtr.clip(upper=5)).groupby(["week", "q"]).epa.agg(["sum", "size"])
    k = q["sum"].idxmax() if tot > 0 else q["sum"].idxmin()
    best, n = float(q.loc[k, "sum"]), int(q.loc[k, "size"])
    if abs(tot) < 1 or best * tot <= 0 or abs(best) <= abs(tot) / 2 or n >= len(g):
        return None
    if abs(tot / len(g) - (tot - best) / (len(g) - n)) < ONE_Q_SHIFT:
        return None
    return {"week": int(k[0]), "qtr": int(k[1]), "epa": round(best, 2), "n": n, "total": round(tot, 2),
            "without": round((tot - best) / (len(g) - n), 3)}


def qb_scenarios(p: pd.DataFrame, Q: pd.DataFrame, ros_cur: pd.DataFrame, inj_last: pd.DataFrame, teams, W: int = 99) -> dict:
    d = p[p.db & p.passer_id.notna()]
    starts = (d.groupby(["posteam", "game_id", "passer_id"]).size().reset_index(name="n")
              .sort_values("n", ascending=False).drop_duplicates(["posteam", "game_id"]))
    starts["week"] = starts.game_id.str[5:7].astype(int)     # main passer of each game: most dropbacks
    true = qb_starts(p)                                        # the quarterback who started it
    sc = p[p.sc]
    out = {}
    qn = Q.set_index("passer_id")
    for t in teams:
        st = starts[starts.posteam == t].sort_values("week")
        latest = st.iloc[-1].passer_id if len(st) else None
        tq = d[d.posteam == t].groupby("passer_id").size()
        rows = []
        for pid, ndb in tq[tq >= 30].sort_values(ascending=False).items():
            gids = set(st[st.passer_id == pid].game_id)
            off_games = sc[(sc.posteam == t) & sc.game_id.isin(gids)]
            r = qn.loc[pid] if pid in qn.index else None
            ro = ros_cur[(ros_cur.gsis_id == pid)]
            ij = inj_last[inj_last.gsis_id == pid]
            rows.append({
                "id": pid, "name": (r.name_full if r is not None and isinstance(r.name_full, str) else str(r.name if r is not None else pid)),
                "dropbacks": int(ndb), "starts": int(((true.posteam == t) & (true.passer_id == pid)).sum()),
                "start_weeks": sorted(int(w) for w in true[(true.posteam == t) & (true.passer_id == pid)].week),
                "epa_db": None if r is None else float(r.epa_db), "adj_epa_db": None if r is None else float(r.adj_epa_db),
                "sr": None if r is None else float(r.sr),
                "sack_rate": None if r is None else float(r.sack_rate),
                "int_worthy": None if r is None or pd.isna(r.int_worthy_rate) else float(r.int_worthy_rate),
                "epa_vs_blitz": None if r is None or pd.isna(r.epa_vs_blitz) else float(r.epa_vs_blitz),
                "db_blitz": None if r is None else int(r.db_blitz), "db_hit": None if r is None else int(r.db_hit),
                "epa_hit_sack": None if r is None or pd.isna(r.epa_hit_sack) else float(r.epa_hit_sack),
                "scr_rate": None if r is None else float(r.scr_rate),
                "team_epa_play_in_starts": float(off_games.epa.mean()) if len(off_games) else None,
                "team_plays_in_starts": int(len(off_games)),
                "roster_status": ro.status.iloc[0] if len(ro) else None,
                "report_status": ij.report_status.iloc[0] if len(ij) and pd.notna(ij.report_status.iloc[0]) else None,
                "practice_status": ij.practice_status.iloc[0] if len(ij) and pd.notna(ij.practice_status.iloc[0]) else None,
                "report_week": int(ij.week.iloc[0]) if len(ij) else None,
                "latest_starter": pid == latest,
                "one_q": one_quarter(d[(d.posteam == t) & (d.passer_id == pid)]),
            })
        primary = max(rows, key=lambda r: (r["starts"], r["dropbacks"]))["id"] if rows else None
        flags = []
        if len(st.passer_id.unique()) > 1:
            flags.append("Season figures mix quarterbacks.")
        lr = next((r for r in rows if r["latest_starter"]), None)
        def rep_lab(r):
            return f"last week's report (week {r['report_week']})" if r["report_week"] and r["report_week"] <= W else f"the week {r['report_week']} report"

        def status(r):
            if r["roster_status"] == "RES":
                return "is on the reserve list"
            if r["report_status"]:
                return f"was listed {r['report_status']} in {rep_lab(r)}" + (
                    f" ({r['practice_status'].lower()})" if r["practice_status"] else "")
            if r["practice_status"]:
                return f"practice status in {rep_lab(r)}: {r['practice_status'].lower()}"
            return None
        most = max(rows, key=lambda r: (r["starts"], r["dropbacks"])) if rows else None
        if lr and (lr["roster_status"] == "RES" or lr["report_status"] in ("Out", "Doubtful")):
            flags.append(f"Latest starter {lr['name']} {status(lr)}: another quarterback is likely to start.")
        elif lr and lr["report_status"] == "Questionable":
            flags.append(f"Latest starter {lr['name']} {status(lr)}.")
        elif lr and (lr["practice_status"] or "").startswith("Did Not"):
            flags.append(f"Latest starter {lr['name']}: {status(lr)}.")
        for r in rows:
            if r is lr or r["starts"] < 2:
                continue
            if r["roster_status"] == "RES":
                flags.append(f"{r['name']} ({r['starts']} starts) {status(r)}: his games are in the season figures, but he will not play.")
            elif r is most and status(r):
                flags.append(f"{r['name']} ({r['starts']} starts, the most on the team) {status(r)}. If he returns, "
                             f"the passing profile could differ from the recent games.")
        out[t] = {"qbs": rows, "latest": latest, "primary": primary, "flags": flags}
    return out


MIX_FLAG = "Season figures mix quarterbacks."
ONE_Q_SHIFT = 0.10   # EPA per dropback: a single quarter is flagged only if leaving it out moves the average this much
MIN_SAMPLE = 30   # dropbacks needed before a reported starter's own numbers are shown


def load_qb_news(season: int, week: int) -> dict:
    """The hand-kept quarterback news for one week ({} when the file or the week is missing)."""
    f = Path(__file__).resolve().parent / f"qb_news_{season}.json"
    if not f.exists():
        return {}
    return json.loads(f.read_text(encoding="utf-8")).get("weeks", {}).get(str(week), {})


def _key(name) -> str:
    s = re.sub(r"\b(jr|sr|ii|iii|iv)\b\.?", "", str(name).lower())
    return re.sub(r"[^a-z]", "", s)


def apply_qb_news(qbs: dict, news: dict, Q: pd.DataFrame, p: pd.DataFrame, week: int) -> list[str]:
    """Add reported starters and departures that the rosters and injury reports cannot show yet (trades, signings,
    benchings). The named starter becomes the team's expected starter; his own 2026 sample comes from every team he
    played for (none for a quarterback without a regular-season dropback). Quarterbacks listed as unavailable keep their
    rows (their games are in the season figures) with the reason. Returns one line per team for the quality checks."""
    true = qb_starts(p)
    qn = Q.assign(k=Q.name_full.fillna(Q.name).map(_key))
    lines = []
    for t, e in sorted(news.items()):
        info = qbs.setdefault(t, {"qbs": [], "latest": None, "primary": None, "flags": []})
        rows = info["qbs"]
        for r in rows:
            r.pop("news", None)
        k = _key(e["starter"])
        row = next((r for r in rows if _key(r["name"]) == k), None)
        if row is None:
            q = qn[qn.k == k]
            q = q.iloc[0] if len(q) else None
            pid = None if q is None else q.passer_id
            mine = true[true.passer_id == pid] if pid is not None else true.iloc[0:0]
            nn = lambda c: None if q is None or c not in q or pd.isna(q[c]) else float(q[c])   # noqa: E731
            row = {"id": pid, "name": e["starter"], "dropbacks": 0 if q is None else int(q.dropbacks),
                   "starts": int(len(mine)), "start_weeks": sorted(int(w) for w in mine.week),
                   "start_teams": sorted(set(mine.posteam)),
                   "epa_db": nn("epa_db"), "adj_epa_db": nn("adj_epa_db"), "sr": nn("sr"), "sack_rate": nn("sack_rate"),
                   "int_worthy": nn("int_worthy_rate"), "epa_vs_blitz": nn("epa_vs_blitz"),
                   "db_blitz": None if q is None else int(q.db_blitz), "db_hit": None if q is None else int(q.db_hit),
                   "epa_hit_sack": nn("epa_hit_sack"), "scr_rate": nn("scr_rate"),
                   "team_epa_play_in_starts": None, "team_plays_in_starts": 0,
                   "roster_status": None, "report_status": None, "practice_status": None, "report_week": None,
                   "latest_starter": False, "sample_team": None if q is None else str(q.teams),
                   "one_q": None if pid is None else one_quarter(p[p.db & (p.passer_id == pid)])}
            rows.append(row)
        row["news"] = True
        row["news_status"] = "reported starter" if e["conf"] == "named" else "expected starter, not confirmed"
        gone = []
        for u in e.get("unavailable", []):
            r = next((r for r in rows if _key(r["name"]) == _key(u["player"])), None)
            if r is not None:
                r["news_status"] = u["why"]
                gone.append(f"{r['name']} ({r['starts']} start{'' if r['starts'] == 1 else 's'}) {u['why']}")
        src = "; ".join(f"{s['who']}, {s['when']}: {s['what']}" for s in e["sources"])
        if row["dropbacks"] == 0 or row["adj_epa_db"] is None:
            sample = "no 2026 regular-season dropbacks, so no own sample"
        elif row["dropbacks"] < MIN_SAMPLE:
            sample = f"only {row['dropbacks']} 2026 dropbacks, too few for an own sample"
        else:
            other = row.get("sample_team") and row["sample_team"] != t
            sample = (f"his 2026 sample is {row['dropbacks']} dropbacks{' with ' + row['sample_team'] if other else ''}"
                      f" ({row['starts']} start{'' if row['starts'] == 1 else 's'})")
        verb = "is the reported starter" if e["conf"] == "named" else "is expected to start (not confirmed by the team)"
        one = len(gone) == 1
        news_flag = (f"Week {week} news: {e['starter']} {verb}; {sample}." + (" " + "; ".join(gone) + (": his games are in the season figures, "
                     "but he will not play for this team." if one else ": their games are in the season figures, but they will not play "
                     "for this team.") if gone else "") + f" Source: {src}.")
        info["flags"] = [f for f in info["flags"] if "likely to start" not in f and "If he returns" not in f] + [news_flag]
        info["news"] = {"starter": e["starter"], "conf": e["conf"], "sources": e["sources"], "flag": news_flag}
        lines.append(f"{t} {e['starter']} ({e['conf']})")
    return lines


def qb_news_qc(lines: list[str], week: int) -> str:
    if not lines:
        return f"Quarterback news: no hand-kept entries for week {week}; expected starters follow the rosters and injury reports only."
    return (f"Quarterback news (hand-kept, with sources, for what rosters and injury reports cannot show yet): week {week} starters "
            f"{', '.join(lines)}. Injury reports still decide game statuses.")


# ----------------------------------------------------------------------------------------- run style
def run_style(p: pd.DataFrame, teams) -> pd.DataFrame:
    r = p[p.drush_live & ~p.qb_drun].copy()
    r["inside"] = (r.run_location == "middle") | (r.run_gap == "guard")
    r["outside"] = r.run_gap.isin(["tackle", "end"])
    out = pd.DataFrame(index=teams)
    known = r[r.inside | r.outside]
    out["run_inside_share"] = known.groupby("posteam").inside.mean()
    for lab in ["inside", "outside"]:
        s = r[r[lab]]
        out[f"off_epa_{lab}"] = s.groupby("posteam").epa.mean()
        out[f"off_n_{lab}"] = s.groupby("posteam").size()
        out[f"def_epa_{lab}"] = s.groupby("defteam").epa.mean()
        out[f"def_n_{lab}"] = s.groupby("defteam").size()
    out["def_inside_share_faced"] = known.groupby("defteam").inside.mean()
    return out
