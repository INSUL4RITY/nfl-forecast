"""End-to-end pipeline steps. Run everything with: python -m nflcast all"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import polars as pl
import yaml

from nflcast import __version__
from nflcast.config import PROCESSED_DIR, RAW_DIR, RELEASES_DIR, REPORTS_DIR, ROOT, settings, utc_now, utc_stamp
from nflcast.data import sources as S
from nflcast.data.games import build_games, market_asof
from nflcast.evaluation import backtest as BT
from nflcast.evaluation import prob_eval as PE
from nflcast.features.asof import AsOfFeatureBuilder, build_feature_snapshots
from nflcast.features import personnel as P
from nflcast.features.team_games import attach_game_info, team_game_stats
from nflcast.models.core import FootballRidge, MarketCalibrated, MarketRaw, select_alpha_chronologically


def code_hash() -> str:
    h = hashlib.sha256()
    for p in sorted((ROOT / "src").rglob("*.py")):
        h.update(p.read_bytes())
    h.update((ROOT / "configs" / "settings.yaml").read_bytes())
    return h.hexdigest()


def data_manifest() -> list[dict]:
    """The latest raw snapshot used for each source/season, with its content hash."""
    out = []
    for meta in sorted(RAW_DIR.rglob("*.json")):
        out.append(meta)
    latest: dict[str, Path] = {}
    for m in out:
        latest[str(m.parent)] = m  # sorted => last is newest
    res = []
    for m in latest.values():
        j = json.loads(m.read_text(encoding="utf-8"))
        res.append({k: j.get(k) for k in ("source", "season", "observed_at_utc", "http_last_modified", "content_sha256", "rows")})
    return res


def _seasons() -> tuple[list[int], list[int]]:
    s = settings()["seasons"]
    all_s = list(range(s["warmup_start"], s["current"] + 1))
    feat_s = list(range(s["core_start"], s["current"] + 1))
    return all_s, feat_s


# ---------------------------------------------------------------- ingest
def ingest() -> None:
    cur = settings()["seasons"]["current"]
    all_s, _ = _seasons()
    print("[ingest] schedules (refresh)")
    S.fetch("schedules", refresh=True)
    for s in all_s:
        refresh = s == cur
        print(f"[ingest] pbp {s}{' (refresh)' if refresh else ''}")
        S.fetch("pbp", s, refresh=refresh)
    for src in ("injuries", "depth_charts", "rosters_weekly"):
        print(f"[ingest] {src} {cur} (refresh, archived for prospective as-of use)")
        S.fetch(src, cur, refresh=True)


# ---------------------------------------------------------------- build
PBP_COLS = ["game_id", "play_id", "posteam", "defteam", "play_type", "qb_dropback", "qb_spike", "qb_kneel", "rush",
            "score_differential", "qtr", "epa", "yards_gained", "sack", "interception", "fumble_lost", "cpoe",
            "passer_player_id", "passer_id", "fixed_drive", "fixed_drive_result", "yardline_100"]


def personnel_objects(games: pl.DataFrame, tg: pl.DataFrame, qbg: pl.DataFrame):
    all_s, _ = _seasons()
    inj_s = [s for s in all_s if s >= 2012]
    qbm = P.QBModel(qbg)
    dcs = P.DepthCharts(P.depth_chart_qb1([s for s in all_s if s >= settings()["seasons"]["core_start"]]))
    avail = P.Availability(P.injury_player_weeks(inj_s, games), P.snap_shares(inj_s, games), tg)
    return qbm, dcs, avail


def build() -> None:
    all_s, feat_s = _seasons()
    games = build_games()
    games.write_parquet(PROCESSED_DIR / "games.parquet")
    print(f"[build] games: {games.height} rows")
    pbp = pl.concat([S.fetch("pbp", s).select(PBP_COLS) for s in all_s], how="diagonal_relaxed")
    tg = attach_game_info(team_game_stats(pbp), games)
    tg.write_parquet(PROCESSED_DIR / "team_games.parquet")
    qbg = P.qb_games(pbp, games)
    qbg.write_parquet(PROCESSED_DIR / "qb_games.parquet")
    print(f"[build] team-games: {tg.height} rows from {pbp.height} plays; qb-games {qbg.height}")
    feats = build_feature_snapshots(games, tg, feat_s)
    qbm, dcs, avail = personnel_objects(games, tg, qbg)
    feats = P.add_personnel_features(feats, games, qbm, dcs, avail)
    feats.write_parquet(PROCESSED_DIR / "feature_snapshots.parquet")
    print(f"[build] feature snapshots: {feats.height} rows x {len(feats.columns)} cols")
    cuts = feats.select("game_id", "horizon", "cutoff_utc")
    mk = market_asof(games, cuts, allow_approx_closing=True)
    mk.write_parquet(PROCESSED_DIR / "market_asof.parquet")
    print(f"[build] market rows with lines: {mk['market_available'].sum()} / {mk.height}")


# ---------------------------------------------------------------- backtest
def backtest(include_locked: bool = False) -> Path:
    cfg = settings()
    v = cfg["validation"]
    games = pl.read_parquet(PROCESSED_DIR / "games.parquet")
    feats = pl.read_parquet(PROCESSED_DIR / "feature_snapshots.parquet")
    market = pl.read_parquet(PROCESSED_DIR / "market_asof.parquet")
    data = BT.assemble(games, feats, market)
    locked = [v["locked_test"]] if include_locked else []
    folds = list(v["tune_folds"]) + list(v["dev_folds"]) + locked
    preds, fold_info = BT.run(data, folds, list(cfg["horizons"].keys()))
    summary = BT.summarise(preds, v["bootstrap_reps"], v["seed"], tune_folds=list(v["tune_folds"]), locked_folds=locked)
    run_id = f"{'locked' if include_locked else 'bt'}_{utc_stamp()}"
    manifest = {"run_id": run_id, "generated_at_utc": utc_now().isoformat(), "package_version": __version__,
                "code_hash": code_hash(), "folds": folds, "locked_test": v["locked_test"], "locked_included": include_locked,
                "settings": cfg, "production": yaml.safe_load((ROOT / "configs" / "production.yaml").read_text(encoding="utf-8")),
                "data": data_manifest()}
    out = REPORTS_DIR / ("locked_test" if include_locked else "backtest") / run_id
    out.mkdir(parents=True, exist_ok=True)
    preds.write_parquet(out / "predictions.parquet")
    (out / "summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str), encoding="utf-8")
    (out / "fold_info.json").write_text(json.dumps(fold_info, indent=1, default=str), encoding="utf-8")
    prob = PE.evaluate(preds, games, list(v["tune_folds"]), tuple(v["interval_levels"]), v["bootstrap_reps"], v["seed"],
                       locked_folds=locked)
    prob.pop("per_game_frame").write_parquet(out / "probabilities_per_game.parquet")
    (out / "probabilities.json").write_text(json.dumps(prob, indent=1, default=str), encoding="utf-8")
    md = BT.to_markdown(summary, fold_info, manifest) + "\n" + PE.to_markdown(prob)
    (out / "report.md").write_text(md, encoding="utf-8")
    (out.parent / "LATEST.md").write_text(md, encoding="utf-8")
    print(f"[backtest] wrote {out}")
    return out


# ---------------------------------------------------------------- predict
def predict(horizon: str = "final", days_ahead: int = 8) -> Path | None:
    """Produce an immutable release for scheduled games kicking off within `days_ahead` days.

    The information cutoff is the generation time (now). The release is labelled by hours-to-kickoff;
    a forecast generated after a horizon's cutoff is never labelled as that horizon.
    """
    cfg = settings()
    now = utc_now()
    games = build_games(S.fetch("schedules"))
    upcoming = games.filter((pl.col("status") == "scheduled") & (pl.col("kickoff_utc") > now)
                            & (pl.col("kickoff_utc") <= now + pl.duration(days=days_ahead)))
    if upcoming.height == 0:
        print("[predict] no upcoming games in window")
        return None
    # One release covers one (season, week): the earliest week with unplayed games.
    first = upcoming.sort("kickoff_utc").row(0, named=True)
    upcoming = upcoming.filter((pl.col("season") == first["season"]) & (pl.col("week") == first["week"]))
    tg = pl.read_parquet(PROCESSED_DIR / "team_games.parquet")
    b = AsOfFeatureBuilder(tg)
    now_us = int(now.timestamp() * 1_000_000)
    recs = []
    for r in upcoming.iter_rows(named=True):
        hf = b.team_features(r["home_id"], now_us, r["season"])
        af = b.team_features(r["away_id"], now_us, r["season"])
        rec = {"game_id": r["game_id"], "horizon": "live", "cutoff_utc": now}
        rec.update({f"home_{k}": v for k, v in hf.items()})
        rec.update({f"away_{k}": v for k, v in af.items()})
        recs.append(rec)
    feats = upcoming.select("game_id", "season", "week", "home_id", "away_id", "neutral_site", "is_playoff", "div_game",
                            (pl.col("home_rest") - pl.col("away_rest")).alias("rest_diff")).join(
        pl.DataFrame(recs), on="game_id")
    cuts = feats.select("game_id", pl.lit("final").alias("horizon"), pl.lit(now).alias("cutoff_utc"))
    mk = market_asof(games, cuts, allow_approx_closing=False).drop("horizon", "cutoff_utc")
    feats = feats.join(mk, on="game_id", how="left")

    # Fit production models on all completed games at the matching historical horizon.
    hist = BT.assemble(pl.read_parquet(PROCESSED_DIR / "games.parquet"),
                       pl.read_parquet(PROCESSED_DIR / "feature_snapshots.parquet"),
                       pl.read_parquet(PROCESSED_DIR / "market_asof.parquet"))
    train = hist.filter((pl.col("horizon") == horizon) & (pl.col("season") >= cfg["seasons"]["core_start"]))
    alpha, _ = select_alpha_chronologically(train)
    mb = FootballRidge(alpha=alpha).fit(train)
    pb = mb.predict(feats)
    cal = MarketCalibrated().fit(train.filter(pl.col("market_available")))
    has_mkt = feats["market_available"].fill_null(False).to_numpy()
    fm = feats.with_columns(home_spread=pl.col("home_spread").fill_null(0.0), total=pl.col("total").fill_null(0.0))
    pa, pc = MarketRaw().predict(fm), cal.predict(fm)

    run_id = f"rel_{utc_stamp(now)}"
    out_games = []
    for i, r in enumerate(feats.iter_rows(named=True)):
        g = upcoming.filter(pl.col("game_id") == r["game_id"]).row(0, named=True)
        hours_to_kick = (g["kickoff_utc"] - now).total_seconds() / 3600
        label = "early" if hours_to_kick >= cfg["horizons"]["early"] else ("final" if hours_to_kick <= cfg["horizons"]["final"] else "update")
        entry = {
            "game_id": r["game_id"], "season": g["season"], "week": g["week"], "game_type": g["game_type"],
            "kickoff_utc": g["kickoff_utc"].isoformat(), "kickoff_time_known": g["kickoff_time_known"],
            "home_team": g["home_team"], "away_team": g["away_team"], "neutral_site": g["neutral_site"],
            "stadium": g["stadium"], "roof": g["roof"],
            "release_label": label, "hours_to_kickoff": round(hours_to_kick, 2),
            "football_only": {"home_pts": float(pb["home_pts"][i]), "away_pts": float(pb["away_pts"][i]),
                              "margin": float(pb["margin"][i]), "total": float(pb["total"][i])},
            "market": None, "market_raw": None, "market_calibrated": None,
            "status": "ok" if has_mkt[i] else "fallback_football_only_no_market_line",
            "history_games_home": r["home_games_hist"], "history_games_away": r["away_games_hist"],
        }
        if has_mkt[i]:
            entry["market"] = {"home_spread": r["home_spread"], "total": r["total"], "source": r["market_source"],
                               "snapshot_at": r["snapshot_at"].isoformat() if r["snapshot_at"] else None,
                               "timing": r["market_timing"]}
            entry["market_raw"] = {k: float(pa[k][i]) for k in ("home_pts", "away_pts", "margin", "total")}
            entry["market_calibrated"] = {k: float(pc[k][i]) for k in ("home_pts", "away_pts", "margin", "total")}
        out_games.append(entry)
    release = {
        "run_id": run_id, "generated_at_utc": now.isoformat(), "information_cutoff_utc": now.isoformat(),
        "stage": "milestone_2_baseline", "models": {"football_only": f"FootballRidge(alpha={alpha}) core_v1",
                                                    "market_calibrated": cal.params()},
        "training_horizon": horizon, "code_hash": code_hash(), "data": data_manifest(),
        "notes": ["Baseline release: point forecasts only; probabilities/intervals arrive in Milestone 5.",
                  "Combined market+football model not yet selected (Milestone 4)."],
        "games": out_games,
    }
    season, week = int(upcoming["season"].min()), int(upcoming["week"].min())
    d = RELEASES_DIR / str(season) / f"week_{week:02d}"
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{run_id}.json"
    if path.exists():
        raise FileExistsError(f"Release {path} already exists; releases are immutable")
    path.write_text(json.dumps(release, indent=1, default=str), encoding="utf-8")
    print(f"[predict] wrote {path} ({len(out_games)} games)")
    return path
