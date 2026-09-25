"""The Odds API feed: prices discarded, team matching and home-spread signs, line selection, budget/due rules.
No network: synthetic responses in the documented v4 /odds format."""

import json
from datetime import datetime, timedelta, timezone

import polars as pl

from nflcast.data import odds_api as OA
from nflcast.data.policy import banned_columns

UTC = timezone.utc
KO = datetime(2026, 10, 2, 0, 15, tzinfo=UTC)          # Thursday-night kickoff
NOW = KO - timedelta(hours=40)


def _book(key, home, away, home_pt, total, upd=KO - timedelta(hours=41)):
    t = upd.isoformat().replace("+00:00", "Z")
    return {"key": key, "title": key, "last_update": t, "markets": [
        {"key": "spreads", "last_update": t, "outcomes": [
            {"name": home, "price": -110, "point": home_pt}, {"name": away, "price": -110, "point": -home_pt}]},
        {"key": "totals", "last_update": t, "outcomes": [
            {"name": "Over", "price": -105, "point": total}, {"name": "Under", "price": -115, "point": total}]}]}


def _event(home="Cleveland Browns", away="Pittsburgh Steelers", books=None):
    return {"id": "ev1", "sport_key": "americanfootball_nfl", "commence_time": KO.isoformat().replace("+00:00", "Z"),
            "home_team": home, "away_team": away,
            "bookmakers": books if books is not None else [_book("dk", home, away, 2.5, 38.5), _book("fd", home, away, 3.0, 39.0),
                                                           _book("mgm", home, away, 3.0, 38.5)]}


def test_all_32_teams_mapped_to_distinct_abbreviations():
    assert len(OA.TEAM_ABBR) == 32 and len(set(OA.TEAM_ABBR.values())) == 32


def test_sanitize_discards_every_price():
    snap = OA.sanitize([_event()], NOW)
    text = json.dumps(snap)
    assert '"price"' not in text and "-110" not in text and "-105" not in text and "-115" not in text
    keys = {k for ev in snap["events"] for b in ev["books"] for k in b}
    assert not banned_columns(sorted(keys))


def test_home_spread_sign_and_median_rule():
    ev = OA.sanitize([_event()], NOW)["events"][0]
    c = OA.consensus(ev, "CLE", KO, 2)
    # CLE home +2.5/+3/+3 -> home underdog: project convention home_spread > 0 means the AWAY team is favoured
    assert c["home_spread"] == 3.0 and c["total"] == 38.5 and c["n_books"] == 3 and not c["teams_reversed_in_api"]


def test_teams_listed_the_other_way_round_flip_the_sign():
    ev = OA.sanitize([_event(home="Pittsburgh Steelers", away="Cleveland Browns",
                             books=[_book("dk", "Pittsburgh Steelers", "Cleveland Browns", -3.0, 38.5),
                                    _book("fd", "Pittsburgh Steelers", "Cleveland Browns", -3.0, 38.5)])], NOW)["events"][0]
    c = OA.consensus(ev, "CLE", KO, 2)          # nflverse home is CLE
    assert c["home_spread"] == 3.0 and c["teams_reversed_in_api"]


def test_post_kickoff_and_inconsistent_books_excluded():
    books = [_book("dk", "Cleveland Browns", "Pittsburgh Steelers", 3.0, 38.5),
             _book("live", "Cleveland Browns", "Pittsburgh Steelers", -7.0, 30.5, upd=KO + timedelta(minutes=5))]
    bad = _book("bad", "Cleveland Browns", "Pittsburgh Steelers", 3.0, 38.5)
    bad["markets"][0]["outcomes"][1]["point"] = 2.5          # spread points not opposite
    ev = OA.sanitize([_event(books=books + [bad])], NOW)["events"][0]
    assert OA.consensus(ev, "CLE", KO, 2) is None             # only one valid pre-kickoff book remains
    assert OA.consensus(ev, "CLE", KO, 1)["home_spread"] == 3.0


def test_market_rows_match_nflverse_game_and_skip_post_kickoff_snapshots(tmp_path, monkeypatch):
    monkeypatch.setattr(OA, "DIR", tmp_path)
    (tmp_path / "2026").mkdir()
    for when in (NOW, KO + timedelta(minutes=1)):
        (tmp_path / "2026" / f"odds_{when:%Y%m%dT%H%M%SZ}.json").write_text(json.dumps(OA.sanitize([_event()], when)))
    games = pl.DataFrame({"game_id": ["2026_04_PIT_CLE"], "home_id": ["CLE"], "away_id": ["PIT"], "kickoff_utc": [KO]})
    rows = OA.market_rows(games)
    assert rows.height == 1 and rows["game_id"][0] == "2026_04_PIT_CLE" and rows["home_spread"][0] == 3.0
    assert rows["snapshot_at"][0] < KO and rows["provider_updated_at"][0] < KO


def test_line_available_only_from_later_of_receipt_and_provider_update(tmp_path, monkeypatch):
    monkeypatch.setattr(OA, "DIR", tmp_path)
    (tmp_path / "2026").mkdir()
    upd = NOW + timedelta(seconds=1)                          # provider time just after the recorded retrieval
    books = [_book(k, "Cleveland Browns", "Pittsburgh Steelers", 3.0, 38.5, upd=upd) for k in ("dk", "fd")]
    (tmp_path / "2026" / "odds_x.json").write_text(json.dumps(OA.sanitize([_event(books=books)], NOW)))
    games = pl.DataFrame({"game_id": ["g"], "home_id": ["CLE"], "away_id": ["PIT"], "kickoff_utc": [KO]})
    assert OA.market_rows(games)["snapshot_at"][0] == upd


def test_cross_check_rejects_sign_flips_and_absurd_totals():
    assert OA.cross_check_ok(3.0, 38.5, 2.5, 39.0)
    assert OA.cross_check_ok(-1.0, 44.0, 1.5, 44.0)           # near pick'em: sign change allowed
    assert not OA.cross_check_ok(-6.5, 44.0, 6.5, 44.0)       # sign error
    assert not OA.cross_check_ok(3.0, 55.0, 3.0, 40.0)
    assert OA.cross_check_ok(3.0, 40.0, None, None)


def _state(last_ok, rem=400, ok=True, at=None):
    at = at or last_ok
    return {"last_success_utc": last_ok.isoformat() if last_ok else None,
            "requests": [{"at_utc": at.isoformat(), "ok": ok, "cost": 2, "requests_remaining": rem}]}


def test_due_rules(monkeypatch):
    monkeypatch.setenv("ODDS_API_KEY", "x" * 32)
    t = datetime(2026, 9, 27, 12, 0, tzinfo=UTC)
    assert OA.due(t, None, {"requests": []}) == (True, "routine refresh")
    assert OA.due(t, None, _state(t - timedelta(hours=2)))[0] is False                 # cached
    assert OA.due(t, None, _state(t - timedelta(days=3)))[1] == "routine refresh"      # after downtime: once, no replay
    assert OA.due(t, t + timedelta(minutes=80), _state(t - timedelta(hours=1)))[1] == "pregame refresh"
    assert OA.due(t, t + timedelta(minutes=80), _state(t - timedelta(minutes=20)))[0] is False
    assert "budget" in OA.due(t, t + timedelta(minutes=80), _state(t - timedelta(hours=1), rem=30))[1]
    assert "quota low" in OA.due(t, None, _state(t - timedelta(days=1), rem=5))[1]
    assert OA.due(t, None, _state(t - timedelta(days=1), ok=False, at=t - timedelta(minutes=10)))[1] == "waiting after a failed request"
    monkeypatch.setenv("ODDS_API_KEY", "")
    assert OA.due(t, None, {"requests": []})[0] is False


def test_routine_budget_fits_free_allowance():
    c = OA.cfg()["odds_api"]
    per_month = 31 * 24 / c["routine_interval_hours"] * c["cost_per_request"]
    assert per_month + c["safety_reserve"] < c["monthly_allowance"]


def test_error_messages_never_contain_the_key(monkeypatch):
    monkeypatch.setenv("ODDS_API_KEY", "k" * 32)
    assert "k" * 32 not in OA._scrub("GET https://api.the-odds-api.com/v4/...?apiKey=" + "k" * 32)
