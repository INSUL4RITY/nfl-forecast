"""Build the self-contained HTML report from compute.py outputs.

    .venv\\Scripts\\python.exe scripts\\team_analytics\\build_html.py --dir reports\\team_analytics\\2026_week08

Everything on the page is derived from the CSV/JSON files in --dir, plus the hand-written analyst_notes.json
(optional) in the same folder.
"""
from __future__ import annotations

import argparse
import html
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

# ------------------------------------------------------------------------------------------ helpers
def zs(s):
    return (s - s.mean()) / s.std(ddof=0)


def rank(s, higher_better=True):
    return s.rank(ascending=not higher_better, method="min")


def ordinal(n):
    n = int(n)
    suf = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


def fmt(v, f):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "n/a"
    if f == "epa":
        return f"{v:+.3f}"
    if f == "pct":
        return f"{100 * v:.1f}%"
    if f == "n1":
        return f"{v:.1f}"
    if f == "n2":
        return f"{v:.2f}"
    if f == "s1":
        return f"{v:+.1f}"
    if f == "s2":
        return f"{v:+.2f}"
    if f == "int":
        return f"{int(round(v))}"
    return str(v)


def esc(s):
    return html.escape(str(s))


# column spec: (key, label, format, direction: 1 higher better, -1 lower better, 0 neutral, tooltip)
def C(k, l, f="epa", d=1, tip=""):
    return {"k": k, "l": l, "f": f, "d": d, "t": tip}


def table(tid, title, cols, sort, note="", desc=None, rows="teams", order=None):
    return {"id": tid, "title": title, "cols": cols, "sort": sort, "note": note, "rows": rows,
            "desc": desc, "order": order}


# --------------------------------------------------------------------------------------- derived data
def derive(T: pd.DataFrame, G: pd.DataFrame, meta: dict):
    T = T.copy()
    T["record"] = T.w.astype(int).astype(str) + "-" + T.l.astype(int).astype(str) + np.where(T.t > 0, "-" + T.t.astype(int).astype(str), "")
    T["one_score"] = T.one_w.astype(int).astype(str) + "-" + T.one_l.astype(int).astype(str)
    T["three_pt"] = T.three_w.astype(int).astype(str) + "-" + T.three_l.astype(int).astype(str)
    T["ot_rec"] = T.ot_w.astype(int).astype(str) + "-" + T.ot_l.astype(int).astype(str)
    T["d4_rec"] = T.off_d4_conv.map(lambda v: "n/a" if pd.isna(v) else f"{100*v:.0f}%") + " (" + T.off_d4_n.astype(int).astype(str) + ")"
    T["vs_strong"] = T.w_vs_strong.fillna(0).astype(int).astype(str) + "/" + T.g_vs_strong.fillna(0).astype(int).astype(str)
    T["vs_winning"] = T.w_vs_winning.fillna(0).astype(int).astype(str) + "/" + T.g_vs_winning.fillna(0).astype(int).astype(str)
    T["off_raw_rank"] = rank(T.off_epa_play)
    T["off_adj_rank"] = rank(T.off_adj_epa)
    T["def_raw_rank"] = rank(T.def_epa_play, False)
    T["def_adj_rank"] = rank(T.def_adj_epa, False)
    T["net_raw_rank"] = rank(T.raw_net_epa)
    T["net_adj_rank"] = rank(T.adj_net_epa)
    T["rating_rank"] = rank(T.rating_pg)
    T["stab_rank"] = rank(T.stab_rating_pg)
    T["winpct_rank"] = rank(T.win_pct)
    T["off_adj_shift"] = T.off_raw_rank - T.off_adj_rank        # >0: improves after adjustment
    T["def_adj_shift"] = T.def_raw_rank - T.def_adj_rank
    T["record_vs_rating"] = T.rating_rank - T.winpct_rank         # >0: record ranks better than rating
    T["off_rank_sr"] = rank(T.off_adj_sr)
    T["off_rank_ppd"] = rank(T.off_ppd)
    T["off_rank_spread"] = pd.concat([T.off_adj_rank, T.off_rank_sr, T.off_rank_ppd], axis=1).max(axis=1) - pd.concat([T.off_adj_rank, T.off_rank_sr, T.off_rank_ppd], axis=1).min(axis=1)
    T["def_rank_sr"] = rank(T.def_adj_sr, False)
    T["def_rank_ppd"] = rank(T.def_ppd, False)
    T["def_rank_spread"] = pd.concat([T.def_adj_rank, T.def_rank_sr, T.def_rank_ppd], axis=1).max(axis=1) - pd.concat([T.def_adj_rank, T.def_rank_sr, T.def_rank_ppd], axis=1).min(axis=1)
    T["off_pts_vs_yards"] = rank(T.off_yards_pd) - rank(T.off_pts_over_ep)      # >0 finishes worse than it moves
    T["def_fp_help"] = rank(T.def_ppd, False) - rank(T.def_pts_over_ep, False)   # <0: ppd rank flattered by field position
    T["pass_minus_rush"] = zs(T.off_adj_epa_db) - zs(T.off_adj_epa_rush)
    T["off_expl_epa_share_rank"] = rank(T.off_expl_epa_share)
    # offence vs strong-tier defences (game level)
    strong = G[G.opp_tier == "strong"]
    T["off_epa_vs_strong"] = strong.groupby("team").off_epa_play.mean()
    T["def_epa_vs_strong"] = strong.groupby("team").def_epa_play.mean()
    # luck categories
    T["category"] = np.where(T.luck_index >= 0.75, "over", np.where(T.luck_index <= -0.75, "under", "supported"))
    return T


UNITS_OFF = [("Passing", "off_adj_epa_db", 1, "epa", "adj. EPA/dropback"),
             ("Rushing", "off_adj_epa_rush", 1, "epa", "adj. EPA/designed rush"),
             ("Early downs", "off_adj_early_epa", 1, "epa", "adj. early-down EPA/play"),
             ("Third/fourth downs", "off_late_conv", 1, "pct", "late-down conversion rate"),
             ("Red zone", "off_rz_td_rate", 1, "pct", "red-zone TD rate per trip"),
             ("Explosive plays", "off_expl_rate", 1, "pct", "explosive-play rate"),
             ("Ball security", "giveaway_rate", -1, "pct", "giveaways per play"),
             ("Pass protection", "off_pressure_rate", -1, "pct", "pressure rate allowed")]
UNITS_DEF = [("Pass defence", "def_adj_epa_db", -1, "epa", "adj. EPA/dropback allowed"),
             ("Run defence", "def_adj_epa_rush", -1, "epa", "adj. EPA/designed rush allowed"),
             ("Pass rush", "def_pressure_rate", 1, "pct", "pressure rate"),
             ("Third/fourth-down defence", "def_late_conv", -1, "pct", "late-down conversion allowed"),
             ("Red-zone defence", "def_rz_td_rate", -1, "pct", "red-zone TD rate allowed"),
             ("Explosive prevention", "def_expl_rate", -1, "pct", "explosive-play rate allowed"),
             ("Takeaways", "takeaway_rate", 1, "pct", "takeaways per play")]


def unit_ranks(T):
    out = {}
    for name, col, d, f, lab in UNITS_OFF + UNITS_DEF:
        out[name] = (rank(T[col], d == 1), col, f, lab)
    return out


def profile(t, T, U, G, meta):
    r = T.loc[t]
    def u(name):
        rk, col, f, lab = U[name]
        return int(rk[t]), fmt(r[col], f), lab
    off = sorted([(u(n)[0], n) for n, *_ in UNITS_OFF])
    de = sorted([(u(n)[0], n) for n, *_ in UNITS_DEF])
    allu = sorted(off + de)
    def say(n):
        k, v, lab = u(n)
        return f"{n}: {ordinal(k)} ({lab} {v})"
    best_off, best_def, worst = off[0][1], de[0][1], allu[-1][1]
    worst2 = allu[-2][1]
    lines = []
    lines.append(("Most reliable offensive strength", say(best_off)))
    lines.append(("Most significant defensive strength", say(best_def)))
    lines.append(("Consistently inefficient", f"{say(worst)}; next weakest {say(worst2)}"))
    dep = (f"Explosive plays account for {fmt(r.off_expl_epa_share, 'pct')} of its positive offensive EPA "
           f"({ordinal(rank(T.off_expl_epa_share)[t])} most dependent); turnover margin {int(r.to_margin):+d} "
           f"against an expected {r.x_to_margin:+.1f}; average drive start own {r.off_start_own:.1f} "
           f"({ordinal(rank(T.off_start_own)[t])}).")
    lines.append(("Dependence on explosives, turnovers, field position", dep))
    gs = G[(G.team == t) & (G.opp_tier == "strong")]
    if len(gs):
        lines.append(("Sustains drives against strong defences?",
                      f"{len(gs)} game(s) against top-third opponents: offence {gs.off_epa_play.mean():+.3f} EPA/play "
                      f"(season {r.off_epa_play:+.3f}). Small sample."))
    else:
        lines.append(("Sustains drives against strong defences?", "No games yet against top-third opponents."))
    lines.append(("Stops efficient passing and rushing?", f"{say('Pass defence')}; {say('Run defence')}"))
    lines.append(("Protects the quarterback?",
                  f"Pressure allowed {fmt(r.off_pressure_rate, 'pct')} ({ordinal(rank(T.off_pressure_rate, False)[t])}), "
                  f"sack rate {fmt(r.off_sack_rate, 'pct')} ({ordinal(rank(T.off_sack_rate, False)[t])})."))
    lines.append(("Pressure without blitzing?",
                  f"Hit-or-sack rate with four or fewer rushers {fmt(r.def_hs_noblitz, 'pct')} "
                  f"({ordinal(rank(T.def_hs_noblitz)[t])}); blitz rate {fmt(r.def_blitz_rate, 'pct')} "
                  f"({'highest in the league' if rank(T.def_blitz_rate)[t] == 1 else ordinal(rank(T.def_blitz_rate)[t]) + ' highest'})."))
    lines.append(("Supported by opponent-adjusted metrics?",
                  f"Net EPA/play rank {ordinal(r.net_raw_rank)} raw, {ordinal(r.net_adj_rank)} adjusted; schedule "
                  f"{'tougher' if r.sos_net > 0 else 'easier'} than average ({r.sos_net:+.3f} opponent net EPA/play)."))
    lines.append(("Consistent across situations?",
                  f"Game-to-game SD of net EPA/play {r.net_sd:.3f} ({ordinal(rank(T.net_sd, False)[t])} steadiest); "
                  f"early-down offence {ordinal(u('Early downs')[0])}, late-down offence {ordinal(u('Third/fourth downs')[0])}."))
    lines.append(("Weakness a strong opponent could exploit", say(worst)))
    return {"best_off": best_off, "best_def": best_def, "worst": worst, "lines": lines}


def mismatches(T, nxt):
    Z = {
        "pass_o": zs(T.off_adj_epa_db), "pass_dw": zs(T.def_adj_epa_db),
        "rush_o": zs(T.off_adj_epa_rush), "rush_dw": zs(T.def_adj_epa_rush),
        "prot_w": zs(T.off_pressure_rate), "rush_pr": zs(T.def_pressure_rate),
        "expl_o": zs(T.off_expl_rate), "expl_dw": zs(T.def_expl_rate),
        "blitz": zs(T.def_blitz_rate), "vs_blitz": zs(T.off_epa_blitz),
    }
    rows = []
    for _, g in nxt.iterrows():
        h, a = g.home_team, g.away_team
        edges = []
        for o, d in [(h, a), (a, h)]:
            edges += [
                (Z["pass_o"][o] + Z["pass_dw"][d], f"{o} passing vs {d} pass defence",
                 f"{o} adj. EPA/dropback {T.off_adj_epa_db[o]:+.3f} ({ordinal(rank(T.off_adj_epa_db)[o])}); {d} allows {T.def_adj_epa_db[d]:+.3f} ({ordinal(rank(T.def_adj_epa_db, False)[d])})", o, d),
                (Z["rush_o"][o] + Z["rush_dw"][d], f"{o} run game vs {d} run defence",
                 f"{o} adj. EPA/rush {T.off_adj_epa_rush[o]:+.3f} ({ordinal(rank(T.off_adj_epa_rush)[o])}); {d} allows {T.def_adj_epa_rush[d]:+.3f} ({ordinal(rank(T.def_adj_epa_rush, False)[d])})", o, d),
                (Z["rush_pr"][d] + Z["prot_w"][o], f"{d} pass rush vs {o} protection",
                 f"{d} pressure rate {fmt(T.def_pressure_rate[d], 'pct')} ({ordinal(rank(T.def_pressure_rate)[d])}); {o} allows {fmt(T.off_pressure_rate[o], 'pct')} ({ordinal(rank(T.off_pressure_rate, False)[o])} in protection)", d, o),
                (Z["expl_o"][o] + Z["expl_dw"][d], f"{o} big plays vs {d} explosive prevention",
                 f"{o} explosive rate {fmt(T.off_expl_rate[o], 'pct')} ({ordinal(rank(T.off_expl_rate)[o])}); {d} allows {fmt(T.def_expl_rate[d], 'pct')} ({ordinal(rank(T.def_expl_rate, False)[d])} in prevention)", o, d),
                (Z["blitz"][d] + Z["vs_blitz"][o], f"{d} blitz frequency vs {o} passing against the blitz",
                 f"{d} blitzes {fmt(T.def_blitz_rate[d], 'pct')} of dropbacks ({ordinal(rank(T.def_blitz_rate)[d])}); {o} EPA/dropback vs blitz {T.off_epa_blitz[o]:+.3f} ({ordinal(rank(T.off_epa_blitz)[o])})", o, d),
            ]
        edges = sorted(edges, key=lambda e: -abs(e[0]))[:3]
        rows.append({"game": f"{a} at {h}", "day": str(g.gameday), "edges": [
            {"score": round(float(e[0]), 2), "what": e[1], "detail": e[2], "favours": e[3] if e[0] >= 0 else e[4]} for e in edges]})
    return rows


# ------------------------------------------------------------------------------------------ page
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(ROOT / "reports" / "team_analytics" / "2026_week08"))
    args = ap.parse_args()
    d = Path(args.dir)
    T = pd.read_csv(d / "team_metrics.csv", index_col=0)
    G = pd.read_csv(d / "team_games.csv")
    Q = pd.read_csv(d / "quarterbacks.csv")
    A = pd.read_csv(d / "absences.csv")
    nxt = pd.read_csv(d / "next_week_schedule.csv")
    meta = json.loads((d / "bundle_meta.json").read_text())
    notes_path = d / "analyst_notes.json"
    notes = json.loads(notes_path.read_text(encoding="utf-8")) if notes_path.exists() else {}
    T = derive(T, G, meta)
    U = unit_ranks(T)
    profiles = {t: profile(t, T, U, G, meta) for t in T.index}
    mm = mismatches(T, nxt)
    order = list(T.sort_values("rating_pg", ascending=False).index)

    # ---------------- tables
    tables = []
    tables.append(table("power", "Power rankings: all ten categories", [
        C("record", "Record", "str", 0), C("rating_pg", "Overall team", "s1", 1, "Opponent-adjusted net EPA converted to points per game (offence + defence) plus special-teams EPA per game"),
        C("off_composite", "Offence overall", "s2", 1, "Weighted z-score: 61% adj. EPA/play, 39% adj. success rate (weights fitted on 2021-25)"),
        C("def_composite", "Defence overall", "s2", 1, "Weighted z-score: 53% adj. EPA/play, 35% adj. success rate, 12% points per drive allowed"),
        C("off_adj_epa", "Off. efficiency", "epa", 1, "Opponent-adjusted EPA per play"),
        C("def_adj_epa", "Def. efficiency", "epa", -1, "Opponent-adjusted EPA per play allowed"),
        C("off_adj_epa_db", "Passing O", "epa", 1, "Adj. EPA per dropback"),
        C("off_adj_epa_rush", "Rushing O", "epa", 1, "Adj. EPA per designed rush"),
        C("def_adj_epa_db", "Pass D", "epa", -1, "Adj. EPA per dropback allowed"),
        C("def_adj_epa_rush", "Run D", "epa", -1, "Adj. EPA per designed rush allowed"),
        C("off_situational", "Situational O", "s2", 1, "Mean z-score of late-down conversion rate and red-zone TD rate"),
        C("def_situational", "Situational D", "s2", 1, "Mean z-score (reversed) of late-down conversion and red-zone TD rate allowed"),
        C("st_epa_pg", "Special teams", "s2", 1, "Special-teams EPA per game (kicking, punting, returns)"),
    ], "rating_pg", "Every column is sortable. The small number after each value is its rank (1 = best). Colour marks the top and bottom eight in each column."))
    tables.append(table("agree", "Do independent metrics agree?", [
        C("record", "Record", "str", 0),
        C("off_adj_rank", "Off. rank: adj. EPA", "int", -1), C("off_rank_sr", "adj. success", "int", -1), C("off_rank_ppd", "pts/drive", "int", -1),
        C("off_rank_spread", "Off. spread", "int", -1, "Largest minus smallest of the three offensive ranks"),
        C("def_adj_rank", "Def. rank: adj. EPA", "int", -1), C("def_rank_sr", "adj. success", "int", -1), C("def_rank_ppd", "pts/drive", "int", -1),
        C("def_rank_spread", "Def. spread", "int", -1),
    ], "off_rank_spread", "A spread of 10 or more ranks means the unit's standing depends on which metric is used.", desc=False))
    tables.append(table("eff_off", "Offensive efficiency", [
        C("off_epa_play", "EPA/play", "epa", 1), C("off_adj_epa", "Adj. EPA/play", "epa", 1),
        C("off_adj_shift", "Rank change after adj.", "s1", 0, "Positive = ranks higher once opponents are accounted for"),
        C("off_epa_play_neutral", "EPA/play, WP 10-90%", "epa", 1, "Excludes plays when either team's win probability is above 90%"),
        C("off_sr", "Success rate", "pct", 1), C("off_adj_sr", "Adj. success", "pct", 1),
        C("off_epa_db", "EPA/dropback", "epa", 1), C("off_epa_rush", "EPA/designed rush", "epa", 1),
        C("off_early_epa", "Early-down EPA", "epa", 1), C("off_early_sr", "Early-down SR", "pct", 1),
        C("off_d3_conv", "3rd-down conv.", "pct", 1), C("off_d4_conv", "4th-down conv.", "pct", 1), C("off_d4_n", "4th-down att.", "int", 0),
        C("off_rz_td_rate", "Red-zone TD%", "pct", 1), C("off_g2g_td_rate", "Goal-to-go TD%", "pct", 1),
        C("off_expl_rate", "Explosive rate", "pct", 1),
        C("off_epa_nonto", "EPA/play excl. turnover plays", "epa", 1), C("off_to_epa_play", "Turnover EPA per play", "epa", 1),
        C("dvoa", "DVOA", "str", 0, "Not available: FTN's DVOA is proprietary and was not used"),
    ], "off_adj_epa", "Raw values are unadjusted; 'Adj.' columns are opponent-adjusted (see Method)."))
    tables.append(table("eff_def", "Defensive efficiency", [
        C("def_epa_play", "EPA/play allowed", "epa", -1), C("def_adj_epa", "Adj. EPA/play", "epa", -1),
        C("def_adj_shift", "Rank change after adj.", "s1", 0),
        C("def_epa_play_neutral", "EPA/play, WP 10-90%", "epa", -1),
        C("def_sr", "Success allowed", "pct", -1), C("def_adj_sr", "Adj. success", "pct", -1),
        C("def_epa_db", "EPA/dropback", "epa", -1), C("def_epa_rush", "EPA/designed rush", "epa", -1),
        C("def_early_epa", "Early-down EPA", "epa", -1), C("def_early_sr", "Early-down SR", "pct", -1),
        C("def_d3_conv", "3rd-down conv. allowed", "pct", -1), C("def_d4_conv", "4th-down conv. allowed", "pct", -1), C("def_d4_n", "4th-down att. faced", "int", 0),
        C("def_rz_td_rate", "Red-zone TD% allowed", "pct", -1), C("def_expl_rate", "Explosive rate allowed", "pct", -1),
        C("def_epa_vs_pass_heavy", "EPA vs pass-heavy offences", "epa", -1, "Opponents in the top half of neutral early-down pass rate over expected"),
        C("def_epa_vs_run_heavy", "EPA vs run-heavy offences", "epa", -1),
        C("dvoa", "DVOA", "str", 0, "Not available"),
    ], "def_adj_epa", "Lower is better for every allowed-rate column.", desc=False))
    tables.append(table("drives_off", "Offensive drives", [
        C("off_drives", "Drives", "int", 0), C("off_ppd", "Points/drive", "n2", 1), C("off_td_pd", "TD/drive", "pct", 1),
        C("off_fg_pd", "FG/drive", "pct", 0), C("off_punt_pd", "Punt/drive", "pct", -1), C("off_to_pd", "Turnover/drive", "pct", -1),
        C("off_downs_pd", "Downs/drive", "pct", -1), C("off_start_own", "Avg start (own yd line)", "n1", 1),
        C("off_plays_pd", "Plays/drive", "n1", 0), C("off_yards_pd", "Yards/drive", "n1", 1), C("off_top_pd", "Seconds/drive", "n1", 0),
        C("off_rz_trips_pd", "RZ trips/drive", "pct", 1), C("off_rz_td_rate", "RZ TD%", "pct", 1), C("off_pts_per_rz_trip", "Pts/RZ trip", "n2", 1),
        C("off_ep_start", "EP at drive start", "n2", 1, "nflfastR expected points at the first snap: field-position value the offence was handed"),
        C("off_pts_over_ep", "Points over start EP", "s2", 1, "Points per drive minus expected points at the drive's first snap"),
        C("off_pts_vs_yards", "Yards rank minus finishing rank", "s1", 0, "Negative = moves the ball better than it converts field position into points"),
    ], "off_ppd", "Kneel-only drives and drives starting with 30 seconds or less in a half are excluded."))
    tables.append(table("drives_def", "Defensive drives", [
        C("def_drives", "Drives", "int", 0), C("def_ppd", "Points/drive allowed", "n2", -1), C("def_td_pd", "TD/drive", "pct", -1),
        C("def_fg_pd", "FG/drive", "pct", 0), C("def_punt_pd", "Punt/drive", "pct", 1), C("def_to_pd", "Takeaway/drive", "pct", 1),
        C("def_downs_pd", "Downs/drive", "pct", 1), C("def_start_own", "Opp. avg start (own yd line)", "n1", -1),
        C("def_plays_pd", "Plays/drive", "n1", -1), C("def_yards_pd", "Yards/drive", "n1", -1),
        C("def_rz_td_rate", "RZ TD% allowed", "pct", -1), C("def_ep_start", "Opp. EP at start", "n2", -1),
        C("def_pts_over_ep", "Points over start EP allowed", "s2", -1),
        C("def_fp_help", "Pts/drive rank minus field-position-adjusted rank", "s1", 0, "Negative = points-allowed rank looks better than it is after field position"),
        C("def_return_td", "Defensive TDs", "int", 1),
    ], "def_ppd", desc=False))
    tables.append(table("pass_off", "Passing offence", [
        C("off_dropbacks", "Dropbacks", "int", 0), C("off_epa_db", "EPA/dropback", "epa", 1), C("off_adj_epa_db", "Adj. EPA/db", "epa", 1),
        C("off_sr_db", "Success", "pct", 1), C("off_cpoe", "CPOE", "n1", 1, "Completion % over expected (nflfastR model)"),
        C("off_ypa", "Y/A", "n2", 1), C("off_nya", "NY/A", "n2", 1, "(Passing yards + sack yards) / (attempts + sacks)"),
        C("off_pass_fd", "1st downs/db", "pct", 1), C("off_expl_pass_rate", "20+ yd rate", "pct", 1), C("off_n_expl_pass", "20+ yd passes", "int", 1),
        C("off_int_rate", "INT rate", "pct", -1), C("int_worthy_rate", "INT-worthy rate", "pct", -1, "FTN charting: throws charted as interception-worthy"),
        C("off_sack_rate", "Sack rate", "pct", -1), C("off_pressure_rate", "Pressure allowed", "pct", -1, "PFR pressures / dropbacks, games with PFR data"),
        C("off_pressure_to_sack", "Sacks/pressure", "pct", -1), C("time_to_throw", "Time to throw (s)", "n2", 0, "Next Gen Stats, attempt-weighted"),
        C("off_epa_db_clean", "EPA, no hit/sack", "epa", 1), C("off_epa_db_hit", "EPA, hit or sacked", "epa", 1),
        C("off_early_db_epa", "Early-down EPA/db", "epa", 1), C("off_d3_db_epa", "3rd-down EPA/db", "epa", 1), C("off_rz_db_epa", "Red-zone EPA/db", "epa", 1),
        C("off_yacoe", "YAC over expected", "n2", 1), C("off_drop_rate", "Drop rate", "pct", -1, "FTN drops / catchable balls"),
        C("off_pa_rate", "Play-action rate", "pct", 0), C("off_epa_pa", "EPA on play action", "epa", 1), C("off_epa_oop", "EPA out of pocket", "epa", 1),
        C("off_deep_epa", "EPA, 20+ air yd", "epa", 1), C("cov", "Man/zone splits", "str", 0, "Not available in free data"),
    ], "off_adj_epa_db"))
    tables.append(table("pass_def", "Pass defence", [
        C("def_dropbacks", "Dropbacks faced", "int", 0), C("def_epa_db", "EPA/db allowed", "epa", -1), C("def_adj_epa_db", "Adj. EPA/db", "epa", -1),
        C("def_sr_db", "Success allowed", "pct", -1), C("def_cpoe", "CPOE allowed", "n1", -1), C("def_ypa", "Y/A allowed", "n2", -1),
        C("def_nya", "NY/A allowed", "n2", -1), C("def_pass_fd", "1st downs/db", "pct", -1),
        C("def_expl_pass_rate", "20+ yd rate", "pct", -1), C("def_n_expl_pass", "20+ yd allowed", "int", -1),
        C("def_pass_td", "Pass TD allowed", "int", -1), C("int_made", "INTs", "int", 1), C("def_int_worthy_rate", "INT-worthy throws forced", "pct", 1),
        C("def_sack_rate", "Sack rate", "pct", 1), C("def_pressure_rate", "Pressure rate", "pct", 1),
        C("def_deep_att", "Deep att. faced", "int", 0), C("def_deep_epa", "EPA allowed, 20+ air yd", "epa", -1), C("def_deep_comp", "Deep comp. allowed", "pct", -1),
        C("def_epa_pa", "EPA vs play action", "epa", -1), C("def_epa_screen", "EPA vs screens", "epa", -1),
        C("def_early_db_epa", "Early-down EPA/db", "epa", -1), C("def_d3_db_epa", "3rd-down EPA/db", "epa", -1), C("def_rz_db_epa", "Red-zone EPA/db", "epa", -1),
    ], "def_adj_epa_db", desc=False))
    tables.append(table("rush_off", "Rushing offence", [
        C("off_rushes", "Designed rushes", "int", 0), C("off_epa_rush", "EPA/rush", "epa", 1), C("off_adj_epa_rush", "Adj. EPA/rush", "epa", 1),
        C("off_sr_rush", "Success", "pct", 1), C("off_ypc", "Yards/carry", "n2", 1), C("off_rush_fd", "1st-down rate", "pct", 1),
        C("off_expl_run_rate", "10+ yd rate", "pct", 1), C("off_stuff_rate", "Stuff rate (<=0 yd)", "pct", -1),
        C("off_sy_conv", "Short-yardage conv.", "pct", 1, "3rd/4th and 2 or less, designed rushes"), C("off_sy_n", "SY att.", "int", 0),
        C("off_gl_td", "TD rate inside 3", "pct", 1), C("off_gl_n", "Att. inside 3", "int", 0),
        C("off_early_rush_epa", "Early-down EPA/rush", "epa", 1),
        C("off_rb_runs", "Non-QB runs", "int", 0), C("off_epa_rb_run", "EPA, non-QB runs", "epa", 1),
        C("off_qb_runs", "QB designed runs", "int", 0), C("off_epa_qb_run", "EPA, QB designed", "epa", 1),
        C("off_scrambles", "Scrambles", "int", 0), C("off_epa_scr", "EPA/scramble", "epa", 1),
        C("ybc_per_att", "Yards before contact", "n2", 1, "PFR: a blocking indicator"),
        C("yac_per_att", "Yards after contact", "n2", 1, "PFR: a ball-carrier indicator"),
        C("ryoe_per_att", "RYOE/att", "n2", 1, "Next Gen Stats rush yards over expected; qualifying rushers only"),
        C("rush_broken_tackles_pg", "Broken tackles/game", "n1", 1),
    ], "off_adj_epa_rush"))
    tables.append(table("rush_def", "Run defence", [
        C("def_rushes", "Designed rushes faced", "int", 0), C("def_epa_rush", "EPA/rush allowed", "epa", -1), C("def_adj_epa_rush", "Adj. EPA/rush", "epa", -1),
        C("def_sr_rush", "Success allowed", "pct", -1), C("def_ypc", "Yards/carry", "n2", -1), C("def_rush_fd", "1st-down rate", "pct", -1),
        C("def_expl_run_rate", "10+ yd allowed", "pct", -1), C("def_stuff_rate", "Stuff rate", "pct", 1),
        C("def_sy_conv", "Short-yardage allowed", "pct", -1), C("def_gl_td", "TD rate inside 3", "pct", -1),
        C("def_ybc_allowed", "Yds before contact allowed", "n2", -1), C("def_yac_allowed", "Yds after contact allowed", "n2", -1),
        C("def_missed_tackle_pct", "Missed tackle %", "pct", -1, "PFR, all plays"),
        C("def_qb_runs", "QB designed runs faced", "int", 0), C("def_qb_run_epa", "EPA vs QB designed runs", "epa", -1),
        C("def_scr_epa", "EPA vs scrambles", "epa", -1),
    ], "def_adj_epa_rush", desc=False))
    tables.append(table("expl", "Explosive plays", [
        C("off_expl_rate", "Off. explosive rate", "pct", 1), C("off_n_explosive", "Off. explosives", "int", 1),
        C("off_expl_epa_share", "Share of positive EPA on explosives", "pct", 0, "EPA gained on explosive plays / all positive EPA"), C("off_epa_nonexpl", "Off. EPA/play, non-explosive", "epa", 1),
        C("off_sr_nonexpl", "Off. success, non-explosive", "pct", 1),
        C("def_expl_rate", "Def. explosive rate", "pct", -1), C("def_n_explosive", "Def. explosives allowed", "int", -1),
        C("def_expl_td", "TDs on explosives allowed", "int", -1), C("def_epa_on_explosive", "EPA allowed on explosives", "n1", -1),
        C("def_epa_nonexpl", "Def. EPA/play, non-explosive", "epa", -1), C("def_sr_nonexpl", "Def. success, non-explosive", "pct", -1),
    ], "off_expl_rate", "Explosive = completed pass of 20+ yards, designed rush or scramble of 10+ yards (no-play penalties excluded)."))
    tables.append(table("pen_off", "Offensive discipline", [
        C("pen_off_n", "Off. penalties", "int", -1), C("pen_off_pg", "Per game", "n2", -1), C("pen_off_per100", "Per 100 plays", "n2", -1),
        C("pen_off_yds_pg", "Yards/game", "n1", -1), C("pen_off_presnap", "Pre-snap", "int", -1), C("pen_false_start", "False starts (all units)", "int", -1),
        C("pen_off_holding", "Off. holding", "int", -1), C("pen_off_d3", "On 3rd down", "int", -1), C("pen_off_rz", "In red zone", "int", -1),
        C("pen_negated_expl", "Negated explosives/TDs", "int", -1, "No-play offensive penalties that wiped out a 20+ yd pass, 10+ yd run or a TD (text-parsed)"),
        C("pen_negated_td", "Negated TDs", "int", -1),
        C("pen_off_np_epa_cost", "EPA cost (no-play)", "n1", -1, "EPA lost on plays where the penalty replaced the play; excludes the value of the negated play"),
        C("pen_drawn_def", "Def. penalties drawn", "int", 1), C("pen_auto_fd_drawn", "Auto 1st downs drawn", "int", 1),
    ], "pen_off_per100", desc=False))
    tables.append(table("pen_def", "Defensive discipline", [
        C("pen_def_n", "Def. penalties", "int", -1), C("pen_def_pg", "Per game", "n2", -1), C("pen_def_per100", "Per 100 plays", "n2", -1),
        C("pen_def_yds_pg", "Yards/game", "n1", -1), C("pen_def_presnap", "Pre-snap", "int", -1),
        C("pen_dpi", "DPI", "int", -1), C("pen_def_hold_contact", "Holding/illegal contact", "int", -1), C("pen_rtp", "Roughing the passer", "int", -1),
        C("pen_personal_foul", "Personal fouls (all units)", "int", -1), C("pen_auto_fd", "Auto 1st downs given", "int", -1),
        C("pen_def_d3", "On 3rd down", "int", -1), C("pen_def_rz", "In red zone", "int", -1),
        C("pen_negated_takeaway", "Negated takeaways", "int", -1),
        C("pen_def_np_epa_cost", "EPA conceded (no-play)", "n1", -1),
        C("pen_def_aggr_share", "Coverage/contact share", "pct", 0, "Share of defensive penalties that are DPI, holding, illegal contact or roughing the passer: fouls tied to aggressive coverage and rush"),
        C("pen_st_n", "Special-teams penalties", "int", -1), C("pen_declined", "Declined (not counted)", "int", 0),
    ], "pen_def_per100", desc=False))
    tables.append(table("turnovers", "Turnovers and sustainability", [
        C("giveaways", "Giveaways", "int", -1), C("takeaways", "Takeaways", "int", 1), C("to_margin", "Margin", "s1", 1),
        C("to_margin_pg", "Margin/game", "s2", 1), C("to_margin_pd", "Margin/drive", "s2", 1),
        C("int_thrown", "INT thrown", "int", -1), C("x_int_thrown", "Expected INT thrown", "n1", -1, "From FTN interception-worthy charting"),
        C("int_made", "INT made", "int", 1), C("x_int_made", "Expected INT made", "n1", 1),
        C("fum_lost", "Fumbles lost", "int", -1), C("fum_taken", "Fumbles taken", "int", 1),
        C("fum_rec_pct", "Fumble recovery %", "pct", 0, "All fumbles in its games, excluding out of bounds. Very small samples"),
        C("fumbles_total", "Fumbles in games", "int", 0),
        C("x_to_margin", "Expected margin", "s1", 1), C("to_luck", "Margin minus expected", "s1", 0, "Positive = more favourable than charted throws and fumble counts predict"),
        C("giveaway_rate", "Giveaways/play", "pct", -1), C("giveaways_opp_terr", "Giveaways in opp. territory", "int", -1),
        C("giveaways_rz", "Giveaways in red zone", "int", -1),
        C("pts_off_takeaways", "Points off takeaways", "int", 1), C("pts_after_giveaways", "Points after giveaways", "int", -1),
        C("to_epa_off", "Off. turnover EPA", "n1", 1), C("to_epa_def", "Def. turnover EPA gained", "n1", 1),
    ], "to_margin"))
    tables.append(table("luck", "Record versus performance", [
        C("record", "Record", "str", 0), C("pf", "PF", "int", 1), C("pa", "PA", "int", -1), C("pt_diff_pg", "Diff/game", "s1", 1),
        C("pyth_xw", "Pythagorean xW", "n2", 1, "Games x PF^2.37 / (PF^2.37 + PA^2.37)"),
        C("eff_xw", "EPA-based xW", "n2", 1, "Sum of single-game win probabilities from net EPA (logistic fitted on 2021-25 games)"),
        C("w_minus_pyth", "W - Pyth", "s2", 0), C("w_minus_eff", "W - EPA xW", "s2", 0),
        C("luck_index", "Luck index", "s2", 0, "Mean of the two differences; +/-0.75 sets the categories"),
        C("one_score", "One-score", "str", 0), C("three_pt", "3 pts or less", "str", 0), C("ot_rec", "OT", "str", 0),
        C("close_off_epa", "Close-late off. EPA", "epa", 1, "4th quarter/OT plays with the score within 8"),
        C("close_def_epa", "Close-late def. EPA", "epa", -1),
        C("to_luck", "Turnover margin minus expected", "s1", 0), C("fum_rec_pct", "Fumble rec. %", "pct", 0),
        C("fg_pts_oe", "FG pts over expected", "s1", 1), C("fg_pts_oe_against", "Opp. FG pts over expected", "s1", -1),
        C("d4_rec", "4th-down conv. (att.)", "str", 0), C("def_d4_conv", "4th-down conv. allowed", "pct", -1),
        C("off_pts_over_ep", "Off. pts over EP/drive", "s2", 1), C("def_pts_over_ep", "Def. pts over EP/drive", "s2", -1),
        C("sos_net", "Schedule strength", "epa", 0, "Average opponent net adjusted EPA/play; positive = tougher"),
        C("opp_net_beaten", "Quality of teams beaten", "epa", 1), C("opp_net_lost", "Quality of teams lost to", "epa", 1),
    ], "luck_index"))
    tables.append(table("press_def", "Defensive pressure and blitzing", [
        C("def_pressure_rate", "Pressure rate", "pct", 1, "PFR pressures / dropbacks"), C("def_sack_rate", "Sack rate", "pct", 1),
        C("def_hurry_rate", "Hurry rate", "pct", 1), C("def_qbhit_rate", "QB hit rate", "pct", 1),
        C("def_blitz_rate", "Blitz rate (FTN)", "pct", 0, "Share of charted dropbacks with 5+ rushers"),
        C("def_pfr_blitz_rate", "Blitz rate (PFR)", "pct", 0),
        C("def_hs_noblitz", "Hit/sack, 4 or fewer", "pct", 1, "Hit-or-sack rate (pbp) when rushing four or fewer"),
        C("def_hs_blitz", "Hit/sack, 5+", "pct", 1),
        C("def_sack_noblitz", "Sack rate, 4 or fewer", "pct", 1), C("def_sack_blitz", "Sack rate, 5+", "pct", 1),
        C("def_epa_noblitz", "EPA allowed, 4 or fewer", "epa", -1), C("def_epa_blitz", "EPA allowed, 5+", "epa", -1),
        C("def_d3_sack_rate", "3rd-down sack rate", "pct", 1), C("def_time_to_throw", "Opp. time to throw", "n2", 0),
        C("def_epa_oop", "EPA vs QB out of pocket", "epa", -1, "FTN: rollouts and scrambles from the pocket"),
        C("def_pfr_games", "Games with PFR data", "int", 0),
    ], "def_pressure_rate"))
    tables.append(table("press_off", "Pass protection", [
        C("off_pressure_rate", "Pressure allowed", "pct", -1), C("off_sack_rate", "Sack rate", "pct", -1),
        C("off_pressure_to_sack", "Sacks per pressure", "pct", -1), C("off_hit_or_sack_rate", "Hit-or-sack rate", "pct", -1),
        C("off_epa_db_clean", "EPA, no hit/sack", "epa", 1), C("off_epa_db_hit", "EPA, hit/sacked", "epa", 1),
        C("off_blitz_rate", "Blitzed rate", "pct", 0), C("off_epa_blitz", "EPA vs 5+", "epa", 1), C("off_epa_noblitz", "EPA vs 4 or fewer", "epa", 1),
        C("off_sack_blitz", "Sack rate vs 5+", "pct", -1), C("off_scr_rate", "Scramble rate", "pct", 0), C("off_epa_scr", "EPA/scramble", "epa", 1),
        C("time_to_throw", "Time to throw", "n2", 0),
        C("ol_starters_used", "OL starters used", "int", -1, "Distinct players among each game's top five OL by snaps"),
        C("ol_combos", "OL combinations", "int", -1), C("absent_OL", "OL regulars out", "int", -1),
        C("off_pfr_games", "Games with PFR data", "int", 0),
    ], "off_pressure_rate", desc=False))
    tables.append(table("sos", "Strength of schedule", [
        C("record", "Record", "str", 0), C("sos_net", "Opp. net adj. EPA/play", "epa", 0, "Positive = tougher schedule"),
        C("sos_off", "Defences faced (adj. EPA allowed effect)", "epa", 0, "Positive = faced defences that allow more (easier for the offence)"),
        C("sos_def", "Offences faced (adj. EPA effect)", "epa", 0, "Positive = faced stronger offences"),
        C("opp_record_pct", "Opp. win %", "pct", 0, "Context only: early records are unstable"),
        C("vs_strong", "W/G vs top third", "str", 0), C("net_vs_strong", "Net EPA vs top third", "epa", 1),
        C("net_vs_average", "vs middle third", "epa", 1), C("net_vs_weak", "vs bottom third", "epa", 1),
        C("net_home", "Net EPA home", "epa", 1), C("net_away", "Net EPA away/neutral", "epa", 1),
        C("vs_winning", "W/G vs winning teams", "str", 0),
        C("off_adj_shift", "Off. rank change after adj.", "s1", 0), C("def_adj_shift", "Def. rank change after adj.", "s1", 0),
    ], "sos_net"))
    tables.append(table("coach", "Game management and tendencies", [
        C("fd_decisions", "4th-down decisions", "int", 0, "4th downs with win probability 20-80% and more than 2:00 left in the half"),
        C("fd_go_rate", "Go rate", "pct", 0), C("fd_agree_rate", "Agrees with EP reference", "pct", 1),
        C("fd_clear_go_n", "Clear go spots", "int", 0, "Reference value of going exceeds the best kick by 0.5 EP or more"),
        C("fd_clear_go_rate", "Went for it there", "pct", 1), C("fd_ep_lost_per", "EP lost per decision", "n2", -1),
        C("pace_sec", "Sec between snaps", "n1", 0, "Median, within drives, win probability 20-80%, quarters 1-3"),
        C("neutral_early_pass_rate", "Neutral early-down pass rate", "pct", 0), C("neutral_proe", "Pass rate over expected", "s1", 0),
        C("net_h2_minus_h1", "2nd-half minus 1st-half net EPA", "epa", 1),
        C("off_epa_leading", "Off. EPA leading by 9+", "epa", 1), C("off_epa_close", "within 8", "epa", 1), C("off_epa_trailing", "trailing by 9+", "epa", 1),
        C("eoh_drives", "End-of-half drives", "int", 0), C("eoh_ppd", "End-of-half pts/drive", "n2", 1, "Drives starting in the last 2:00 of the first half (31 s or more left)"),
        C("bye_week", "Bye week", "int", 0), C("net_after_bye", "Net EPA after bye (1 game)", "epa", 1),
        C("one_score", "One-score record", "str", 0),
    ], "fd_agree_rate"))
    tables.append(table("st", "Special teams", [
        C("st_epa_pg", "ST EPA/game", "s2", 1), C("st_field_goal_epa_pg", "FG EPA/g", "s2", 1), C("st_extra_point_epa_pg", "XP EPA/g", "s2", 1),
        C("st_punt_epa_pg", "Punt EPA/g", "s2", 1), C("st_kickoff_epa_pg", "Kickoff EPA/g", "s2", 1),
        C("fg_att", "FG att.", "int", 0), C("fg_pct", "FG%", "pct", 1), C("fg_u40", "FG <40", "str", 0), C("fg_40_49", "FG 40-49", "str", 0), C("fg_50p", "FG 50+", "str", 0),
        C("fg_pts_oe", "FG pts over expected", "s1", 1), C("xp_pct", "XP%", "pct", 1),
        C("punt_gross", "Punt gross", "n1", 1), C("punt_net", "Punt net", "n1", 1), C("punt_in20", "Inside 20", "pct", 1),
        C("opp_punt_net", "Opp. punt net", "n1", -1), C("punt_ret_avg", "Punt return avg", "n1", 1),
        C("ko_tb_rate", "Kickoff touchback %", "pct", 0), C("ko_ret_avg", "Kick return avg", "n1", 1), C("ko_ret_avg_allowed", "Kick return allowed", "n1", -1),
        C("start_after_ko", "Start after kickoff", "n1", 1), C("opp_start_after_ko", "Opp. start after kickoff", "n1", -1),
        C("start_after_punt", "Start after punt", "n1", 1),
        C("st_td", "Return TDs", "int", 1), C("st_td_allowed", "Return TDs allowed", "int", -1),
        C("blocks_made", "Kicks blocked", "int", 1), C("blocks_allowed", "Kicks blocked against", "int", -1),
        C("pen_st_n", "ST penalties", "int", -1), C("pen_st_yds", "ST penalty yds", "int", -1),
    ], "st_epa_pg"))
    tables.append(table("depth", "Availability and depth", [
        C("qb_starts", "QB starts", "str", 0), C("qb_changed_since_prior", "New primary QB vs 2025", "str", 0),
        C("regulars", "Regulars", "int", 0, "Players averaging 50%+ of offensive or defensive snaps in 2+ games"),
        C("absent_n", "Regulars out (confirmed)", "int", -1, "Reserve list in the week 8 roster, or Out/Doubtful in the team's latest report"),
        C("absent_snap_weighted", "Snap-weighted absences", "n2", -1, "Sum of absent regulars' snap shares; 1.0 = one full-time starter"),
        C("absent_QB", "QB", "int", -1), C("absent_OL", "OL", "int", -1), C("absent_WR/TE", "WR/TE", "int", -1), C("absent_RB", "RB", "int", -1),
        C("absent_DL/EDGE", "DL/EDGE", "int", -1), C("absent_LB", "LB", "int", -1), C("absent_DB", "DB", "int", -1),
        C("questionable_n", "Questionable", "int", -1), C("unconfirmed_n", "Missed last game, no designation", "int", -1),
        C("ol_starters_used", "OL starters used", "int", -1), C("ol_w1_starters_in_last", "Week-1 OL starters in latest game", "int", 1),
        C("top_rb_carry_share", "Top RB carry share", "pct", 0), C("def_top11_snap_share", "Top-11 share of def. snaps", "pct", 0),
        C("def_players_25pct", "Defenders with 25%+ snaps in a game", "int", 0),
    ], "absent_snap_weighted", desc=True))
    # B: consolidated comparison, consistent team order
    B = [
        ("Record and ratings", [C("record", "Record", "str", 0), C("rating_pg", "Overall rating", "s1", 1), C("stab_rating_pg", "With 2025 prior", "s1", 1),
                                C("off_composite", "Off. composite", "s2", 1), C("def_composite", "Def. composite", "s2", 1), C("st_epa_pg", "ST EPA/g", "s2", 1),
                                C("off_dvoa", "Off. DVOA", "str", 0, "Not available"), C("def_dvoa", "Def. DVOA", "str", 0, "Not available")]),
        ("Efficiency", [C("off_epa_play", "Off. EPA/play", "epa", 1), C("off_adj_epa", "Off. adj.", "epa", 1), C("def_epa_play", "Def. EPA/play", "epa", -1),
                        C("def_adj_epa", "Def. adj.", "epa", -1), C("off_sr", "Off. SR", "pct", 1), C("def_sr", "Def. SR", "pct", -1),
                        C("off_adj_epa_db", "Pass O", "epa", 1), C("off_adj_epa_rush", "Rush O", "epa", 1), C("def_adj_epa_db", "Pass D", "epa", -1), C("def_adj_epa_rush", "Run D", "epa", -1)]),
        ("Scoring and explosives", [C("off_ppd", "Pts/drive", "n2", 1), C("def_ppd", "Pts/drive allowed", "n2", -1), C("off_expl_rate", "Explosive rate", "pct", 1),
                                    C("def_expl_rate", "Explosive allowed", "pct", -1), C("to_margin", "TO margin", "s1", 1), C("to_luck", "TO margin minus expected", "s1", 0)]),
        ("Discipline and pressure", [C("pen_off_n", "Off. pen.", "int", -1), C("pen_off_yds", "Off. pen. yds", "int", -1), C("pen_def_n", "Def. pen.", "int", -1), C("pen_def_yds", "Def. pen. yds", "int", -1),
                                     C("def_blitz_rate", "Blitz rate", "pct", 0), C("def_pressure_rate", "Pressure rate", "pct", 1), C("def_sack_rate", "Sack rate", "pct", 1),
                                     C("off_pressure_rate", "Pressure allowed", "pct", -1), C("off_sack_rate", "Sack rate allowed", "pct", -1)]),
        ("Schedule and luck", [C("one_score", "One-score", "str", 0), C("sos_net", "Schedule strength", "epa", 0), C("pyth_xw", "Pyth. xW", "n2", 1),
                               C("eff_xw", "EPA xW", "n2", 1), C("w_minus_eff", "W - EPA xW", "s2", 0), C("rating_rank", "Combined rank", "int", -1),
                               C("off_adj_rank", "Off. rank", "int", -1), C("def_adj_rank", "Def. rank", "int", -1)]),
    ]
    for i, (name, cols) in enumerate(B):
        tables.append(table(f"B{i}", name, cols, "order", "", order=order))

    # ---------------- lists (C, D, E, F)
    over = T[T.category == "over"].sort_values("luck_index", ascending=False)
    under = T[T.category == "under"].sort_values("luck_index")
    def evidence(t):
        r = T.loc[t]
        return [f"Record {r.record}; Pythagorean {r.pyth_xw:.1f} and EPA-based {r.eff_xw:.1f} expected wins",
                f"One-score games {r.one_score}; 3 points or fewer {r.three_pt}",
                f"Turnover margin {int(r.to_margin):+d} vs expected {r.x_to_margin:+.1f}; fumble recovery {fmt(r.fum_rec_pct, 'pct')} of {int(r.fumbles_total)}",
                f"Combined rating {ordinal(r.rating_rank)}; record {ordinal(r.winpct_rank)}; schedule {r.sos_net:+.3f}",
                f"FG points over expected {r.fg_pts_oe:+.1f}; special teams {r.st_epa_pg:+.2f} EPA/game"]
    cats = {"over": [{"team": t, "luck": float(T.luck_index[t]), "ev": evidence(t)} for t in over.index],
            "under": [{"team": t, "luck": float(T.luck_index[t]), "ev": evidence(t)} for t in under.index],
            "supported": list(T[T.category == "supported"].sort_values("rating_pg", ascending=False).index)}
    bal_cols = [("off_adj_epa_db", 1), ("off_adj_epa_rush", 1), ("def_adj_epa_db", -1), ("def_adj_epa_rush", -1)]
    R4 = pd.concat([rank(T[c], d == 1) for c, d in bal_cols], axis=1)
    T["worst_unit_rank"] = R4.max(axis=1)
    T["best_unit_rank"] = R4.min(axis=1)
    T["balance"] = np.where(T.worst_unit_rank <= 20, "well-rounded",
                            np.where((T.best_unit_rank <= 5) & (T.worst_unit_rank >= 23), "elite in one area, exposed elsewhere", "mixed"))
    sus = T.sort_values("stab_rating_pg", ascending=False)
    D = [{"team": t, "stab": float(T.stab_rating_pg[t]), "rating": float(T.rating_pg[t]), "balance": T.balance[t],
          "worst": int(T.worst_unit_rank[t]), "absent": float(T.absent_snap_weighted[t]),
          "qbchg": bool(T.qb_changed_since_prior[t] in (True, "True")), "qbs": int(T.qb_starters_n[t])} for t in sus.index[:12]]
    # E: exploitable = count of bottom-6 ranks among key units
    keys = [("Pass defence", "def_adj_epa_db", -1), ("Run defence", "def_adj_epa_rush", -1), ("Pass protection", "off_pressure_rate", -1),
            ("Explosive prevention", "def_expl_rate", -1), ("Ball security", "giveaway_rate", -1), ("Passing offence", "off_adj_epa_db", 1),
            ("Rushing offence", "off_adj_epa_rush", 1), ("Red-zone defence", "def_rz_td_rate", -1), ("Third/fourth-down defence", "def_late_conv", -1)]
    E = []
    for t in T.index:
        weak = []
        for name, col, dd in keys:
            rk = int(rank(T[col], dd == 1)[t])
            if rk >= 27:
                weak.append({"unit": name, "rank": rk, "col": col})
        if weak:
            E.append({"team": t, "weak": weak, "n": len(weak), "rating": float(T.rating_pg[t])})
    E = sorted(E, key=lambda e: (-e["n"], e["rating"]))[:10]
    for e in E:
        for w in e["weak"]:
            w["value"] = fmt(T.loc[e["team"], w["col"]], "epa" if "epa" in w["col"] else "pct")
    def top(col, n=5, hb=True):
        return list(T[col].sort_values(ascending=not hb).index[:n])
    F = {
        "overall": top("rating_pg"), "offence": top("off_composite"), "defence": top("def_composite"),
        "underrated": list(T.sort_values("record_vs_rating").index[:5]),
        "overrated": list(T.sort_values("record_vs_rating", ascending=False).index[:5]),
        "pos_reg": [c["team"] for c in cats["under"]][:5], "neg_reg": [c["team"] for c in cats["over"]][:5],
        "injury": list(T.sort_values("absent_snap_weighted", ascending=False).index[:5]),
        "to_dep": list(T.sort_values("to_luck", ascending=False).index[:5]),
        "expl_dep": list(T.sort_values("off_expl_epa_share", ascending=False).index[:5]),
        "easiest": list(T.sort_values("sos_net").index[:5]), "hardest": list(T.sort_values("sos_net", ascending=False).index[:5]),
    }
    # disagreements
    dis = {
        "adj_up": [(t, int(T.off_adj_shift[t])) for t in T.sort_values("off_adj_shift", ascending=False).index[:5] if T.off_adj_shift[t] >= 4],
        "adj_down": [(t, int(T.off_adj_shift[t])) for t in T.sort_values("off_adj_shift").index[:5] if T.off_adj_shift[t] <= -4],
        "def_up": [(t, int(T.def_adj_shift[t])) for t in T.sort_values("def_adj_shift", ascending=False).index[:5] if T.def_adj_shift[t] >= 4],
        "def_down": [(t, int(T.def_adj_shift[t])) for t in T.sort_values("def_adj_shift").index[:5] if T.def_adj_shift[t] <= -4],
        "rec_better": [(t, int(T.record_vs_rating[t])) for t in T.sort_values("record_vs_rating", ascending=False).index[:6] if T.record_vs_rating[t] >= 6],
        "rec_worse": [(t, int(T.record_vs_rating[t])) for t in T.sort_values("record_vs_rating").index[:6] if T.record_vs_rating[t] <= -6],
        "move_not_finish": [t for t in T.index if rank(T.off_yards_pd)[t] <= 12 and rank(T.off_pts_over_ep)[t] >= 18],
        "def_fp": [t for t in T.index if T.def_fp_help[t] <= -6],
        "expl_dependent": [t for t in T.index if rank(T.off_expl_epa_share)[t] <= 6 and rank(T.off_sr)[t] >= 17],
        "efficient_steady": [t for t in T.index if rank(T.off_sr)[t] <= 8 and rank(T.off_expl_epa_share)[t] >= 20],
        "bend_break": [t for t in T.index if rank(T.def_sr_nonexpl, False)[t] <= 10 and rank(T.def_expl_rate, False)[t] >= 22],
        "run_block": [t for t in T.index if rank(T.ybc_per_att)[t] <= 8],
        "run_talent": [t for t in T.index if rank(T.yac_per_att)[t] <= 8 and rank(T.ybc_per_att)[t] >= 17],
        "pressure4": list(T.sort_values("def_hs_noblitz", ascending=False).index[:6]),
        "protect": list(T.sort_values("off_pressure_rate").index[:6]),
        "blitz_vuln": [t for t in T.index if rank(T.off_epa_blitz)[t] >= 25],
    }

    teams_js = []
    for t in T.index:
        r = T.loc[t]
        rec = {k: (None if (isinstance(v, float) and math.isnan(v)) else (v.item() if hasattr(v, "item") else v)) for k, v in r.items()}
        rec["team"] = t
        rec["dvoa"] = rec["off_dvoa"] = rec["def_dvoa"] = rec["cov"] = "n/a"
        teams_js.append(rec)
    qcols = ["name_full", "team", "teams", "games", "dropbacks", "epa_db", "adj_epa_db", "sr", "cpoe", "ypa", "adot", "sack_rate", "int_rate",
             "int_worthy_rate", "pressure_rate", "p2s", "epa_clean", "epa_hit_sack", "epa_vs_blitz", "epa_no_blitz", "blitzed_rate",
             "scr_rate", "epa_scr", "designed_runs", "epa_designed_run", "fd_td_rate", "epa_early", "epa_d3", "epa_rz", "game_sd",
             "time_to_throw", "yacoe", "drop_rate", "team_pressure_allowed", "qb_composite", "team_db_share", "latest_starter", "qualified"]
    qbs = Q[qcols].replace({np.nan: None}).to_dict("records")
    absn = A.replace({np.nan: None}).to_dict("records")

    data = {"teams": teams_js, "qbs": qbs, "absences": absn, "tables": tables, "meta": meta, "profiles": profiles,
            "mismatch": mm, "cats": cats, "D": D, "E": E, "F": F, "dis": dis, "notes": notes, "order": order,
            "names": T.team_name.to_dict()}
    page = TEMPLATE.replace("/*DATA*/", json.dumps(data, default=str).replace("</", "<\\/"))
    page = page.replace("{{METHOD}}", method_html(meta, T))
    (d / "report.html").write_text(page, encoding="utf-8")
    print("wrote", d / "report.html", f"{len(page) / 1e6:.2f} MB")


def method_html(meta, T):
    co, cd = meta["composite_off"], meta["composite_def"]
    po, pdf = meta["prior_off"], meta["prior_def"]
    lg = meta["league"]
    src = "".join(f"<tr><td>{esc(s['url'].split('/download/')[1])}</td><td>{esc(s.get('http_last_modified') or 'n/a')}</td>"
                  f"<td>{esc(s['retrieved_utc'])}</td><td class='mono'>{esc(s['sha256'][:12])}</td></tr>"
                  for s in {s["url"]: s for s in meta["sources"]}.values())
    qc = "".join(f"<li>{esc(q)}</li>" for q in meta["qc"])
    w26 = T.off_w2026.mean()
    return f"""
<p>Window: {meta['season']} regular season, weeks 1-{meta['through_week']} ({meta['games']} games, {meta['plays']:,} scrimmage plays,
{meta['drives']:,} drives). Generated {esc(meta['generated_utc'])}. Historical seasons {meta['history_seasons'][0]}-{meta['history_seasons'][-1]}
are used only for reference models and weights, never as 2026 evidence.</p>
<h3>Plays and filters</h3>
<ul>
<li><b>Scrimmage play</b>: nflfastR <code>pass</code> or <code>rush</code> flag, EPA present, down present (two-point tries excluded), kneel-downs and spikes excluded. Plays nullified by penalty that nflfastR tags as a pass or rush are included, as in nflfastR's standard team summaries.</li>
<li><b>Dropback</b> = pass attempts, sacks and scrambles. <b>Designed rush</b> = nflfastR <code>rush</code> (scrambles excluded). QB designed runs are designed rushes by players with 5+ dropbacks; they are reported separately from scrambles.</li>
<li><b>Success</b> = EPA &gt; 0. <b>Early downs</b> = 1st and 2nd. <b>Late downs</b> = third- and fourth-down conversion flags. <b>Red zone</b> = inside the opponent's 20.</li>
<li><b>Explosive</b>: completed or attempted pass (not a scramble or sack) gaining {20}+ yards; designed rush or scramble gaining 10+ yards; live plays only.</li>
<li><b>WP 10-90%</b> columns drop plays when either side's win probability is outside 10-90%, as a garbage-time check.</li>
<li><b>Hit-or-sack rate</b> uses the pbp <code>qb_hit</code> and <code>sack</code> flags. It is a proxy, not pressure: free data has no play-level pressure.</li>
</ul>
<h3>Opponent adjustment</h3>
<p>For each metric (EPA/play, success, EPA/dropback, EPA/designed rush, early-down EPA) a play-level least-squares fit
<code>y = intercept + home + offence(team) + defence(team)</code> with sum-to-zero team effects and no shrinkage. The adjusted value is the league
mean plus the team effect, so a raw and an adjusted value sit on the same scale. Schedule strength is the play-weighted average opponent effect.
The home coefficient this season is {meta['home_coef']:+.3f} EPA/play. Quarterback adjustment subtracts the average dropback-defence effect of the
defences each passer faced.</p>
<h3>Composite rankings and weights</h3>
<p>EPA/play, success rate and points per drive measure overlapping things, so the composites are weighted by how well each one, measured over
weeks 1-{meta['through_week']}, predicted a team's opponent-adjusted EPA/play over the rest of the season in {meta['history_seasons'][0]}-{meta['history_seasons'][-1]}
(non-negative least squares on within-season z-scores, {co['n']} team-seasons). The regression handles their correlation, so nothing is double-counted.</p>
<table class="mini"><tr><th></th><th>adj. EPA/play</th><th>adj. success</th><th>pts/drive</th><th>R² (combined)</th></tr>
<tr><td>Offence weights</td><td>{co['weights']['o_epa']:.0%}</td><td>{co['weights']['o_sr']:.0%}</td><td>{co['weights']['o_ppd']:.0%}</td><td>{co['r2']:.2f}</td></tr>
<tr><td>Offence single-metric R²</td><td>{co['single_r2']['o_epa']:.2f}</td><td>{co['single_r2']['o_sr']:.2f}</td><td>{co['single_r2']['o_ppd']:.2f}</td><td></td></tr>
<tr><td>Defence weights</td><td>{cd['weights']['d_epa']:.0%}</td><td>{cd['weights']['d_sr']:.0%}</td><td>{cd['weights']['d_ppd']:.0%}</td><td>{cd['r2']:.2f}</td></tr>
<tr><td>Defence single-metric R²</td><td>{cd['single_r2']['d_epa']:.2f}</td><td>{cd['single_r2']['d_sr']:.2f}</td><td>{cd['single_r2']['d_ppd']:.2f}</td><td></td></tr></table>
<p>Seven-week defensive numbers explain only about a tenth of rest-of-season defensive performance (R² {cd['r2']:.2f}), against about a third for offence
({co['r2']:.2f}). Read defensive rankings with more caution.</p>
<p><b>Overall team rating</b> = (adj. offensive EPA/play − league mean) × {meta['plays_per_game']:.1f} plays + (league mean − adj. defensive EPA/play) × {meta['plays_per_game']:.1f}
+ special-teams EPA per game, in points per game. EPA is in points, so this needs no arbitrary weights. Special teams is kept separate everywhere else.
<b>Situational</b> = equal-weight z-scores of late-down conversion and red-zone TD rate (two distinct situations). <b>Passing, rushing, pass D, run D</b>
rank on one adjusted metric each.</p>
<h3>Prior-season stabilisation</h3>
<p>The "with 2025 prior" rating shrinks each 2026 adjusted EPA/play towards a prior of league mean + b × (team's 2025 adjusted value − 2025 mean). Year-to-year slopes
from {meta['history_seasons'][0]}-{meta['history_seasons'][-1]}: offence b = {po['slope']:.2f}, defence b = {pdf['slope']:.2f}. The weight on 2026 is τ² / (τ² + σ²/n), with τ² the
variance of true change between seasons (offence {po['tau2']:.4f}, defence {pdf['tau2']:.4f}) and σ²/n the sampling variance of this season's estimate. On average the
2026 data gets {w26:.0%} of the weight on offence and {T.def_w2026.mean():.0%} on defence, and the share rises each week. Teams with a new primary quarterback
are flagged, because last season's offence then says less.</p>
<h3>Scoring and drives</h3>
<p>Drives are nflfastR <code>fixed_drive</code>. Points per drive are the offence's score change from the start of the drive to the start of the next drive, so
extra points count and defensive or return scores do not. Every game's drive points reconcile to its final score. Points over start EP = drive points minus nflfastR's
expected points at the first snap. That measures finishing relative to field position (it is a next-score expectation, so it is approximate).</p>
<h3>Expected wins, luck and turnovers</h3>
<ul><li>Pythagorean expected wins use exponent {2.37}.</li>
<li>EPA-based expected wins: P(win) = logistic({meta['epa_win_coef']:.3f} × game net EPA), fitted on {meta['history_seasons'][0]}-{meta['history_seasons'][-1]} games, summed over games played.</li>
<li>Luck index = mean of (wins − Pythagorean xW) and (wins − EPA xW). At +0.75 or more a team is a potential overperformer, at −0.75 or less a potential underperformer. With 6-7 games the sampling error of either difference is about one win.</li>
<li>Expected interceptions: each charted attempt gets the league rate for its FTN interception-worthy status (worthy {lg['p_int_worthy']:.1%}, not worthy {lg['p_int_not']:.2%}).
Expected fumbles lost: own fumbles × {meta['fum_lost_rate']:.3f}, the 2021-25 loss rate.</li></ul>
<h3>Fourth downs</h3>
<p>A transparent reference, not nfl4th. For 4th downs with win probability 20-80% and more than two minutes left in the half, each option (go, punt, field goal) is valued at the average
expected points after that choice in the same distance × field-position bucket in 2021-25 (buckets with 20+ cases). Selection bias (teams go when conditions favour it) and ignoring the clock limit it.</p>
<h3>Penalties</h3>
<p>nflfastR records one penalty per play, so no play is counted twice. Declined and offsetting penalties are excluded from the counts. Phase: special teams if the play was a
kick, otherwise offence or defence by the penalised team. The EPA cost counts no-play penalties only; for accepted penalties on live plays the penalty and the play cannot be separated.
Negated explosive plays and TDs are parsed from the play text.</p>
<h3>Not available, and proxies used</h3>
<ul>
<li><b>DVOA</b>: FTN's proprietary metric. It is not in nflverse and was not used, so every DVOA column reads n/a. The closest computed analogues here are opponent-adjusted EPA and success rate. They are not DVOA.</li>
<li><b>Coverage (man/zone), time to pressure, pressure by play</b>: not in free data. PFR pressures are game-level, so pressure-when-blitzing uses the hit-or-sack proxy.</li>
<li><b>Pressure coverage</b>: PFR advanced stats are available for {T.off_pfr_games.sum()/2:.0f} of {meta['games']} games; pressure rates use only those games.</li>
<li><b>FTN charting</b> is missing one game (week 7 DAL at PHI), so blitz and expected-INT figures for those two teams have one fewer game.</li>
<li><b>Participation data</b> (players on field per play) is not published for 2026, so personnel groupings and on/off splits are not possible. Availability uses snap counts, weekly rosters and injury reports.</li>
<li><b>Week 8 injury reports</b> are not out yet. Statuses come from each team's latest report (week 7, or week 6 after a bye) and the week 8 roster list.</li>
<li><b>Timeout use</b> is not scored: there is no defensible free benchmark. <b>Bye effects</b> rest on one game per team.</li>
<li><b>Blitz</b>: FTN's blitz is five or more rushers, so "blitz" and "5+ rushers" are the same split here.</li></ul>
<h3>Quality checks</h3><ul>{qc}</ul>
<h3>Sources</h3>
<div class="table-wrap"><table class="mini"><tr><th>nflverse release file</th><th>Last modified (server)</th><th>Retrieved (UTC)</th><th>sha256</th></tr>{src}</table></div>
<h3>Reproduce</h3>
<pre>.venv\\Scripts\\python.exe scripts\\team_analytics\\compute.py --season {meta['season']} --through-week {meta['through_week']}
.venv\\Scripts\\python.exe scripts\\team_analytics\\build_html.py --dir reports\\team_analytics\\{meta['season']}_week{meta['through_week']+1:02d}</pre>
<p>Outputs: team_metrics.csv (every team metric), quarterbacks.csv, team_games.csv, drives.csv, penalty_types.csv, absences.csv, offensive_line.csv, bundle_meta.json.
No market data is read: spread, total and price columns are dropped on load.</p>
"""


TEMPLATE = (Path(__file__).with_name("template.html")).read_text(encoding="utf-8") if (Path(__file__).with_name("template.html")).exists() else ""

if __name__ == "__main__":
    main()
