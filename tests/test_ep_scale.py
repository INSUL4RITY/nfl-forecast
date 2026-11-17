"""EP-scale harmonisation of the current season's play-by-play (src/nflcast/data/ep_scale.py, configs/ep_scale.yaml)."""

import numpy as np
import polars as pl
import pytest

from nflcast.data import ep_scale as E
from nflcast.predict import alerts as AL

MAPS = {"pass": [0.001, 1.25], "run": [0.002, 1.2], "kickoff": [0.3, 1.27], "td": [-0.13, 1.16]}
CFG = {"season": 2026, "reference_snapshot": "ref.parquet", "reference_file_sha256": "x", "maps": MAPS,
       "check": {"team_error_sd_max": 0.015, "team_error_mean_max": 0.01}}
TEAMS = ["AAA", "BBB", "CCC", "DDD"]


def _plays(n_per_team: int, game: str, seed: int, start_id: int = 1) -> pl.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    pid = start_id
    for t in TEAMS:
        for i in range(n_per_team):
            pt = "pass" if i % 2 else "run"
            rows.append({"game_id": game, "play_id": float(pid), "posteam": t, "defteam": "ZZZ", "play_type": pt,
                         "desc": f"play {pid}", "down": 1.0, "ydstogo": 10.0, "yardline_100": 75.0,
                         "yards_gained": float(i % 7), "qtr": 1.0, "game_seconds_remaining": 3600.0 - pid,
                         "touchdown": 0.0, "penalty": 0.0, "fumble_lost": 0.0, "interception": 0.0, "sack": 0.0,
                         "two_point_attempt": 0.0, "epa": float(rng.normal(0, 1.2)), "ep": 2.0, "wp": 0.5,
                         "two_point_conversion_prob": 0.4735})
            pid += 1
    df = pl.DataFrame(rows)
    df = df.with_columns(qb_epa=pl.col("epa"), success=(pl.col("epa") > 0).cast(pl.Float64))
    return df


def _revise(old: pl.DataFrame) -> pl.DataFrame:
    """The same plays on the 'revised' scale: exactly invertible with MAPS, ep lower, two-point prob 0.49."""
    a_b = pl.when(pl.col("play_type") == "pass").then(pl.lit(1.25)).otherwise(pl.lit(1.2))
    a_a = pl.when(pl.col("play_type") == "pass").then(pl.lit(0.001)).otherwise(pl.lit(0.002))
    return old.with_columns(epa=(pl.col("epa") - a_a) / a_b, ep=pl.lit(1.6), wp=pl.lit(0.51),
                            two_point_conversion_prob=pl.lit(0.49)).with_columns(
        qb_epa=pl.col("epa"), success=(pl.col("epa") > 0).cast(pl.Float64))


@pytest.fixture()
def setup(monkeypatch):
    ref = _plays(40, "2026_10_AAA_BBB", 1)
    monkeypatch.setattr(E, "config", lambda: CFG)
    monkeypatch.setattr(E, "_reference", lambda name, sha: ref)
    monkeypatch.setattr(E, "_last_status", {})
    return ref


def test_archived_plays_keep_their_old_values_and_new_plays_are_converted(setup):
    ref = setup
    later = _plays(10, "2026_11_CCC_DDD", 2, start_id=1000)
    new = pl.concat([_revise(ref), _revise(later)])
    out = E.harmonise(new, 2026)
    assert out.height == new.height and out.columns == new.columns + ["ep_scale"]
    old_part = out.filter(pl.col("ep_scale") == "old").sort("play_id")
    assert old_part.height == ref.height
    for c in ("epa", "qb_epa", "ep", "wp", "success", "two_point_conversion_prob"):
        assert old_part[c].to_list() == ref.sort("play_id")[c].to_list()          # exact archived values
    conv = out.filter(pl.col("ep_scale") == "converted").sort("play_id")
    assert conv.height == later.height
    np.testing.assert_allclose(conv["epa"].to_numpy(), later.sort("play_id")["epa"].to_numpy(), atol=1e-9)
    assert conv["success"].to_list() == (conv["epa"] > 0).cast(pl.Float64).to_list()
    assert conv["wp"].to_list() == [0.51] * conv.height                       # other valuation columns stay as published
    st = E.status()
    assert st["ok"] and st["plays_old_values"] == ref.height and st["plays_converted"] == later.height
    assert E.converted_games(out) == {"2026_11_CCC_DDD"}


def test_an_edited_play_is_converted_not_pinned(setup):
    ref = setup
    new = _revise(ref).with_columns(yards_gained=pl.when(pl.col("play_id") == 1.0).then(99.0)
                                    .otherwise(pl.col("yards_gained")))
    out = E.harmonise(new, 2026)
    edited = out.filter(pl.col("play_id") == 1.0)
    assert edited["ep_scale"][0] == "converted"
    assert edited["epa"][0] == pytest.approx(ref.filter(pl.col("play_id") == 1.0)["epa"][0])   # exact map in this test


def test_old_scale_frames_and_other_seasons_are_untouched(setup):
    ref = setup
    assert E.harmonise(ref, 2026) is ref                                     # not the revised scale: nothing to do
    rev = _revise(ref)
    assert E.harmonise(rev, 2025) is rev
    assert E.status() == {}


def test_a_further_scale_change_fails_the_check(setup):
    ref = setup
    new = _revise(ref).with_columns(epa=pl.col("epa") * 0.5 + pl.when(pl.col("posteam") == "AAA").then(0.2).otherwise(0.0))
    E.harmonise(new, 2026)
    assert E.status()["ok"] is False


def test_valuation_columns_never_include_the_play_itself():
    cols = E.IDENTITY + ["epa", "qb_epa", "ep", "wp", "wpa", "success", "cpoe", "td_prob", "total_home_epa",
                         "home_wp_post", "xyac_epa", "xpass", "pass_oe", "passer_player_id", "fixed_drive", "week"]
    v = set(E.valuation_columns(cols))
    assert not v & set(E.IDENTITY)
    assert {"epa", "qb_epa", "ep", "wp", "wpa", "success", "cpoe", "td_prob", "total_home_epa", "home_wp_post",
            "xyac_epa", "xpass", "pass_oe"} == v


def test_alert_is_quiet_when_handled_and_raised_when_the_check_fails(setup, monkeypatch, tmp_path):
    ref = setup
    path = tmp_path / "pbp.parquet"
    _revise(ref).write_parquet(path)
    from nflcast.data import sources as S
    monkeypatch.setattr(S, "latest_snapshot", lambda name, season=None: path)
    assert AL.ep_scale_items(2026) == []
    _revise(ref).with_columns(epa=pl.col("epa") * 0.5 + pl.when(pl.col("posteam") == "AAA").then(0.2)
                              .otherwise(0.0)).write_parquet(path)
    items = AL.ep_scale_items(2026)
    assert len(items) == 1 and "conversion check failed" in items[0]["text"]


def test_frozen_config_matches_the_archived_snapshots():
    """The reference snapshot is the one recorded, and the frozen maps are what the recorded fit produces."""
    from nflcast.config import RAW_DIR
    cfg = E.config()
    d = RAW_DIR / "pbp" / str(cfg["season"])
    ref_p, fit_p = d / cfg["reference_snapshot"], d / cfg["fit_snapshot"]
    if not (ref_p.exists() and fit_p.exists()):
        pytest.skip("archived play-by-play snapshots not present")
    assert E.file_sha256(ref_p) == cfg["reference_file_sha256"]
    assert E.file_sha256(fit_p) == cfg["fit_file_sha256"]
    maps, n = E.fit_maps(pl.read_parquet(ref_p), pl.read_parquet(fit_p))
    assert n == 25773
    for g, (a, b) in cfg["maps"].items():
        assert maps[g] == pytest.approx([a, b], abs=1e-6)
