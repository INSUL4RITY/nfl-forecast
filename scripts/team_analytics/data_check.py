r"""Is the last week in? Every game of week W in play-by-play, FTN charting, PFR advanced stats and snap counts, plus the
latest injury-report week (with practice reasons), the weekly roster's reserve list (RES) and the depth-chart date.
Re-downloads those nflverse files (free, no key).

    .venv\Scripts\python.exe scripts\team_analytics\data_check.py 11
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compute as cp  # noqa: E402

S, W = 2026, int(sys.argv[1])
sch = cp.fetch("schedules/games.parquet", refresh=True)
sch = sch[(sch.season == S) & (sch.week == W) & (sch.game_type == "REG")]
ids = set(sch.game_id)
print(f"week {W}: {len(ids)} games scheduled; finished in schedule: {sch.result.notna().sum()}")
pbp = cp.fetch(f"pbp/play_by_play_{S}.parquet", refresh=True)
got = set(pbp.loc[pbp.week == W, "game_id"])
print("pbp:", len(got & ids), "missing", sorted(ids - got))
ftn = cp.fetch(f"ftn_charting/ftn_charting_{S}.parquet", refresh=True)
wk = "week" if "week" in ftn else None
print("ftn weeks:", sorted(ftn[wk].unique())[-3:] if wk else ftn.columns[:10].tolist(),
      "week rows", int((ftn[wk] == W).sum()) if wk else "?")
if wk:
    fg = ftn[ftn[wk] == W]
    key = "nflverse_game_id" if "nflverse_game_id" in fg else None
    if key:
        print("ftn games:", fg[key].nunique(), "missing", sorted(ids - set(fg[key])))
for k in ("pass", "rush", "rec", "def"):
    a = cp.fetch(f"pfr_advstats/advstats_week_{k}_{S}.parquet", refresh=True)
    g = set(a.loc[a.week == W, "game_id"]) if "game_id" in a else set()
    print(f"pfr {k}: games {len(g & ids)} missing {sorted(ids - g)}")
sn = cp.fetch(f"snap_counts/snap_counts_{S}.parquet", refresh=True)
print("snaps games:", sn.loc[sn.week == W, "game_id"].nunique())
inj = cp.fetch(f"injuries/injuries_{S}.parquet", refresh=True)
lw = inj.week.max()
print(f"injury report: latest week {lw}, {int((inj.week == lw).sum())} rows, {int(inj[inj.week == lw].report_status.notna().sum())} with a game status; "
      f"rest days (not injury related - rest): {int(inj[inj.week == lw].practice_primary_injury.fillna('').str.contains('not injury related.*rest', case=False).sum())}")
ros = cp.fetch(f"weekly_rosters/roster_weekly_{S}.parquet", refresh=True)
print("roster weeks:", sorted(ros.week.unique())[-3:])
r = ros[ros.week == ros.week.max()]
print("roster statuses latest week:", r.status.value_counts().to_dict(), "(RES = reserve lists, IR included)")
dc = cp.fetch(f"depth_charts/depth_charts_{S}.parquet", refresh=True)
dcol = [c for c in dc.columns if "dt" in c.lower() or "date" in c.lower() or c == "week"]
print("depth chart latest:", {c: str(dc[c].max()) for c in dcol})
print(sch[["game_id", "away_score", "home_score"]].to_string())
