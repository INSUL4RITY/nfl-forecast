"""Weather line in the team analytics report: grouping rules, forecast window and wording (no network)."""
import datetime as dt
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "team_analytics"))
import game_weather as gw  # noqa: E402

UTC = dt.timezone.utc
HIST = {"years": [2021, 2025], "games_used": 100, "groups": {k: {"games": 10, "pass_rate": 0.55, "epa_db": 0.01, "epa_rush": -0.05, "ypc": 4.1} for k in gw.BUCKETS}}


def game(roof="outdoors", gameday="2026-11-15", gametime="13:00"):
    return SimpleNamespace(game_id="g", gameday=gameday, gametime=gametime, roof=roof, location="Home", stadium="x", home_team="BAL")


def body(ko, pop=80, wind=6, code=61, temp=61):
    t = [(ko + dt.timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(5)]
    n = len(t)
    return {"hourly": {"time": t, "temperature_2m": [temp] * n, "precipitation_probability": [pop] * n, "precipitation": [0.1] * n,
                       "weather_code": [code] * n, "wind_speed_10m": [wind] * n, "wind_gusts_10m": [wind + 5] * n}}


def fake_get(payload):
    return lambda *a, **k: SimpleNamespace(raise_for_status=lambda: None, json=lambda: payload)


def test_past_game_groups():
    assert gw.text_bucket("Rain Temp: 78 F, Humidity: 81%, Wind: E 9 mph", "outdoors") == "rain"
    assert gw.text_bucket("Rain Temp: 78 F, Humidity: 81%, Wind: E 15 mph", "open") == "rain_wind"
    assert gw.text_bucket("Light Snow Temp: 28 F, Wind: N 5 mph", "outdoors") == "snow"
    assert gw.text_bucket("Sunny Temp: 70 F, Wind: W 18 mph", "outdoors") == "wind"
    assert gw.text_bucket("Sunny Temp: 70 F, Wind: W 5 mph", "dome") is None
    assert gw.text_bucket("Rain Temp: 70 F", "outdoors") is None     # wind missing: unusable, never assumed


def test_kickoff_is_eastern_time():
    assert gw.kickoff(game()) == dt.datetime(2026, 11, 15, 18, 0, tzinfo=UTC)


def test_rain_forecast_shows_history():
    now = dt.datetime(2026, 11, 14, 12, 0, tzinfo=UTC)
    r = gw.game_record(game(), now, fake_get(body(gw.kickoff(game()))))
    assert r["kind"] == "forecast" and gw.conditions(r) == ("Rain likely", "rain")
    assert "games with rain and wind under 15 mph" in gw.line(r, HIST)


def test_dry_forecast_has_no_history():
    now = dt.datetime(2026, 11, 10, 12, 0, tzinfo=UTC)
    r = gw.game_record(game(), now, fake_get(body(gw.kickoff(game()), pop=5, code=1)))
    txt = gw.line(r, HIST)
    assert txt.startswith("Dry:") and "games with" not in txt and "early forecast" in txt


def test_snow_needs_a_likely_chance():
    r = {"pop": 30, "snow": True, "wind": 5}
    assert gw.conditions(r) == ("Some chance of rain", "calm_dry")
    assert gw.conditions(r | {"pop": 60})[1] == "snow"


def test_indoor_unknown_roof_and_started():
    now = dt.datetime(2026, 11, 14, 12, 0, tzinfo=UTC)
    assert gw.line(gw.game_record(game("dome"), now), HIST) == "Indoors, so no weather effect."
    r = gw.game_record(game(float("nan")), now, fake_get(body(gw.kickoff(game()))))
    assert r["kind"] == "roof_unknown" and "games with" not in gw.line(r, HIST)
    assert gw.line(gw.game_record(game(), dt.datetime(2026, 11, 16, tzinfo=UTC)), HIST) is None


def test_nws_is_used_for_us_venues():
    ko = gw.kickoff(game())
    periods = [{"startTime": (ko + dt.timedelta(hours=i)).astimezone(gw.ET).isoformat(), "temperature": 61, "windSpeed": "6 mph",
                "probabilityOfPrecipitation": {"value": 80}, "shortForecast": "Showers And Thunderstorms"} for i in range(4)]

    def get(url, **k):
        p = {"forecastHourly": "hourly"} if "points" in url else {"periods": periods}
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"properties": p})
    r = gw.game_record(game(), dt.datetime(2026, 11, 14, 12, 0, tzinfo=UTC), get)
    assert r["source"] == "National Weather Service" and gw.conditions(r) == ("Rain likely", "rain")
    assert "wind 6 mph, 80% chance" in gw.line(r, HIST)


def test_failed_read_never_raises():
    def boom(*a, **k):
        raise OSError("down")
    now = dt.datetime(2026, 11, 14, 12, 0, tzinfo=UTC)
    assert gw.line(gw.game_record(game(), now, boom), HIST) == "Forecast not loaded."
    assert gw.game_window({"hourly": {"time": []}}, gw.kickoff(game())) is None
