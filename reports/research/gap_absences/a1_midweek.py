"""A1 (research A10): what did a practice-only row at the 2026 lock turn into? Descriptive, player participation only.

For every 2026 lock-24h and original-pick lock (kicked off before the last archived snapshot), each non-QB player listed
for the game with NO game status at the lock: his practice status in the lock snapshot, his final pre-kickoff game status
and whether he took an offensive/defensive snap (2026 snap counts). The shadow input charges every such row
1 - 0.865 = 13.5% of his recent snap share. Writes a1_midweek.json.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import polars as pl  # noqa: E402

from common import SEASON, injury_snapshots, live_player_losses, locked_games, save, snapshot_at, slot  # noqa: E402
from nflcast.config import PROCESSED_DIR  # noqa: E402
from nflcast.features import personnel as P  # noqa: E402

last = injury_snapshots()[-1]["observed_at"]
G = locked_games().filter((pl.col("kickoff_utc") < last) & ~pl.col("provisional") & pl.col("rule").is_in(["lock-24h", "original-pick"]))
games = pl.read_parquet(PROCESSED_DIR / "games.parquet")
sn = P.snap_shares([SEASON], games).select("game_id", "pfr_player_id", game_share="share")
HAVE = set(sn["game_id"].unique().to_list())          # games whose snap counts are in the data (others excluded)
G = G.filter(pl.col("game_id").is_in(list(HAVE)))
rows = []
for g in G.iter_rows(named=True):
    r = [{"game_id": g["game_id"], "home": g["home"], "away": g["away"], "kickoff_utc": g["kickoff_utc"]}]
    lk = live_player_losses(snapshot_at(g["lock_at"]), g["week"], r)
    fn = live_player_losses([s for s in injury_snapshots() if s["observed_at"] < g["kickoff_utc"]][-1], g["week"], r)
    if lk.height == 0:
        continue
    lk = lk.filter(pl.col("status") == "None").select("game_id", "team", "gsis_id", "pfr_player_id", "full_name", "unit",
                                                      "practice_status", "recent_share", "lost")
    lk = lk.join(fn.select("gsis_id", final_status="status"), on="gsis_id", how="left").join(sn, on=["game_id", "pfr_player_id"], how="left")
    rows.append(lk.with_columns(rule=pl.lit(g["rule"]), slot=pl.lit(slot(g["kickoff_utc"]))))
D = pl.concat(rows, how="diagonal_relaxed").with_columns(
    pl.col("game_share").fill_null(0.0), pl.col("final_status").fill_null("dropped from report"),
    practice=pl.when(pl.col("practice_status").str.contains("(?i)did not")).then(pl.lit("DNP"))
    .when(pl.col("practice_status").str.contains("(?i)limited")).then(pl.lit("Limited"))
    .when(pl.col("practice_status").str.contains("(?i)full")).then(pl.lit("Full")).otherwise(pl.lit("none/other")),
    regular=pl.col("recent_share") >= 0.5)
D = D.with_columns(played=(pl.col("game_share") > 0).cast(pl.Int8),
                   out_or_doubtful=pl.col("final_status").is_in(["Out", "Doubtful"]).cast(pl.Int8))
tab = (D.group_by("practice", "regular").agg(n=pl.len(), played=pl.col("played").mean(),
                                               out_or_doubtful=pl.col("out_or_doubtful").mean(),
                                               charged_lost=pl.col("lost").sum(),
                                               realised_lost=(pl.col("recent_share") * (1 - pl.col("played"))).sum())
       .sort("regular", "practice"))
res = {"rows": D.height, "games": D["game_id"].n_unique(), "assumed_play_rate": 0.865, "table": tab.to_dicts(),
       "by_slot_dnp_regulars": D.filter((pl.col("practice") == "DNP") & pl.col("regular")).group_by("slot")
       .agg(n=pl.len(), played=pl.col("played").mean()).sort("slot").to_dicts()}
save("a1_midweek", res)
print(res["rows"], "rows in", res["games"], "games")
for r in res["table"]:
    print(r)
print(res["by_slot_dnp_regulars"])
