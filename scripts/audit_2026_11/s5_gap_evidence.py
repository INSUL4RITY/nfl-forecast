"""Audit section 5: does the historical record support calling a gap from the market line an "edge"?

For each walk-forward game 2019-2024 (section 2's out-of-fold predictions, reports/audit_2026_11/s2_oof_predictions.parquet),
gap = model margin - market margin (market margin = -home_spread, the single untimed nflverse line ~ closing). The game
counts for the model's side if the final margin finished on the model's side of the line; results level with the line
and zero gaps are excluded. Tiers as shown on the site: tiny < 0.5, small 0.5-1.5, moderate 1.5-3, large >= 3 (and
>= 4, "Biggest gap"). 95% Wilson intervals; 50% = no better than chance. Wording inventory is collected by grep.
Run: .venv\\Scripts\\python.exe scripts\\audit_2026_11\\s5_gap_evidence.py
"""

import re
import subprocess

import numpy as np
import polars as pl

from common import OUT, ROOT, save

P = pl.read_parquet(OUT / "s2_oof_predictions.parquet").filter(pl.col("season").is_between(2019, 2024)
                                                                & pl.col("home_spread").is_not_null())
P = P.with_columns(gap=pl.col("pred_margin") + pl.col("home_spread"), ats=pl.col("margin") + pl.col("home_spread"))
P = P.filter((pl.col("gap") != 0) & (pl.col("ats") != 0)).with_columns(
    model_side=(pl.col("gap") > 0) == (pl.col("ats") > 0),
    tier=pl.when(pl.col("gap").abs() < 0.5).then(pl.lit("1 tiny <0.5")).when(pl.col("gap").abs() < 1.5).then(pl.lit("2 small 0.5-1.5"))
    .when(pl.col("gap").abs() < 3).then(pl.lit("3 moderate 1.5-3")).when(pl.col("gap").abs() < 4).then(pl.lit("4 large 3-4"))
    .otherwise(pl.lit("5 large 4+")))


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [float(c - h), float(c + h)]


rows = []
for (m, t), g in P.group_by(["model", "tier"], maintain_order=True):
    k, n = int(g["model_side"].sum()), g.height
    rows.append({"model": m, "tier": t, "n": n, "model_side": k, "rate": k / n, "ci95": wilson(k, n)})
for (m,), g in P.filter(pl.col("gap").abs() >= 3).group_by(["model"]):
    k, n = int(g["model_side"].sum()), g.height
    rows.append({"model": m, "tier": "gap >= 3 (Big gap)", "n": n, "model_side": k, "rate": k / n, "ci95": wilson(k, n)})
rows.sort(key=lambda r: (r["model"], r["tier"]))

# wording inventory: every public source line using "edge" or "value" in a sense that could read as betting value
out = subprocess.run(["git", "grep", "-n", "-i", "-E", r"\bedges?\b|\bvalue\b", "--", "web/app", "web/components"],
                     cwd=ROOT, capture_output=True, text=True).stdout.splitlines()
inv = [l for l in out if re.search(r"(?i)edge|value", l) and not re.search(r"\.value|value=|valueOf|\bvalue:|v: number", l)]
res = {"tiers": rows, "wording_inventory": inv}
save("s5_gap_evidence", res)
for r in rows:
    print(f"{r['model']:14s} {r['tier']:20s} n={r['n']:4d} model side {r['rate']:.3f} [{r['ci95'][0]:.3f}, {r['ci95'][1]:.3f}]")
print(len(inv), "wording lines")
for l in inv:
    print("  ", l[:170])
