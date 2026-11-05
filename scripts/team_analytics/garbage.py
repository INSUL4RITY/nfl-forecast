"""Garbage-time splits for the team analytics report (display only; ratings keep all plays).

Lopsided snaps are scrimmage plays where the offence's win probability (nflfastR `wp`) is below 10% (trailing badly)
or above 90% (protecting a lead); competitive snaps are the rest, the same 10-90% cut as the efficiency tables' check
column. The project's model found that dropping garbage time did not improve predictions, so nothing here feeds a
rating: it shows where raw yards, TDs and EPA are inflated or deflated by game script.

Run on its own (re-uses compute.py's cached downloads):
    python scripts/team_analytics/garbage.py --season 2026 --through-week 7
compute.py also calls build() and writes garbage.json with the rest of the bundle.
"""
from __future__ import annotations

import argparse
import json

import pandas as pd

TRAIL, LEAD = 0.10, 0.90
FLAG_EPA = 0.04            # |all-snap EPA/play - competitive EPA/play| at or above this flags a team


def build(p: pd.DataFrame) -> dict:
    sc = p[p.sc & p.wp.notna()].copy()
    sc["trail"] = sc.wp < TRAIL
    sc["lead"] = sc.wp > LEAD
    sc["comp"] = ~(sc.trail | sc.lead)
    sc["td"] = (sc.touchdown == 1) & (sc.td_team == sc.posteam)   # offensive TDs only, not a defensive return
    out = {}
    for side, key in (("off", "posteam"), ("def", "defteam")):
        g = sc.groupby(key)
        t = pd.DataFrame({"plays": g.size(), "yds": g.yards_gained.sum(), "tds": g.td.sum(), "epa_all": g.epa.mean()})
        # for a defence, "trail" means the offence it faces is trailing badly (the defence is protecting a lead)
        for lab in ("trail", "lead", "comp"):
            s = sc[sc[lab]].groupby(key)
            t[f"{lab}_plays"], t[f"{lab}_yds"], t[f"{lab}_tds"] = s.size(), s.yards_gained.sum(), s.td.sum()
            t[f"{lab}_epa"] = s.epa.mean()
        t = t.fillna({c: 0 for c in t.columns if not c.endswith("epa")})
        t["lop_play_share"] = (t.trail_plays + t.lead_plays) / t.plays
        t["lop_yds_share"] = (t.trail_yds + t.lead_yds) / t.yds
        t["lop_td_share"] = (t.trail_tds + t.lead_tds) / t.tds
        t["gt_effect"] = t.epa_all - t.comp_epa          # >0: all-snap EPA/play is higher than in competitive snaps
        for team, r in t.iterrows():
            out.setdefault(team, {})[side] = {k: (None if pd.isna(v) else float(v)) for k, v in r.items()}
    return {"trail": TRAIL, "lead": LEAD, "flag_epa": FLAG_EPA, "teams": out}


def main():
    import compute as cp  # noqa: E402 (re-uses the cached, policy-checked downloads)
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, default=2026)
    ap.add_argument("--through-week", type=int, default=7)
    a = ap.parse_args()
    p = cp.add_unit_flags(cp.load_pbp(a.season, a.through_week))
    d = cp.ROOT / "reports" / "team_analytics" / f"{a.season}_week{a.through_week + 1:02d}"
    (d / "garbage.json").write_text(json.dumps(build(p), indent=1), encoding="utf-8")
    print("wrote", d / "garbage.json")


if __name__ == "__main__":
    main()
