"""Team analytics audit, phases A and B: EP scale, QB team labels, win-rate staleness, sharing tags, glossary, document shell."""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parents[1] / "scripts" / "team_analytics"
sys.path.insert(0, str(HERE))
import ep_harmonise as EH  # noqa: E402

MAPS = {"pass": [0.001, 1.25], "run": [0.002, 1.2], "kickoff": [0.3, 1.27], "td": [-0.13, 1.16]}
CFG = {"season": 2026, "reference_snapshot": "ref.parquet", "reference_file_sha256": "x", "maps": MAPS,
       "check": {"team_error_sd_max": 0.015, "team_error_mean_max": 0.01}}
TEAMS = ["AAA", "BBB", "CCC", "DDD"]


def _plays(n_per_team, game, seed, start_id=1):
    rng = np.random.default_rng(seed)
    rows, pid = [], start_id
    for t in TEAMS:
        for i in range(n_per_team):
            rows.append({"game_id": game, "play_id": float(pid), "posteam": t, "defteam": "ZZZ", "play_type": "pass" if i % 2 else "run",
                         "desc": f"play {pid}", "down": 1.0, "ydstogo": 10.0, "yardline_100": 75.0, "yards_gained": float(i % 7), "qtr": 1.0,
                         "game_seconds_remaining": 3600.0 - pid, "touchdown": 0.0, "penalty": 0.0, "fumble_lost": 0.0, "interception": 0.0,
                         "sack": 0.0, "two_point_attempt": 0.0, "epa": float(rng.normal(0, 1.2)), "ep": 2.0, "wp": 0.5,
                         "two_point_conversion_prob": 0.4735})
            pid += 1
    df = pd.DataFrame(rows)
    df["qb_epa"] = df.epa
    df["success"] = (df.epa > 0).astype(float)
    return df


def _revise(old):
    """The same plays on the 'revised' scale: exactly invertible with MAPS, ep lower, two-point probability 0.49."""
    b = np.where(old.play_type == "pass", 1.25, 1.2)
    a = np.where(old.play_type == "pass", 0.001, 0.002)
    new = old.copy()
    new["epa"] = (old.epa - a) / b
    new["qb_epa"] = new.epa
    new["success"] = (new.epa > 0).astype(float)
    new["ep"], new["wp"], new["two_point_conversion_prob"] = 1.6, 0.51, 0.49
    return new


@pytest.fixture()
def ref(monkeypatch):
    r = _plays(40, "2026_10_AAA_BBB", 1)
    monkeypatch.setattr(EH, "config", lambda: CFG)
    monkeypatch.setattr(EH, "_reference", lambda: r)
    return r


def test_archived_plays_keep_old_values_and_later_plays_are_converted(ref):
    later = _plays(10, "2026_11_CCC_DDD", 2, start_id=1000)
    new = pd.concat([_revise(ref), _revise(later)], ignore_index=True)
    out = EH.harmonise(new, 2026)
    assert len(out) == len(new) and list(out.columns) == list(new.columns) + ["ep_scale"]
    old = out[out.ep_scale == "old"].sort_values("play_id")
    assert len(old) == len(ref)
    assert np.allclose(old.epa.values, ref.epa.values) and np.allclose(old.ep.values, 2.0)      # archived valuation restored
    conv = out[out.ep_scale == "converted"].sort_values("play_id")
    assert np.allclose(conv.epa.values, later.epa.values)                                       # the frozen line inverts the revision
    assert (conv.success == (conv.epa > 0).astype(float)).all()
    assert EH.STATUS["ok"] and EH.STATUS["plays_converted"] == len(later) and abs(EH.STATUS["check_team_error_sd"]) < 1e-9
    assert "keep their archived original values" in EH.qc_line(EH.STATUS)


def test_edited_play_is_converted_not_restored(ref):
    new = _revise(ref)
    new.loc[0, "yards_gained"] = 99.0                                                           # nflverse edited this play
    out = EH.harmonise(new, 2026)
    row = out[out.play_id == new.loc[0, "play_id"]].iloc[0]
    assert row.ep_scale == "converted" and row.ep == 1.6


def test_old_scale_and_other_seasons_are_untouched(ref):
    assert EH.harmonise(ref, 2026) is ref                                                       # already on the original scale
    rev = _revise(ref)
    assert EH.harmonise(rev, 2025) is rev


def test_vendored_config_matches_main_shape():
    cfg = EH.config()
    assert cfg["season"] == 2026 and set(cfg["maps"]) >= {"pass", "run", "kickoff", "td"}
    assert len(cfg["reference_file_sha256"]) == 64


# ---- A6: quarterbacks who changed team
def test_team_label_lists_every_team_in_order():
    import compute as cp
    g = pd.DataFrame({"posteam": ["LV"] * 9 + ["MIN"], "week": list(range(1, 10)) + [10], "play_id": range(10),
                      "game_id": [f"g{w}" for w in range(1, 11)]})
    assert cp.team_label(g) == "LV 9 g, MIN 1 g (now)"
    assert cp.team_label(g[g.posteam == "LV"]) == "LV"


# ---- A7: win rates within one week of the report are used
def test_win_rates_one_week_behind_pass_two_weeks_fail():
    import build_html as bh
    WR = {"through_week": 9, "teams": {t: {**{k: 50 for k in bh.WR_KEYS}, **{f"{k}_rank": 1 for k in bh.WR_KEYS}} for t in TEAMS}}
    assert bh.validate_win_rates(WR, TEAMS, 10) == []
    WR["through_week"] = 8
    assert any("more than one week behind" in p for p in bh.validate_win_rates(WR, TEAMS, 10))


# ---- A8: sharing tags
def test_head_tags_with_and_without_image():
    import og_card
    meta = {"season": 2026, "through_week": 10}
    with_img = og_card.head_tags(meta, True)
    assert 'property="og:image"' in with_img and "summary_large_image" in with_img and og_card.PUBLIC_URL + "og.png" in with_img
    no_img = og_card.head_tags(meta, False)
    assert "og:image" not in no_img and 'content="summary"' in no_img
    T = pd.DataFrame({"rating_pg": [5.0, -3.0, 9.0]}, index=["AAA", "BBB", "CCC"])
    card = og_card.card_html(T, meta)
    assert card.index("CCC") < card.index("AAA") < card.index("BBB")


# ---- B1: glossary
def test_glossary_names_every_variant():
    import glossary
    page = glossary.render()
    assert page.startswith("<!DOCTYPE html>") and 'lang="en-GB"' in page
    for term in ("raw", "opponent-adjusted", "weighted and shrunk", "Luck index (points and EPA)", "Team ratings", "qb_dropback"):
        assert term in page


# ---- A1/A3: document shell and accessibility hooks in the template
def test_template_is_a_full_document_with_accessibility_hooks():
    t = (HERE / "template.html").read_text(encoding="utf-8")
    assert t.lstrip().startswith("<!DOCTYPE html>") and '<html lang="en-GB">' in t and "<body>" in t and t.rstrip().endswith("</html>")
    labels = re.findall(r'<nav class="subnav" aria-label="([^"]+)"', t)
    assert len(labels) == len(set(labels)) >= 6
    assert 'role="img" aria-label="${esc(NAME[p.t])}' in t
    assert 'w.setAttribute("tabindex", "0"); w.setAttribute("role", "region")' in t
    assert "rkSpan" in t and ", rank " in t
    assert "<th></th>" not in t


# ---- A10: the caution quotes the pre-game cost
def test_line_caution_uses_pregame_definition():
    import build_html as bh
    if not bh.LINE_BT:
        pytest.skip("pre-game backtest output missing")
    assert "pre-game" in bh.LINE_BT["definition"]
    A = pd.DataFrame([{"team": "OFF", "player": "Left Tackle", "group": "OL", "status_class": "listed Out/Doubtful", "share": 0.98,
                       "term": "new", "out_since_week": 10}])
    c = bh.line_caution("OFF", "DEF", A, pd.DataFrame({"def_pressure_rate": [0.2, 0.3]}, index=["OFF", "DEF"]))
    assert "known to be out before kickoff" in c and f"{bh.LINE_BT['epa']['per_missing_starter']:+.3f}" in c
    assert "pre-game figure is about" in bh.line_method()


# ---- traded quarterbacks: the sample behind their rates is their whole 2026 season
def test_own_db_uses_the_whole_season_sample():
    import build_html as bh
    q = {"dropbacks": 38, "dropbacks_season": 391, "season_teams": "LV/MIN"}
    assert bh.own_db(q) == 391 and bh.with_teams(q) == " with LV and MIN"
    assert bh.own_db({"dropbacks": 120}) == 120 and bh.with_teams({"season_teams": "MIN"}) == ""



# ---- touchdown opportunities and box-score links (week 12 additions)
def test_td_rate_by_distance():
    import usage
    if usage.TDX is None:
        pytest.skip("td_expectation.json missing")
    yl = pd.Series([1, 4, 8, 15, 30, 70])
    r_t, r_c = usage.td_rate("target", yl), usage.td_rate("carry", yl)
    assert list(r_t) == sorted(r_t, reverse=True) and list(r_c) == sorted(r_c, reverse=True)   # closer = likelier
    assert r_c.iloc[0] > 0.4 and r_t.iloc[-1] < 0.02


def test_td_expectation_file_records_its_test():
    import json
    d = json.loads((HERE / "td_expectation.json").read_text(encoding="utf-8"))
    t = d["test"]
    assert t["players"] > 500 and 0 <= t["gap_kept"] < 1
    assert t["mae_expected_td_pg"] < t["mae_actual_td_pg"]            # the reason the table leads with expected touchdowns


def test_box_score_links():
    import build_html as bh
    G = pd.DataFrame({"team": ["AAA", "AAA", "BBB"], "week": [9, 10, 10], "game_id": ["2026_09_AAA_CCC", "2026_10_DDD_AAA", "2026_10_BBB_EEE"]})
    games = [{"id": "2026_11_AAA_BBB", "away": "AAA", "home": "BBB"}]
    bh.add_box_scores(games, G)
    assert games[0]["box"]["game"] == "https://rbsdm.com/box_scores/#2026_11_AAA_BBB"
    assert games[0]["box"]["last"] == {"AAA": "https://rbsdm.com/box_scores/#2026_10_DDD_AAA", "BBB": "https://rbsdm.com/box_scores/#2026_10_BBB_EEE"}
