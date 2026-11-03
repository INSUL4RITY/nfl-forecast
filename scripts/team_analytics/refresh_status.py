"""Status refresh for the team analytics report: run after the final injury reports (Friday about 16:30 ET; Thursday
afternoon for a Thursday game), once the week's report already exists.

Re-downloads only the injury reports, weekly rosters and depth charts, then rebuilds what depends on player status:
absences (and the team absence columns), next man up, pass-rusher and usage statuses, arrivals, quarterback scenarios,
then the page and the per-game files. Team performance numbers are not recomputed (they do not change before the games).

    .venv\\Scripts\\python.exe scripts\\team_analytics\\refresh_status.py --season 2026 --through-week 8
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compute as cp  # noqa: E402
import context as ctx  # noqa: E402
import depth  # noqa: E402
import players  # noqa: E402
import usage  # noqa: E402
import nextup  # noqa: E402
import arrivals  # noqa: E402

STATUS_FILES = ("injuries/injuries_{S}.parquet", "weekly_rosters/roster_weekly_{S}.parquet", "depth_charts/depth_charts_{S}.parquet")
QC_PREFIXES = ("Absences:", "Absence classes", "Injury reports", "Duplicate players", "Next man up", "Arrivals", "Status refresh")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, default=2026)
    ap.add_argument("--through-week", type=int, required=True)
    ap.add_argument("--no-download", action="store_true", help="rebuild from the cached files (testing)")
    a = ap.parse_args()
    S, W = a.season, a.through_week
    out_dir = cp.ROOT / "reports" / "team_analytics" / f"{S}_week{W + 1:02d}"
    meta = json.loads((out_dir / "bundle_meta.json").read_text())
    for rel in STATUS_FILES:
        cp.fetch(rel.format(S=S), refresh=not a.no_download)
    qc: list[str] = []
    p = cp.add_unit_flags(cp.load_pbp(S, W))
    teams = sorted(p.posteam.dropna().unique())
    pers, _, absences = cp.personnel(S, W, p, teams, qc)
    T = pd.read_csv(out_dir / "team_metrics.csv", index_col=0)
    for c in pers.columns:
        T[c] = pers[c]
    Q = pd.read_csv(out_dir / "quarterbacks.csv")
    ros = cp.fetch(f"weekly_rosters/roster_weekly_{S}.parquet")
    ros_cur = ros[ros.week == ros.groupby("team").week.transform("max")]
    inj = cp.fetch(f"injuries/injuries_{S}.parquet")
    inj_last = inj[inj.week == inj.groupby("team").week.transform("max")]
    CTX = json.loads((out_dir / "context.json").read_text())
    CTX["qb"] = ctx.qb_scenarios(p, Q, ros_cur, inj_last, teams, W)
    DPj = depth.build(S, W, absences, cp.fetch)
    PLj = players.build(S, W, absences, cp.fetch)
    USj = usage.build(p, S, W, absences, cp.fetch)
    sn = cp.fetch(f"snap_counts/snap_counts_{S}.parquet")
    sn = sn[(sn.week <= W) & (sn.game_type == "REG")].assign(team=lambda x: x.team.replace({"LAR": "LA"}))
    DPj["nextup"] = nextup.build(DPj["depth"]["absences"], absences, sn, p, PLj, USj)
    ARR = arrivals.build(S, W, p, cp.fetch)
    qc.append(f"Next man up: {sum(1 for r in DPj['depth']['absences'] if r.get('next_up'))} absences have a listed replacement; "
              f"{len(DPj['nextup'])} matched to his own 2026 sample.")
    qc.append(arrivals.qc_line(ARR, W))
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    inj_week = int(inj.week.max())
    if not a.no_download:
        qc.append(f"Status refresh {now}: injury reports (latest week {inj_week}), weekly rosters and depth charts re-downloaded; "
                  "absences, next man up, arrivals and quarterback scenarios rebuilt. Team performance numbers are unchanged.")
    # files
    T.to_csv(out_dir / "team_metrics.csv", float_format="%.5f")
    absences.to_csv(out_dir / "absences.csv", index=False)
    (out_dir / "context.json").write_text(json.dumps(CTX, indent=1, default=str))
    (out_dir / "depth.json").write_text(json.dumps(DPj, indent=1, default=str), encoding="utf-8")
    (out_dir / "players.json").write_text(json.dumps({k: v for k, v in PLj.items() if k != "all"}, indent=1, default=str), encoding="utf-8")
    (out_dir / "usage.json").write_text(json.dumps(USj, indent=1, default=str), encoding="utf-8")
    (out_dir / "arrivals.json").write_text(json.dumps(ARR, indent=1, default=str), encoding="utf-8")
    meta["qc"] = [q for q in meta["qc"] if not q.startswith(QC_PREFIXES)] + qc
    fresh = {m["url"]: m for m in cp.MANIFEST}
    meta["sources"] = [fresh.get(m["url"], m) for m in meta["sources"]]
    if not a.no_download:
        meta["status_refreshed_utc"] = now
    (out_dir / "bundle_meta.json").write_text(json.dumps(meta, indent=1, default=str))
    print("\n".join(qc))
    here = Path(__file__).resolve().parent
    for script in ("build_html.py", "export_games.py"):
        subprocess.run([sys.executable, str(here / script), "--dir", str(out_dir)], check=True)


if __name__ == "__main__":
    main()
