"""Model v2 trial line (user decisions 2026-10-26; reports/research/v2_*). The frozen v1.0 models are untouched.

The pre-registered v2.0 test failed (margin error worse than v1.0), so by the user's rule v2 is NOT the official line.
The user chose to run v2.1 (v2.0 without the garbage-time filter and travel / body clock; feature set "v2.1",
features/v2.py) as a trial line next to v1.0 from week 8: display and tracking only, never the official pick.
It is a football-only ridge fitted once on all completed final-horizon games from 2016 to the fit time and frozen
(artifacts/v2/<version>/model.joblib, sha256 in configs/model_v2.yaml); probabilities and intervals use its walk-forward
out-of-fold predictions (2019-2025). The `official` switch exists for a future version that passes a pre-registered
test; it is false here. Any failure leaves the trial line out: it never blocks a release.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import polars as pl
import yaml

from nflcast.config import PROCESSED_DIR, ROOT, settings, utc_now

V2_FILE = ROOT / "configs" / "model_v2.yaml"
ART_DIR = ROOT / "artifacts" / "v2"
FEATURE_SET = "v2.1"
SNAPSHOTS = "feature_snapshots_v21.parquet"
_CACHE: dict = {}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def training_frame() -> pl.DataFrame:
    from nflcast.evaluation import backtest as BT
    games = pl.read_parquet(PROCESSED_DIR / "games.parquet")
    hist = BT.assemble(games, pl.read_parquet(PROCESSED_DIR / SNAPSHOTS),
                       pl.read_parquet(PROCESSED_DIR / "market_asof.parquet"))
    return hist.filter((pl.col("horizon") == "final") & (pl.col("season") >= settings()["seasons"]["core_start"]))


def fit(version: str, evaluation: Path, oof: Path, official: bool, official_from: str) -> Path:
    """evaluation: the pre-registered v2.0 report; oof: walk-forward predictions of this feature set (model "B_v2")."""
    import json
    from nflcast.features import personnel as P
    from nflcast.models.core import FootballRidge, feature_set, select_alpha_chronologically
    from nflcast.models.probability import OutcomeModel
    if V2_FILE.exists():
        raise SystemExit(f"Model v2 already recorded ({yaml.safe_load(V2_FILE.read_text())['version']}).")
    train = training_frame()
    fs = feature_set(FEATURE_SET)
    alpha, scores = select_alpha_chronologically(train, feature_set=fs)
    mod = FootballRidge(alpha=alpha, feature_set=fs).fit(train)
    games = pl.read_parquet(PROCESSED_DIR / "games.parquet")
    oof_path = oof
    oof = pl.read_parquet(oof_path).filter(pl.col("model") == "B_v2")
    calib = {"outcome": OutcomeModel().fit(oof, games), "res_margin": (oof["margin"] - oof["pred_margin"]).to_numpy(),
             "res_total": (oof["total_points"] - oof["pred_total"]).to_numpy(), "n_oof": oof.height,
             "oof_seasons": [int(oof["season"].min()), int(oof["season"].max())]}
    season = settings()["seasons"]["current"]
    tg = pl.read_parquet(PROCESSED_DIR / "team_games.parquet")
    inj_s = list(range(season - 5, season))
    p_play = P.Availability(P.injury_player_weeks(inj_s, games), P.snap_shares(inj_s, games), tg).p_play(season)
    d = ART_DIR / version
    d.mkdir(parents=True, exist_ok=True)
    art = d / "model.joblib"
    joblib.dump({"mod": mod, "calib": calib, "alpha": alpha, "p_play": p_play, "season": season}, art, compress=3)
    last = train.sort("season", "week")["game_id"][-1]
    ev = json.loads(evaluation.read_text(encoding="utf-8"))
    rec = {"version": version, "fitted_at_utc": utc_now().isoformat(), "feature_set": FEATURE_SET,
           "artifact": art.relative_to(ROOT).as_posix(), "artifact_sha256": _sha(art), "alpha": alpha,
           "alpha_scores": {str(k): v for k, v in scores.items()},
           "training": {"games": train.height, "first_season": int(train["season"].min()), "last_training_game": last},
           "calibration": {"oof_predictions": oof_path.relative_to(ROOT).as_posix(), "oof_seasons": calib["oof_seasons"],
                           "n": oof.height},
           "p_play_by_status": p_play, "p_play_seasons": inj_s,
           "preregistered_v2_0_test": {"report": evaluation.relative_to(ROOT).as_posix(), "pass": bool(ev["pass"]),
                                       "se_margin_diff_v2_minus_v1": ev["primary_se_margin_diff_v2_minus_v1"]["mean_diff"]},
           "official": bool(official), "official_from": official_from,
           "rules": ("Fitted once; do not refit or retune this season. Trial line: display and tracking only, never the "
                     "official pick (v2.1 was chosen after seeing the v2.0 test; weeks 8-18 of 2026 are its clean test).")}
    V2_FILE.write_text(yaml.safe_dump(rec, sort_keys=False), encoding="utf-8")
    return V2_FILE


def record() -> dict | None:
    return yaml.safe_load(V2_FILE.read_text(encoding="utf-8")) if V2_FILE.exists() else None


def load() -> dict | None:
    """The v2.0 artifact if recorded and its sha256 matches; None otherwise."""
    if "m" in _CACHE:
        return _CACHE["m"]
    m, rec = None, record()
    if rec:
        art = ROOT / rec["artifact"]
        if art.exists() and _sha(art) == rec["artifact_sha256"]:
            m = {**joblib.load(art), "version": rec["version"], "official": bool(rec["official"]),
                 "official_from": datetime.fromisoformat(rec["official_from"])}
    _CACHE["m"] = m
    return m


def is_official_for(kickoff: datetime) -> bool:
    m = load()
    return bool(m and m["official"] and kickoff >= m["official_from"])


def release_frame(feats: pl.DataFrame, upcoming: pl.DataFrame, games_all: pl.DataFrame, inj_now: pl.DataFrame,
                  season: int, week: int, now: datetime, p_play: dict) -> pl.DataFrame:
    """v2.0 feature rows aligned with the release's rows (one per QB scenario): v1.0 QB / schedule / context columns,
    v2.0 team form as of `now`, live injury losses (training rule), travel, live weather, QB experience term."""
    from nflcast.features import v2 as V2
    from nflcast.features import weather as W
    from nflcast.predict import shadow as SH
    tg2 = pl.read_parquet(PROCESSED_DIR / "team_games_v2.parquet")
    b = V2.builder(tg2, V2.METRICS_V21)
    now_us = int(now.timestamp() * 1_000_000)
    form = []
    for g in upcoming.iter_rows(named=True):
        rec = {"game_id": g["game_id"]}
        for side in ("home", "away"):
            tf = b.team_features(g[f"{side}_id"], now_us, season)
            rec.update({f"{side}_{k}": v for k, v in tf.items() if k.startswith(("off_", "def_", "adj_"))})
        form.append(rec)
    form = pl.DataFrame(form)
    trav = V2.travel_features(games_all, V2.venue_coords()).filter(pl.col("game_id").is_in(upcoming["game_id"].to_list()))
    wx = []
    for g in upcoming.iter_rows(named=True):
        s = W.latest_snapshot(season, g["game_id"], now)
        k = (s or {}).get("kickoff_hour")
        if k:
            wx.append({"game_id": g["game_id"], "temp_c": float(k["temperature_2m"]), "wind_kmh": float(k["wind_speed_10m"]),
                       "gust_kmh": float(k["wind_gusts_10m"]), "precip_mm": float(k["precipitation"]),
                       "exposure": float(s["exposure"])})
    wxf = (W.weather_features(pl.DataFrame(wx)).select(["game_id"] + W.WX_FEATURES) if wx
           else pl.DataFrame(schema={"game_id": pl.Utf8, **{c: pl.Float64 for c in W.WX_FEATURES}}))
    L = SH.live_losses(upcoming, inj_now, season, week, p_play)
    lost = [f"lost_{u}" for u in SH.UNITS]
    drop = [c for c in feats.columns if c.startswith(("home_off_", "home_def_", "away_off_", "away_def_", "home_adj_",
                                                       "away_adj_")) and not c.endswith("_off_bye")]
    f = feats.drop(drop).with_row_index("_row").join(form, on="game_id", how="left").join(trav, on="game_id", how="left")
    f = f.join(wxf, on="game_id", how="left").join(upcoming.select("game_id", "div_game"), on="game_id", how="left")
    for side in ("home", "away"):
        part = L.select("game_id", pl.col("team").alias(f"{side}_id"), *[pl.col(c).alias(f"{side}_{c}") for c in lost])
        f = f.join(part, on=["game_id", f"{side}_id"], how="left")
    f = (f.sort("_row").drop("_row")
         .with_columns([pl.col(c).fill_null(0.0) for c in V2.WX] + [pl.col(f"{s}_{c}").fill_null(0.0)
                                                                     for s in ("home", "away") for c in lost]))
    f = V2.add_qb_exp(f)
    if f.height != feats.height or f["game_id"].to_list() != feats["game_id"].to_list():
        raise ValueError("v2 feature rows do not line up with the release rows")
    return f


def release_inputs(feats, upcoming, games_all, inj_now, season, week, now) -> dict | None:
    """v2.0 predictions for the release rows, plus the frame (for the breakdown). None when v2.0 is not recorded."""
    m = load()
    if m is None:
        return None
    f = release_frame(feats, upcoming, games_all, inj_now, season, week, now, m["p_play"])
    preds = m["mod"].predict(f)
    if not all(np.isfinite(preds[k]).all() for k in ("home_pts", "away_pts")):
        raise ValueError("non-finite v2 predictions")
    return {"preds": preds, "calib": m["calib"], "frame": f, "mod": m["mod"], "version": m["version"],
            "official": m["official"], "official_from": m["official_from"]}
