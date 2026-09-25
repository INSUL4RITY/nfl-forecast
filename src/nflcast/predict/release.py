"""Production forecast releases (schema v3).

A release freezes, for every scheduled game of the next NFL week that has not kicked off:
  * the headline forecast: combined market+football model; the football-only model when no market line
    was observed before the cutoff; or the football-only model when the combined forecast FAILS validation
    (status fallback_after_validation_failure). If no model passes validation the entry is kept for audit
    with status rejected_validation_failed and no headline forecast (it is never displayed or scored);
  * football-only and market-only benchmark forecasts;
  * outcome probabilities and 80/95% intervals calibrated on walk-forward out-of-fold predictions;
  * quarterback availability for every relevant QB with evidence, timestamps and historical start rates,
    and a scenario mixture whenever the starter is uncertain (features/qb_availability.py);
  * notable listed injuries (display only; non-QB injuries are not model inputs);
  * an input fingerprint per game (market, quarterbacks, injury report, team form, model) used to decide
    when a new release is needed.
The information cutoff is the generation time; every input snapshot's observation time is recorded.
Publication time is NOT known when the file is written: it is established later from independent
evidence (predict/publication.py). Files are write-once.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import polars as pl
import yaml

from nflcast.config import PROCESSED_DIR, RELEASES_DIR, REPORTS_DIR, ROOT, settings, utc_now, utc_stamp
from nflcast.data import odds_api as OA
from nflcast.data import sources as S
from nflcast.data.games import build_games, franchise, market_asof
from nflcast.evaluation import backtest as BT
from nflcast.features import personnel as P
from nflcast.features import qb_availability as QA
from nflcast.features.asof import AsOfFeatureBuilder
from nflcast.models.combined import ResidualRidge, game_matrix, select_resid_alphas
from nflcast.models.core import FootballRidge, MarketRaw, feature_set, select_alpha_chronologically
from nflcast.models.probability import OutcomeModel
from nflcast.predict import validation as V

SCHEMA_VERSION = 3
LEVELS = (0.8, 0.95)

FEATURE_LABELS = {
    "off_epa_play": "offense EPA/play", "def_epa_play": "defense EPA/play allowed", "off_epa_db": "passing EPA/dropback",
    "def_epa_db": "pass defense EPA/dropback allowed", "off_epa_rush": "rushing EPA/rush", "def_epa_rush": "run defense EPA/rush allowed",
    "off_succ_play": "offense success rate", "def_succ_play": "defense success rate allowed", "off_expl_db": "explosive pass rate",
    "def_expl_db": "explosive passes allowed", "off_expl_rush": "explosive run rate", "def_expl_rush": "explosive runs allowed",
    "off_sack_rate": "sack rate taken", "def_sack_rate": "sack rate generated", "off_int_rate": "interception rate thrown",
    "def_int_rate": "interception rate generated", "off_fum_rate": "fumbles lost rate", "def_fum_rate": "fumbles forced/lost rate",
    "off_neutral_pass": "neutral-situation pass rate", "def_neutral_pass": "opponents' neutral pass rate",
    "off_pts_drive": "points per drive", "def_pts_drive": "points per drive allowed", "off_rz_td": "red-zone TD rate",
    "def_rz_td": "red-zone TD rate allowed", "off_start_fp": "offensive starting field position (yds to goal)",
    "def_start_fp": "opponent starting field position", "off_plays_pg": "offensive plays per game", "def_plays_pg": "opponent plays per game",
    "off_points_pg": "points per game", "def_points_pg": "points allowed per game", "adj_off_epa": "opponent-adjusted offense rating",
    "adj_def_epa": "opponent-adjusted defense rating", "adj_off_pts": "opponent-adjusted scoring rating",
    "adj_def_pts": "opponent-adjusted scoring defense", "qb_rating": "expected QB rating (EPA/dropback)",
    "qb_log_db": "expected QB experience", "qb_delta": "expected QB vs recent baseline", "qb_change": "QB change",
    "off_bye": "coming off bye", "short_week": "short week", "home_field": "home field", "rest_diff": "rest difference",
    "is_playoff": "playoff game", "dome": "dome/closed roof", "market_margin": "market spread", "market_total": "market total",
}
EFF_KEYS = ["off_epa_play", "def_epa_play", "off_epa_db", "def_epa_db", "off_epa_rush", "def_epa_rush",
            "off_succ_play", "def_succ_play", "off_pts_drive", "def_pts_drive", "off_sack_rate", "def_sack_rate",
            "adj_off_epa", "adj_def_epa", "games_this_season", "ess_games"]


def _label(name: str, home: str, away: str) -> str:
    for side, team in (("home_", home), ("away_", away)):
        if name.startswith(side):
            return f"{team} {FEATURE_LABELS.get(name[len(side):], name[len(side):])}"
    return FEATURE_LABELS.get(name, name)


def _hash(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def latest_oof() -> pl.DataFrame:
    """Walk-forward out-of-fold predictions (prefer the locked-test run, which includes the latest season)."""
    cands = sorted((REPORTS_DIR / "locked_test").glob("*/predictions.parquet")) or sorted((REPORTS_DIR / "backtest").glob("*/predictions.parquet"))
    if not cands:
        raise FileNotFoundError("No backtest predictions found; run `python -m nflcast backtest` first")
    return pl.read_parquet(cands[-1]).with_columns(source_run=pl.lit(cands[-1].parent.name))


def _records(games: pl.DataFrame, season: int, now) -> dict[str, str]:
    done = games.filter((pl.col("season") == season) & (pl.col("status") == "final") & (pl.col("game_type") == "REG")
                        & (pl.col("kickoff_utc") < now))
    rec: dict[str, list[int]] = {}
    for r in done.iter_rows(named=True):
        for team, pts, opp in ((r["home_team"], r["home_score"], r["away_score"]), (r["away_team"], r["away_score"], r["home_score"])):
            w = rec.setdefault(team, [0, 0, 0])
            w[0 if pts > opp else 1 if pts < opp else 2] += 1
    return {t: (f"{w[0]}-{w[1]}" + (f"-{w[2]}" if w[2] else "")) for t, w in rec.items()}


def _weighted_quantiles(values: np.ndarray, weights: np.ndarray, qs) -> list[float]:
    o = np.argsort(values)
    v, w = values[o], weights[o]
    cw = np.cumsum(w) / w.sum()
    return [float(np.interp(q, cw, v)) for q in qs]


def ensure_rates(current_season: int) -> dict:
    """Historical QB start rates from seasons before `current_season`, cached on disk.

    Weekly depth charts (2016-2024, no timestamps) give long history; daily depth charts (2025+) match live
    releases better and are used per category when they have >= 30 cases. Two sets are built: as the chart
    stood 72 h before kickoff ("early") and 1 h before kickoff ("final").
    """
    key = f"v3_start_practice_listed_through_{current_season - 1}"
    try:
        r = QA.load_rates()
        if r.get("key") == key:
            return r
    except FileNotFoundError:
        pass
    games = pl.read_parquet(PROCESSED_DIR / "games.parquet")
    qbg = pl.read_parquet(PROCESSED_DIR / "qb_games.parquet")
    weekly_seasons = [s for s in range(2016, current_season) if s <= 2024]
    daily_seasons = [s for s in range(2025, current_season)]
    inj = P.injury_player_weeks(weekly_seasons + daily_seasons, games)
    practice = QA.injury_practice(weekly_seasons + daily_seasons)
    weekly = QA.estimate_start_rates(QA.build_history_team_weeks(games, qbg, QA.weekly_depth_qbs(weekly_seasons), inj, practice),
                                     max(weekly_seasons))
    out = {"key": key}
    for label, lead in (("early", 72), ("final", 1)):
        daily = None
        if daily_seasons:
            dd = QA.daily_depth_qbs(daily_seasons, games, lead)
            if dd.height:
                daily = QA.estimate_start_rates(QA.build_history_team_weeks(games, qbg, dd, inj, practice), max(daily_seasons))
        out[label] = QA.merge_rates(daily, weekly)
    QA.save_rates(out)
    return out


def _team_depth(dc: pl.DataFrame | None, team: str, now: datetime) -> tuple[list[tuple[str, int]], datetime | None]:
    if dc is None or "dt" not in dc.columns:
        return [], None
    s = (dc.filter((franchise(pl.col("team")) == team) & (pl.col("pos_abb") == "QB") & pl.col("gsis_id").is_not_null())
         .with_columns(t=pl.col("dt").str.to_datetime(time_zone="UTC")).filter(pl.col("t") <= now))
    if s.height == 0:
        return [], None
    last = s["t"].max()
    s = s.filter(pl.col("t") == last).sort("pos_rank").unique("gsis_id", keep="first", maintain_order=True)
    return list(zip(s["gsis_id"].to_list(), s["pos_rank"].to_list())), last


def _weather_display(g: dict, now: datetime) -> dict:
    """Latest archived forecast snapshot for kickoff (display only; weather is not a model input)."""
    from nflcast.features import weather as W
    s = W.latest_snapshot(g["season"], g["game_id"], now)
    if not s:
        return {"available": False, "model_input": False, "note": "no forecast snapshot collected before this release"}
    k = s.get("kickoff_hour") or {}
    return {"available": bool(k), "model_input": False, "observed_at_utc": s["observed_at_utc"], "lead_hours": s["lead_hours"],
            "exposure": s["exposure"], "temperature_c": k.get("temperature_2m"), "wind_kmh": k.get("wind_speed_10m"),
            "gust_kmh": k.get("wind_gusts_10m"), "precip_mm": k.get("precipitation"), "source": "Open-Meteo forecast API",
            "note": "Display only: weather did not pass the feature-group evaluation, so it is not used by the model."}


def fit_production(season: int) -> dict:
    """Fit the production models (configs/production.yaml) on all completed final-horizon history available now."""
    cfg = settings()
    prod = yaml.safe_load((ROOT / "configs" / "production.yaml").read_text(encoding="utf-8"))
    games = pl.read_parquet(PROCESSED_DIR / "games.parquet")
    hist = BT.assemble(games, pl.read_parquet(PROCESSED_DIR / "feature_snapshots.parquet"),
                       pl.read_parquet(PROCESSED_DIR / "market_asof.parquet"))
    train = hist.filter((pl.col("horizon") == "final") & (pl.col("season") >= cfg["seasons"]["core_start"]))
    fs_name = prod["primary"]["feature_set"]
    am, at = select_resid_alphas(train.filter(pl.col("market_available")), fs_name)
    cmod = ResidualRidge(fs_name, am, at).fit(train.filter(pl.col("market_available")))
    a_b, _ = select_alpha_chronologically(train, feature_set=feature_set(prod["fallback"]["feature_set"]))
    bmod = FootballRidge(alpha=a_b, feature_set=feature_set(prod["fallback"]["feature_set"])).fit(train)
    oof = latest_oof().filter(pl.col("horizon") == "final")
    oof_models = {"primary": "C_resid_noinj", "fallback": "B_qb", "market": "A_market_raw"}
    calib = {}
    for key, mname in oof_models.items():
        o = oof.filter(pl.col("model") == mname)
        calib[key] = {"outcome": OutcomeModel().fit(o, games), "res_margin": (o["margin"] - o["pred_margin"]).to_numpy(),
                      "res_total": (o["total_points"] - o["pred_total"]).to_numpy(), "n_oof": o.height,
                      "oof_seasons": [int(o["season"].min()), int(o["season"].max())]}
    last_train = train.sort("season", "week")["game_id"][-1]
    return {"cmod": cmod, "bmod": bmod, "calib": calib, "alpha_margin": am, "alpha_total": at, "alpha_fallback": a_b,
            "oof_models": oof_models, "oof_source_run": oof["source_run"][0], "qb_rates": ensure_rates(season),
            "training_games": train.height, "last_training_game": last_train, "production": prod}


_PROD_CACHE: dict = {}


def production_models(season: int) -> dict:
    """Frozen artifact if configs/model_freeze.yaml exists (verified by sha256), else a fresh fit (development only)."""
    if season in _PROD_CACHE:
        return _PROD_CACHE[season]
    from nflcast.predict import freeze
    if freeze.is_frozen():
        M = freeze.load()
    else:
        from nflcast.pipeline import code_hash
        M = fit_production(season)
        M.update({"frozen": False, "model_version": "unfrozen-" + _hash([code_hash(), M["production"], M["oof_source_run"]])})
    _PROD_CACHE[season] = M
    return M


def _market_freshness(market: dict | None, schedule_fresh, now):
    """Freshness row for the market source actually used (The Odds API snapshot, or the nflverse schedule)."""
    if not market or market.get("source") != OA.SOURCE:
        return schedule_fresh
    got = datetime.fromisoformat(market["retrieved_at"])
    age_h = (now - got).total_seconds() / 3600
    state = "fresh" if age_h <= OA.cfg()["odds_api"]["max_age_hours"] else "stale_retrieval"
    return QA.SourceFreshness(OA.SOURCE, state, market["retrieved_at"], market["retrieved_at"],
                              market.get("provider_updated_at"), f"{market.get('n_bookmakers')} US bookmakers; retrieved {age_h:.1f} h before the cutoff")


def _game_freshness(freshness, market_fresh, market, res, now) -> dict:
    """Explicit per-game data freshness: every source's state, the market line's age and the QB-evidence flags."""
    sources = [f.to_json() for f in freshness] + [market_fresh.to_json()]
    line_age_h = None
    if market and market.get("snapshot_at"):
        line_age_h = round((now - datetime.fromisoformat(market["snapshot_at"])).total_seconds() / 3600, 1)
    qb_flags = {side: [f for f in res[side].flags if not f.startswith("chain_qb_unavailable")] for side in res}
    data_problem = ("missing", "stale", "not_available", "exhausted", "no_candidate", "no_available")
    problems = [f"{s['source']}: {s['state']}" for s in sources if s["state"] != "fresh"]
    if market is None:
        problems.append("market line: missing")
    elif line_age_h is not None and line_age_h > 36:
        problems.append(f"market line: {line_age_h:.0f} h old")
    for side, fl in qb_flags.items():
        problems += [f"{side} QB: {f}" for f in fl if any(k in f for k in data_problem)]
    return {"sources": sources, "market_line_age_hours": line_age_h, "qb_flags": qb_flags,
            "problems": problems, "all_fresh": not problems}


def build_candidate(now: datetime | None = None, days_ahead: int = 8) -> dict | None:
    """Compute a complete release for the next week's unplayed games WITHOUT writing it."""
    cfg = settings()
    prod = yaml.safe_load((ROOT / "configs" / "production.yaml").read_text(encoding="utf-8"))
    now = now or utc_now()
    now_us = int(now.timestamp() * 1_000_000)
    sched, sched_meta = S.snapshot_asof("schedules", None, now)
    games_all = build_games(sched if sched is not None else S.fetch("schedules"))
    upcoming = games_all.filter((pl.col("status") == "scheduled") & (pl.col("kickoff_utc") > now)
                                & (pl.col("kickoff_utc") <= now + pl.duration(days=days_ahead)))
    if upcoming.height == 0:
        return None
    first = upcoming.sort("kickoff_utc").row(0, named=True)
    upcoming = upcoming.filter((pl.col("season") == first["season"]) & (pl.col("week") == first["week"]))
    season, week = int(first["season"]), int(first["week"])

    games = pl.read_parquet(PROCESSED_DIR / "games.parquet")
    tg = pl.read_parquet(PROCESSED_DIR / "team_games.parquet")
    qbg = pl.read_parquet(PROCESSED_DIR / "qb_games.parquet")
    builder = AsOfFeatureBuilder(tg)
    qbm = P.QBModel(qbg)
    all_rates = production_models(season)["qb_rates"]
    overrides = QA.load_overrides()
    ros_now, ros_meta = S.snapshot_asof("rosters_weekly", season, now)
    inj_now, inj_meta = S.snapshot_asof("injuries", season, now)
    inj_now = (inj_now.with_columns(team=franchise(pl.col("team"))) if inj_now is not None
               else pl.DataFrame(schema={"team": pl.Utf8, "week": pl.Int32, "gsis_id": pl.Utf8, "report_status": pl.Utf8,
                                         "practice_status": pl.Utf8, "full_name": pl.Utf8, "position": pl.Utf8}))
    inj_confirmed = datetime.fromisoformat(inj_meta["last_confirmed_at_utc"]) if inj_meta else None
    dc_now, dc_meta = S.snapshot_asof("depth_charts", season, now)
    freshness = [QA.assess_freshness("injuries", inj_meta, now), QA.assess_freshness("depth_charts", dc_meta, now),
                 QA.assess_freshness("rosters_weekly", ros_meta, now)]
    market_fresh = QA.assess_freshness("schedules", sched_meta, now)

    def team_roster(team: str) -> dict[str, str] | None:
        """{gsis_id: status} for the team's QBs in the latest roster week <= the game week (None if unavailable)."""
        if ros_now is None:
            return None
        r = ros_now.filter((franchise(pl.col("team")) == team) & (pl.col("position") == "QB") & (pl.col("week") <= week))
        if r.height == 0:
            return None
        r = r.filter(pl.col("week") == r["week"].max())
        return dict(zip(r["gsis_id"].to_list(), r["status"].to_list()))
    players = S.fetch("players").select("gsis_id", "display_name", "position")
    name_of = dict(zip(players["gsis_id"].to_list(), players["display_name"].to_list()))
    hl, carry = float(cfg["features"]["half_life_games"]), float(cfg["features"]["season_carryover"])
    team_db = qbg.group_by("game_id", "team").agg(team_db=pl.col("db").sum())
    qb_share = qbg.join(team_db, on=["game_id", "team"]).with_columns(share=pl.col("db") / pl.col("team_db"))
    done = games.filter(pl.col("status") == "final")

    def last_game(team: str) -> tuple[str | None, datetime | None]:
        d = done.filter(((pl.col("home_id") == team) | (pl.col("away_id") == team)) & (pl.col("kickoff_utc") < now)).sort("kickoff_utc")
        return (d["game_id"][-1], d["kickoff_utc"][-1]) if d.height else (None, None)

    rows, meta = [], {}
    for g in upcoming.iter_rows(named=True):
        tf = {side: builder.team_features(g[f"{side}_id"], now_us, season) for side in ("home", "away")}
        hours_to_ko = (g["kickoff_utc"] - now).total_seconds() / 3600
        rates = all_rates["early" if hours_to_ko >= cfg["horizons"]["early"] else "final"]
        res = {}
        for side in ("home", "away"):
            team = g[f"{side}_id"]
            depth, depth_at = _team_depth(dc_now, team, now)
            prev_gid, prev_ko = last_game(team)
            qb1 = depth[0][0] if depth else qbm.previous_starter(team, now_us)
            sh = qb_share.filter((pl.col("game_id") == prev_gid) & (pl.col("team") == team) & (pl.col("qb_id") == qb1))
            prev_share = float(sh["share"][0]) if sh.height else (0.0 if prev_gid else None)
            res[side] = QA.resolve_team_qbs(
                team=team, season=season, week=week, now=now, depth=depth, depth_at=depth_at,
                injuries=inj_now, injury_observed_at=inj_confirmed, previous_starter=qbm.previous_starter(team, now_us),
                previous_game_kickoff=prev_ko, previous_share=prev_share, rates=rates, overrides=overrides,
                roster=team_roster(team), freshness=freshness)
            if not res[side].scenarios:
                res[side].scenarios = [(1.0, None)]
                res[side].flags.append("no_candidate_qb_prior_used")
        eff = {side: {k: float(tf[side][k]) for k in EFF_KEYS} for side in ("home", "away")}
        for side in ("home", "away"):
            eff[side]["expected_qb_rating"] = float(sum(p * qbm.rating(q, now_us, season)[0] for p, q in res[side].scenarios))
        meta[g["game_id"]] = {"res": res, "efficiency": eff, "tf": tf}
        for ph, qh in res["home"].scenarios:
            for pa, qa in res["away"].scenarios:
                rec = {"game_id": g["game_id"], "scenario_p": ph * pa, "scenario": f"{qh}|{qa}", "horizon": "final", "cutoff_utc": now}
                for side, qb in (("home", qh), ("away", qa)):
                    team = g[f"{side}_id"]
                    rec.update({f"{side}_{k}": v for k, v in tf[side].items()})
                    rating, wdb = qbm.rating(qb, now_us, season)
                    prev = qbm.previous_starter(team, now_us)
                    rec.update({f"{side}_qb_rating": rating, f"{side}_qb_log_db": float(np.log1p(wdb)),
                                f"{side}_qb_delta": rating - qbm.baseline_rating(team, now_us, season, hl, carry),
                                f"{side}_qb_change": float(qb is not None and prev is not None and qb != prev),
                                f"{side}_off_bye": float((g[f"{side}_rest"] or 7) >= 13),
                                f"{side}_short_week": float((g[f"{side}_rest"] or 7) <= 5)})
                rows.append(rec)
    feats = pl.DataFrame(rows).join(upcoming.select(
        "game_id", "season", "week", "home_id", "away_id", "neutral_site", "is_playoff",
        (pl.col("home_rest") - pl.col("away_rest")).alias("rest_diff"),
        pl.col("roof").is_in(["dome", "closed"]).cast(pl.Float64).alias("dome")), on="game_id")
    mk = market_asof(games_all, feats.select("game_id", "horizon", "cutoff_utc").unique(), allow_approx_closing=False)
    feats = feats.join(mk.drop("horizon", "cutoff_utc"), on="game_id", how="left")

    # ---- production models: the FROZEN artifact when a freeze exists, otherwise fitted now
    M = production_models(season)
    cmod, bmod, calib = M["cmod"], M["bmod"], M["calib"]
    am, at, a_b, oof_models = M["alpha_margin"], M["alpha_total"], M["alpha_fallback"], M["oof_models"]
    has_mkt = feats["market_available"].fill_null(False).to_numpy()
    fm = feats.with_columns(home_spread=pl.col("home_spread").fill_null(0.0), total=pl.col("total").fill_null(0.0))
    preds = {"primary": cmod.predict(fm), "fallback": bmod.predict(feats), "market": MarketRaw().predict(fm)}
    Xc, cnames = game_matrix(fm, cmod.fs)
    contrib = (Xc - cmod.gm[0].mean_) / cmod.gm[0].scale_ * cmod.gm[-1].coef_
    from nflcast.pipeline import code_hash
    model_fp = M["model_version"]

    def summarise(key: str, idx: np.ndarray, weights: np.ndarray, playoff: bool) -> dict:
        p, c = preds[key], calib[key]
        w = weights / weights.sum()
        H, A = float((w * p["home_pts"][idx]).sum()), float((w * p["away_pts"][idx]).sum())
        pr = c["outcome"].predict(p["margin"][idx], np.full(len(idx), playoff))
        out = {"home_pts": H, "away_pts": A, "margin": H - A, "total": H + A,
               "p_home": float((w * pr["p_home"]).sum()), "p_away": float((w * pr["p_away"]).sum()),
               "p_tie": float((w * pr["p_tie"]).sum()), "intervals": {}}
        for tgt, resid in (("margin", c["res_margin"]), ("total", c["res_total"])):
            vals = np.concatenate([p[tgt][i] + resid for i in idx])
            wts = np.concatenate([np.full(len(resid), wi / len(resid)) for wi in w])
            for lv in LEVELS:
                lo, hi = _weighted_quantiles(vals, wts, [(1 - lv) / 2, 1 - (1 - lv) / 2])
                out["intervals"][f"{tgt}_{int(lv * 100)}"] = [lo, hi]
        out["scenario_disagreement_margin"] = float(np.sqrt((w * (p["margin"][idx] - (H - A)) ** 2).sum()))
        return out

    records = _records(games_all, season, now)
    fid = feats["game_id"].to_list()
    out_games = []
    for g in upcoming.sort("kickoff_utc").iter_rows(named=True):
        idx = np.array([i for i, x in enumerate(fid) if x == g["game_id"]])
        i0 = int(idx[0])
        w = feats["scenario_p"].to_numpy()[idx]
        mkt_ok = bool(has_mkt[i0])
        hours = (g["kickoff_utc"] - now).total_seconds() / 3600
        label = "early" if hours >= cfg["horizons"]["early"] else ("final" if hours <= cfg["horizons"]["final"] else "update")
        playoff = bool(g["is_playoff"])
        prim = summarise("primary", idx, w, playoff) if mkt_ok else None
        fb = summarise("fallback", idx, w, playoff)
        mo = summarise("market", idx, w, playoff) if mkt_ok else None
        problems = {"combined": V.check_forecast(prim, playoff) if mkt_ok else None, "football_only": V.check_forecast(fb, playoff)}
        if mkt_ok and not problems["combined"]:
            headline, status, model_label = prim, "ok", prod["primary"]["label"]
        elif not problems["football_only"]:
            headline, model_label = fb, prod["fallback"]["label"]
            status = "fallback_after_validation_failure" if mkt_ok else "fallback_football_only_no_market_line"
        else:
            headline, status, model_label = None, "rejected_validation_failed", None
        top = []
        if mkt_ok and status == "ok":
            ci = contrib[idx].T @ (w / w.sum())
            for j in np.argsort(-np.abs(ci))[:5]:
                top.append({"feature": _label(cnames[j], g["home_team"], g["away_team"]), "margin_points": float(ci[j])})
        res = meta[g["game_id"]]["res"]
        lineup = {}
        for side in ("home", "away"):
            j = res[side].to_json(name_of)
            top_qb = res[side].scenarios[0][1]
            j.update({"team": g[f"{side}_team"], "expected_qb_id": top_qb, "expected_qb": name_of.get(top_qb),
                      "uncertain": res[side].uncertain})
            lineup[side] = j
        notable = (inj_now.filter((pl.col("week") == week) & pl.col("team").is_in([g["home_id"], g["away_id"]])
                                  & pl.col("report_status").is_in(["Out", "Doubtful", "Questionable"]))
                   .select("team", "full_name", "position", "report_status").sort("team", "report_status", "full_name").to_dicts())
        pu = feats["provider_updated_at"][i0]
        market = ({"home_spread": float(feats["home_spread"][i0]), "total": float(feats["total"][i0]),
                   "source": feats["market_source"][i0], "timing": feats["market_timing"][i0],
                   "snapshot_at": feats["snapshot_at"][i0].isoformat(),          # our retrieval time
                   "retrieved_at": feats["snapshot_at"][i0].isoformat(),
                   "provider_updated_at": pu.isoformat() if pu is not None else None,
                   "n_bookmakers": feats["n_books"][i0], "fallback_reason": feats["market_fallback_reason"][i0],
                   "feed_version": OA.feed_version()} if mkt_ok else None)
        tfm = meta[g["game_id"]]["tf"]
        fingerprint = {
            "market": _hash([market["home_spread"], market["total"], market["source"]] if market else None),
            "quarterbacks": _hash({s: {"scenarios": [(q, round(p, 3)) for p, q in res[s].scenarios],
                                       "qbs": [(i.qb_id, i.status, i.evidence, round(i.p_available, 3)) for i in res[s].qbs],
                                       "flags": sorted(res[s].flags), "overrides": res[s].overrides_used} for s in res}),
            "injury_report": _hash(notable),
            "team_form": _hash({s: {k: round(float(v), 4) for k, v in tfm[s].items()} for s in tfm}),
            "model": model_fp,
        }
        out_games.append({
            "game_id": g["game_id"], "season": season, "week": week, "game_type": g["game_type"],
            "kickoff_utc": g["kickoff_utc"].isoformat(), "kickoff_time_known": g["kickoff_time_known"],
            "home_team": g["home_team"], "away_team": g["away_team"], "home_record": records.get(g["home_team"], "0-0"),
            "away_record": records.get(g["away_team"], "0-0"), "neutral_site": g["neutral_site"], "stadium": g["stadium"],
            "roof": g["roof"], "release_label": label, "hours_to_kickoff": round(hours, 2), "status": status,
            "validation_problems": {k: v for k, v in problems.items() if v},
            "primary_model": model_label, "market_inputs_used": bool(mkt_ok and status == "ok"),
            "forecast": headline, "combined": prim, "football_only": fb, "market_only": mo, "market": market,
            "lineup": lineup, "lineup_uncertain": bool(res["home"].uncertain or res["away"].uncertain),
            "notable_injuries": notable, "contributions": top, "team_efficiency": meta[g["game_id"]]["efficiency"],
            "scenario_forecasts": [
                {"p": float(w[k]), "home_qb": name_of.get(feats["scenario"][int(i)].split("|")[0]),
                 "away_qb": name_of.get(feats["scenario"][int(i)].split("|")[1]),
                 "combined_margin": float(preds["primary"]["margin"][i]) if mkt_ok else None,
                 "combined_total": float(preds["primary"]["total"][i]) if mkt_ok else None,
                 "football_margin": float(preds["fallback"]["margin"][i]), "football_total": float(preds["fallback"]["total"][i])}
                for k, i in enumerate(idx)],
            "input_fingerprint": fingerprint,
            "data_freshness": _game_freshness(freshness, _market_freshness(market, market_fresh, now), market, res, now),
            "weather": _weather_display(g, now),
        })

    def snap_info(m):
        return None if not m else {k: m.get(k) for k in ("observed_at_utc", "last_confirmed_at_utc", "http_last_modified", "content_sha256")}
    return {
        "schema_version": SCHEMA_VERSION, "run_id": f"rel_{utc_stamp(now)}", "generated_at_utc": now.isoformat(),
        "information_cutoff_utc": now.isoformat(), "season": season, "week": week, "stage": "production_v1.1",
        "input_snapshots": {"schedules": snap_info(sched_meta), "injuries": snap_info(inj_meta), "depth_charts": snap_info(dc_meta)},
        "market_feed": OA.status(now),
        "publication_note": "Publication time is not recorded here. It is established from independent evidence in "
                            "releases/publication_evidence.json (GitHub server timestamps).",
        "models": {"primary": {**prod["primary"], "alpha_margin": am, "alpha_total": at},
                   "fallback": {**prod["fallback"], "alpha": a_b}, "benchmark": prod["benchmark"],
                   "calibration": {k: {"oof_model": oof_models[k], "n_oof": v["n_oof"], "oof_seasons": v["oof_seasons"],
                                       "outcome_params": v["outcome"].params()} for k, v in calib.items()},
                   "oof_source_run": M["oof_source_run"], "qb_start_rates": all_rates["key"],
                   "model_version": M["model_version"], "frozen": M["frozen"],
                   "model_artifact_sha256": M.get("artifact_sha256")},
        "notes": [prod["early_horizon_note"].strip(),
                  "Contributions explain the fitted model's adjustment to the market line; they are not causal claims.",
                  "Probabilities: P(home/away/tie). Intervals: 80%/95% ranges from out-of-fold residuals.",
                  "Non-QB injuries are displayed for context only; they are not model inputs. Weather and coaching are not modelled."],
        "code_hash": code_hash(),
        "games": out_games,
    }


def write_release(release: dict) -> Path:
    d = RELEASES_DIR / str(release["season"]) / f"week_{release['week']:02d}"
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{release['run_id']}.json"
    if path.exists():
        raise FileExistsError(f"{path} exists; releases are immutable")
    path.write_text(json.dumps(release, indent=1, default=str), encoding="utf-8")
    print(f"[release] wrote {path} ({len(release['games'])} games)")
    return path


def generate(now: datetime | None = None, days_ahead: int = 8) -> Path | None:
    rel = build_candidate(now, days_ahead)
    if rel is None:
        print("[release] no upcoming games in window")
        return None
    return write_release(rel)
