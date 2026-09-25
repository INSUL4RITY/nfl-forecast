"""Regression tests: invalid forecasts are never published as current, displayed, or scored; version states."""

import copy
from datetime import datetime, timedelta, timezone

import polars as pl

from nflcast.predict import export_web, score
from nflcast.predict.operate import decide
from nflcast.predict.publication import verification_label
from nflcast.predict.validation import check_forecast, entry_is_valid, select_frozen

KO = datetime(2026, 9, 27, 17, 0, tzinfo=timezone.utc)


def good_fc(margin=3.0, total=44.0):
    h, a = (total + margin) / 2, (total - margin) / 2
    return {"home_pts": h, "away_pts": a, "margin": margin, "total": total, "p_home": 0.58, "p_away": 0.416, "p_tie": 0.004,
            "intervals": {"margin_80": [margin - 16, margin + 16], "margin_95": [margin - 26, margin + 26],
                          "total_80": [total - 17, total + 17], "total_95": [total - 26, total + 26]}}


def entry(fc=None, status="ok", fp=None):
    return {"game_id": "G1", "game_type": "REG", "kickoff_utc": KO.isoformat(), "status": status, "release_label": "update",
            "forecast": fc if fc is not None else good_fc(), "primary_model": "Combined",
            "input_fingerprint": fp or {k: "x" for k in ("market", "quarterbacks", "injury_report", "team_form", "model")}}


def bad_fc():
    f = good_fc()
    f["home_pts"] = -1.0   # negative expected score
    return f


def test_check_forecast_catches_problems():
    assert check_forecast(good_fc(), False) == []
    assert check_forecast(bad_fc(), False)
    f = good_fc(); f["p_home"] += 0.1
    assert "probabilities do not sum to 1" in check_forecast(f, False)
    assert "playoff tie probability not zero" in check_forecast(good_fc(), True)
    f = good_fc(); f["intervals"]["total_80"] = [60, 30]
    assert any("out of order" in p for p in check_forecast(f, False))


def test_failed_newer_forecast_cannot_replace_valid_older_one():
    older = ((KO - timedelta(hours=30)).isoformat(), entry(good_fc(3.0)))
    newer_bad = ((KO - timedelta(hours=2)).isoformat(), entry(bad_fc(), status="ok"))            # mislabelled, fails checks
    newer_rej = ((KO - timedelta(hours=1)).isoformat(), entry(None, status="rejected_validation_failed"))
    newer_rej[1]["forecast"] = None
    sel = select_frozen([older, newer_bad, newer_rej], KO)
    assert sel is not None and sel[0] == older[0]
    assert not entry_is_valid(newer_bad[1]) and not entry_is_valid(newer_rej[1])


def _rel(gen, e):
    return ({"run_id": f"rel_{gen:%H%M}", "generated_at_utc": gen.isoformat(), "information_cutoff_utc": gen.isoformat()}, e)


def test_export_view_keeps_valid_version_and_labels_states():
    ev = {"files": {}}
    vs = [_rel(KO - timedelta(hours=30), entry(good_fc(3.0))), _rel(KO - timedelta(hours=2), entry(bad_fc()))]
    v = export_web.game_view(vs, KO, False, KO - timedelta(hours=1), ev)
    assert v["forecast_state"] == "latest_pregame" and v["forecast"]["forecast"]["margin"] == 3.0
    assert [h["version_state"] for h in v["history"]] == ["latest_pregame", "rejected_failed_validation"]
    v = export_web.game_view(vs, KO, False, KO + timedelta(hours=1), ev)
    assert v["forecast_state"] == "locked_at_kickoff"
    v = export_web.game_view(vs + [_rel(KO + timedelta(minutes=5), entry(good_fc(9.0)))], KO, True, KO + timedelta(hours=5), ev)
    assert v["forecast_state"] == "scored" and v["forecast"]["forecast"]["margin"] == 3.0
    assert v["history"][-1]["version_state"] == "generated_after_kickoff_not_used"


def test_future_game_never_labelled_scored():
    vs = [_rel(KO - timedelta(hours=30), entry())]
    v = export_web.game_view(vs, KO, False, KO - timedelta(hours=10), {"files": {}})
    assert all("scored" not in h["version_state"] for h in v["history"])


def test_scoring_ignores_invalid_versions():
    rows = [
        {"run_id": "a", "generated_at": KO - timedelta(hours=30), "public_at": None, "game_id": "G1", "kickoff": KO,
         "valid": True, "pred_margin": 3.0},
        {"run_id": "b", "generated_at": KO - timedelta(hours=1), "public_at": None, "game_id": "G1", "kickoff": KO,
         "valid": False, "pred_margin": 99.0},
    ]
    fz = score.frozen_versions(pl.DataFrame(rows).with_columns(pl.col("public_at").cast(pl.Datetime("us", "UTC"))))
    fin = fz.filter(pl.col("horizon_type") == "final_pregame")
    assert fin["run_id"].to_list() == ["a"]


def test_verification_labels():
    gen = KO - timedelta(hours=1)
    assert verification_label(gen, KO, KO - timedelta(minutes=30)) == "publicly_verifiable_pregame"
    assert verification_label(gen, KO, KO + timedelta(minutes=16)) == "generated_pregame_published_after_kickoff"
    assert verification_label(gen, KO, None) == "generated_pregame_not_yet_evidenced_public"
    assert verification_label(KO + timedelta(minutes=1), KO, None) == "generated_after_kickoff"


def _cand(fp):
    e = entry(fp=fp)
    return {"games": [e]}


def test_input_change_triggers_release_and_unchanged_does_not():
    fp = {k: "x" for k in ("market", "quarterbacks", "injury_report", "team_form", "model")}
    now = KO - timedelta(hours=10)
    latest = {"G1": (now - timedelta(hours=2), entry(fp=fp))}
    due, reasons = decide(_cand(copy.deepcopy(fp)), now, latest, now - timedelta(hours=2))
    assert not due
    changed = {**fp, "quarterbacks": "y"}
    due, reasons = decide(_cand(changed), now, latest, now - timedelta(hours=2))
    assert due and any("quarterbacks" in r for r in reasons)
    changed = {**fp, "market": "z"}
    assert decide(_cand(changed), now, latest, now - timedelta(hours=2))[0]


def test_final_window_and_kicked_off_games():
    fp = {k: "x" for k in ("market", "quarterbacks", "injury_report", "team_form", "model")}
    now = KO - timedelta(minutes=40)
    latest = {"G1": (KO - timedelta(hours=5), entry(fp=fp))}
    due, reasons = decide(_cand(fp), now, latest, KO - timedelta(hours=5))
    assert due and any("final-pregame" in r for r in reasons)
    # after kickoff nothing about this game can trigger an update
    due, reasons = decide(_cand({**fp, "market": "changed"}), KO + timedelta(minutes=1), latest, KO - timedelta(minutes=30))
    assert not due
