"""B2 (display): historical rate of the model line finishing on its side of the line, by gap band and spread size.

Retrospective: the frozen v1.0 Model line's walk-forward out-of-fold predictions (locked run locked_20260924T234835Z,
model B_qb, final horizon: actual starter as the QB proxy) for 2019-2025, against nflverse untimed (~closing) lines
(market_asof, final horizon). Gap = model margin - line margin; bands under 1, 1-2, 2-3, 3-4 and 4+ points (the first three added 2026-11-24); spread size |line| < 7 and >= 7.
Results level with the line and zero gaps excluded. 95% Wilson intervals. Writes
reports/research/gap_band_history_2026-11-24.json (the 2026-11-21 file had 3-4 and 4+ only), which export_web reads (display only).
"""
import json
import sys
from pathlib import Path

import numpy as np
import polars as pl

from nflcast.config import PROCESSED_DIR, ROOT

RUN = "locked_20260924T234835Z"
p = pl.read_parquet(ROOT / "reports" / "locked_test" / RUN / "predictions.parquet").filter(
    (pl.col("model") == "B_qb") & (pl.col("horizon") == "final") & pl.col("season").is_between(2019, 2025))
mk = pl.read_parquet(PROCESSED_DIR / "market_asof.parquet").filter(pl.col("horizon") == "final").select("game_id", "home_spread").drop_nulls()
d = p.join(mk, on="game_id", how="inner").with_columns(gap=pl.col("pred_margin") + pl.col("home_spread"),
                                                        res=pl.col("margin") + pl.col("home_spread"))
d = d.filter((pl.col("gap") != 0) & (pl.col("res") != 0)).with_columns(side=(pl.col("gap") > 0) == (pl.col("res") > 0),
                                                                    ag=pl.col("gap").abs(), big=pl.col("home_spread").abs() >= 7)


def wilson(k, n, z=1.96):
    p_ = k / n
    den = 1 + z * z / n
    c = (p_ + z * z / (2 * n)) / den
    h = z * np.sqrt(p_ * (1 - p_) / n + z * z / (4 * n * n)) / den
    return [round(float(c - h), 4), round(float(c + h), 4)]


out = {"source": f"walk-forward v1.0 Model line (B_qb), locked run {RUN}, 2019-2025, final horizon",
       "lines": "nflverse untimed lines (about closing)", "retrospective": True, "bands": {}}
for band, lo, hi in (("0-1", 0, 1), ("1-2", 1, 2), ("2-3", 2, 3), ("3-4", 3, 4), ("4+", 4, 99)):
    b = {}
    for lab, cond in (("all", pl.lit(True)), ("lt7", ~pl.col("big")), ("ge7", pl.col("big"))):
        s = d.filter((pl.col("ag") >= lo) & (pl.col("ag") < hi) & cond)
        k, n = int(s["side"].sum()), s.height
        b[lab] = {"n": n, "model_side": k, "rate": round(k / n, 4) if n else None, "ci95": wilson(k, n) if n else None}
    out["bands"][band] = b
path = ROOT / "reports" / "research" / "gap_band_history_2026-11-24.json"
path.write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps(out["bands"]))
