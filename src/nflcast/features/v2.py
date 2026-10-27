"""Model v2.0 inputs for the stats-only line (user decision 2026-10-26; pre-registered in
reports/research/v2_preregistration_2026-10-26.md). The frozen v1.0 features and models are untouched.

Team form uses the same as-of machinery as v1.0 (features/asof.py: exponential decay, season carry-over, shrinkage to the
as-of league mean, opponent-adjusted ratings) with these metric definitions:
  * garbage-time filter: efficiency stats and the opponent-adjusted EPA rating count only plays with the offence's
    pre-snap nflfastR win probability (`wp`, the non-market model) in [WP_LO, WP_HI]; scoring stats are unchanged;
  * penalties: EPA of accepted penalties that cancel the play (no_play rows), offensive committed / defensive committed;
  * luck and regression inputs: all fumbles per play (next to fumbles lost), 3rd/4th-down conversion, one-score results;
  * QB mobility: scramble EPA per dropback; coaching proxy: 4th-down go rate on 4th and <= 3 inside the opponent's 60;
  * special teams: net EPA per game on kickoffs, punts, field goals and extra points (own minus opponent's).
Game context: travel distance, time-zone shift and body-clock kickoff from the team's home venue, consecutive road games,
divisional flag, weather (exposure-weighted; history is retrospective, labelled).
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import numpy as np
import polars as pl

from nflcast.config import settings
from nflcast.data.games import franchise
from nflcast.features.asof import METRICS, AsOfFeatureBuilder, forecast_cutoffs

WP_LO, WP_HI = 0.10, 0.90
ST_TYPES = ["kickoff", "punt", "field_goal", "extra_point"]
PBP_COLS_V2 = ["game_id", "posteam", "defteam", "play_type", "qb_dropback", "qb_spike", "qb_kneel", "rush", "wp", "epa",
               "yards_gained", "qb_scramble", "down", "ydstogo", "yardline_100", "third_down_converted",
               "fourth_down_converted", "fumble", "penalty", "penalty_team", "fixed_drive", "drive_time_of_possession"]

_V1 = {m[0]: m for m in METRICS}
METRICS_V2: list[tuple[str, str, str | None, float]] = [
    ("epa_play", "epa_play_sum_g", "plays_g", 120.0),
    ("epa_db", "epa_db_sum_g", "dropbacks_g", 80.0),
    ("epa_rush", "epa_rush_sum_g", "rushes_g", 60.0),
    ("succ_play", "succ_play_sum_g", "plays_g", 120.0),
    ("expl_db", "expl_db_g", "dropbacks_g", 80.0),
    ("expl_rush", "expl_rush_g", "rushes_g", 60.0),
    *[_V1[k] for k in ("sack_rate", "int_rate", "fum_rate", "neutral_pass", "pts_drive", "rz_td", "start_fp",
                       "plays_pg", "points_pg")],
    ("fum_all", "fum_all", "plays", 200.0),
    ("scr_epa", "scr_epa_sum", "dropbacks", 80.0),
    ("third", "third_conv", "third_att", 40.0),
    ("fourth", "fourth_conv", "fourth_att", 8.0),
    ("go_rate", "go_n", "go_opp", 10.0),
    ("pen_off", "pen_off_epa_sum", "plays", 200.0),
    ("pen_def", "pen_def_epa_sum", "plays", 200.0),
    ("st", "st_net", None, 4.0),
    ("close", "close_net", None, 6.0),
]

# v2.1 (user decision 2026-10-26, after the pre-registered v2.0 test failed): v2.0 without the garbage-time filter
# (efficiency stats as in v1.0) and without travel / body clock, the two groups whose removal improved the test.
# Chosen after seeing those results, so it runs as a trial line only; weeks 8-18 of 2026 are its clean test.
METRICS_V21 = [_V1[k] for k in ("epa_play", "epa_db", "epa_rush", "succ_play", "expl_db", "expl_rush")] + METRICS_V2[6:]
# v2.2 (user request 2026-10-27; reports/research/v2_2_preregistration_2026-10-27.md): v2.1 + time of possession
# (off_top = own possession minutes per game, def_top = the defence's average time on the field) + previous-game fatigue
METRICS_V22 = METRICS_V21 + [("top", "top_min", None, 4.0)]
FATIGUE = ["def_last_plays", "def_plays3", "def_short_load", "last_ot"]
SHORT_LOAD_FROM = 65.0           # plays faced above this in the previous game count as extra load on a short week

# Feature lists (team row = own offence vs the opponent's defence; "opp" items read the opponent's columns)
_OFF = [m[0] for m in METRICS_V2]
_DEF = [m for m in _OFF if m not in ("go_rate", "st", "close")]   # def_st / def_close are exactly -off_* (zero-sum)
TRAVEL = ["travel_k", "tz_shift", "bc_early", "bc_late", "road_streak"]
WX = ["wx_wind", "wx_gust", "wx_cold", "wx_precip", "wx_exposed"]
V2_TEAM = ([f"off_{m}" for m in _OFF] + ["adj_off_epa", "adj_off_pts", "qb_rating", "qb_log_db", "qb_delta",
           "qb_change", "qb_exp", "off_bye", "short_week", "lost_ol", "lost_skill"] + TRAVEL)
V2_OPP = ([f"def_{m}" for m in _DEF] + ["adj_def_epa", "adj_def_pts", "off_bye", "short_week", "lost_front", "lost_db",
          "off_st", "off_close"] + TRAVEL)
V2_CONTEXT = ["venue", "rest_adv", "is_playoff", "own_games_this_season", "opp_games_this_season", "dome", "div_game"] + WX

# Venue time zones by nflverse stadium_id prefix (city code); exceptions by full id.
_TZ_PREFIX = {
    "ATL": "America/New_York", "BAL": "America/New_York", "BOS": "America/New_York", "BUF": "America/New_York",
    "CAR": "America/New_York", "CIN": "America/New_York", "CLE": "America/New_York", "DET": "America/Detroit",
    "IND": "America/Indiana/Indianapolis", "JAX": "America/New_York", "MIA": "America/New_York",
    "NYC": "America/New_York", "PHI": "America/New_York", "PIT": "America/New_York", "TAM": "America/New_York",
    "WAS": "America/New_York", "CHI": "America/Chicago", "DAL": "America/Chicago", "GNB": "America/Chicago",
    "HOU": "America/Chicago", "KAN": "America/Chicago", "MIN": "America/Chicago", "NAS": "America/Chicago",
    "NOR": "America/Chicago", "STL": "America/Chicago", "SAN": "America/Chicago", "DEN": "America/Denver",
    "PHO": "America/Phoenix", "LAX": "America/Los_Angeles", "OAK": "America/Los_Angeles", "SDG": "America/Los_Angeles",
    "SEA": "America/Los_Angeles", "SFO": "America/Los_Angeles", "VEG": "America/Los_Angeles",
    "LON": "Europe/London", "FRA": "Europe/Berlin", "GER": "Europe/Berlin", "MUN": "Europe/Berlin",
    "BRG": "Europe/Berlin", "MAD": "Europe/Madrid", "PAR": "Europe/Paris", "MEX": "America/Mexico_City",
    "SAO": "America/Sao_Paulo", "RIO": "America/Sao_Paulo", "MEL": "Australia/Melbourne", "DUB": "Europe/Dublin",
}


def venue_tz(stadium_id: str) -> str:
    return _TZ_PREFIX[stadium_id[:3]]


# ------------------------------------------------------------------ per (game, offence) sums
def team_game_extra(pbp: pl.DataFrame, tg: pl.DataFrame) -> pl.DataFrame:
    """v1.0 team-games (features/team_games.py) plus the v2.0 sums, one row per (game_id, offence team)."""
    cfg = settings()["features"]
    exp_pass, exp_rush = cfg["explosive_pass_yards"], cfg["explosive_rush_yards"]
    base = pbp.filter(pl.col("posteam").is_not_null()).with_columns(
        posteam=franchise(pl.col("posteam")), defteam=franchise(pl.col("defteam")),
        pen_team=franchise(pl.col("penalty_team")), epa0=pl.col("epa").fill_null(0.0),
        in_wp=(pl.col("wp").is_null() | pl.col("wp").is_between(WP_LO, WP_HI)))
    p = base.filter(pl.col("play_type") != "no_play").with_columns(
        is_db=((pl.col("qb_dropback") == 1) & (pl.col("qb_spike").fill_null(0) == 0)).cast(pl.Int32),
        is_rush=((pl.col("rush") == 1) & (pl.col("qb_kneel").fill_null(0) == 0)).cast(pl.Int32),
    ).with_columns(is_play=((pl.col("is_db") == 1) | (pl.col("is_rush") == 1)).cast(pl.Int32),
                   succ=(pl.col("epa0") > 0).cast(pl.Int32), g=pl.col("in_wp").cast(pl.Int32))
    agg = p.group_by(["game_id", "posteam"]).agg(
        plays_g=(pl.col("is_play") * pl.col("g")).sum(),
        dropbacks_g=(pl.col("is_db") * pl.col("g")).sum(),
        rushes_g=(pl.col("is_rush") * pl.col("g")).sum(),
        epa_play_sum_g=(pl.col("epa0") * pl.col("is_play") * pl.col("g")).sum(),
        epa_db_sum_g=(pl.col("epa0") * pl.col("is_db") * pl.col("g")).sum(),
        epa_rush_sum_g=(pl.col("epa0") * pl.col("is_rush") * pl.col("g")).sum(),
        succ_play_sum_g=(pl.col("succ") * pl.col("is_play") * pl.col("g")).sum(),
        expl_db_g=((pl.col("yards_gained").fill_null(0) >= exp_pass) & (pl.col("is_db") == 1) & pl.col("in_wp")).sum(),
        expl_rush_g=((pl.col("yards_gained").fill_null(0) >= exp_rush) & (pl.col("is_rush") == 1) & pl.col("in_wp")).sum(),
        fum_all=((pl.col("fumble").fill_null(0) == 1) & (pl.col("is_play") == 1)).sum(),
        scr_epa_sum=(pl.col("epa0") * pl.col("is_db") * (pl.col("qb_scramble").fill_null(0) == 1)).sum(),
        third_att=((pl.col("down") == 3) & (pl.col("is_play") == 1)).sum(),
        third_conv=((pl.col("down") == 3) & (pl.col("is_play") == 1) & (pl.col("third_down_converted") == 1)).sum(),
        fourth_att=((pl.col("down") == 4) & (pl.col("is_play") == 1)).sum(),
        fourth_conv=((pl.col("down") == 4) & (pl.col("is_play") == 1) & (pl.col("fourth_down_converted") == 1)).sum(),
    )
    # 4th-down decisions (punts, field goals and plays; kneels/spikes excluded), 4th and <= 3 inside the opponent's 60
    dec = base.filter((pl.col("down") == 4) & (pl.col("ydstogo") <= 3) & (pl.col("yardline_100") <= 60) & pl.col("in_wp")
                      & pl.col("play_type").is_in(["run", "pass", "punt", "field_goal"]))
    go = dec.group_by(["game_id", "posteam"]).agg(go_opp=pl.len(), go_n=pl.col("play_type").is_in(["run", "pass"]).sum())
    pen = base.filter((pl.col("play_type") == "no_play") & (pl.col("penalty") == 1)).group_by(["game_id", "posteam"]).agg(
        pen_off_epa_sum=(pl.col("epa0") * (pl.col("pen_team") == pl.col("posteam"))).sum(),
        pen_def_epa_sum=(pl.col("epa0") * (pl.col("pen_team") == pl.col("defteam"))).sum())
    st = (base.filter(pl.col("play_type").is_in(ST_TYPES)).group_by(["game_id", "posteam"])
          .agg(st_pos=pl.col("epa0").sum()))
    # time of possession: each drive's possession time once (nflverse drive_time_of_possession, "m:ss")
    top = (base.filter(pl.col("fixed_drive").is_not_null() & pl.col("drive_time_of_possession").is_not_null())
           .group_by(["game_id", "posteam", "fixed_drive"]).agg(t=pl.col("drive_time_of_possession").first())
           .with_columns(mm=pl.col("t").str.split(":").list.get(0, null_on_oob=True).cast(pl.Int32, strict=False),
                         ss=pl.col("t").str.split(":").list.get(1, null_on_oob=True).cast(pl.Int32, strict=False))
           .group_by(["game_id", "posteam"]).agg(top_min=(pl.col("mm") * 60 + pl.col("ss")).sum() / 60.0))
    out = (tg.join(agg.rename({"posteam": "team"}), on=["game_id", "team"], how="left")
           .join(go.rename({"posteam": "team"}), on=["game_id", "team"], how="left")
           .join(pen.rename({"posteam": "team"}), on=["game_id", "team"], how="left")
           .join(st.rename({"posteam": "team"}), on=["game_id", "team"], how="left")
           .join(top.rename({"posteam": "team"}), on=["game_id", "team"], how="left"))
    opp = out.select("game_id", pl.col("team").alias("opp"), pl.col("st_pos").alias("st_opp"))
    out = out.join(opp, on=["game_id", "opp"], how="left").with_columns(
        st_net=pl.col("st_pos").fill_null(0.0) - pl.col("st_opp").fill_null(0.0),
        close_net=pl.when(((pl.col("points") - pl.col("points_allowed")).abs() <= 8)
                          & (pl.col("points") != pl.col("points_allowed")))
        .then(pl.when(pl.col("points") > pl.col("points_allowed")).then(1).otherwise(-1)).otherwise(0).cast(pl.Float64))
    fill = [c for c in ("go_opp", "go_n", "pen_off_epa_sum", "pen_def_epa_sum") if c in out.columns]
    return out.with_columns([pl.col(c).fill_null(0) for c in fill]).drop("st_pos", "st_opp")


def builder(tg_v2: pl.DataFrame, metrics=None) -> AsOfFeatureBuilder:
    return AsOfFeatureBuilder(tg_v2, metrics=metrics or METRICS_V2)


# ------------------------------------------------------------------ fatigue (v2.2)
def fatigue_features(games: pl.DataFrame, tg: pl.DataFrame) -> pl.DataFrame:
    """Per game: home_/away_ def_last_plays (plays that team's defence faced in its previous game), def_plays3 (per game
    over its last 3), last_ot (previous game went to overtime), def_short_load (plays faced above SHORT_LOAD_FROM in the
    previous game when this game is on <= 5 days' rest). Only completed games before kickoff count."""
    faced = tg.select("game_id", pl.col("opp").alias("team"), pl.col("plays").alias("faced"))
    hist = (tg.select("game_id", "team", "kickoff_utc").join(faced, on=["game_id", "team"], how="inner")
            .join(games.select("game_id", pl.col("overtime").fill_null(0).cast(pl.Float64).alias("ot")), on="game_id",
                  how="left")
            .sort("team", "kickoff_utc")
            .with_columns(def_plays3=pl.col("faced").cast(pl.Float64).rolling_mean(3, min_samples=1).over("team"))
            .select("team", pl.col("kickoff_utc").alias("prev_ko"), pl.col("faced").cast(pl.Float64).alias("def_last_plays"),
                    "def_plays3", pl.col("ot").alias("last_ot")).sort("prev_ko"))
    out = games.select("game_id", "kickoff_utc", "home_id", "away_id", "home_rest", "away_rest")
    for side in ("home", "away"):
        q = (out.select("game_id", "kickoff_utc", pl.col(f"{side}_id").alias("team"), pl.col(f"{side}_rest").alias("rest"))
             .sort("kickoff_utc"))
        j = q.join_asof(hist, left_on="kickoff_utc", right_on="prev_ko", by="team", strategy="backward",
                        allow_exact_matches=False, check_sortedness=False)
        j = j.with_columns(def_last_plays=pl.col("def_last_plays").fill_null(63.0),
                           def_plays3=pl.col("def_plays3").fill_null(63.0),
                           last_ot=pl.col("last_ot").fill_null(0.0)).with_columns(
            def_short_load=((pl.col("def_last_plays") - SHORT_LOAD_FROM).clip(0, None)
                            * (pl.col("rest").fill_null(7) <= 5).cast(pl.Float64)))
        out = out.join(j.select("game_id", *[pl.col(c).alias(f"{side}_{c}") for c in FATIGUE]), on="game_id", how="left")
    return out.select(["game_id"] + [f"{s}_{c}" for s in ("home", "away") for c in FATIGUE])


# ------------------------------------------------------------------ travel and body clock
def _haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def _utc_hours(tz: str, at: datetime) -> float:
    return at.astimezone(ZoneInfo(tz)).utcoffset().total_seconds() / 3600


def travel_features(games: pl.DataFrame, coords: dict[str, tuple[float, float]]) -> pl.DataFrame:
    """Per game: home_/away_ travel_k (1,000 km from the team's home venue), tz_shift (venue minus home UTC offset,
    hours), bc_early / bc_late (kickoff in the team's home time zone: hours before 13:00 / after 20:00) and road_streak
    (consecutive previous games away from home, cap 3). A team's home venue is its most common non-neutral home venue in
    that season (known from the schedule before the season)."""
    g = games.sort("kickoff_utc")
    home_venue = (g.filter(~pl.col("neutral_site")).group_by("season", "home_id", "stadium_id").len()
                  .sort("len", descending=True).unique(["season", "home_id"], keep="first")
                  .select("season", pl.col("home_id").alias("team"), pl.col("stadium_id").alias("home_venue")))
    hv = {(r["season"], r["team"]): r["home_venue"] for r in home_venue.iter_rows(named=True)}
    last_away: dict[str, int] = {}
    rows = []
    for r in g.iter_rows(named=True):
        ko, sid = r["kickoff_utc"], r["stadium_id"]
        rec = {"game_id": r["game_id"]}
        for side in ("home", "away"):
            team = r[f"{side}_id"]
            home = hv.get((r["season"], team)) or hv.get((r["season"] - 1, team)) or sid
            at_home = side == "home" and not r["neutral_site"]
            ven, hom = coords.get(sid), coords.get(home)
            km = 0.0 if at_home or ven is None or hom is None else _haversine_km(hom, ven)
            htz = venue_tz(home)
            local = ko.astimezone(ZoneInfo(htz))
            hour = local.hour + local.minute / 60
            rec.update({f"{side}_travel_k": km / 1000.0,
                        f"{side}_tz_shift": 0.0 if at_home else _utc_hours(venue_tz(sid), ko) - _utc_hours(htz, ko),
                        f"{side}_bc_early": max(0.0, 13.0 - hour) if r["kickoff_time_known"] else 0.0,
                        f"{side}_bc_late": max(0.0, hour - 20.0) if r["kickoff_time_known"] else 0.0,
                        f"{side}_road_streak": float(min(last_away.get(team, 0), 3))})
        rows.append(rec)
        if r["status"] == "final" or ko <= datetime.now(timezone.utc):
            for side in ("home", "away"):
                team = r[f"{side}_id"]
                away = side == "away" or r["neutral_site"]
                last_away[team] = last_away.get(team, 0) + 1 if away else 0
    return pl.DataFrame(rows)


def venue_coords() -> dict[str, tuple[float, float]]:
    import json
    from nflcast.features.weather import GEO_CACHE
    return {k: (v["latitude"], v["longitude"]) for k, v in json.loads(GEO_CACHE.read_text(encoding="utf-8")).items()}


# ------------------------------------------------------------------ weather (game level)
def weather_history(games: pl.DataFrame) -> pl.DataFrame:
    """wx_* per game: the retrospective historical-forecast cache (2019+, labelled retrospective), else the latest
    prospective snapshot taken at least 1 h before kickoff (2026), else the reanalysis cache (2016-2018, retrospective)."""
    from nflcast.config import PROCESSED_DIR
    from nflcast.features import weather as W
    parts = [W.historical_kickoff_weather(games, PROCESSED_DIR / "weather_historical_forecast.parquet")
             .with_columns(wx_source=pl.lit("historical_forecast_retrospective"))]
    re_cache = PROCESSED_DIR / "weather_reanalysis_2016_2018.parquet"
    if re_cache.exists():
        parts.append(pl.read_parquet(re_cache).with_columns(wx_source=pl.lit("reanalysis_retrospective")))
    have = set(pl.concat([p.select("game_id") for p in parts])["game_id"].to_list())
    snap = []
    for r in games.filter((pl.col("season") >= 2026) & (pl.col("status") == "final")).iter_rows(named=True):
        if r["game_id"] in have:
            continue
        s = W.latest_snapshot(r["season"], r["game_id"], r["kickoff_utc"] - timedelta(hours=1))
        k = (s or {}).get("kickoff_hour")
        if k:
            snap.append({"game_id": r["game_id"], "temp_c": k["temperature_2m"], "wind_kmh": k["wind_speed_10m"],
                         "gust_kmh": k["wind_gusts_10m"], "precip_mm": k["precipitation"], "exposure": s["exposure"],
                         "wx_source": "prospective_snapshot"})
    if snap:
        parts.append(pl.DataFrame(snap))
    cols = ["game_id", "temp_c", "wind_kmh", "gust_kmh", "precip_mm", "exposure", "wx_source"]
    wx = pl.concat([p.select(cols).with_columns(pl.col(c).cast(pl.Float64) for c in cols[1:6]) for p in parts])
    return W.weather_features(wx.unique("game_id", keep="first")).select(["game_id", "wx_source"] + W.WX_FEATURES)


# ------------------------------------------------------------------ assembled snapshots (history)
def build_snapshots(v1_feats: pl.DataFrame, games: pl.DataFrame, tg_v2: pl.DataFrame, metrics=None,
                    version: str = "v2.0", fatigue: bool = False) -> pl.DataFrame:
    """Final-horizon v2.0 feature rows for every game in the v1.0 snapshots: v1.0 QB / schedule / injury / context
    columns, v2.0 team form at the same cutoff, travel, weather, QB experience term."""
    b = builder(tg_v2, metrics)
    base = v1_feats.filter(pl.col("horizon") == "final")
    keep = [c for c in base.columns if c.endswith("_off_bye") or not c.startswith(
        ("home_off_", "home_def_", "away_off_", "away_def_", "home_adj_", "away_adj_"))]
    recs = []
    for r in base.select("game_id", "season", "home_id", "away_id", "cutoff_utc").iter_rows(named=True):
        c_us = int(r["cutoff_utc"].timestamp() * 1_000_000)
        rec = {"game_id": r["game_id"]}
        for side in ("home", "away"):
            tf = b.team_features(r[f"{side}_id"], c_us, r["season"])
            rec.update({f"{side}_{k}": v for k, v in tf.items() if k.startswith(("off_", "def_", "adj_"))})
        recs.append(rec)
    out = base.select(keep).join(pl.DataFrame(recs), on="game_id", how="left")
    out = out.join(travel_features(games, venue_coords()), on="game_id", how="left")
    if fatigue:
        out = out.join(fatigue_features(games, tg_v2), on="game_id", how="left")
    wx = weather_history(games)
    out = out.join(wx, on="game_id", how="left").with_columns([pl.col(c).fill_null(0.0) for c in WX])
    return add_qb_exp(out).with_columns(feature_version=pl.lit(version))


def add_qb_exp(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns([(pl.col(f"{s}_qb_rating") * pl.col(f"{s}_qb_log_db")).alias(f"{s}_qb_exp") for s in ("home", "away")])
