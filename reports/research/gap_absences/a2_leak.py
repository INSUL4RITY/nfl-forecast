"""A2 leakage test (pre-registration section 4). For 40 seeded target team-games (2019-2026), corrupt everything dated at
or after the target's kickoff (snap rows of the target and later games: shares randomised, 30% dropped, fake rows added;
injury rows of later weeks; roster rows of the target week and later; later team-game rows dropped), rebuild the inputs
and compare with the clean build. The target's own final injury report is allowed (published before kickoff).
Week-1 targets read the week-1 roster file by the pre-registered definition; they are reported separately.
Writes a2_leak.json.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import numpy as np  # noqa: E402
import polars as pl  # noqa: E402

import a2_build as B  # noqa: E402
from common import OUT, save  # noqa: E402

rng = np.random.default_rng(20261121)
raw = B.load_raw()
tg = raw["tg"].filter(pl.col("season").is_between(2019, 2026))
pick = tg.sample(n=40, seed=20261121)
clean_cache: dict = {}
results = []
for t in pick.iter_rows(named=True):
    Y, W, ko = t["season"], t["week"], t["kickoff_utc"]
    if Y not in clean_cache:
        clean_cache[Y] = B.build(raw, [Y])[0]
    clean = clean_cache[Y].filter((pl.col("game_id") == t["game_id"]) & (pl.col("team") == t["team"]))
    later_games = raw["tg"].filter(pl.col("kickoff_utc") >= ko)["game_id"].unique().to_list()
    sn = raw["snaps"]
    bad = sn.filter(pl.col("game_id").is_in(later_games))
    bad = bad.with_columns(offense_pct=pl.Series(rng.random(bad.height)), defense_pct=pl.Series(rng.random(bad.height)))
    bad = bad.filter(pl.Series(rng.random(bad.height) > 0.3))
    fake = bad.sample(fraction=0.2, seed=1).with_columns(pfr=pl.lit("FAKE") + pl.int_range(pl.len()).cast(pl.Utf8))
    sn_c = pl.concat([sn.filter(~pl.col("game_id").is_in(later_games)), bad, fake])
    inj = raw["inj"]
    later_inj = (pl.col("season") > Y) | ((pl.col("season") == Y) & (pl.col("week") > W))
    ij = inj.filter(later_inj)
    ij = ij.with_columns(status=pl.Series(rng.choice(["Out", "None", "Questionable", "Doubtful"], ij.height)),
                         practice_status=pl.lit("Did Not Participate In Practice")).filter(pl.Series(rng.random(ij.height) > 0.3))
    inj_c = pl.concat([inj.filter(~later_inj), ij])
    ros = raw["ros"]
    later_ros = (pl.col("season") > Y) | ((pl.col("season") == Y) & (pl.col("week") >= W))
    rr = ros.filter(later_ros)
    rr = rr.with_columns(status=pl.Series(rng.choice(["ACT", "RES", "CUT", "INA"], rr.height))).filter(pl.Series(rng.random(rr.height) > 0.3))
    ros_c = pl.concat([ros.filter(~later_ros), rr])
    tg_c = raw["tg"].filter((pl.col("kickoff_utc") < ko) | (pl.col("game_id") == t["game_id"]))
    raw_c = {**raw, "snaps": sn_c, "inj": inj_c, "ros": ros_c, "tg": tg_c}
    cor = B.build(raw_c, [Y])[0].filter((pl.col("game_id") == t["game_id"]) & (pl.col("team") == t["team"]))
    cols = [c for c in clean.columns if "|" in c]
    if clean.height == 0 and cor.height == 0:
        diff = 0.0
    elif clean.height != cor.height:
        diff = float("inf")
    else:
        diff = max(abs(float(clean[c][0] or 0) - float(cor[c][0] or 0)) for c in cols)
    results.append({"game_id": t["game_id"], "team": t["team"], "season": Y, "week": W, "max_abs_diff": diff})
    print(t["game_id"], t["team"], W, diff)
R = pl.DataFrame(results)
res = {"n": R.height, "week1_targets": int((R["week"] == 1).sum()),
       "max_abs_diff_excluding_week1": float(R.filter(pl.col("week") > 1)["max_abs_diff"].max()),
       "max_abs_diff_week1": float(R.filter(pl.col("week") == 1)["max_abs_diff"].max()) if (R["week"] == 1).any() else None,
       "passed": bool(R.filter(pl.col("week") > 1)["max_abs_diff"].max() <= 1e-12), "rows": results}
save("a2_leak", res)
print({k: v for k, v in res.items() if k != "rows"})
