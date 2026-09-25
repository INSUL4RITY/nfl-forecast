"""Regression tests for quarterback availability (issue: missing reports treated as healthy; QB2 promoted unchecked)."""

from datetime import datetime, timedelta, timezone

import polars as pl
import pytest

from nflcast.features import qb_availability as QA

NOW = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)
QB1, QB2, QB3, PREV = "00-QB1", "00-QB2", "00-QB3", "00-PREV"

RATES = {
    "through_season": 2024,
    "by_status": {"NotListed": {"p": 0.933}, "None": {"p": 0.931}, "Questionable": {"p": 0.579},
                  "Doubtful": {"p": 0.03}, "Out": {"p": 0.006}},
    "no_report": {"all": {"p": 0.884}, "finished_prev": {"p": 0.95}, "did_not_finish_prev": {"p": 0.444}},
    "backup_by_status": {"NotListed": {"p": 0.71, "k": 352, "n": 495}, "None": {"p": 0.81, "k": 41, "n": 50},
                         "Questionable": {"p": 0.53, "k": 7, "n": 13}, "Out": {"p": 0.14, "k": 0, "n": 5}},
}
P_PLAY = {"None": 0.93, "Questionable": 0.66, "Doubtful": 0.02, "Out": 0.0}
DEPTH = [(QB1, 1), (QB2, 2), (QB3, 3)]


def injuries(rows):
    base = {"team": "CHI", "week": 3, "full_name": "x", "position": "QB", "practice_status": None}
    other = {**base, "gsis_id": "00-WR", "position": "WR", "report_status": "Questionable"}  # proves the report exists
    return pl.DataFrame([{**base, **r} for r in rows] + [other],
                        schema={"team": pl.Utf8, "week": pl.Int32, "full_name": pl.Utf8, "position": pl.Utf8,
                                "practice_status": pl.Utf8, "gsis_id": pl.Utf8, "report_status": pl.Utf8})


def no_overrides():
    return QA.load_overrides(path=QA.OVERRIDE_FILE.with_name("__none__.csv"))


ROSTER = {QB1: "ACT", QB2: "ACT", QB3: "ACT"}


def resolve(inj=None, depth=DEPTH, depth_at=NOW - timedelta(hours=6), inj_obs=NOW - timedelta(hours=1),
            prev_ko=NOW - timedelta(days=6), prev_share=1.0, overrides=None, roster=ROSTER, freshness=None, rates=None):
    return QA.resolve_team_qbs(team="CHI", season=2026, week=3, now=NOW, depth=depth, depth_at=depth_at,
                               injuries=inj if inj is not None else injuries([]), injury_observed_at=inj_obs,
                               previous_starter=QB1, previous_game_kickoff=prev_ko, previous_share=prev_share,
                               rates=rates or RATES, overrides=overrides if overrides is not None else no_overrides(),
                               roster=roster, freshness=freshness)


def probs(res):
    return {q: p for p, q in res.scenarios}


def test_qb1_and_qb2_both_out_promotes_qb3():
    res = resolve(injuries([{"gsis_id": QB1, "report_status": "Out"}, {"gsis_id": QB2, "report_status": "Out"}]))
    p = probs(res)
    assert QB1 not in p and QB2 not in p
    assert p[QB3] == pytest.approx(1.0)


def test_qb2_availability_is_checked_when_qb1_out():
    res = resolve(injuries([{"gsis_id": QB1, "report_status": "Out"}, {"gsis_id": QB2, "report_status": "Questionable"}]))
    p = probs(res)
    assert QB1 not in p
    assert p[QB2] == pytest.approx(0.53, abs=1e-6)          # historical backup rate, not 100%
    assert p[QB3] == pytest.approx(0.47, abs=1e-6)
    assert res.uncertain


def test_missing_report_is_not_confirmed_availability():
    inj = injuries([]).filter(pl.col("team") == "NONE")    # no rows for the team this week
    res = resolve(inj)
    assert "report_not_available" in res.flags
    assert probs(res)[QB1] < 1.0
    assert probs(res)[QB1] == pytest.approx(0.95)          # finished previous game -> historical 0.95
    assert res.uncertain
    assert res.qbs[0].status == "Unknown"


def test_missing_report_after_early_exit_uses_lower_rate():
    inj = injuries([]).filter(pl.col("team") == "NONE")
    res = resolve(inj, prev_share=0.3)
    assert "qb1_did_not_finish_previous_game" in res.flags
    assert probs(res)[QB1] == pytest.approx(0.444)
    assert len(res.scenarios) >= 2


def test_stale_injury_snapshot_flagged():
    res = resolve(inj_obs=NOW - timedelta(days=3))
    assert "report_stale" in res.flags
    assert res.qbs[0].status == "Unknown"


def test_not_listed_on_published_report_uses_evidence_rate():
    res = resolve(injuries([]))
    assert res.flags == []
    assert res.qbs[0].evidence == "not_on_published_report"
    assert res.qbs[0].p_available == pytest.approx(0.933)


def test_stale_depth_chart_flagged_and_previous_starter_leads():
    res = resolve(injuries([]), depth=[(QB2, 1), (QB1, 2)], depth_at=NOW - timedelta(days=8))
    assert "depth_chart_stale" in res.flags
    assert res.qbs[0].qb_id == QB1                          # previous actual starter, not the stale chart's QB1


def test_depth_chart_older_than_last_game_is_stale():
    res = resolve(injuries([]), depth_at=NOW - timedelta(days=3), prev_ko=NOW - timedelta(days=2))
    assert "depth_chart_stale" in res.flags


def test_missing_depth_chart_flagged():
    res = resolve(injuries([]), depth=[], depth_at=None)
    assert "depth_chart_missing" in res.flags and res.qbs[0].qb_id == QB1


HEADER = "team,season,week,qb_gsis_id,status,p_start,source,source_published_at_utc,entered_at_utc,expires_at_utc,note\n"


def _override_file(tmp_path, published, expires="2026-09-28T00:00:00Z"):
    f = tmp_path / "ov.csv"
    f.write_text(HEADER + f"CHI,2026,3,{QB1},out,,https://example.org/report,{published},2026-09-27T10:00:00Z,{expires},test\n",
                 encoding="utf-8")
    return QA.load_overrides(f)


def test_override_applies_only_after_its_publication(tmp_path):
    before = resolve(injuries([]), overrides=_override_file(tmp_path, "2026-09-27T11:00:00Z"))
    assert QB1 not in probs(before) and before.overrides_used
    after = resolve(injuries([]), overrides=_override_file(tmp_path, "2026-09-27T13:00:00Z"))   # published after cutoff
    assert QB1 in probs(after) and not after.overrides_used


def test_override_without_source_rejected(tmp_path):
    f = tmp_path / "ov.csv"
    f.write_text(HEADER + f"CHI,2026,3,{QB1},out,,,2026-09-27T11:00:00Z,2026-09-27T11:05:00Z,2026-09-28T00:00:00Z,\n", encoding="utf-8")
    with pytest.raises(ValueError):
        QA.load_overrides(f)


def test_override_without_expiry_rejected(tmp_path):
    f = tmp_path / "ov.csv"
    f.write_text(HEADER + f"CHI,2026,3,{QB1},out,,https://example.org,2026-09-27T11:00:00Z,2026-09-27T11:05:00Z,,\n", encoding="utf-8")
    with pytest.raises(ValueError):
        QA.load_overrides(f)


def test_expired_override_ignored_and_flagged(tmp_path):
    ov = _override_file(tmp_path, "2026-09-26T11:00:00Z", expires="2026-09-27T06:00:00Z")   # expired before NOW
    res = resolve(injuries([]), overrides=ov)
    assert QB1 in probs(res) and not res.overrides_used and "override_expired" in res.flags


# ---- roster validation across the replacement chain
def test_qb1_on_reserve_skipped_and_qb2_checked():
    res = resolve(injuries([{"gsis_id": QB2, "report_status": "Questionable"}]), roster={QB1: "RES", QB2: "ACT", QB3: "ACT"})
    p = probs(res)
    assert QB1 not in p and res.qbs[0].status == "roster:RES"
    assert p[QB2] == pytest.approx(0.53)                      # QB2's own (Questionable) availability, not assumed


def test_qb1_reserve_and_qb2_released_promotes_qb3():
    res = resolve(injuries([]), roster={QB1: "RES", QB2: "CUT", QB3: "ACT"})
    p = probs(res)
    assert QB1 not in p and QB2 not in p and p[QB3] == pytest.approx(1.0)


def test_qb_missing_from_current_roster_is_not_available():
    res = resolve(injuries([]), roster={QB2: "ACT", QB3: "ACT"})   # QB1 no longer on the team's roster
    assert QB1 not in probs(res)


def test_declared_inactive_cannot_start():
    res = resolve(injuries([]), roster={QB1: "INA", QB2: "ACT", QB3: "ACT"})
    assert QB1 not in probs(res)


def test_chain_exhaustion_flagged():
    res = resolve(injuries([{"gsis_id": q, "report_status": "Questionable"} for q in (QB1, QB2, QB3)]))
    assert "replacement_chain_exhausted" in res.flags and res.chain_residual > 0.02
    assert sum(p for p, _ in res.scenarios) == pytest.approx(1.0)


def test_missing_roster_flagged_not_used():
    res = resolve(injuries([]), roster=None)
    assert "roster_missing" in res.flags and QB1 in probs(res)


def test_midweek_listing_without_designation_is_pending_not_final_rate():
    # Wednesday: QB1 did not practise, no team member has a game designation yet
    inj = injuries([{"gsis_id": QB1, "report_status": None, "practice_status": "Did Not Participate In Practice"}])
    inj = inj.with_columns(pl.lit(None, pl.Utf8).alias("report_status"))
    res = resolve(inj)
    info = res.qbs[0]
    assert info.status == "Pending" and "designation not yet published" in info.detail
    # pooled over listed final statuses (None/Questionable/Doubtful/Out in RATES), not the final DNP-specific cell
    assert 0.0 < info.p_available < 0.93 and "designation_pending" in res.flags


# ---- freshness
def test_assess_freshness_states():
    meta = {"observed_at_utc": (NOW - timedelta(hours=2)).isoformat(), "last_confirmed_at_utc": (NOW - timedelta(hours=1)).isoformat(),
            "http_last_modified": "Sat, 26 Sep 2026 12:00:00 GMT"}
    assert QA.assess_freshness("injuries", meta, NOW).state == "fresh"
    old_provider = {**meta, "http_last_modified": "Wed, 23 Sep 2026 12:00:00 GMT"}
    assert QA.assess_freshness("injuries", old_provider, NOW).state == "stale_provider"
    old_check = {**meta, "last_confirmed_at_utc": (NOW - timedelta(days=3)).isoformat()}
    assert QA.assess_freshness("injuries", old_check, NOW).state == "stale_retrieval"
    assert QA.assess_freshness("injuries", None, NOW).state == "missing"


def test_stale_provider_injury_file_is_not_a_published_report():
    stale = QA.SourceFreshness("injuries", "stale_provider", None, None, None)
    res = resolve(injuries([]), freshness=[stale])
    assert "report_stale" in res.flags and res.qbs[0].status == "Unknown"


def test_stale_provider_depth_chart_flagged():
    stale = QA.SourceFreshness("depth_charts", "stale_provider", None, None, None)
    res = resolve(injuries([]), freshness=[stale])
    assert "depth_chart_stale" in res.flags


def test_practice_specific_rate_used_for_questionable_qb1():
    rates = {**RATES, "by_status_practice": {"Questionable|Full": {"p": 0.87, "k": 36, "n": 41, "lo": 0.78, "hi": 0.94},
                                             "Questionable|DNP": {"p": 0.39, "k": 8, "n": 21, "lo": 0.23, "hi": 0.56}}}
    full = resolve(injuries([{"gsis_id": QB1, "report_status": "Questionable", "practice_status": "Full Participation in Practice"}]),
                   rates=rates)
    dnp = resolve(injuries([{"gsis_id": QB1, "report_status": "Questionable", "practice_status": "Did Not Participate In Practice"}]),
                  rates=rates)
    assert probs(full)[QB1] == pytest.approx(0.87) and probs(dnp)[QB1] == pytest.approx(0.39)
    assert "90% interval" in full.qbs[0].detail


def test_scenarios_sum_to_one_and_leader_never_inflated():
    for inj in (injuries([]), injuries([{"gsis_id": QB1, "report_status": "Questionable"}]),
                injuries([]).filter(pl.col("team") == "NONE")):
        res = resolve(inj)
        assert sum(p for p, _ in res.scenarios) == pytest.approx(1.0)
        assert probs(res)[QB1] == pytest.approx(res.qbs[0].p_available)   # small backups folded into backups, not QB1
        assert len(res.scenarios) <= 1 + 3
