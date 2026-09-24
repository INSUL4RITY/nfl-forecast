"""Aggregate play-by-play into one row per (game, offense team) with counts and sums.

Sums and denominators are kept (not only rates) so later as-of aggregation can weight by volume and
report effective sample sizes.

Play definitions (configurable conventions, documented in docs/methodology.md):
  * dropback: nflfastR `qb_dropback == 1` (includes sacks and scrambles); spikes excluded.
  * designed rush: `rush == 1` and not a QB kneel. Scrambles are dropbacks, not designed rushes.
  * success: EPA > 0.
  * explosive: >= 20 yards on a dropback, >= 10 yards on a designed rush (settings.yaml).
  * neutral situation: pre-play score differential within +/-10 and quarters 1-3. Built from pre-play
    state only, never from the eventual result and never from a market-informed win probability.
  * no_play rows (penalties that wipe out the play) are excluded from efficiency; nflfastR sets
    epa on them but they are not plays the offence ran.
"""

from __future__ import annotations

import polars as pl

from nflcast.config import settings
from nflcast.data.games import franchise


def team_game_stats(pbp: pl.DataFrame) -> pl.DataFrame:
    cfg = settings()["features"]
    exp_pass, exp_rush = cfg["explosive_pass_yards"], cfg["explosive_rush_yards"]
    p = pbp.filter(pl.col("posteam").is_not_null() & (pl.col("play_type") != "no_play")).with_columns(
        posteam=franchise(pl.col("posteam")), defteam=franchise(pl.col("defteam")),
        is_db=((pl.col("qb_dropback") == 1) & (pl.col("qb_spike").fill_null(0) == 0)).cast(pl.Int32),
        is_rush=((pl.col("rush") == 1) & (pl.col("qb_kneel").fill_null(0) == 0)).cast(pl.Int32),
        neutral=((pl.col("score_differential").abs() <= 10) & (pl.col("qtr") <= 3)).cast(pl.Int32),
    ).with_columns(
        is_play=((pl.col("is_db") == 1) | (pl.col("is_rush") == 1)).cast(pl.Int32),
        epa0=pl.col("epa").fill_null(0.0),
        succ=(pl.col("epa").fill_null(0.0) > 0).cast(pl.Int32),
    )
    agg = p.group_by(["game_id", "posteam", "defteam"]).agg(
        plays=pl.col("is_play").sum(),
        dropbacks=pl.col("is_db").sum(),
        rushes=pl.col("is_rush").sum(),
        epa_play_sum=(pl.col("epa0") * pl.col("is_play")).sum(),
        epa_db_sum=(pl.col("epa0") * pl.col("is_db")).sum(),
        epa_rush_sum=(pl.col("epa0") * pl.col("is_rush")).sum(),
        succ_play_sum=(pl.col("succ") * pl.col("is_play")).sum(),
        succ_db_sum=(pl.col("succ") * pl.col("is_db")).sum(),
        succ_rush_sum=(pl.col("succ") * pl.col("is_rush")).sum(),
        expl_db=((pl.col("yards_gained").fill_null(0) >= exp_pass) & (pl.col("is_db") == 1)).sum(),
        expl_rush=((pl.col("yards_gained").fill_null(0) >= exp_rush) & (pl.col("is_rush") == 1)).sum(),
        sacks=((pl.col("sack").fill_null(0) == 1) & (pl.col("is_db") == 1)).sum(),
        ints=((pl.col("interception").fill_null(0) == 1) & (pl.col("is_db") == 1)).sum(),
        fumbles_lost=((pl.col("fumble_lost").fill_null(0) == 1) & (pl.col("is_play") == 1)).sum(),
        neutral_plays=(pl.col("neutral") * pl.col("is_play")).sum(),
        neutral_db=(pl.col("neutral") * pl.col("is_db")).sum(),
        cpoe_sum=pl.when(pl.col("is_db") == 1).then(pl.col("cpoe")).otherwise(None).sum(),
        cpoe_n=(pl.col("cpoe").is_not_null() & (pl.col("is_db") == 1)).sum(),
    )
    # Drive-level: offensive drives, points per drive (TD=7, FG=3 approximation; non-offensive scores excluded),
    # starting field position, red-zone trips and TDs.
    drv = (pbp.filter(pl.col("posteam").is_not_null() & pl.col("fixed_drive").is_not_null())
           .with_columns(posteam=franchise(pl.col("posteam")))
           .group_by(["game_id", "posteam", "fixed_drive"]).agg(
               result=pl.col("fixed_drive_result").first(),
               # first scrimmage play (kickoffs/punts are special-teams rows with other field-position frames)
               start_yl100=pl.col("yardline_100").filter(pl.col("play_type").is_in(["pass", "run"])).first(),
               min_yl100=pl.col("yardline_100").min(),
               n=pl.len()))
    drv = drv.with_columns(
        pts=pl.when(pl.col("result") == "Touchdown").then(7).when(pl.col("result") == "Field goal").then(3).otherwise(0),
        rz=(pl.col("min_yl100") <= 20).cast(pl.Int32),
    ).with_columns(rz_td=((pl.col("rz") == 1) & (pl.col("result") == "Touchdown")).cast(pl.Int32))
    dagg = drv.group_by(["game_id", "posteam"]).agg(
        drives=pl.len(), drive_pts=pl.col("pts").sum(), start_yl100_sum=pl.col("start_yl100").sum(),
        start_yl100_n=pl.col("start_yl100").is_not_null().sum(),
        rz_trips=pl.col("rz").sum(), rz_tds=pl.col("rz_td").sum())
    # Starting QB (the passer with the most dropbacks) - a post-game identity used for QB history.
    qb = (p.filter((pl.col("is_db") == 1) & pl.col("passer_player_id").is_not_null())
          .group_by(["game_id", "posteam", "passer_player_id"]).agg(n=pl.len(), qb_epa=pl.col("epa0").sum())
          .sort("n", descending=True).group_by(["game_id", "posteam"]).first()
          .rename({"passer_player_id": "primary_qb_id", "n": "primary_qb_db", "qb_epa": "primary_qb_epa_sum"}))
    out = (agg.join(dagg, on=["game_id", "posteam"], how="left").join(qb, on=["game_id", "posteam"], how="left")
           .rename({"posteam": "team", "defteam": "opp"}))
    return out


def attach_game_info(tg: pl.DataFrame, games: pl.DataFrame) -> pl.DataFrame:
    """Add season/kickoff and points scored so each row is one team's offensive game."""
    g = games.select("game_id", "season", "week", "game_type", "kickoff_utc", "home_id", "away_id",
                     "home_score", "away_score", "neutral_site")
    out = tg.join(g, on="game_id", how="inner").with_columns(
        is_home=(pl.col("team") == pl.col("home_id")),
    ).with_columns(
        points=pl.when(pl.col("is_home")).then(pl.col("home_score")).otherwise(pl.col("away_score")).cast(pl.Float64),
        points_allowed=pl.when(pl.col("is_home")).then(pl.col("away_score")).otherwise(pl.col("home_score")).cast(pl.Float64),
    ).drop("home_score", "away_score", "home_id", "away_id")
    return out.sort(["kickoff_utc", "game_id", "team"])
