"""Production forecast releases (schema v2).

A release freezes, for every scheduled game of the next NFL week that has not kicked off:
  * primary forecast (configs/production.yaml): combined market+football model, or the football-only
    fallback with a visible flag when no market line was observed before the cutoff;
  * football-only and market-only benchmark forecasts;
  * outcome probabilities and 80/95% intervals calibrated on walk-forward out-of-fold predictions;
  * expected starting QBs with their source and injury status; if a starter is Questionable, a
    two-scenario mixture weighted by the historical P(played | Questionable);
  * notable listed injuries (display only; injury features are not in the production model);
  * top model-derived contributions (explanations of the fitted model, not causal claims).
The information cutoff is the generation time. Files are write-once.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import polars as pl
import yaml

from nflcast.config import PROCESSED_DIR, RELEASES_DIR, REPORTS_DIR, ROOT, settings, utc_now, utc_stamp
from nflcast.data import sources as S
from nflcast.data.games import build_games, franchise, market_asof
from nflcast.evaluation import backtest as BT
from nflcast.features import personnel as P
from nflcast.features.asof import AsOfFeatureBuilder
from nflcast.models.combined import ResidualRidge, select_resid_alphas
from nflcast.models.core import FootballRidge, MarketRaw, feature_set, select_alpha_chronologically
from nflcast.models.probability import IntervalModel, OutcomeModel

SCHEMA_VERSION = 2
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


def _label(name: str, home: str, away: str) -> str:
    for side, team in (("home_", home), ("away_", away)):
        if name.startswith(side):
            return f"{team} {FEATURE_LABELS.get(name[len(side):], name[len(side):])}"
    return FEATURE_LABELS.get(name, name)


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


def _live_qbs(team: str, week: int, season: int, now_us: int, inj: pl.DataFrame, qb_q_play: float) -> dict:
    """Expected starter from the latest depth-chart snapshot at or before now + current injury report."""
    dc = S.fetch("depth_charts", season)
    snap = (dc.filter((franchise(pl.col("team")) == team) & (pl.col("pos_abb") == "QB"))
            .with_columns(dt_us=pl.col("dt").str.to_datetime(time_zone="UTC").dt.epoch("us"))
            .filter(pl.col("dt_us") <= now_us))
    if snap.height == 0:
        return {"qb1": None, "qb2": None, "source": "none", "dt": None}
    last = snap["dt_us"].max()
    s = snap.filter(pl.col("dt_us") == last).sort("pos_rank")
    ids = s["gsis_id"].to_list()
    out = {"qb1": ids[0] if ids else None, "qb2": ids[1] if len(ids) > 1 else None, "source": "depth_chart_daily",
           "dt": s["dt"][0]}
    st = inj.filter((pl.col("team") == team) & (pl.col("week") == week) & (pl.col("gsis_id") == out["qb1"]))
    status = st["report_status"][0] if st.height else None
    practice = st["practice_status"][0] if st.height else None
    out.update({"qb1_status": status, "qb1_practice": practice})
    if status in ("Out", "Doubtful") and out["qb2"]:
        out.update({"expected": out["qb2"], "scenarios": [(1.0, out["qb2"])], "note": f"QB1 listed {status}; backup expected"})
    elif (status == "Questionable" or (status is None and practice and "Did Not" in practice)) and out["qb2"]:
        p = qb_q_play
        out.update({"expected": out["qb1"], "scenarios": [(p, out["qb1"]), (1 - p, out["qb2"])],
                    "note": f"QB1 {'Questionable' if status else 'did not practice'}: scenario mixture, P(plays)={p:.2f} (historical rate)"})
    else:
        out.update({"expected": out["qb1"], "scenarios": [(1.0, out["qb1"])], "note": None})
    return out


def _weighted_quantiles(values: np.ndarray, weights: np.ndarray, qs) -> list[float]:
    o = np.argsort(values)
    v, w = values[o], weights[o]
    cw = np.cumsum(w) / w.sum()
    return [float(np.interp(q, cw, v)) for q in qs]


def generate(now=None, days_ahead: int = 8) -> Path | None:
    cfg = settings()
    prod = yaml.safe_load((ROOT / "configs" / "production.yaml").read_text(encoding="utf-8"))
    now = now or utc_now()
    now_us = int(now.timestamp() * 1_000_000)
    games_all = build_games(S.fetch("schedules"))
    upcoming = games_all.filter((pl.col("status") == "scheduled") & (pl.col("kickoff_utc") > now)
                                & (pl.col("kickoff_utc") <= now + pl.duration(days=days_ahead)))
    if upcoming.height == 0:
        print("[release] no upcoming games in window")
        return None
    first = upcoming.sort("kickoff_utc").row(0, named=True)
    upcoming = upcoming.filter((pl.col("season") == first["season"]) & (pl.col("week") == first["week"]))
    season, week = int(first["season"]), int(first["week"])

    games = pl.read_parquet(PROCESSED_DIR / "games.parquet")
    tg = pl.read_parquet(PROCESSED_DIR / "team_games.parquet")
    qbg = pl.read_parquet(PROCESSED_DIR / "qb_games.parquet")
    builder = AsOfFeatureBuilder(tg)
    qbm = P.QBModel(qbg)
    inj_hist = P.injury_player_weeks([s for s in range(2012, season + 1)], games)
    p_q = P.Availability(inj_hist, P.snap_shares(list(range(season - 6, season)), games), tg).p_play(season)
    qb_q_play = float(p_q.get("Questionable", 0.66))
    inj_now = S.fetch("injuries", season).with_columns(team=franchise(pl.col("team")))
    players = S.fetch("players").select("gsis_id", "display_name", "position")
    name_of = dict(zip(players["gsis_id"].to_list(), players["display_name"].to_list()))
    hl, carry = float(cfg["features"]["half_life_games"]), float(cfg["features"]["season_carryover"])

    # ---- feature rows per scenario
    rows, meta = [], {}
    for g in upcoming.iter_rows(named=True):
        tf = {side: builder.team_features(g[f"{side}_id"], now_us, season) for side in ("home", "away")}
        qbs = {side: _live_qbs(g[f"{side}_id"], week, season, now_us, inj_now, qb_q_play) for side in ("home", "away")}
        for side in ("home", "away"):
            if qbs[side].get("expected") is None:  # no depth chart: previous starter
                prev = qbm.previous_starter(g[f"{side}_id"], now_us)
                qbs[side].update({"expected": prev, "scenarios": [(1.0, prev)], "source": "previous_game_starter", "note": None})
        meta[g["game_id"]] = {"qbs": qbs}
        for ph, qh in qbs["home"]["scenarios"]:
            for pa, qa in qbs["away"]["scenarios"]:
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

    # ---- production models on all completed history (final-horizon features)
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
        calib[key] = {"outcome": OutcomeModel().fit(o, games),
                      "res_margin": (o["margin"] - o["pred_margin"]).to_numpy(),
                      "res_total": (o["total_points"] - o["pred_total"]).to_numpy(), "n_oof": o.height,
                      "oof_seasons": [int(o["season"].min()), int(o["season"].max())]}

    has_mkt = feats["market_available"].fill_null(False).to_numpy()
    fm = feats.with_columns(home_spread=pl.col("home_spread").fill_null(0.0), total=pl.col("total").fill_null(0.0))
    preds = {"primary": cmod.predict(fm), "fallback": bmod.predict(feats), "market": MarketRaw().predict(fm)}
    Xc, cnames = __import__("nflcast.models.combined", fromlist=["game_matrix"]).game_matrix(fm, cmod.fs)
    scaler, ridge = cmod.gm[0], cmod.gm[-1]
    contrib = (Xc - scaler.mean_) / scaler.scale_ * ridge.coef_

    def summarise_forecast(key: str, idx: np.ndarray, weights: np.ndarray, playoff: bool, cal_key: str) -> dict:
        p = preds[key]
        w = weights / weights.sum()
        H, A = float((w * p["home_pts"][idx]).sum()), float((w * p["away_pts"][idx]).sum())
        c = calib[cal_key]
        pr = c["outcome"].predict(p["margin"][idx], np.full(len(idx), playoff))
        out = {"home_pts": H, "away_pts": A, "margin": H - A, "total": H + A,
               "p_home": float((w * pr["p_home"]).sum()), "p_away": float((w * pr["p_away"]).sum()),
               "p_tie": float((w * pr["p_tie"]).sum()), "intervals": {}}
        for tgt, res in (("margin", c["res_margin"]), ("total", c["res_total"])):
            vals = np.concatenate([p[tgt][i] + res for i in idx])
            wts = np.concatenate([np.full(len(res), wi / len(res)) for wi in w])
            for lv in LEVELS:
                lo, hi = _weighted_quantiles(vals, wts, [(1 - lv) / 2, 1 - (1 - lv) / 2])
                out["intervals"][f"{tgt}_{int(lv * 100)}"] = [lo, hi]
        out["scenario_disagreement_margin"] = float(np.sqrt((w * (p["margin"][idx] - (H - A)) ** 2).sum()))
        return out

    records = _records(games_all, season, now)
    run_id = f"rel_{utc_stamp(now)}"
    out_games = []
    fid = feats["game_id"].to_list()
    for g in upcoming.sort("kickoff_utc").iter_rows(named=True):
        idx = np.array([i for i, x in enumerate(fid) if x == g["game_id"]])
        w = feats["scenario_p"].to_numpy()[idx]
        mkt_ok = bool(has_mkt[int(idx[0])])
        hours = (g["kickoff_utc"] - now).total_seconds() / 3600
        label = "early" if hours >= cfg["horizons"]["early"] else ("final" if hours <= cfg["horizons"]["final"] else "update")
        prim = summarise_forecast("primary", idx, w, g["is_playoff"], "primary") if mkt_ok else None
        fb = summarise_forecast("fallback", idx, w, g["is_playoff"], "fallback")
        mo = summarise_forecast("market", idx, w, g["is_playoff"], "market") if mkt_ok else None
        headline = prim or fb
        # validity checks before publishing
        checks = [headline["home_pts"] >= 0, headline["away_pts"] >= 0,
                  abs(headline["p_home"] + headline["p_away"] + headline["p_tie"] - 1) < 1e-9,
                  (not g["is_playoff"]) or headline["p_tie"] == 0,
                  all(v[0] <= v[1] for v in headline["intervals"].values()),
                  all(np.isfinite([headline["home_pts"], headline["away_pts"]]))]
        status = ("ok" if mkt_ok else "fallback_football_only_no_market_line") if all(checks) else "pending_validation_failed"
        top = []
        if mkt_ok:
            ci = contrib[idx].T @ (w / w.sum())
            for j in np.argsort(-np.abs(ci))[:5]:
                top.append({"feature": _label(cnames[j], g["home_team"], g["away_team"]), "margin_points": float(ci[j])})
        qbs = meta[g["game_id"]]["qbs"]
        lineup = {}
        for side in ("home", "away"):
            q = qbs[side]
            lineup[side] = {"expected_qb_id": q.get("expected"), "expected_qb": name_of.get(q.get("expected")),
                            "source": q.get("source"), "depth_chart_at": q.get("dt"), "qb1": name_of.get(q.get("qb1")),
                            "qb1_status": q.get("qb1_status"), "qb1_practice": q.get("qb1_practice"), "note": q.get("note"),
                            "scenarios": [{"p": p_, "qb": name_of.get(qid), "qb_id": qid} for p_, qid in q.get("scenarios", [])]}
        notable = (inj_now.filter((pl.col("week") == week) & pl.col("team").is_in([g["home_id"], g["away_id"]])
                                  & pl.col("report_status").is_in(["Out", "Doubtful", "Questionable"]))
                   .select("team", "full_name", "position", "report_status").sort("team", "report_status").to_dicts())
        entry = {
            "game_id": g["game_id"], "season": season, "week": week, "game_type": g["game_type"],
            "kickoff_utc": g["kickoff_utc"].isoformat(), "kickoff_time_known": g["kickoff_time_known"],
            "home_team": g["home_team"], "away_team": g["away_team"], "home_record": records.get(g["home_team"], "0-0"),
            "away_record": records.get(g["away_team"], "0-0"), "neutral_site": g["neutral_site"], "stadium": g["stadium"],
            "roof": g["roof"], "release_label": label, "hours_to_kickoff": round(hours, 2), "status": status,
            "primary_model": prod["primary"]["label"] if mkt_ok else prod["fallback"]["label"],
            "market_inputs_used": mkt_ok,
            "forecast": headline, "combined": prim, "football_only": fb, "market_only": mo,
            "market": ({"home_spread": float(feats["home_spread"][int(idx[0])]), "total": float(feats["total"][int(idx[0])]),
                        "source": feats["market_source"][int(idx[0])], "timing": feats["market_timing"][int(idx[0])],
                        "snapshot_at": feats["snapshot_at"][int(idx[0])].isoformat()} if mkt_ok else None),
            "lineup": lineup, "lineup_uncertain": bool(len(idx) > 1), "notable_injuries": notable,
            "contributions": top,
        }
        out_games.append(entry)
    release = {
        "schema_version": SCHEMA_VERSION, "run_id": run_id, "generated_at_utc": now.isoformat(),
        "information_cutoff_utc": now.isoformat(), "season": season, "week": week, "stage": "production_v1",
        "models": {"primary": {**prod["primary"], "alpha_margin": am, "alpha_total": at},
                   "fallback": {**prod["fallback"], "alpha": a_b}, "benchmark": prod["benchmark"],
                   "calibration": {k: {"oof_model": oof_models[k], "n_oof": v["n_oof"], "oof_seasons": v["oof_seasons"],
                                       "outcome_params": v["outcome"].params()} for k, v in calib.items()},
                   "oof_source_run": oof["source_run"][0]},
        "notes": [prod["early_horizon_note"].strip(),
                  "Contributions explain the fitted model's adjustment to the market line; they are not causal claims.",
                  "Probabilities: P(home/away/tie). Intervals: 80%/95% ranges from out-of-fold residuals."],
        "code_hash": __import__("nflcast.pipeline", fromlist=["code_hash"]).code_hash(),
        "games": out_games,
    }
    d = RELEASES_DIR / str(season) / f"week_{week:02d}"
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{run_id}.json"
    if path.exists():
        raise FileExistsError(f"{path} exists; releases are immutable")
    path.write_text(json.dumps(release, indent=1, default=str), encoding="utf-8")
    print(f"[release] wrote {path} ({len(out_games)} games)")
    return path
