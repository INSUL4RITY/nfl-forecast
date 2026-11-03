"""Individual pass rushers and coverage defenders for the team analytics report.

PFR advanced defence (nflverse `pfr_advstats/advstats_week_def`) has one row per defender per game: pressures, hurries,
QB hits, sacks and times blitzed (pass rush), and targets, completions, yards, TDs and INTs allowed as the nearest
defender (coverage). Rows are summed per player and team, so a traded player appears under each team with that team's
games only. Defensive snaps come from snap counts (same PFR player id). Current status comes from the report's
absences (latest roster and injury report), matched by team and player name.

Run on its own:
    python scripts/team_analytics/players.py --season 2026 --through-week 7
compute.py also calls build() and writes players.json with the rest of the bundle.
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from depth import OUT_CLASSES, STATUS_TEXT, _norm

OUT, STATUS = OUT_CLASSES, STATUS_TEXT
N_RUSH, N_COV = 6, 6
PRESS_FLAG, TGT_FLAG = 0.15, 0.20     # a caution when players now out made this share of pressures / drew this share of targets


def passer_rating(cmp, att, yds, td, ints):
    """NFL passer rating on targets (the defender's 'attempts'); None below one target."""
    if att <= 0:
        return None
    parts = [((cmp / att) - 0.3) * 5, ((yds / att) - 3) * 0.25, (td / att) * 20, 2.375 - (ints / att) * 25]
    return float(sum(min(max(x, 0), 2.375) for x in parts) / 6 * 100)


def build(season: int, through_week: int, absences: pd.DataFrame, fetch) -> dict:
    d = fetch(f"pfr_advstats/advstats_week_def_{season}.parquet")
    d = d[(d.week <= through_week) & (d.game_type == "REG")].copy()
    d["team"] = d.team.replace({"LAR": "LA"})
    sn = fetch(f"snap_counts/snap_counts_{season}.parquet")
    sn = sn[(sn.week <= through_week) & (sn.game_type == "REG")].copy()
    sn["team"] = sn.team.replace({"LAR": "LA"})
    snaps = sn.groupby(["team", "pfr_player_id"]).defense_snaps.sum()
    pos = sn.sort_values("week").groupby("pfr_player_id").position.last()
    team_games = d.groupby("team").game_id.nunique()

    # status: absences carry the snap-count player name; link it to the PFR id through the snap counts
    name_id = {(t, _norm(n)): pid for t, n, pid in sn[["team", "player", "pfr_player_id"]].drop_duplicates().itertuples(index=False)}
    status = {}
    for a in absences.itertuples():
        pid = name_id.get((a.team, _norm(a.player)))
        if pid:
            status[(a.team, pid)] = a.status_class

    num = ["def_pressures", "def_times_hurried", "def_times_hitqb", "def_sacks", "def_times_blitzed", "def_targets",
           "def_completions_allowed", "def_yards_allowed", "def_receiving_td_allowed", "def_ints", "def_missed_tackles"]
    g = d.groupby(["team", "pfr_player_id"])
    P = g[num].sum()
    P["name"] = g.pfr_player_name.last()
    P["games"] = g.game_id.nunique()
    P = P.reset_index()
    P["pos"] = P.pfr_player_id.map(pos).fillna("")
    P["snaps"] = [int(snaps.get((t, pid), 0)) for t, pid in zip(P.team, P.pfr_player_id)]
    P["status_class"] = [status.get((t, pid)) for t, pid in zip(P.team, P.pfr_player_id)]
    P["status"] = P.status_class.map(STATUS).fillna("")
    P["out"] = P.status_class.isin(OUT)

    teams, league = {}, {}
    for t, x in P.groupby("team"):
        press, tgts = x.def_pressures.sum(), x.def_targets.sum()
        rush = x[x.def_pressures > 0].sort_values(["def_pressures", "def_sacks"], ascending=False)
        cov = x[x.def_targets > 0].sort_values(["def_targets", "def_yards_allowed"], ascending=False)
        rush_rows = [{"name": r.name, "pos": r.pos, "games": int(r.games), "snaps": r.snaps,
                      "pressures": int(r.def_pressures), "hurries": int(r.def_times_hurried), "hits": int(r.def_times_hitqb),
                      "sacks": float(r.def_sacks), "blitzes": int(r.def_times_blitzed),
                      "share": float(r.def_pressures / press) if press else None,
                      "per100": float(r.def_pressures / r.snaps * 100) if r.snaps else None, "status": r.status}
                     for r in rush.head(N_RUSH).itertuples()]
        cov_rows = [{"name": r.name, "pos": r.pos, "games": int(r.games), "snaps": r.snaps, "targets": int(r.def_targets),
                     "cmp": int(r.def_completions_allowed), "yds": int(r.def_yards_allowed),
                     "td": int(r.def_receiving_td_allowed), "ints": int(r.def_ints),
                     "cmp_pct": float(r.def_completions_allowed / r.def_targets),
                     "ypt": float(r.def_yards_allowed / r.def_targets),
                     "rating": passer_rating(r.def_completions_allowed, r.def_targets, r.def_yards_allowed,
                                             r.def_receiving_td_allowed, r.def_ints),
                     "share": float(r.def_targets / tgts) if tgts else None, "status": r.status}
                    for r in cov.head(N_COV).itertuples()]
        out_r, out_c = rush[rush.out], cov[cov.out]
        teams[t] = {
            "pfr_games": int(team_games.get(t, 0)), "pressures": int(press), "targets": int(tgts),
            "rush": rush_rows, "cov": cov_rows,
            "top3_press_share": float(rush.def_pressures.head(3).sum() / press) if press else None,
            "press_out_share": float(out_r.def_pressures.sum() / press) if press else 0.0,
            "press_out_names": [f"{r.name} ({int(r.def_pressures)})" for r in out_r.itertuples()],
            "tgt_out_share": float(out_c.def_targets.sum() / tgts) if tgts else 0.0,
            "tgt_out_names": [f"{r.name} ({int(r.def_targets)} targets)" for r in out_c.itertuples()],
        }
    # league reference: defenders with 30+ targets
    q = P[P.def_targets >= 30]
    league["cov_rating_30"] = passer_rating(q.def_completions_allowed.sum(), q.def_targets.sum(), q.def_yards_allowed.sum(),
                                            q.def_receiving_td_allowed.sum(), q.def_ints.sum())
    league["n_cov_30"] = int(len(q))
    # every defender's season line by team and normalised name (used for next-man-up samples)
    allp = {t: {_norm(r.name): {"name": r.name, "pos": r.pos, "games": int(r.games), "snaps": int(r.snaps),
                                "pressures": int(r.def_pressures), "sacks": float(r.def_sacks), "targets": int(r.def_targets),
                                "rating": passer_rating(r.def_completions_allowed, r.def_targets, r.def_yards_allowed,
                                                        r.def_receiving_td_allowed, r.def_ints)}
                for r in x.itertuples()} for t, x in P.groupby("team")}
    return {"teams": teams, "league": league, "press_flag": PRESS_FLAG, "tgt_flag": TGT_FLAG,
            "matched_status": int(P.status_class.notna().sum()), "all": allp}


def main():
    import compute as cp  # noqa: E402 (re-uses the cached, policy-checked downloads)
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, default=2026)
    ap.add_argument("--through-week", type=int, default=7)
    a = ap.parse_args()
    d = cp.ROOT / "reports" / "team_analytics" / f"{a.season}_week{a.through_week + 1:02d}"
    out = build(a.season, a.through_week, pd.read_csv(d / "absences.csv"), cp.fetch)
    (d / "players.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print("wrote", d / "players.json", len(out["teams"]), "teams,", out["matched_status"], "players with a status")


if __name__ == "__main__":
    main()
