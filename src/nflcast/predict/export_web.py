"""Export versioned JSON for the Next.js site (web/public/data). The site never computes forecasts.

Files:
  manifest.json            weeks available, latest week, export time, model labels
  weeks/<season>-<wk>.json every scheduled game of the week, its frozen forecast (latest release
                           generated before kickoff), all forecast versions, and the result if final
  performance.json         walk-forward (tune/dev), locked-test and prospective evaluation summaries
  retro_<season>.json      per-game RETROSPECTIVE backtest predictions for the locked season
  ratings.json             as-of team ratings at export time
  teams.json               names and colours (nflverse)
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

import numpy as np
import polars as pl
import yaml

from nflcast.config import PROCESSED_DIR, RELEASES_DIR, REPORTS_DIR, ROOT, settings, utc_now
from nflcast.data import sources as S
from nflcast.data.games import build_games, franchise
from nflcast.features.asof import AsOfFeatureBuilder
from nflcast.features.personnel import QBModel

WEB_DATA = ROOT / "web" / "public" / "data"

TEAM_TZ = {
    "ARI": "America/Phoenix", "ATL": "America/New_York", "BAL": "America/New_York", "BUF": "America/New_York",
    "CAR": "America/New_York", "CHI": "America/Chicago", "CIN": "America/New_York", "CLE": "America/New_York",
    "DAL": "America/Chicago", "DEN": "America/Denver", "DET": "America/Detroit", "GB": "America/Chicago",
    "HOU": "America/Chicago", "IND": "America/Indiana/Indianapolis", "JAX": "America/New_York", "KC": "America/Chicago",
    "LA": "America/Los_Angeles", "LAC": "America/Los_Angeles", "LV": "America/Los_Angeles", "MIA": "America/New_York",
    "MIN": "America/Chicago", "NE": "America/New_York", "NO": "America/Chicago", "NYG": "America/New_York",
    "NYJ": "America/New_York", "PHI": "America/New_York", "PIT": "America/New_York", "SEA": "America/Los_Angeles",
    "SF": "America/Los_Angeles", "TB": "America/New_York", "TEN": "America/Chicago", "WAS": "America/New_York",
}
VENUE_TZ = [  # neutral / international venues matched by stadium-name keyword
    ("Melbourne", "Australia/Melbourne"), ("Maracana", "America/Sao_Paulo"), ("Tottenham", "Europe/London"),
    ("Wembley", "Europe/London"), ("Stade de France", "Europe/Paris"), ("Bernabeu", "Europe/Madrid"),
    ("Munich", "Europe/Berlin"), ("Allianz", "Europe/Berlin"), ("Frankfurt", "Europe/Berlin"), ("Deutsche Bank", "Europe/Berlin"),
    ("Croke", "Europe/Dublin"), ("Banorte", "America/Mexico_City"), ("Azteca", "America/Mexico_City"),
    ("Corinthians", "America/Sao_Paulo"), ("Levi", "America/Los_Angeles"), ("SoFi", "America/Los_Angeles"),
    ("Allegiant", "America/Los_Angeles"), ("State Farm", "America/Phoenix"), ("Superdome", "America/Chicago"),
    ("NRG", "America/Chicago"), ("U.S. Bank", "America/Chicago"), ("Hard Rock", "America/New_York"),
    ("Raymond James", "America/New_York"), ("Mercedes-Benz Stadium", "America/New_York"),
]


def venue_tz(stadium: str | None, home_id: str) -> str:
    for key, tz in VENUE_TZ:
        if stadium and key.lower() in stadium.lower():
            return tz
    return TEAM_TZ.get(home_id, "America/New_York")


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, default=str, separators=(",", ":")), encoding="utf-8")


def _releases() -> list[dict]:
    out = []
    for f in sorted(RELEASES_DIR.rglob("rel_*.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        if r.get("schema_version", 1) >= 2:
            out.append(r)
    return out


def _latest(pattern: str) -> Path | None:
    c = sorted(REPORTS_DIR.glob(pattern))
    return c[-1] if c else None


def export() -> Path:
    now = utc_now()
    if WEB_DATA.exists():
        shutil.rmtree(WEB_DATA)
    WEB_DATA.mkdir(parents=True)
    teams = S.fetch("teams")
    team_info = {r["team_abbr"]: {"abbr": r["team_abbr"], "name": r["team_name"], "nick": r["team_nick"],
                                  "color": r["team_color"], "color2": r["team_color2"], "conf": r["team_conf"],
                                  "division": r["team_division"]} for r in teams.iter_rows(named=True)}
    _write(WEB_DATA / "teams.json", team_info)
    games = build_games(S.fetch("schedules"))
    releases = _releases()
    versions: dict[str, list[tuple[dict, dict]]] = {}
    for r in releases:
        for g in r["games"]:
            versions.setdefault(g["game_id"], []).append((r, g))
    weeks = sorted({(r["season"], r["week"]) for r in releases})
    cur = settings()["seasons"]["current"]
    # also export the other weeks of the current season (fixtures, results; forecasts only if archived)
    weeks = sorted(set(weeks) | {(cur, int(w)) for w in games.filter(pl.col("season") == cur)["week"].unique().to_list()})
    week_index = []
    for season, week in weeks:
        wk = games.filter((pl.col("season") == season) & (pl.col("week") == week)).sort("kickoff_utc")
        items = []
        for g in wk.iter_rows(named=True):
            vs = sorted(versions.get(g["game_id"], []), key=lambda x: x[0]["generated_at_utc"])
            kick = g["kickoff_utc"]
            pre = [(r, e) for r, e in vs if datetime.fromisoformat(r["generated_at_utc"]) < kick]
            frozen = pre[-1] if pre else None
            if frozen:
                state = "published"
            elif g["status"] == "final" or kick <= now:
                state = "not_archived"   # game before the first production release: no forecast is shown
            else:
                state = "pending"
            item = {
                "game_id": g["game_id"], "season": season, "week": week, "game_type": g["game_type"],
                "kickoff_utc": kick.isoformat(), "kickoff_time_known": g["kickoff_time_known"],
                "venue_tz": venue_tz(g["stadium"], g["home_id"]), "stadium": g["stadium"],
                "neutral_site": g["neutral_site"], "roof": g["roof"], "home": g["home_team"], "away": g["away_team"],
                "status": g["status"], "score": ({"home": g["home_score"], "away": g["away_score"]}
                                                 if g["status"] == "final" else None),
                "forecast_state": state, "forecast": frozen[1] if frozen else None,
                "forecast_run_id": frozen[0]["run_id"] if frozen else None,
                "forecast_generated_at": frozen[0]["generated_at_utc"] if frozen else None,
                "history": [{"run_id": r["run_id"], "generated_at": r["generated_at_utc"], "label": e["release_label"],
                             "home_pts": e["forecast"]["home_pts"], "away_pts": e["forecast"]["away_pts"],
                             "margin": e["forecast"]["margin"], "total": e["forecast"]["total"],
                             "p_home": e["forecast"]["p_home"], "primary_model": e["primary_model"],
                             "market_spread": (e.get("market") or {}).get("home_spread"),
                             "market_total": (e.get("market") or {}).get("total"),
                             "before_kickoff": datetime.fromisoformat(r["generated_at_utc"]) < kick} for r, e in vs],
            }
            items.append(item)
        rel = [r for r in releases if r["season"] == season and r["week"] == week]
        doc = {"season": season, "week": week,
               "date_range": [wk["gameday"].min(), wk["gameday"].max()] if wk.height else None,
               "n_games": wk.height, "last_release_at": rel[-1]["generated_at_utc"] if rel else None,
               "release_count": len(rel), "games": items}
        _write(WEB_DATA / "weeks" / f"{season}-{week:02d}.json", doc)
        week_index.append({"season": season, "week": week, "n_games": wk.height, "has_forecasts": bool(rel),
                           "date_range": doc["date_range"]})
    with_fc = [w for w in week_index if w["has_forecasts"]]
    latest = with_fc[-1] if with_fc else week_index[-1]
    prod = yaml.safe_load((ROOT / "configs" / "production.yaml").read_text(encoding="utf-8"))
    _write(WEB_DATA / "manifest.json", {"exported_at": now.isoformat(), "weeks": week_index,
                                        "latest": {"season": latest["season"], "week": latest["week"]},
                                        "production": prod, "release_count": len(releases)})
    _export_performance()
    _export_ratings(now)
    print(f"[export] wrote {WEB_DATA} ({len(week_index)} weeks, {len(releases)} releases)")
    return WEB_DATA


def _export_performance() -> None:
    perf: dict = {"generated_at": utc_now().isoformat()}
    for key, pattern in (("walk_forward", "backtest/bt_*/summary.json"), ("locked", "locked_test/locked_*/summary.json")):
        p = _latest(pattern)
        if p:
            perf[key] = {"run_id": p.parent.name, "summary": json.loads(p.read_text(encoding="utf-8")),
                         "probabilities": json.loads((p.parent / "probabilities.json").read_text(encoding="utf-8")),
                         "manifest": {k: v for k, v in json.loads((p.parent / "manifest.json").read_text(encoding="utf-8")).items()
                                      if k in ("run_id", "generated_at_utc", "code_hash", "folds", "locked_test", "locked_included")}}
    pp = REPORTS_DIR / "prospective" / "summary.json"
    perf["prospective"] = json.loads(pp.read_text(encoding="utf-8")) if pp.exists() else {"n_scored": 0}
    ev = REPORTS_DIR / "prospective" / "evaluations.parquet"
    if ev.exists():
        e = pl.read_parquet(ev)
        perf["prospective_games"] = e.select("game_id", "horizon_type", "run_id", "generated_at", "pred_home", "pred_away",
                                             "pred_margin", "pred_total", "p_home", "home_score", "away_score", "margin",
                                             "total_points", "ae_margin", "ae_total", "ae_margin_market", "winner_correct",
                                             "log_loss").sort("game_id").to_dicts()
    # cumulative absolute margin error by week (retrospective walk-forward + locked)
    series = []
    for pattern in ("backtest/bt_*/predictions.parquet", "locked_test/locked_*/predictions.parquet"):
        p = _latest(pattern)
        if p is None:
            continue
        d = pl.read_parquet(p).filter((pl.col("horizon") == "final") & pl.col("model").is_in(
            ["C_resid_noinj", "A_market_raw", "B_qb", "N_naive_home"]))
        if "locked" in pattern:
            d = d.filter(pl.col("season") == settings()["validation"]["locked_test"])
        series.append(d)
    if series:
        d = pl.concat(series, how="diagonal_relaxed").unique(["game_id", "model"]).with_columns(
            ae=(pl.col("pred_margin") - pl.col("margin")).abs(), aet=(pl.col("pred_total") - pl.col("total_points")).abs())
        wk = d.group_by("season", "week", "model").agg(pl.col("ae").sum(), pl.col("aet").sum(), n=pl.len()).sort("season", "week")
        wk = wk.with_columns(cum_ae=pl.col("ae").cum_sum().over("model"), cum_aet=pl.col("aet").cum_sum().over("model"),
                             cum_n=pl.col("n").cum_sum().over("model")).with_columns(
            cum_margin_mae=pl.col("cum_ae") / pl.col("cum_n"), cum_total_mae=pl.col("cum_aet") / pl.col("cum_n"))
        perf["cumulative"] = wk.select("season", "week", "model", "cum_margin_mae", "cum_total_mae", "cum_n").to_dicts()
    _write(WEB_DATA / "performance.json", perf)
    # retrospective per-game archive for the locked season
    lp = _latest("locked_test/locked_*/predictions.parquet")
    if lp:
        ls = settings()["validation"]["locked_test"]
        d = pl.read_parquet(lp).filter((pl.col("season") == ls) & (pl.col("horizon") == "final")
                                       & pl.col("model").is_in(["C_resid_noinj", "A_market_raw", "B_qb"]))
        pg = pl.read_parquet(lp.parent / "probabilities_per_game.parquet").filter(
            (pl.col("season") == ls) & (pl.col("horizon") == "final")).select("game_id", "model", "p_home")
        d = d.join(pg, on=["game_id", "model"], how="left")
        g = build_games(S.fetch("schedules")).select("game_id", "home_team", "away_team", "gameday")
        wide = (d.select("game_id", "season", "week", "model", "pred_home", "pred_away", "pred_margin", "pred_total", "p_home",
                         "home_score", "away_score").join(g, on="game_id").sort("season", "week", "game_id"))
        _write(WEB_DATA / f"retro_{ls}.json", {"season": ls, "label": "Retrospective walk-forward backtest (not published before games)",
                                              "rows": wide.to_dicts()})


def _export_ratings(now) -> None:
    tg = pl.read_parquet(PROCESSED_DIR / "team_games.parquet")
    qbg = pl.read_parquet(PROCESSED_DIR / "qb_games.parquet")
    b, qbm = AsOfFeatureBuilder(tg), QBModel(qbg)
    now_us = int(now.timestamp() * 1_000_000)
    season = settings()["seasons"]["current"]
    players = S.fetch("players").select("gsis_id", "display_name")
    names = dict(zip(players["gsis_id"].to_list(), players["display_name"].to_list()))
    rows = []
    for team in sorted(set(tg["team"].to_list())):
        f = b.team_features(team, now_us, season)
        qb = qbm.previous_starter(team, now_us)
        rows.append({"team": team, "adj_off_epa": f["adj_off_epa"], "adj_def_epa": f["adj_def_epa"],
                     "adj_off_pts": f["adj_off_pts"], "adj_def_pts": f["adj_def_pts"], "off_epa_play": f["off_epa_play"],
                     "def_epa_play": f["def_epa_play"], "off_pts_drive": f["off_pts_drive"], "def_pts_drive": f["def_pts_drive"],
                     "games_this_season": f["games_this_season"], "ess_games": f["ess_games"],
                     "last_starter": names.get(qb), "last_starter_rating": qbm.rating(qb, now_us, season)[0]})
    _write(WEB_DATA / "ratings.json", {"as_of": now.isoformat(), "season": season, "teams": rows,
                                       "note": "As-of ratings: exponentially weighted, shrunk, opponent-adjusted; see methodology."})
