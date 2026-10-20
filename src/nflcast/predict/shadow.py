"""Shadow injury-adjusted model line (display and tracking only; user decision 2026-10-20).

The frozen v1.0 model and the official model pick are untouched. This adds ONE extra forecast per game: the stats-only
(football-only) ridge with the non-QB injury features of the pre-season evaluation (feature set "core_qb_inj"; backtest
name B_qb_inj: expected lost snap share by unit from the injury report). It is fitted once on exactly the frozen model's
training games and frozen itself (artifacts/shadow/<version>/shadow.joblib, sha256 in configs/shadow_injury.yaml).
Its probabilities and intervals use B_qb_inj's walk-forward out-of-fold predictions, as the frozen model does for B_qb.

Live injury inputs follow the training rule: the current week's injury report (game status; rows without a status yet
count as "None"), P(miss | status) from the five seasons before the current one (stored with the artifact), and each
listed player's mean snap share over his team's previous 6 games. Training used the FINAL weekly report, so the shadow
line is only like-for-like once the final report is out (it is published before every 24-hour pick lock).
Any failure leaves the shadow forecast out: it never blocks a release.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import joblib
import numpy as np
import polars as pl
import yaml

from nflcast.config import PROCESSED_DIR, ROOT, settings, utc_now

SHADOW_FILE = ROOT / "configs" / "shadow_injury.yaml"
ART_DIR = ROOT / "artifacts" / "shadow"
FEATURE_SET = "core_qb_inj"
OOF_MODEL = "B_qb_inj"
UNITS = ("ol", "skill", "front", "db")
_CACHE: dict = {}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def training_frame() -> pl.DataFrame:
    """Exactly the frozen model's training games: completed final-horizon games from core_start through the frozen
    artifact's last training game (configs/model_freeze.yaml)."""
    from nflcast.evaluation import backtest as BT
    from nflcast.predict import freeze
    rec = freeze.record()
    games = pl.read_parquet(PROCESSED_DIR / "games.parquet")
    hist = BT.assemble(games, pl.read_parquet(PROCESSED_DIR / "feature_snapshots.parquet"),
                       pl.read_parquet(PROCESSED_DIR / "market_asof.parquet"))
    ko = games.select("game_id", "kickoff_utc")
    last_ko = ko.filter(pl.col("game_id") == rec["training"]["last_training_game"])["kickoff_utc"][0]
    train = hist.join(ko, on="game_id").filter(
        (pl.col("horizon") == "final") & (pl.col("season") >= settings()["seasons"]["core_start"])
        & (pl.col("kickoff_utc") <= last_ko))
    if train.height != rec["training"]["games"]:
        raise RuntimeError(f"training games {train.height} != frozen {rec['training']['games']}")
    return train


def fit(version: str) -> Path:
    """One-off: fit, save and record the shadow artifact. Refuses to overwrite an existing record."""
    from nflcast.features import personnel as P
    from nflcast.models.core import FootballRidge, feature_set, select_alpha_chronologically
    from nflcast.models.probability import OutcomeModel
    from nflcast.predict.release import latest_oof
    if SHADOW_FILE.exists():
        raise SystemExit(f"Shadow model already recorded ({yaml.safe_load(SHADOW_FILE.read_text())['version']}).")
    train = training_frame()
    fs = feature_set(FEATURE_SET)
    alpha, scores = select_alpha_chronologically(train, feature_set=fs)
    mod = FootballRidge(alpha=alpha, feature_set=fs).fit(train)
    games = pl.read_parquet(PROCESSED_DIR / "games.parquet")
    oof = latest_oof().filter((pl.col("horizon") == "final") & (pl.col("model") == OOF_MODEL))
    calib = {"outcome": OutcomeModel().fit(oof, games), "res_margin": (oof["margin"] - oof["pred_margin"]).to_numpy(),
             "res_total": (oof["total_points"] - oof["pred_total"]).to_numpy(), "n_oof": oof.height,
             "oof_seasons": [int(oof["season"].min()), int(oof["season"].max())]}
    season = settings()["seasons"]["current"]
    tg = pl.read_parquet(PROCESSED_DIR / "team_games.parquet")
    inj_s = list(range(season - 5, season))
    avail = P.Availability(P.injury_player_weeks(inj_s, games), P.snap_shares(inj_s, games), tg)
    p_play = avail.p_play(season)
    d = ART_DIR / version
    d.mkdir(parents=True, exist_ok=True)
    art = d / "shadow.joblib"
    joblib.dump({"mod": mod, "calib": calib, "alpha": alpha, "p_play": p_play, "season": season,
                 "oof_source_run": oof["source_run"][0]}, art, compress=3)
    rec = {"version": version, "fitted_at_utc": utc_now().isoformat(), "purpose": "display and tracking only",
           "artifact": art.relative_to(ROOT).as_posix(), "artifact_sha256": _sha(art), "feature_set": FEATURE_SET,
           "alpha": alpha, "alpha_scores": {str(k): v for k, v in scores.items()},
           "training": {"games": train.height, "same_as": "configs/model_freeze.yaml training games"},
           "calibration": {"oof_model": OOF_MODEL, "oof_source_run": oof["source_run"][0], "n": oof.height},
           "p_play_by_status": p_play, "p_play_seasons": inj_s,
           "rules": "Fitted once; do not refit or retune this season. Never used for the official pick."}
    SHADOW_FILE.write_text(yaml.safe_dump(rec, sort_keys=False), encoding="utf-8")
    return SHADOW_FILE


def load() -> dict | None:
    """The shadow artifact if recorded and its sha256 matches; None otherwise."""
    if "m" in _CACHE:
        return _CACHE["m"]
    m = None
    if SHADOW_FILE.exists():
        rec = yaml.safe_load(SHADOW_FILE.read_text(encoding="utf-8"))
        art = ROOT / rec["artifact"]
        if art.exists() and _sha(art) == rec["artifact_sha256"]:
            m = {**joblib.load(art), "version": rec["version"]}
    _CACHE["m"] = m
    return m


def live_losses(upcoming: pl.DataFrame, inj_now: pl.DataFrame, season: int, week: int, p_play: dict) -> pl.DataFrame:
    """Rows per (game_id, team): lost_<unit> for the upcoming games, by the training rule (personnel.Availability)."""
    from nflcast.data import sources as S
    from nflcast.features import personnel as P
    games = pl.read_parquet(PROCESSED_DIR / "games.parquet")
    idmap = S.fetch("players").select("gsis_id", pl.col("pfr_id").alias("pfr_player_id")).drop_nulls().unique("gsis_id")
    sides = pl.concat([upcoming.select("game_id", pl.col("home_id").alias("team"), "kickoff_utc"),
                       upcoming.select("game_id", pl.col("away_id").alias("team"), "kickoff_utc")])
    rep = (inj_now.filter(pl.col("week") == week)
           .select("team", "gsis_id", "position", P._status_key(pl.col("report_status")).alias("status"))
           .unique(["team", "gsis_id"], keep="last")
           .join(idmap, on="gsis_id", how="left")
           .with_columns(unit=pl.col("position").replace_strict(P.UNIT_OF_POSITION, default=None),
                         season=pl.lit(season, dtype=pl.Int32))
           .join(sides.select("game_id", "team"), on="team", how="inner"))
    snaps = P.snap_shares([season - 1, season], games)
    tg = pl.read_parquet(PROCESSED_DIR / "team_games.parquet").select("game_id", "team", "kickoff_utc")
    tg = pl.concat([tg.filter(~pl.col("game_id").is_in(sides["game_id"].to_list())), sides], how="vertical_relaxed")
    avail = P.Availability(rep, snaps, tg)
    avail._p_cache[season] = p_play
    return avail.unit_losses(sides["game_id"].unique().to_list(), [season])


def release_inputs(feats: pl.DataFrame, upcoming: pl.DataFrame, inj_now: pl.DataFrame, season: int, week: int) -> dict | None:
    """Shadow predictions for the release's feature rows (one row per QB scenario), the calibration to summarise them,
    and the injury inputs per game and side. None when no shadow artifact is recorded."""
    m = load()
    if m is None:
        return None
    L = live_losses(upcoming, inj_now, season, week, m["p_play"])
    cols = [f"lost_{u}" for u in UNITS]
    f = feats.with_row_index("_row")
    for side in ("home", "away"):
        part = L.select("game_id", pl.col("team").alias(f"{side}_id"), *[pl.col(c).alias(f"{side}_{c}") for c in cols])
        f = f.join(part, on=["game_id", f"{side}_id"], how="left")
    f = (f.sort("_row").drop("_row")       # same row order as `feats`: the release maps predictions by position
         .with_columns([pl.col(f"{s}_{c}").fill_null(0.0) for s in ("home", "away") for c in cols]))
    if f.height != feats.height or f["game_id"].to_list() != feats["game_id"].to_list():
        raise ValueError("shadow feature rows do not line up with the release rows")
    inputs = {}
    for r in f.unique("game_id").iter_rows(named=True):
        inputs[r["game_id"]] = {s: {c: round(float(r[f"{s}_{c}"]), 4) for c in cols} for s in ("home", "away")}
    preds = m["mod"].predict(f)
    if not all(np.isfinite(preds[k]).all() for k in ("home_pts", "away_pts")):
        raise ValueError("non-finite shadow predictions")
    return {"preds": preds, "calib": m["calib"], "inputs": inputs, "version": m["version"]}
