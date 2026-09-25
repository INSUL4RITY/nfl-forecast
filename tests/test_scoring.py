from datetime import datetime, timedelta, timezone

import polars as pl

from nflcast.predict.score import frozen_versions

KO = datetime(2026, 9, 27, 17, 0, tzinfo=timezone.utc)


def _entries():
    base = {"game_id": "G1", "kickoff": KO, "status": "ok"}
    rows = [
        {**base, "run_id": "r1", "generated_at": KO - timedelta(hours=96), "pred_margin": 1.0},
        {**base, "run_id": "r2", "generated_at": KO - timedelta(hours=75), "pred_margin": 2.0},
        {**base, "run_id": "r3", "generated_at": KO - timedelta(hours=10), "pred_margin": 3.0},
        {**base, "run_id": "r4", "generated_at": KO - timedelta(minutes=50), "pred_margin": 4.0},
        {**base, "run_id": "r5", "generated_at": KO + timedelta(minutes=5), "pred_margin": 99.0},  # after kickoff
    ]
    return pl.DataFrame(rows).with_columns(valid=pl.lit(True), public_at=pl.lit(None, pl.Datetime("us", "UTC")))


def test_one_row_per_game_and_horizon():
    fz = frozen_versions(_entries())
    assert fz.height == 2
    assert sorted(fz["horizon_type"].to_list()) == ["early", "final_pregame"]


def test_final_uses_last_pre_kickoff_version_and_early_respects_72h():
    fz = frozen_versions(_entries())
    fin = fz.filter(pl.col("horizon_type") == "final_pregame").row(0, named=True)
    ear = fz.filter(pl.col("horizon_type") == "early").row(0, named=True)
    assert fin["run_id"] == "r4" and fin["pred_margin"] == 4.0   # never the post-kickoff r5
    assert ear["run_id"] == "r2"                                  # latest version >= 72h before kickoff
