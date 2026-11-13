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
import re
from pathlib import Path

import numpy as np
import pandas as pd

import game_weather  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
         11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen", 15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen"}
WK = {"thru": 8, "word": "eight"}            # set from bundle_meta.json in main()

# Small samples: below the minimum a value is shown muted with its n, gets no rank or colour, and is not used in
# mismatch findings. key -> (sample-size column, minimum)
SAMPLE_MIN = {
    "off_g2g_td_rate": ("off_g2g_trips", 5), "def_g2g_td_rate": ("def_g2g_trips", 5),
    "eoh_ppd": ("eoh_drives", 5),
    "off_epa_leading": ("off_plays_leading", 30), "off_epa_trailing": ("off_plays_trailing", 30),
    "def_epa_after_to": ("def_n_after_to", 15), "def_epa_after_three_out": ("def_n_after_three_out", 15),
    "fd_go_rate": ("fd_decisions", 10), "fd_agree_rate": ("fd_decisions", 10), "fd_ep_lost_per": ("fd_decisions", 10),
    "fd_clear_go_rate": ("fd_clear_go_n", 5),
    "off_epa_scr": ("off_scrambles", 8), "def_scr_epa": ("def_scrambles", 8),
    "fg_pct": ("fg_att", 8), "fg_pts_oe": ("fg_att", 8),
    "off_deep_epa": ("off_deep_att", 15), "off_deep_comp": ("off_deep_att", 15),
    "def_deep_epa": ("def_deep_att", 15), "def_deep_comp": ("def_deep_att", 15),
    "def_qb_run_epa": ("def_qb_runs", 8), "off_epa_qb_run": ("off_qb_runs", 8),
}
PLAYER_MIN = {"epa_tgt": ("targets", 10), "ypt": ("targets", 10), "sr_tgt": ("targets", 10), "catch_rate": ("targets", 10),
              "adot": ("targets", 10), "yac_pr": ("rec", 10), "yacoe_pr": ("rec", 10), "sep": ("targets", 10),
              "epa_car": ("carries", 10), "ypc": ("carries", 10), "sr_car": ("carries", 10), "stuff": ("carries", 10),
              "expl_run": ("carries", 10), "ryoe_att": ("carries", 10), "ybc_att": ("carries", 10), "yaco_att": ("carries", 10),
              "brk_per_car": ("carries", 10)}
# player ranking tables rank on usage only: in 2021-25 only about 3% of a player's per-carry or per-target efficiency gap at 10
# opportunities, and about 20% at 80, lasted (backtest_player_sample.py); efficiency columns carry a reliability badge instead
PLAYER_USAGE_KEYS = {"games", "snap_pct", "carries", "car_share", "car_share_l3", "rz_car", "gl_car", "targets", "tgt_share",
                     "tgt_share_l3", "air_share", "rz_tgt", "rz_tgt_share"}


def player_col_rule(c: dict) -> dict:
    """Usage columns keep their rank; every other numeric column is context (no rank or colour). Efficiency columns get the
    badge of the sample they rest on."""
    if c["k"] in PLAYER_USAGE_KEYS or c["f"] == "str":
        return c
    c["d"] = 0
    if c["k"] in PLAYER_MIN:
        c["b"] = "rel_car" if PLAYER_MIN[c["k"]][0] == "carries" else "rel_tgt"
    return c


SAMPLE_LABEL = {"targets": "targets", "carries": "carries", "rec": "catches", "db_blitz": "blitzed dropbacks", "db_noblitz": "dropbacks vs 4 or fewer",
                "db_hit": "dropbacks hit or sacked", "scrambles": "scrambles","off_g2g_trips": "goal-to-go trips", "def_g2g_trips": "goal-to-go trips", "eoh_drives": "end-of-half drives",
                "off_plays_leading": "plays leading by 9+", "off_plays_trailing": "plays trailing by 9+",
                "def_n_after_to": "plays after a turnover", "def_n_after_three_out": "plays after a three-and-out",
                "fd_decisions": "4th-down decisions", "fd_clear_go_n": "clear go spots", "off_scrambles": "scrambles",
                "def_scrambles": "scrambles faced", "fg_att": "FG attempts", "off_deep_att": "deep attempts",
                "def_deep_att": "deep attempts faced", "def_qb_runs": "QB designed runs faced", "off_qb_runs": "QB designed runs"}
# sample size shown in the tooltip of other rate columns: (prefix of the key, n column, what it counts)
N_RULES = [
    ("rz_td_rate", "rz_trips", "red-zone trips"), ("g2g", "g2g_trips", "goal-to-go trips"), ("d3_conv", "d3_n", "third downs"),
    ("d4_conv", "d4_n", "fourth downs"), ("sy_conv", "sy_n", "short-yardage runs"), ("gl_td", "gl_n", "runs inside the 3"),
    ("_db", "dropbacks", "dropbacks"), ("pass", "attempts", "attempts"), ("sack", "dropbacks", "dropbacks"), ("pressure", "dropbacks", "dropbacks"),
    ("int_", "attempts", "attempts"), ("rush", "rushes", "designed rushes"), ("ypc", "rushes", "designed rushes"), ("stuff", "rushes", "designed rushes"),
    ("expl_run", "rushes", "designed rushes"), ("pd", "drives", "drives"), ("ppd", "drives", "drives"), ("epa", "plays", "plays"), ("sr", "plays", "plays"),
    ("expl", "plays", "plays"),
]


def n_info(k, T):
    """(n column, label) for the tooltip of column k, or None."""
    if k in SAMPLE_MIN:
        c = SAMPLE_MIN[k][0]
        return c, SAMPLE_LABEL.get(c, c)
    side = k[:4] if k.startswith(("off_", "def_")) else None
    if not side:
        return None
    for pat, col, lab in N_RULES:
        if pat in k[4:] and f"{side}{col}" in T:
            return f"{side}{col}", lab
    return None


DEF_WORDS = [("adj_", "opponent-adjusted "), ("epa_play", "EPA per play"), ("epa_db", "EPA per dropback"), ("epa_rush", "EPA per designed rush"),
             ("sr_db", "success rate on dropbacks"), ("sr_rush", "success rate on designed rushes"), ("sr", "success rate (EPA > 0)"),
             ("ypa", "passing yards per attempt"), ("ypc", "yards per carry"), ("ppd", "points per drive"), ("rate", "rate"), ("pct", "percentage"),
             ("_pg", " per game"), ("epa", "expected points added")]


def definition(c):
    """A short definition for a column header that has no hand-written tooltip."""
    k, lab = c["k"], c["l"]
    who = "Offence: " if k.startswith("off_") else ("Defence (allowed or forced): " if k.startswith("def_") else "")
    unit = {"epa": "EPA, expected points added (points)", "pct": "percentage", "n1": "", "n2": "", "s1": "", "s2": "", "int": "count", "str": ""}.get(c["f"], "")
    return f"{who}{lab}" + (f"; {unit}" if unit else "") + "."

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


def table(tid, title, cols, sort, note="", desc=None, rows="teams", order=None, first=None):
    return {"id": tid, "title": title, "cols": cols, "sort": sort, "note": note, "rows": rows,
            "desc": desc, "order": order, "first": first}


YARD_COLS = ({"off_ypa", "def_ypa", "off_nya", "def_nya", "off_ypc", "def_ypc", "off_rb_ypc", "def_rb_ypc", "ybc_per_att", "yac_per_att",
              "def_ybc_allowed", "def_yac_allowed", "ryoe_per_att", "off_yacoe", "def_yacoe", "rec_separation", "rec_cushion",
              "ypc", "ypt", "ryoe_att", "yacoe_pr", "sep"} | {f"{s}_ypt_{p}" for s in ("off", "def") for p in ("WR", "TE", "RB")}
             | {f"{s}_ypc_{x}" for s in ("off", "def") for x in ("in", "out")})


TP_KEYS = ("name", "pos", "games", "snap_pct", "targets", "tgt_share", "tgt_share_l3", "air_share", "rec", "rec_yds", "rec_td", "epa_tgt",
           "carries", "car_share", "car_share_l3", "rush_yds", "rush_td", "epa_car", "rz_tgt", "rz_car", "status")


def trim_usage(US, tables):
    """Only the player fields the page shows (rank-table columns, sample sizes, the usage table and game logs)."""
    rk = {c[x] for tb in tables if tb["rows"] in ("rb", "wr", "te") for c in tb["cols"] for x in ("k", "n", "b") if c.get(x)}
    rk |= {"label", "sub", "team", "name"}
    return {"rb": [{k: v for k, v in r.items() if k in rk} for r in US["rb"]],
            "wr": [{k: v for k, v in r.items() if k in rk} for r in US["wr"]],
            "te": [{k: v for k, v in r.items() if k in rk} for r in US["te"]],
            "logs": US["logs"], "team_players": {t: [{k: r.get(k) for k in TP_KEYS} for r in v] for t, v in US["team_players"].items()}}


def finish_tables(tables, T, wr_ok, practice_ok=True):
    """Column post-processing: drop win rates that failed validation, yards to one decimal, small-sample minimums,
    sample sizes and a definition for every header, and no rank suffix on columns that are themselves ranks."""
    for t in tables:
        cols = []
        for c in t["cols"]:
            if c["k"] in WR_KEYS and not wr_ok:
                continue
            if c["k"] == "practice_concern_n" and not practice_ok:
                continue
            if c["k"] in YARD_COLS:
                c["f"] = "s1" if c["f"] in ("s1", "s2") else "n1"
                if not any(x in c["l"] for x in ("(yd)", "Y/A", "RYOE", "yd", "Yds", "Yards", "yds")):
                    c["l"] += " (yd)"
            if t["rows"] in ("rb", "wr", "te") and c["k"] in PLAYER_MIN:
                c["n"], c["min"] = PLAYER_MIN[c["k"]]
            if t["rows"] in ("rb", "wr", "te"):
                c = player_col_rule(c)
            if t["rows"] == "teams":
                if c["k"] in SAMPLE_MIN:
                    c["n"], c["min"] = SAMPLE_MIN[c["k"]]
                ni = n_info(c["k"], T)
                if ni and c["f"] in ("pct", "epa"):
                    c["nk"], c["nl"] = ni
            if "rank" in c["k"] and c["f"] == "int":
                c["nr"] = 1
            if not c["t"]:
                c["t"] = definition(c)
            cols.append(c)
        t["cols"] = cols
    return tables


def team_colour(c1, c2):
    """Primary colour, or the secondary when the primary is too dark to see on the dark surface (contrast < 2:1)."""
    def lum(h):
        h = str(h).lstrip("#")
        if len(h) != 6:
            return 0.0
        ch = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        ch = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in ch]
        return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]
    surface = lum("#141a25")
    ratio = lambda c: (max(lum(c), surface) + 0.05) / (min(lum(c), surface) + 0.05)   # noqa: E731
    return c1 if ratio(c1) >= 2 or ratio(c2) < ratio(c1) else c2


def takeaways(T, mm, A, meta, ARR):
    """Five to seven headline cards, each from one measured number with a link to the section that shows it."""
    W = meta["through_week"]
    rk = lambda col, hb=True: rank(T[col], hb)   # noqa: E731
    out = []
    top = T.rating_pg.idxmax()
    out.append({"h": f"{top} is the strongest team through week {W}",
                "ev": [f"Overall rating {T.rating_pg[top]:+.1f} points per game; offence {ordinal(T.off_adj_rank[top])}, defence {ordinal(T.def_adj_rank[top])} (opponent-adjusted).",
                       f"Next: {', '.join(f'{t} {T.rating_pg[t]:+.1f}' for t in T.rating_pg.sort_values(ascending=False).index[1:4])}."],
                "link": "#rankings", "lt": "Team rankings"})
    up, dn = T.form_net_change.idxmax(), T.form_net_change.idxmin()
    out.append({"h": f"Trending up: {up}; trending down: {dn}",
                "ev": [f"{up} net adj. EPA/play {T.form_net_l4[up]:+.3f} over its last four games against {T.form_net_season[up]:+.3f} for the season ({T.form_net_change[up]:+.3f}).",
                       f"{dn}: {T.form_net_l4[dn]:+.3f} against {T.form_net_season[dn]:+.3f} ({T.form_net_change[dn]:+.3f}). Four games is a small sample."],
                "link": "#form", "lt": "Recent form"})
    gap = T.record_vs_rating
    better, worse = gap.idxmax(), gap.idxmin()
    out.append({"h": f"Record and rating disagree most for {worse} and {better}",
                "ev": [f"{worse} is {T.record[worse]} (record {ordinal(T.winpct_rank[worse])}) but rates {ordinal(T.rating_rank[worse])}.",
                       f"{better} is {T.record[better]} (record {ordinal(T.winpct_rank[better])}) but rates {ordinal(T.rating_rank[better])}."],
                "link": "#luck", "lt": "Record versus performance"})
    lk = T.luck_index
    hi, lo = lk.idxmax(), lk.idxmin()
    out.append({"h": f"Regression candidates: {hi} (above its numbers), {lo} (below)",
                "ev": [f"{hi}: luck index {lk[hi]:+.2f}, one-score games {T.one_score[hi]}, turnover margin {int(T.to_margin[hi]):+d} vs expected {T.x_to_margin[hi]:+.1f}.",
                       f"{lo}: luck index {lk[lo]:+.2f}, one-score games {T.one_score[lo]}."],
                "link": "#overunder", "lt": "Over- and underperformers"})
    inj = T.absent_new_snap_weighted.idxmax()
    if T.absent_new_snap_weighted[inj] > 0:
        nw = A[(A.team == inj) & A.status_class.isin(["confirmed: reserve list", "listed Out/Doubtful", "inactive 3+ games"]) & (A.term == "new")]
        names = nw.sort_values("share", ascending=False).drop_duplicates("player").player.head(4)
        out.append({"h": f"{inj} has the heaviest new absences",
                    "ev": [f"{T.absent_new_snap_weighted[inj]:.2f} snap-weighted regulars newly out (0-1 games missed; {int(T.absent_new_n[inj])} players): {', '.join(names)}.",
                           "Absences of 2+ games are listed under Depth and injuries, each with how many of the team's games he played."],
                    "link": "#depth", "lt": "Depth and injuries"})
    fr = [x for v in ARR["teams"].values() for x in v if x["former_regular"] and x["recent"]]
    if fr:
        out.append({"h": "New arrivals who were regulars elsewhere: " + ", ".join(f"{x['name']} ({x['prev_team']} to {x['team']})" for x in fr[:3]),
                    "ev": [x["text"] for x in fr[:2]],
                    "link": "#matchups", "lt": "Matchups (new arrivals)"})
    edges = [(e["score"], g["game"], e) for g in mm for e in g["edges"]]
    if edges:
        sc_, game, e = max(edges, key=lambda x: abs(x[0]))
        out.append({"h": f"Biggest unit mismatch of week {W + 1}: {game}",
                    "ev": [f"{e['what']} (score {sc_:+.1f}, edge to {e['favours']}).", e["detail"] + "."],
                    "link": "#matchups", "lt": "Matchups"})
    hs = T.sos_net.idxmax()
    out.append({"h": f"{hs} has faced the hardest schedule",
                "ev": [f"Average opponent net adj. EPA/play {T.sos_net[hs]:+.3f}; easiest: {T.sos_net.idxmin()} ({T.sos_net.min():+.3f})."],
                "link": "#schedule", "lt": "Strength of schedule"})
    return out[:7]


# --------------------------------------------------------------------------------------- play-callers
CONF_TXT = {"confirmed": "", "reported": "", "assumed": "not confirmed", "unclear": "unclear"}


def caller_label(name, conf, since):
    extra = [f"since wk {since}"] if since else []
    if CONF_TXT.get(conf):
        extra.append(CONF_TXT[conf])
    return f"{name} ({', '.join(extra)})" if extra else name


def apply_callers(T: pd.DataFrame, CL: dict) -> pd.DataFrame:
    """Staff names and current-caller tendencies from callers.json (see callers.py)."""
    T = T.copy()
    for t in T.index:
        s, cur = CL["staff"][t], CL["current"][t]
        for k in ("hc", "oc", "dc", "stc"):
            T.loc[t, k] = s[k]
        for side in ("off", "def"):
            T.loc[t, f"{side}_caller"] = caller_label(s[f"{side}_caller"], s[f"{side}_conf"], cur[side]["since_week"])
            T.loc[t, f"{side}_caller_weeks"] = f"{cur[side]['since_week']}-{CL['through_week']}" if cur[side]["since_week"] else "all"
            for k, v in cur[side].items():
                if k not in ("caller", "weeks", "since_week"):
                    T.loc[t, f"c_{side}_{k}"] = np.nan if v is None else v
        T.loc[t, "caller_src"] = ", ".join(s["src"])
        for k, v in CL["gm"][t].items():
            T.loc[t, k] = np.nan if v is None else v
    return T


def apply_depth(T: pd.DataFrame, DP: dict) -> pd.DataFrame:
    """Depth-chart checks and Next Gen receiving from depth.json (see depth.py)."""
    T = T.copy()
    for t in T.index:
        c = DP["depth"]["checks"].get(t, {})
        T.loc[t, "dc_qb_listed"], T.loc[t, "dc_qb_last"] = c.get("qb_listed"), c.get("qb_last")
        T.loc[t, "dc_qb_flag"] = "" if c.get("qb_match") else "differs"
        T.loc[t, "dc_ol_new"] = ", ".join(c.get("ol_new", []))
        T.loc[t, "dc_ol_dropped"] = ", ".join(c.get("ol_dropped", []))
        r = DP["receiving"]["teams"].get(t, {})
        for k, v in r.items():
            T.loc[t, f"rec_{k}"] = np.nan if v is None else v
    return T


def apply_players(T: pd.DataFrame, PL: dict) -> pd.DataFrame:
    """Team summaries of the individual pass-rush and coverage tables from players.json (see players.py)."""
    T = T.copy()
    for t in T.index:
        r = PL["teams"].get(t, {})
        top = (r.get("rush") or [None])[0]
        cov = (r.get("cov") or [None])[0]
        T.loc[t, "pl_top_rusher"] = f"{top['name']} ({top['pressures']}, {top['share']:.0%})" if top else ""
        T.loc[t, "pl_top3_press_share"] = r.get("top3_press_share", np.nan)
        T.loc[t, "pl_press_out_share"] = r.get("press_out_share", np.nan)
        T.loc[t, "pl_top_cov"] = (f"{cov['name']} ({cov['targets']} tgt, rating {cov['rating']:.0f})" if cov and cov["rating"] is not None
                                  else (f"{cov['name']} ({cov['targets']} tgt)" if cov else ""))
        T.loc[t, "pl_tgt_out_share"] = r.get("tgt_out_share", np.nan)
    return T


def players_caution(t, r, PL):
    out = []
    if r.get("press_out_share", 0) >= PL["press_flag"]:
        out.append(f"{t} pass rush: players now out made {r['press_out_share']:.0%} of its pressures ({', '.join(r['press_out_names'])}), "
                   "so its season pressure figures overstate this week's rush.")
    if r.get("tgt_out_share", 0) >= PL["tgt_flag"]:
        out.append(f"{t} coverage: players now out were the nearest defender on {r['tgt_out_share']:.0%} of targets "
                   f"({', '.join(r['tgt_out_names'])}).")
    return out


def usage_caution(t, r, US):
    out = []
    if r.get("tgt_out_share", 0) >= US["tgt_flag"]:
        out.append(f"{t} receivers: players now out had {r['tgt_out_share']:.0%} of the team's targets ({', '.join(r['tgt_out_names'])}), "
                   "so its season passing figures were built with players who will not play.")
    if r.get("car_out_share", 0) >= US["car_flag"]:
        out.append(f"{t} run game: players now out had {r['car_out_share']:.0%} of the team's designed carries ({', '.join(r['car_out_names'])}).")
    return out


def usage_text(u):
    parts = []
    if u.get("targets"):
        parts.append(f"{u['tgt_share']:.0%} of targets" + (f" ({u['tgt_share_l3']:.0%} last 3)" if u.get("tgt_share_l3") is not None else ""))
    if u.get("carries"):
        parts.append(f"{u['car_share']:.0%} of carries" + (f" ({u['car_share_l3']:.0%} last 3)" if u.get("car_share_l3") is not None else ""))
    return "; ".join(parts)


def apply_garbage(T: pd.DataFrame, GT: dict) -> pd.DataFrame:
    """Garbage-time splits from garbage.json (see garbage.py) plus a plain-English flag per unit."""
    T = T.copy()
    for t in T.index:
        for side in ("off", "def"):
            r = GT["teams"][t][side]
            for k, v in r.items():
                T.loc[t, f"gt_{side}_{k}"] = np.nan if v is None else v
            e = r["gt_effect"] or 0
            # offence: a higher all-snap EPA flatters it; defence: a higher all-snap EPA allowed makes it look worse
            if abs(e) < GT["flag_epa"]:
                flag = ""
            elif (e > 0) == (side == "off"):
                flag = "flatter it"
            else:
                flag = "understate it"
            T.loc[t, f"gt_{side}_flag"] = flag
    return T


def gt_caution(t, side, r):
    flag = r[f"gt_{side}_flag"]
    if not flag:
        return None
    e, a, c = r[f"gt_{side}_gt_effect"], r[f"gt_{side}_epa_all"], r[f"gt_{side}_comp_epa"]
    unit = "offence" if side == "off" else "defence"
    what = "EPA/play" if side == "off" else "EPA/play allowed"
    raw = "raw yards and points" if side == "off" else "raw yards and points allowed"
    return (f"{t} {unit}: {what} is {a:+.3f} on all snaps but {c:+.3f} in competitive ones "
            f"({abs(e):.3f} {'higher' if e > 0 else 'lower'}; {r[f'gt_{side}_lop_play_share']:.0%} of its snaps were lopsided), "
            f"so its {raw} {flag}.")


WR_KEYS = ("pbwr", "prwr", "rbwr", "rswr")


def validate_win_rates(WR, teams, through_week):
    """Problems with the hand-copied ESPN file: 32 teams x 4 metrics, values 0-100, ranks 1-32, same through-week."""
    probs = []
    if WR is None:
        return ["file missing"]
    miss = sorted(set(teams) - set(WR.get("teams", {})))
    if miss:
        probs.append(f"teams missing: {', '.join(miss)}")
    for t, r in WR.get("teams", {}).items():
        for k in WR_KEYS:
            v, rk = r.get(k), r.get(f"{k}_rank")
            if not isinstance(v, (int, float)) or not 0 <= v <= 100:
                probs.append(f"{t} {k} value {v}")
            if not isinstance(rk, int) or not 1 <= rk <= 32:
                probs.append(f"{t} {k} rank {rk}")
    if WR.get("through_week") != through_week:
        probs.append(f"file runs through week {WR.get('through_week')}, the report through week {through_week}")
    return probs


def apply_win_rates(T: pd.DataFrame, meta: dict):
    """ESPN team win rates from the hand-kept win_rates_<season>.json (values as published, whole percentages).
    Returns (T, WR, problems); with any problem the columns are left out of the page."""
    f = Path(__file__).resolve().parent / f"win_rates_{meta['season']}.json"
    WR = json.loads(f.read_text(encoding="utf-8")) if f.exists() else None
    probs = validate_win_rates(WR, list(T.index), meta["through_week"])
    if probs:
        return T, WR, probs
    T = T.copy()
    for k in WR_KEYS:
        T[k] = [WR["teams"][t][k] / 100 if t in WR["teams"] else np.nan for t in T.index]
    return T, WR, []


def win_rate_corr(T):
    """Correlation of each ESPN win rate with the play-by-play outcome it should relate to (32 teams)."""
    pairs = [("prwr", "def_pressure_rate", "pass-rush win rate vs pressure rate"),
             ("pbwr", "off_pressure_rate", "pass-block win rate vs pressure allowed"),
             ("rswr", "def_stuff_rate", "run-stop win rate vs stuff rate"),
             ("rbwr", "ybc_per_att", "run-block win rate vs yards before contact")]
    return [(lab, float(T[a].corr(T[b]))) for a, b, lab in pairs if a in T and b in T]


# --------------------------------------------------------------------------------------- derived data
def derive(T: pd.DataFrame, G: pd.DataFrame, meta: dict):
    T = T.copy()
    for side in ("off", "def"):
        T[f"{side}_sack_yds_pg"] = T[f"{side}_sack_yds_lost"] / T.games
    for side in ("off", "def"):                     # explosive scrambles = all explosives - 20+ passes - 10+ designed runs
        T[f"{side}_n_expl_scr"] = T[f"{side}_n_explosive"] - T[f"{side}_n_expl_pass"] - T[f"{side}_n_expl_run"]
        T[f"{side}_expl_pass_share"] = T[f"{side}_n_expl_pass"] / T[f"{side}_n_explosive"]
    T[[c for c in T.columns if c.startswith("pd_")]] = T[[c for c in T.columns if c.startswith("pd_")]].fillna(0)
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


# (model key, +1 if a higher value helps the offence, label, detail builder)
EDGE_SPECS = [
    ("epa_db", 1, "{o} passing vs {d} pass defence",
     lambda T, o, d: f"{o} adj. EPA/dropback {T.off_adj_epa_db[o]:+.3f} ({ordinal(rank(T.off_adj_epa_db)[o])}); {d} allows {T.def_adj_epa_db[d]:+.3f} ({ordinal(rank(T.def_adj_epa_db, False)[d])})"),
    ("epa_rush", 1, "{o} run game vs {d} run defence",
     lambda T, o, d: f"{o} adj. EPA/rush {T.off_adj_epa_rush[o]:+.3f} ({ordinal(rank(T.off_adj_epa_rush)[o])}); {d} allows {T.def_adj_epa_rush[d]:+.3f} ({ordinal(rank(T.def_adj_epa_rush, False)[d])})"),
    ("pressure", -1, "{d} pass rush vs {o} protection",
     lambda T, o, d: f"{d} pressure rate {fmt(T.def_pressure_rate[d], 'pct')} ({ordinal(rank(T.def_pressure_rate)[d])}); {o} allows {fmt(T.off_pressure_rate[o], 'pct')} ({ordinal(rank(T.off_pressure_rate, False)[o])} in protection)"),
    ("expl_pass", 1, "{o} big passing plays vs {d} deep prevention",
     lambda T, o, d: f"{o} 20+ yard pass rate {fmt(T.off_expl_pass_rate[o], 'pct')} ({ordinal(rank(T.off_expl_pass_rate)[o])}); {d} allows {fmt(T.def_expl_pass_rate[d], 'pct')} ({ordinal(rank(T.def_expl_pass_rate, False)[d])} in prevention)"),
    # explosive runs are not a headline edge: notable ones pointed the right way only 57.5% of the time in 2021-25
    # (backtest_matchups.py); the matchup tables still show the 10+ yard run rates
]


PASS_KEYS = ("epa_db", "pressure", "expl_pass")


def mismatches(T, nxt, MM, QBS=None):
    """The three largest unit-versus-unit edges per game, scored on the matchup models' SHRUNK team effects:
    each side's effect times the share of it the shrinkage keeps, in standard deviations of the true effects
    (w * effect / tau). A measure with no reliable team-to-team signal (w close to 0) cannot become a headline edge.
    Blitz tendencies have no shrinkage model, so they stay in the matchup report as context. Passing edges of a team
    whose reported starter differs from the quarterbacks behind its figures say so in the detail."""
    QBS = QBS or {}
    rows = []
    for _, g in nxt.iterrows():
        h, a = g.home_team, g.away_team
        edges = []
        for o, d in [(h, a), (a, h)]:
            for key, sgn, lab, det in EDGE_SPECS:
                m = MM[key]
                zo = m["off"]["w"][o] * m["off"]["eff"][o] / math.sqrt(m["off"]["tau2"])
                zd = m["def"]["w"][d] * m["def"]["eff"][d] / math.sqrt(m["def"]["tau2"])
                zf = sgn * (zo + zd)                                 # > 0 favours the offence
                score = -zf if lab.startswith("{d}") else zf        # sign follows the unit named first
                news = (QBS.get(o) or {}).get("news")
                note = (f"; built with the quarterbacks who played before {news['starter']} (week news), so treat it with care"
                        if news and key in PASS_KEYS else "")
                edges.append((score, lab.format(o=o, d=d), det(T, o, d) + note, o if zf >= 0 else d,
                              round(float(m["off"]["w"][o]), 2), round(float(m["def"]["w"][d]), 2)))
        edges = sorted(edges, key=lambda e: -abs(e[0]))[:3]
        rows.append({"game": f"{a} at {h}", "day": str(g.gameday), "edges": [
            {"score": round(float(e[0]), 2), "what": e[1], "detail": e[2], "favours": e[3], "w_off": e[4], "w_def": e[5]} for e in edges]})
    return rows


# ------------------------------------------------------------------------------------- matchup pages
# label, model key (None = raw context only), offence column, defence column, format, +1 if higher helps the offence
MATCH_ROWS = {
    "Passing": [
        ("EPA per dropback", "epa_db", "off_epa_db", "def_epa_db", "epa", 1),
        ("Dropback success rate", "sr_db", "off_sr_db", "def_sr_db", "pct", 1),
        ("Yards per attempt", "ypa", "off_ypa", "def_ypa", "n1", 1),
        ("20+ yard pass rate", "expl_pass", "off_expl_pass_rate", "def_expl_pass_rate", "pct", 1),
        ("Sack rate", "sack_rate", "off_sack_rate", "def_sack_rate", "pct", -1),
        ("Pressure rate (PFR)", "pressure", "off_pressure_rate", "def_pressure_rate", "pct", -1),
        ("Pass block vs pass rush win rate (ESPN)", None, "pbwr", "prwr", "pct", 1, True),
        ("Air yards per completion (raw)", None, "off_air_per_cmp", "def_air_per_cmp", "n1", 1),
        ("YAC per completion (raw)", None, "off_yac_per_cmp", "def_yac_per_cmp", "n1", 1),
        ("YAC over expected per catch (NGS)", None, "off_yacoe", "def_yacoe", "n2", 1),
        ("Broken tackles after catch per game (PFR)", None, "rec_brk_tkl_pg", "def_rec_brk_tkl_allowed_pg", "n2", 1),
        ("Contested-target rate (FTN)", None, "off_contested_rate", "def_contested_rate", "pct", -1, True),
        ("EPA per target to wide receivers", None, "off_epa_tgt_WR", "def_epa_tgt_WR", "epa", 1),
        ("EPA per target to tight ends", None, "off_epa_tgt_TE", "def_epa_tgt_TE", "epa", 1),
        ("EPA per target to running backs", None, "off_epa_tgt_RB", "def_epa_tgt_RB", "epa", 1),
        ("20+ yd catches per target, WRs", None, "off_rate20_WR", "def_rate20_WR", "pct", 1),
        ("20+ yd catches per target, TEs", None, "off_rate20_TE", "def_rate20_TE", "pct", 1),
        ("20+ yd catches per target, RBs", None, "off_rate20_RB", "def_rate20_RB", "pct", 1),
        ("Passing yards per game (raw)", None, "off_pass_yds_pg", "def_pass_yds_pg", "n1", 1),
    ],
    "Rushing": [
        ("EPA per designed rush", "epa_rush", "off_epa_rush", "def_epa_rush", "epa", 1),
        ("Rush success rate", "sr_rush", "off_sr_rush", "def_sr_rush", "pct", 1),
        ("Yards per carry", "ypc", "off_ypc", "def_ypc", "n1", 1),
        ("10+ yard run rate", "expl_run", "off_expl_run_rate", "def_expl_run_rate", "pct", 1),
        ("Stuff rate (0 or fewer yards)", "stuff", "off_stuff_rate", "def_stuff_rate", "pct", -1),
        ("EPA per run vs 7+ in the box (FTN)", None, "off_epa_rush_box7p", "def_epa_rush_box7p", "epa", 1),
        ("EPA per inside run", None, "off_epa_in", "def_epa_in", "epa", 1),
        ("EPA per outside run", None, "off_epa_out", "def_epa_out", "epa", 1),
        ("Run block vs run stop win rate (ESPN)", None, "rbwr", "rswr", "pct", 1, True),
        ("Yards before contact (PFR)", None, "ybc_per_att", "def_ybc_allowed", "n1", 1),
        ("Yards after contact (PFR)", None, "yac_per_att", "def_yac_allowed", "n1", 1),
        ("Broken tackles on runs per game (PFR)", None, "rush_broken_tackles_pg", "def_rush_brk_tkl_allowed_pg", "n2", 1),
        ("Rushing yards per game (raw)", None, "off_rush_yds_pg", "def_rush_yds_pg", "n1", 1),
    ],
    "Discipline (penalties)": [
        ("Offensive fouls per game (committed vs drawn by this defence)", None, "pd_off_pg", "pd_off_drawn_pg", "n2", -1),
        ("Offensive penalty yards per game", None, "pd_off_yds_pg", "pd_off_drawn_yds_pg", "n1", -1),
        ("Defensive fouls per game (drawn by this offence vs committed)", None, "pd_drawn_def_pg", "pd_def_pg", "n2", 1),
        ("Defensive penalty yards per game", None, "pd_drawn_def_yds_pg", "pd_def_yds_pg", "n1", 1),
        ("Defensive fouls on 3rd/4th down per game (offence drew vs defence committed)", None, "pd_d34_def_drawn_pg", "pd_d34_def_pg", "n2", 1),
    ],
    "Overall and situational": [
        ("EPA per play", "epa_play", "off_epa_play", "def_epa_play", "epa", 1),
        ("Success rate", "sr", "off_sr", "def_sr", "pct", 1),
        ("Third-down conversion", "d3_conv", "off_d3_conv", "def_d3_conv", "pct", 1),
        ("Points per drive", "ppd", "off_ppd", "def_ppd", "n2", 1),
        ("Red-zone TD rate per trip", "rz_td", "off_rz_td_rate", "def_rz_td_rate", "pct", 1),
        ("Turnovers per drive", "to_pd", "off_to_pd", "def_to_pd", "pct", -1),
        ("Points per game (raw)", None, "off_pts_pg", "def_pts_pg", "n1", 1),
        ("Yards per game (raw)", None, "off_yds_pg", "def_yds_pg", "n1", 1),
    ],
}
ST_ROWS = [("Special-teams EPA per game", "st_epa_pg", "s2", 1), ("Field-goal %", "fg_pct", "pct", 1),
           ("FG points over expected", "fg_pts_oe", "s1", 1), ("FG 50+ (made/att.)", "fg_50p", "str", 0),
           ("Extra-point %", "xp_pct", "pct", 1), ("Punt net average", "punt_net", "n1", 1),
           ("Opponents' punt net", "opp_punt_net", "n1", -1), ("Kick return average", "ko_ret_avg", "n1", 1),
           ("Kick return allowed", "ko_ret_avg_allowed", "n1", -1), ("Start after kickoff (own yd line)", "start_after_ko", "n1", 1),
           ("Opp. start after kickoff", "opp_start_after_ko", "n1", -1), ("Punt return average", "punt_ret_avg", "n1", 1),
           ("Return TDs / allowed", "st_td_pair", "str", 0), ("Kicks blocked / blocked against", "blocks_pair", "str", 0),
           ("Special-teams penalties", "pen_st_n", "int", -1)]


NOTABLE = {"v": 1.5}      # headline-edge size called notable; set from the calibration when the report has one


def conf_label(w):
    return "moderate" if w >= 0.6 else ("low" if w >= 0.35 else ("very low" if w > 0.02 else "no signal yet"))


def coaching_profile(t, T):
    r = T.loc[t]
    zgo = (r.fd_go_rate - T.fd_go_rate.mean()) / T.fd_go_rate.std()
    agg = "aggressive" if zgo >= 0.75 else ("conservative" if zgo <= -0.75 else "typical")
    lean = "pass-leaning" if r.c_off_proe >= 3 else ("run-leaning" if r.c_off_proe <= -3 else "balanced")
    zb = (r.c_def_blitz_rate - T.c_def_blitz_rate.mean()) / T.c_def_blitz_rate.std()
    bl = "blitz-heavy" if zb >= 0.75 else ("rarely blitzes" if zb <= -0.75 else "average blitz rate")
    nn = lambda v: None if pd.isna(v) else float(v)
    return {"agg": agg, "lean": lean, "blitz": bl, "go": nn(r.fd_go_rate), "n4": int(r.fd_decisions),
            "clear_n": nn(r.fd_clear_go_n), "clear": nn(r.fd_clear_go_rate), "agree": nn(r.fd_agree_rate),
            "proe": nn(r.c_off_proe), "pace": nn(r.c_off_pace_sec), "blitz_rate": nn(r.c_def_blitz_rate),
            "off_caller": r.off_caller, "def_caller": r.def_caller, "stc": r.stc,
            "off_weeks": r.off_caller_weeks, "def_weeks": r.def_caller_weeks,
            "pen_pg": float((r.pen_off_n + r.pen_def_n + r.pen_st_n) / r.games), "h2": nn(r.net_h2_minus_h1),
            "one_score": r.one_score}


QB_SHRINK = json.loads((Path(__file__).resolve().parent / "qb_shrinkage.json").read_text(encoding="utf-8"))     if (Path(__file__).resolve().parent / "qb_shrinkage.json").exists() else None


def qb_weight(n, team_tau2=None, rv=None):
    """Share of a passer's gap from average kept at n dropbacks: the 2021-25 quarterback fit (backtest_qb_sample.py),
    else the team-level matchup model's values."""
    if QB_SHRINK:
        return QB_SHRINK["tau2"] / (QB_SHRINK["tau2"] + QB_SHRINK["s2"] / n) if n else 0.0
    return team_tau2 / (team_tau2 + rv / n) if n else 0.0


ROLE = (QB_SHRINK or {}).get("role")


def is_backup(q):
    return q.get("opened_season") is False


def qb_expect(q, m, wd, ed, hsign, tau2=None, rv=None):
    """Expected EPA per dropback for a passer against a defence: league mean + role offset (did he open the season as a
    starter?) + the fitted share of his own gap from average + the defence's effect + home. Without the role fit, the
    plain shrinkage. A passer with no sample gets the role offset alone."""
    base = m["mean"] + wd * ed + m["home"] * hsign
    own = 0.0
    if q.get("adj_epa_db") is not None and q.get("dropbacks"):
        own = qb_weight(q["dropbacks"], tau2, rv) * (q["adj_epa_db"] - m["mean"])
    if not ROLE:
        return base + own
    return base + (ROLE["backup_adj"] if is_backup(q) else ROLE["starter_adj"]) + ROLE["cur_coef"] * own


def role_text(q):
    if not ROLE or not is_backup(q):
        return ""
    lo, hi = sorted(abs(x) for x in ROLE["backup_gap_ci"])
    return (f" He did not open the season as his team's starter: in 2021-25 such quarterbacks played about {abs(ROLE['backup_gap']):.2f} EPA per "
            f"dropback below what their own numbers suggested (95% range {lo:.2f}-{hi:.2f}, {ROLE['backup_seasons']} backup seasons), and the "
            f"matchup expectations include that.")


def qb_range(n):
    """Half-width of a 95% interval for a passer's EPA per dropback on n dropbacks (per-dropback SD from 2021-25)."""
    s2 = QB_SHRINK["s2"] if QB_SHRINK else 2.4
    return 1.96 * math.sqrt(s2 / n) if n else None


def one_q_text(o):
    if not o:
        return ""
    qn = {1: "1st quarter", 2: "2nd quarter", 3: "3rd quarter", 4: "4th quarter", 5: "overtime"}[o["qtr"]]
    return (f" One quarter (week {o['week']}, {qn}, {o['n']} dropbacks) produced {o['epa']:+.2f} EPA against a season total of {o['total']:+.2f}; "
            f"without it he averaged {o['without']:+.3f} per dropback.")


PLAYER_SHRINK = json.loads((Path(__file__).resolve().parent / "player_shrinkage.json").read_text(encoding="utf-8"))     if (Path(__file__).resolve().parent / "player_shrinkage.json").exists() else None


def _lasted(kind, K):
    r = next((x for x in PLAYER_SHRINK["measures"][kind]["by_sample"] if x["K"] == K), None) if PLAYER_SHRINK else None
    return r


def player_note(which):
    """Data-driven caution for the player ranking tables ('rb' or 'rec')."""
    if not PLAYER_SHRINK:
        return ""
    y = PLAYER_SHRINK["fitted_on"]
    if which == "rb":
        a, b = _lasted("carry", 40), _lasted("carry", 80)
        return (f" Efficiency settles slowly: in {y[0]}-{y[1]} only about {a['carried_forward']:.0%} of a running back's EPA-per-carry gap from average after "
                f"40 carries lasted the rest of his season ({b['carried_forward']:.0%} after 80). Carry share and total work are the steadier guide.")
    w, t = _lasted("target_WR", 40), _lasted("target_TE", 40)
    return (f" Efficiency settles slowly: in {y[0]}-{y[1]} only about {w['carried_forward']:.0%} of a wide receiver's EPA-per-target gap from average "
            f"after 40 targets lasted the rest of his season (tight ends about {t['carried_forward']:.0%}, on fewer cases), while early target share "
            f"kept a correlation of about {w['share_corr']:.2f} with later target share. Read per-target columns as noisy; target share is the steadier guide.")


def player_method():
    if not PLAYER_SHRINK:
        return ""
    y = PLAYER_SHRINK["fitted_on"]
    m = PLAYER_SHRINK["measures"]
    c40, w40, t20 = _lasted("carry", 40), _lasted("target_WR", 40), _lasted("target_TE", 20)
    return (f"<p>The same test for other positions ({y[0]}-{y[1]}, players who went on to {PLAYER_SHRINK['rest_min']}+ more opportunities): "
            f"after 40 carries about {c40['carried_forward']:.0%} of a running back's EPA-per-carry gap from average lasted ({m['carry']['rows']} samples), "
            f"after 40 targets about {w40['carried_forward']:.0%} of a wide receiver's EPA-per-target gap ({m['target_WR']['rows']} samples), "
            f"after 20 targets about {t20['carried_forward']:.0%} for tight ends, and running backs' EPA per target showed no measurable carry-over. "
            f"Success rate and capped EPA were no better. Early target share, by contrast, kept a correlation of about {w40['share_corr']:.2f} with later "
            f"target share. Player efficiency feeds no expectation in this report; the player tables and next-man-up lines show it with a 95% range "
            f"and point to usage as the steadier guide.</p>")


def qb_method():
    """Method text for the quarterback shrinkage, from qb_shrinkage.json."""
    if not QB_SHRINK:
        return "It uses the team-level spread of the matchup model."
    k = {r["K"]: r for r in QB_SHRINK["by_sample"]}
    return (f"The spread between quarterbacks is fitted on {QB_SHRINK['fitted_on'][0]}-{QB_SHRINK['fitted_on'][1]}: for each passer-season, his first "
            f"30, 60, 120 or 200 dropbacks were compared with the rest of his season ({QB_SHRINK['rows']} samples from {QB_SHRINK['passers']} passers who "
            f"went on to 150+ more dropbacks, so mostly starters). Only {k[60]['carried_forward']:.0%} of a quarterback's gap from average after 60 dropbacks, "
            f"{k[120]['carried_forward']:.0%} after 120 and {k[200]['carried_forward']:.0%} after 200 carried forward, less than the team-level spread "
            f"implied, so a short hot or cold run moves the expectation little. Capping big plays, success rate and dropping a passer's best quarter "
            f"were tested and predicted no better beyond noise, so they are not used. When one quarter supplied more than half of a passer's total EPA and leaving it out moves his average by 0.10 or more per dropback, "
            f"the quarterback line says so and gives his average without it, as a warning only."
            + (f" A second fit ({ROLE['rows']} samples, passers with {ROLE['rest_min']}+ more dropbacks so backups are included) adds whether the passer "
               f"opened the season as his team's starter (he threw its first dropback of the season). Quarterbacks who did not ({ROLE['backup_seasons']} "
               f"backup seasons) played {abs(ROLE['backup_gap']):.3f} EPA per dropback below what their own numbers suggested (95% range "
               f"{min(abs(x) for x in ROLE['backup_gap_ci']):.3f}-{max(abs(x) for x in ROLE['backup_gap_ci']):.3f}); adding it lowered the "
               f"out-of-sample error for backups from {ROLE['loso_rmse_backups_without']:.3f} to {ROLE['loso_rmse_backups_with_role']:.3f}, so quarterback "
               f"expectations start a backup below average and a season-opening starter slightly above. A passer's previous two seasons were also tested "
               f"and made backups' predictions worse, so they are not used." if ROLE else ""))


def sample_note(q):
    """Plain-language uncertainty for a passer's own numbers."""
    n = q["dropbacks"]
    if not n or q["adj_epa_db"] is None:
        return role_text(q).strip()
    return (f"On {n} dropbacks his EPA per dropback is uncertain by about ±{qb_range(n):.2f}; the matchup expectations keep about "
            f"{qb_weight(n) * (ROLE['cur_coef'] if ROLE else 1):.0%} of his gap from average (fitted on 2021-25 quarterbacks: a short hot or cold run mostly did not last)."
            + role_text(q) + one_q_text(q.get("one_q")))


def expected_starter(info):
    """The latest starter, unless he is on the reserve list or listed Out/Doubtful; then the healthy QB with most starts."""
    rows = info.get("qbs", [])
    if not rows:
        return None
    news = next((r for r in rows if r.get("news")), None)        # hand-kept news: trades, signings, named starters
    if news:
        return news
    down = lambda r: r["roster_status"] == "RES" or r["report_status"] in ("Out", "Doubtful")   # noqa: E731
    lat = next((r for r in rows if r["latest_starter"]), None)
    if lat and not down(lat):
        return lat
    ok = [r for r in rows if not down(r) and r is not lat]
    return max(ok, key=lambda r: (r["starts"], r["dropbacks"])) if ok else lat


def starter_line(t, info):
    """'with [expected starter]' figures when a team's season numbers mix quarterbacks; None otherwise."""
    rows = info.get("qbs", [])
    news = info.get("news")
    if sum(1 for r in rows if r["starts"]) < 2 and not news:
        return None
    q = expected_starter(info)
    if not q:
        return None
    out = {"team": t, "name": q["name"], "starts": q["starts"], "dropbacks": q["dropbacks"], "adj_epa_db": q["adj_epa_db"],
           "sr": q.get("sr"), "sack_rate": q["sack_rate"], "int_worthy": q["int_worthy"], "low": q["starts"] < 4,
           "latest": bool(q["latest_starter"]),
           "kept": round(qb_weight(q["dropbacks"]), 3) if q["dropbacks"] else None,
           "range": round(qb_range(q["dropbacks"]), 3) if q["dropbacks"] else None, "one_q": q.get("one_q"),
           "note": sample_note(q), "backup": is_backup(q)}
    if news and q.get("news"):
        other = q.get("sample_team") and q["sample_team"] != t
        out.update({"news": news["conf"], "news_status": q.get("news_status"), "sample_team": q.get("sample_team") if other else None,
                    "no_sample": q["dropbacks"] < 30 or q["adj_epa_db"] is None,
                    "sources": "; ".join(f"{s['who']}, {s['when']}" for s in news["sources"])})
    return out


def report_label(w):
    """'last week's report (week N)' before the coming week's reports exist, else 'week N report'."""
    if w is None or (isinstance(w, float) and math.isnan(w)):
        return "no report"
    w = int(w)
    return f"last week's report (week {w})" if w <= WK["thru"] else f"week {w} report"


def absence_when(x):
    if x.games_missed == 0:
        return "played the latest game"
    return f"out since week {int(x.out_since_week)}, {int(x.games_missed)} game{'' if x.games_missed == 1 else 's'} without him"


def presence(x):
    """How much of the team's season he was part of; 'mostly reflected' only when his current run of missed games is at
    least half of the team's games, never for a quarterback."""
    txt = f"with {x.team} for {int(x.games)} of its {int(x.team_games)} games"
    if x.position != "QB" and x.games_missed >= x.team_games / 2:
        txt += ", mostly reflected in the season numbers"
    return txt


def long_term_text(x):
    return f"{x.player} ({x.position}, out since week {int(x.out_since_week)}): {presence(x)}"


NGS_LABELS = {  # column -> (label, unit); usage shares unless noted
    "off_11p": ("11 personnel", "%"), "off_12p": ("12 personnel", "%"), "off_13p": ("13 personnel", "%"), "off_21p": ("21 personnel", "%"),
    "off_called_pass": ("called pass rate", "%"), "off_ed_play_action": ("early-down play action", "%"), "off_motion": ("motion", "%"),
    "off_tempo_sec": ("seconds between snaps", "s"), "off_quick_pass": ("quick passes", "%"), "off_in_breaking": ("in-breaking targets", "%"),
    "off_out_breaking": ("out-breaking targets", "%"), "off_10plus_air": ("targets 10+ air yards", "%"), "off_inside_zone": ("inside zone runs", "%"),
    "off_outside_zone": ("outside zone runs", "%"), "off_gap": ("gap runs", "%"), "off_man_blocking": ("man-blocking runs", "%"),
    "def_base": ("base personnel", "%"), "def_nickel": ("nickel", "%"), "def_dime": ("dime", "%"), "def_zone": ("zone coverage", "%"),
    "def_man": ("man coverage", "%"), "def_press": ("press coverage", "%"), "def_single_high": ("single-high shells", "%"),
    "def_split_safety": ("split-safety shells", "%"), "def_cover0": ("cover 0", "%"), "def_blitz": ("blitz rate", "%"),
    "def_pressure_blitz": ("pressure when blitzing", "%"), "def_pressure_no_blitz": ("pressure without a blitz", "%")}


def load_ngs(season):
    f = Path(__file__).resolve().parent / f"ngs_trends_{season}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def ngs_signature(rec, side, n=5):
    """The unit's most distinctive NGS tendencies (80th percentile or higher, or 20th or lower), most extreme first."""
    if not rec:
        return None
    out = []
    for k, (lab, unit) in NGS_LABELS.items():
        if not k.startswith(side) or rec.get(k + "_pct") is None:
            continue
        p = rec[k + "_pct"]
        if p >= 80 or p <= 20:
            v = rec[k]
            val = f"{v:.1f} s" if unit == "s" else f"{100 * v:.0f}%"
            word = ("fast" if p >= 80 else "slow") if k == "off_tempo_sec" else ("high" if p >= 80 else "low")
            out.append((abs(p - 50), f"{lab} {val} ({word}, {ordinal(p)} percentile)"))
    return "; ".join(x[1] for x in sorted(out, reverse=True)[:n]) or "no tendency in the top or bottom fifth"


def build_matchups(T, nxt, MM, A, mm, notes, PL, US, QBS, REF, ARR, UN, WX=None, NG=None):
    games = []
    mm_by = {m["game"]: m for m in mm}
    lg_go = T.fd_go_rate.mean()
    for _, g in nxt.iterrows():
        h, a = g.home_team, g.away_team
        neutral = str(g.location) == "Neutral"
        label = f"{a} at {h}"
        sides, cautions = [], []
        for o, d in [(a, h), (h, a)]:
            hsign = 0 if neutral else (1 if o == h else -1)
            groups = []
            for gname, rows in MATCH_ROWS.items():
                out = []
                for lab, key, oc, dc, f, sgn, *d_high in rows:
                    if oc not in T or dc not in T:
                        continue
                    ov, dv = T.loc[o, oc], T.loc[d, dc]
                    d_good = bool(d_high[0]) if d_high else sgn == -1          # win rates: higher is better for both units
                    row = {"lab": lab, "f": f, "o": None if pd.isna(ov) else float(ov), "o_rank": int(rank(T[oc], sgn == 1)[o]),
                           "d": None if pd.isna(dv) else float(dv), "d_rank": int(rank(T[dc], d_good)[d])}   # 1 = best unit
                    if key:
                        m = MM[key]
                        eo, ed = m["off"]["eff"][o], m["def"]["eff"][d]
                        wo, wd = m["off"]["w"][o], m["def"]["w"][d]
                        exp = m["mean"] + wo * eo + wd * ed + m["home"] * hsign
                        scale = math.sqrt(m["off"]["tau2"] + m["def"]["tau2"])
                        z = sgn * (exp - m["mean"]) / scale if scale > 0 else 0
                        row.update({"exp": exp, "lg": m["mean"], "lean": "offence" if z >= 0.5 else ("defence" if z <= -0.5 else "even"),
                                    "z": round(z, 2), "conf": conf_label((wo + wd) / 2), "wo": wo, "wd": wd,
                                    "no": m["off"]["n"][o], "nd": m["def"]["n"][d]})
                    out.append(row)
                groups.append({"name": gname, "rows": out})
            ex = {r["lab"]: r for grp in groups for r in grp["rows"]}
            sides.append({"off": o, "def": d, "home": o == h, "groups": groups, "exp_epa": ex["EPA per play"]["exp"],
                          "starter": starter_line(o, QBS.get(o, {})),
                          "scheme": ({"off": ngs_signature(NG["teams"].get(o), "off_"), "def": ngs_signature(NG["teams"].get(d), "def_")}
                                     if NG else None),
                          "exp_ppd": ex["Points per drive"]["exp"], "conf_epa": ex["EPA per play"]["conf"]})
        st = []
        for lab, col, f, dd in ST_ROWS:
            def val(t):
                r = T.loc[t]
                if col == "st_td_pair":
                    return f"{int(r.st_td)} / {int(r.st_td_allowed)}"
                if col == "blocks_pair":
                    return f"{int(r.blocks_made)} / {int(r.blocks_allowed)}"
                v = r[col]
                return None if (not isinstance(v, str) and pd.isna(v)) else (v if isinstance(v, str) else float(v))
            row = {"lab": lab, "f": f, "a": val(a), "h": val(h)}
            if dd != 0:
                rk = rank(T[col], dd == 1)
                row["a_rank"], row["h_rank"] = int(rk[a]), int(rk[h])
            st.append(row)
        coach = {a: coaching_profile(a, T), h: coaching_profile(h, T)}
        coach[a]["name"], coach[h]["name"] = str(g.away_coach), str(g.home_coach)
        # what to expect: unit-level expectations, never a score or a winner
        exp = []
        for sd in sides:
            exp.append(f"{sd['off']} offence against the {sd['def']} defence: expected {sd['exp_epa']:+.3f} EPA per play and "
                       f"{sd['exp_ppd']:.2f} points per drive (league {MM['epa_play']['mean']:+.3f} and {MM['ppd']['mean']:.2f}); "
                       f"confidence {sd['conf_epa']}.")
        for e in mm_by.get(label, {}).get("edges", []):
            if abs(e["score"]) >= NOTABLE["v"]:
                exp.append(f"{e['what']}: edge to {e['favours']} ({e['detail']}).")
        for t, opp in [(a, h), (h, a)]:
            c = coach[t]
            if c["lean"] != "balanced":
                exp.append(f"{t} is {c['lean']} on neutral early downs (pass rate over expected {c['proe']:+.1f} points); "
                           f"{opp} ranks {ordinal(rank(T.def_adj_epa_db, False)[opp])} against the pass and "
                           f"{ordinal(rank(T.def_adj_epa_rush, False)[opp])} against the run (adjusted).")
            if c["agg"] != "typical":
                tail = ("More fourth-down attempts mean more high-variance possessions." if c["agg"] == "aggressive"
                        else "Expect more punts and field goals in borderline spots.")
                exp.append(f"{t} has been {c['agg']} on fourth down: went for it on {fmt(c['go'], 'pct')} of {c['n4']} "
                           f"neutral fourth downs (league {fmt(lg_go, 'pct')}). {tail}")
        low = sorted({r["lab"] for sd in sides for grp in sd["groups"] for r in grp["rows"]
                      if r.get("conf") in ("no signal yet", "very low")})
        if low:
            cautions.append("Weak evidence so far, so the expected value stays close to the league average: " + ", ".join(low) + ".")
        for t in (a, h):
            r = T.loc[t]
            if int(r.qb_starters_n) > 1:
                cautions.append(f"{t} season figures mix quarterbacks ({r.qb_starts}).")
            if QBS.get(t, {}).get("news"):
                cautions.append(f"{t} quarterback change the season figures do not reflect yet. " + QBS[t]["news"]["flag"])
            xs = expected_starter(QBS.get(t, {}))
            if xs and ((ROLE and is_backup(xs)) or xs.get("one_q")):
                cautions.append(f"{t} expected quarterback {xs['name']}: be wary of his own numbers ("
                                + (f"{xs['dropbacks']} dropbacks, ±{qb_range(xs['dropbacks']):.2f}" if xs["dropbacks"] else "no 2026 dropbacks") + ")."
                                + role_text(xs) + one_q_text(xs.get("one_q")))
            outs = A[(A.team == t) & A.status_class.isin(["confirmed: reserve list", "listed Out/Doubtful", "inactive 3+ games"]) & (A.term == "new")]
            if len(outs):
                cautions.append(f"{t} regulars newly out (0-1 games missed): " + ", ".join(
                    f"{x.player} ({x.position}, {x.share:.0%} of snaps, {absence_when(x)})" for x in outs.itertuples()) + ".")
            lt = A[(A.team == t) & A.status_class.isin(["confirmed: reserve list", "listed Out/Doubtful", "inactive 3+ games"]) & (A.term == "long-term")]
            if len(lt):
                cautions.append(f"{t} absences of 2+ games: " + "; ".join(long_term_text(x) for x in lt.itertuples()) + ".")
            nd = [x for x in ARR.get("departures", {}).get(t, []) if x["new"]]
            if nd:
                cautions.append(f"{t} new departures, so its season numbers were built with them: " + "; ".join(x["text"] for x in nd) + ".")
            for x in UN["flagged"].get(t, []):
                cautions.append(f"{t} figures include an unusual game ({x['label']}: {x['weather']}, {x['dropbacks']} combined dropbacks): see Recent form.")
            q = A[(A.team == t) & (A.status_class == "listed Questionable")]
            if len(q):
                cautions.append(f"{t} questionable ({report_label(q.last_report_week.max())}): " + ", ".join(f"{x.player} ({x.position})" for x in q.itertuples()) + ".")
            pr = A[(A.team == t) & A.status_class.isin(["did not practise", "limited in practice"])]
            if len(pr):
                cautions.append(f"{t} practice report ({report_label(pr.last_report_week.max())}, no game status yet): " + ", ".join(
                    f"{x.player} ({x.position}, {'DNP' if x.status_class == 'did not practise' else 'limited'})" for x in pr.itertuples()) + ".")
        for t in (a, h):
            r = T.loc[t]
            if r.dc_qb_flag:
                cautions.append(f"{t} depth chart lists {r.dc_qb_listed} at QB; {r.dc_qb_last} took the most snaps in the latest game.")
            if r.dc_ol_new:
                cautions.append(f"{t} offensive line: depth chart lists {r.dc_ol_new}, who were not in the latest game's top five by snaps"
                                + (f" ({r.dc_ol_dropped} were)." if r.dc_ol_dropped else "."))
            cautions.extend(players_caution(t, PL["teams"].get(t, {}), PL))
            cautions.extend(usage_caution(t, US["teams"].get(t, {}), US))
            for side in ("off", "def"):
                gc = gt_caution(t, side, T.loc[t])
                if gc:
                    cautions.append(gc)
        if T.off_pfr_games.min() < T.games.min():
            cautions.append("Pressure and yards-before-contact figures use PFR data, which is missing some recent games.")
        final = None
        if pd.notna(g.home_score) and pd.notna(g.away_score):
            final = f"Final: {a} {int(g.away_score)}, {h} {int(g.home_score)}"
        games.append({
            "id": g.game_id, "label": label, "away": a, "home": h,
            "when": f"{g.weekday} {g.gameday}, {g.gametime} ET", "venue": f"{g.stadium} ({g.roof if isinstance(g.roof, str) and g.roof else 'roof not listed'})",
            "neutral": neutral, "div": bool(g.div_game == 1),
            "rest": {a: None if pd.isna(g.away_rest) else int(g.away_rest), h: None if pd.isna(g.home_rest) else int(g.home_rest)},
            "sides": sides, "st": st, "coach": coach, "expect": exp, "cautions": cautions, "final": final,
            "summary": {t: {"record": T.loc[t, "record"], "rating": float(T.loc[t, "rating_pg"]), "rating_rank": int(T.loc[t, "rating_rank"]),
                            "stab_rank": int(T.loc[t, "stab_rank"]), "off_rank": int(T.loc[t, "off_adj_rank"]),
                            "def_rank": int(T.loc[t, "def_adj_rank"]), "st_rank": int(rank(T.st_epa_pg)[t]),
                            "qb": str(T.loc[t, "qb_starts"])} for t in (a, h)},
            "edges": mm_by.get(label, {}).get("edges", []),
            "form": {t: {k: (None if pd.isna(T.loc[t, f"form_{k}"]) else float(T.loc[t, f"form_{k}"]))
                         for k in ("off_l4", "def_l4", "net_l4", "off_season", "def_season", "net_season", "off_change", "def_change", "net_change")}
                     | {"weeks": str(T.loc[t, "form_weeks"]), "games": int(T.loc[t, "form_games"])} for t in (a, h)},
            "referee": REF["assign"].get(g.game_id),
            "weather": ((WX or {}).get("games", {}).get(g.game_id) or {}).get("text"),
            "arrivals": {t: ARR["teams"].get(t, []) for t in (a, h)},
            "departures": {t: ARR.get("departures", {}).get(t, []) for t in (a, h)},
            "roster_note": f"Rosters through week {ARR.get('roster_week')}; later trades appear after the next roster update.",
            "unusual": {t: UN["flagged"].get(t, []) for t in (a, h)}, "qb_ints": {t: UN["ints"].get(t, []) for t in (a, h)},
            "note": notes.get("games", {}).get(label), "post": notes.get("postgame", {}).get(label),
        })
    return games


# ----------------------------------------------------------------------- structured matchup report
def _rk(T, col, higher_is_good):
    return rank(T[col], higher_is_good)


def _w(MM, key, side, team):
    return MM[key][side]["w"][team] if key in MM else None


def finding_conf(ranks_extreme, weights):
    ws = [w for w in weights if w is not None]
    wmin = min(ws) if ws else 0.0
    if ranks_extreme and wmin >= 0.5:
        return "strong"
    if wmin >= 0.35 or (ranks_extreme and wmin >= 0.2):
        return "moderate"
    return "limited"


def find_mismatches(o, d, T, MM, QBX):
    """Rule-based scan of eleven mismatch types for offence o against defence d. Each finding keeps the
    evidence, the mechanism, what could neutralise it, whether a matchup-specific split supports it, and a
    confidence level. Ranks: 1 = best unit for the measure."""
    F = []
    r = lambda col, hb: int(_rk(T, col, hb)[o])
    rd = lambda col, hb: int(_rk(T, col, hb)[d])
    v = lambda t, col, f: fmt(T.loc[t, col], f)
    lg = lambda col: T[col].mean()

    def add(kind, fav, evidence, mechanism, neutral, specific, conf):
        F.append({"kind": kind, "favours": fav, "evidence": evidence, "mechanism": mechanism,
                  "neutralisers": [n for n in neutral if n], "specific": specific, "conf": conf})

    # 1 rushing offence vs run defence
    ro, rdd = r("off_adj_epa_rush", True), rd("def_adj_epa_rush", False)
    if (ro <= 10 and rdd >= 23) or (ro >= 23 and rdd <= 10):
        fav = o if ro <= 10 else d
        share = T.loc[o, "run_inside_share"]
        pref = "inside" if share >= 0.55 else ("outside" if share <= 0.45 else None)
        spec = None
        if pref:
            de = T.loc[d, f"def_epa_{pref}"]
            spec = (f"{o} runs {pref} on {fmt(share if pref == 'inside' else 1 - share, 'pct')} of non-QB runs; {d} allows "
                    f"{fmt(de, 'epa')} EPA per {pref} run (league {fmt(lg(f'def_epa_{pref}'), 'epa')}).")
            spec_ok = (de > lg(f"def_epa_{pref}")) == (fav == o)
            spec = ("Supported: " if spec_ok else "Not supported: ") + spec
        add("Rushing offence vs run defence", fav,
            f"{o} rushing {ordinal(ro)} (adj. EPA/rush {v(o, 'off_adj_epa_rush', 'epa')}, {v(o, 'off_ypc', 'n2')} yds/carry); "
            f"{d} run defence {ordinal(rdd)} (allows {v(d, 'def_adj_epa_rush', 'epa')}, {v(d, 'def_ypc', 'n2')} yds/carry).",
            "Designed runs that keep the offence on schedule, shorter third downs and more play-action." if fav == o else
            "The defence can stop the run with its base front, leave the offence facing long third downs and make it one-dimensional.",
            [f"Run-defence EPA has no reliable team-to-team signal yet (shrinkage keeps {MM['epa_rush']['def']['w'][d]:.0%} of {d}'s record)."
             if MM["epa_rush"]["def"]["w"][d] < 0.35 else None,
             f"{o} offensive-line regulars out: {int(T.loc[o, 'absent_OL'])}." if T.loc[o, "absent_OL"] > 0 else None,
             f"{o} offence has faced {'easier' if T.loc[o, 'sos_off'] > 0 else 'tougher'} defences than average ({T.loc[o, 'sos_off']:+.3f})."
             if abs(T.loc[o, "sos_off"]) > 0.02 else None,
             f"Blocking indicator: {o} yards before contact {v(o, 'ybc_per_att', 'n2')} ({ordinal(r('ybc_per_att', True))}); {d} allows "
             f"{v(d, 'def_ybc_allowed', 'n2')} ({ordinal(rd('def_ybc_allowed', False))})."],
            spec, finding_conf(min(ro, rdd) <= 5 and max(ro, rdd) >= 28, [MM["epa_rush"]["off"]["w"][o], MM["epa_rush"]["def"]["w"][d]]))
    # 2 passing offence vs pass defence
    po, pdd = r("off_adj_epa_db", True), rd("def_adj_epa_db", False)
    if (po <= 10 and pdd >= 23) or (po >= 23 and pdd <= 10):
        fav = o if po <= 10 else d
        q = QBX.get(o, {})
        spec = q.get("text")
        add("Passing offence vs pass defence", fav,
            f"{o} passing {ordinal(po)} (adj. EPA/dropback {v(o, 'off_adj_epa_db', 'epa')}, {v(o, 'off_ypa', 'n2')} Y/A); "
            f"{d} pass defence {ordinal(pdd)} (allows {v(d, 'def_adj_epa_db', 'epa')}, {v(d, 'def_ypa', 'n2')} Y/A).",
            "Efficient early-down passing and third-down conversions through the air." if fav == o else
            "Coverage that limits completions and forces the offence to sustain long drives without big gains.",
            [q.get("caution"),
             f"{d} pass rush {ordinal(rd('def_pressure_rate', True))} in pressure rate could disrupt the passing game." if fav == o and rd("def_pressure_rate", True) <= 10 else None,
             f"{d} defensive-back regulars out: {int(T.loc[d, 'absent_DB'])}." if T.loc[d, "absent_DB"] > 0 else None],
            spec, finding_conf(min(po, pdd) <= 5 and max(po, pdd) >= 28, [MM["epa_db"]["off"]["w"][o], MM["epa_db"]["def"]["w"][d]]))
    # 3/4 protection vs pass rush
    pa, pr = r("off_pressure_rate", False), rd("def_pressure_rate", True)
    if pa <= 8 and pr >= 25:
        add("Strong protection vs weak pass rush", o,
            f"{o} allows pressure on {v(o, 'off_pressure_rate', 'pct')} of dropbacks ({ordinal(pa)}); {d} generates {v(d, 'def_pressure_rate', 'pct')} ({ordinal(pr)}).",
            "Clean pockets: more time for intermediate and deep concepts, fewer sacks and fewer drive-killing negative plays.",
            [f"{d} may blitz more to compensate (blitz rate {v(d, 'def_blitz_rate', 'pct')})."], None,
            finding_conf(pa <= 4 and pr >= 29, [MM["pressure"]["off"]["w"][o], MM["pressure"]["def"]["w"][d]]))
    if pa >= 25 and pr <= 8:
        add("Weak protection vs elite pass rush", d,
            f"{o} allows pressure on {v(o, 'off_pressure_rate', 'pct')} ({ordinal(pa)} in protection); {d} generates {v(d, 'def_pressure_rate', 'pct')} ({ordinal(pr)}).",
            "Pressure that shortens dropbacks, creates sacks and forces hurried throws on obvious passing downs.",
            [f"{o} quarterback time to throw {v(o, 'time_to_throw', 'n2')} s ({ordinal(rank(T.time_to_throw, False)[o])} quickest): a quick game can blunt the rush."
             if rank(T.time_to_throw, False)[o] <= 10 else None,
             (f"PFR pressure data is missing {int((T.games - T.off_pfr_games).clip(lower=0).sum() // 2)} games."
              if (T.games - T.off_pfr_games).clip(lower=0).sum() else None)],
            None, finding_conf(pa >= 29 and pr <= 4, [MM["pressure"]["off"]["w"][o], MM["pressure"]["def"]["w"][d]]))
    # 5 mobile QB vs QB-run containment
    qb_runs_pg = (T.off_scrambles + T.off_qb_runs) / T.games
    mob = int(rank(qb_runs_pg, True)[o])
    cont_rank = int(rank(T.def_scr_epa.fillna(T.def_scr_epa.mean()), False)[d])
    if mob <= 8 and cont_rank >= 23 and T.loc[d, "def_scrambles"] >= SAMPLE_MIN["def_scr_epa"][1]:
        add("Mobile quarterback vs scramble/QB-run containment", o,
            f"{o} quarterback runs and scrambles {qb_runs_pg[o]:.1f} per game ({ordinal(mob)}); {d} allows {v(d, 'def_scr_epa', 'epa')} EPA per scramble "
            f"({ordinal(cont_rank)}) and {v(d, 'def_qb_run_epa', 'epa')} per designed QB run ({int(T.loc[d, 'def_qb_runs'] or 0)} faced).",
            "Extended plays when coverage holds, and designed QB runs that add a blocker in the run game.",
            ["Scramble and QB-run samples are small (a few dozen plays per defence)."], None, "limited")
    # 6 explosive passing vs deep vulnerability
    eo = r("off_expl_pass_rate", True)
    ed1, ed2 = rd("def_expl_pass_rate", False), rd("def_deep_epa", False)
    if T.loc[d, "def_deep_att"] < SAMPLE_MIN["def_deep_epa"][1]:
        ed2 = 0                                       # too few deep attempts faced to use the deep EPA
    if eo <= 8 and (ed1 >= 24 or ed2 >= 24):
        add("Explosive passing vs deep-ball vulnerability", o,
            f"{o} completes 20+ yard passes on {v(o, 'off_expl_pass_rate', 'pct')} of attempts ({ordinal(eo)}); {d} allows {v(d, 'def_expl_pass_rate', 'pct')} "
            f"({ordinal(ed1)}) and {v(d, 'def_deep_epa', 'epa')} EPA on throws of 20+ air yards ({ordinal(ed2)}, {int(T.loc[d, 'def_deep_att'])} faced).",
            "Shot plays off play-action and vertical routes against the coverage's weakest depth.",
            ["Explosive rates are the noisiest passing measure (shrinkage keeps about a third of each team's record)."],
            f"{o} attempts {int(T.loc[o, 'off_deep_att'])} deep passes ({v(o, 'off_deep_epa', 'epa')} EPA each).", "limited")
    # 7 four-man pressure vs poor protection
    h4 = rd("def_hs_noblitz", True)
    if h4 <= 8 and pa >= 22:
        add("Four-man pressure vs poor protection", d,
            f"{d} hits or sacks the quarterback on {v(d, 'def_hs_noblitz', 'pct')} of dropbacks without blitzing ({ordinal(h4)}); "
            f"{o} allows pressure on {v(o, 'off_pressure_rate', 'pct')} ({ordinal(pa)} in protection).",
            "Pressure without extra rushers, so the defence keeps seven in coverage and the quarterback has fewer open targets.",
            ["Hit-or-sack is a play-level proxy for pressure; free data has no play-level pressure."], None,
            "moderate" if h4 <= 4 and pa >= 27 else "limited")
    # 8 blitz-heavy defence vs QB against the blitz
    bz = int(rank(T.def_blitz_rate, True)[d])
    vb = r("off_epa_blitz", True)
    if bz <= 8 and (vb >= 24 or vb <= 8):
        fav = d if vb >= 24 else o
        add("Blitz-heavy defence vs quarterback against the blitz", fav,
            f"{d} sends five or more on {v(d, 'def_blitz_rate', 'pct')} of dropbacks ({ordinal(bz)} highest); {o} averages {v(o, 'off_epa_blitz', 'epa')} "
            f"EPA per dropback against five-plus rushers ({ordinal(vb)}) and {v(o, 'off_epa_noblitz', 'epa')} against four or fewer.",
            "The blitz forces quick decisions; quarterbacks who handle it find the vacated zones for big gains." if fav == o else
            "Extra rushers get home against a passing game that has struggled to adjust protections or throw hot.",
            [QBX.get(o, {}).get("caution"), f"Samples: about {int(T.loc[o, 'off_n_blitz'])} blitzed dropbacks for {o}."], None, "limited")
    # 9 red zone
    zo, zd = r("off_rz_td_rate", True), rd("def_rz_td_rate", False)
    if (zo <= 8 and zd >= 25) or (zo >= 25 and zd <= 8):
        fav = o if zo <= 8 else d
        add("Red-zone offence vs red-zone defence", fav,
            f"{o} scores touchdowns on {v(o, 'off_rz_td_rate', 'pct')} of red-zone trips ({ordinal(zo)}, {int(T.loc[o, 'off_rz_trips'])} trips); "
            f"{d} allows {v(d, 'def_rz_td_rate', 'pct')} ({ordinal(zd)}, {int(T.loc[d, 'def_rz_trips'])} trips).",
            "Converting trips into touchdowns rather than field goals: a four-point swing per trip.",
            ["Offensive red-zone TD rate has no reliable team-to-team signal yet; it regresses strongly towards the league average."], None, "limited")
    # 10 turnovers
    gv = r("giveaway_rate", False)
    iw = r("int_worthy_rate", False)
    tk = rd("takeaway_rate", True)
    fw = rd("def_int_worthy_rate", True)
    if (gv >= 25 or iw >= 25) and (tk <= 8 or fw <= 8):
        add("Turnover-prone offence vs ball-hawking defence", d,
            f"{o} gives the ball away on {v(o, 'giveaway_rate', 'pct')} of plays ({ordinal(gv)}) and throws interception-worthy passes on "
            f"{v(o, 'int_worthy_rate', 'pct')} of attempts ({ordinal(iw)}); {d} takes it away on {v(d, 'takeaway_rate', 'pct')} of plays ({ordinal(tk)}) and forces "
            f"interception-worthy throws on {v(d, 'def_int_worthy_rate', 'pct')} ({ordinal(fw)}).",
            "Short fields and lost possessions, the biggest single-play swings in expected points.",
            [f"Takeaways per drive show no reliable team-to-team signal after {WK['word']} weeks; forced interception-worthy throws are the more repeatable part.",
             QBX.get(o, {}).get("caution")], None, "limited")
    # 11 tackling vs yards after contact / catch
    miss_pfr = int((T.games - T.def_pfr_games).clip(lower=0).sum() // 2)
    mt, ya = rd("def_missed_tackle_pct", False), rd("def_yac_allowed", False)
    yo, yc = r("yac_per_att", True), r("off_yacoe", True)
    if (mt >= 25 or ya >= 25) and (yo <= 8 or yc <= 8):
        add("Poor tackling vs yards after contact and catch", o,
            f"{d} misses {v(d, 'def_missed_tackle_pct', 'pct')} of tackle attempts ({ordinal(mt)}) and allows {v(d, 'def_yac_allowed', 'n2')} rushing yards after contact ({ordinal(ya)}); "
            f"{o} gains {v(o, 'yac_per_att', 'n2')} yards after contact per carry ({ordinal(yo)}) and {v(o, 'off_yacoe', 'n2')} YAC over expected per catch ({ordinal(yc)}).",
            "Short throws and runs that turn into chunk gains after the first contact.",
            [f"PFR tackling data is missing {miss_pfr} games." if miss_pfr else
             "Missed-tackle rates are PFR charting and swing a lot over a few games."], None, "limited")
    return F


def qb_context(t, d_team, MM, qbs, T, hsign):
    """Expected EPA per dropback against this defence under each quarterback scenario (shrunk)."""
    info = qbs.get(t, {})
    m = MM["epa_db"]
    tau2, rv = m["off"]["tau2"], m["resid_var"]
    wd, ed = m["def"]["w"][d_team], m["def"]["eff"][d_team]
    rows = []
    for q in info.get("qbs", []):
        if q["adj_epa_db"] is None and not (q.get("news") and ROLE):
            continue
        rows.append({**q, "exp_db": qb_expect(q, m, wd, ed, hsign, tau2, rv), "w": qb_weight(q["dropbacks"], tau2, rv)})
    text = caution = None
    flags = info.get("flags", [])
    news = next((r for r in info.get("qbs", []) if r.get("news")), None)

    def lab(r):
        tail = "; did not open the season as a starter" if is_backup(r) and ROLE else ""
        tail += "; one quarter carried his total" if r.get("one_q") else ""
        tail += "; no 2026 sample" if r.get("adj_epa_db") is None else ""
        if r.get("news"):
            return r["name"] + f" ({r['news_status']}{tail})"
        if r.get("news_status"):
            return r["name"] + f" ({r['news_status']}; reference only)"
        if r.get("roster_status") == "RES":
            return r["name"] + " (on the reserve list; reference only)"
        return r["name"] + (f" ({tail[2:]})" if tail else "")
    if news is not None:
        lead = next((r for r in rows if r.get("news")), None)
        oth = [r for r in rows if r is not lead and (r["starts"] >= 2 or r["latest_starter"])]
        head = (f"expected EPA/dropback vs {d_team} with {lab(lead)} {lead['exp_db']:+.3f}" if lead else
                f"no 2026 sample for {lab(news)}, so no quarterback-specific expectation")
        text = "; ".join([head] + [f"with {lab(r)} {r['exp_db']:+.3f}" for r in oth]) + "."
    elif len(rows) > 1:
        lat = next((r for r in rows if r["latest_starter"]), rows[0])
        oth = [r for r in rows if r is not lat and r["starts"] >= 2]
        if oth:
            text = "; ".join([f"expected EPA/dropback vs {d_team} with {lab(lat)} {lat['exp_db']:+.3f}"] +
                             [f"with {lab(r)} {r['exp_db']:+.3f}" for r in oth]) + "."
    subst = [f for f in flags if f != "Season figures mix quarterbacks."]
    if subst and (len(flags) > 1 or news is not None or any("likely to start" in f for f in flags)):
        caution = " ".join(subst)
    return {"rows": rows, "flags": flags, "text": text, "caution": caution}


def penalty_hypotheses(o, d, T, g_home, roof):
    H = []
    rk = lambda col, t: int(rank(T[col], True)[t])          # 1 = highest rate
    away_o = o != g_home
    if (away_o and rk("pd_fs_away_per100", o) <= 8 and T.loc[o, "pd_fs_away_per100"] > T.loc[o, "pd_fs_home_per100"]):
        H.append({"team": o, "risk": "False starts on the road",
                  "evidence": f"{o} false starts {T.loc[o, 'pd_fs_away_per100']:.2f} per 100 road snaps ({ordinal(rk('pd_fs_away_per100', o))} most) vs {T.loc[o, 'pd_fs_home_per100']:.2f} at home.",
                  "caveat": f"Crowd effect depends on the venue ({roof or 'roof not listed'}); road samples are three or four games."})
    if rk("pd_off_holding_per100db", o) <= 8 and rk("def_pressure_rate", d) <= 10:
        H.append({"team": o, "risk": "Holding against a strong pass rush",
                  "evidence": f"{o} offensive holding {T.loc[o, 'pd_off_holding_per100db']:.2f} per 100 dropbacks ({ordinal(rk('pd_off_holding_per100db', o))} most); {d} pressure rate {fmt(T.loc[d, 'def_pressure_rate'], 'pct')} ({ordinal(rk('def_pressure_rate', d))}); {d} draws {T.loc[d, 'pd_off_holding_drawn_per100db']:.2f} holds per 100 dropbacks.",
                  "caveat": "Holding is called at the officials' discretion and varies by crew."})
    if rk("pd_cover_fouls_per100db", d) <= 8 and rank(T.off_adj_epa_db, True)[o] <= 12:
        H.append({"team": d, "risk": "Coverage fouls against a strong passing offence",
                  "evidence": f"{d} commits DPI, holding or illegal contact {T.loc[d, 'pd_cover_fouls_per100db']:.2f} times per 100 dropbacks faced ({ordinal(rk('pd_cover_fouls_per100db', d))} most); {o} passing {ordinal(rank(T.off_adj_epa_db, True)[o])} and draws {T.loc[o, 'pd_dpi_drawn_per100db']:.2f} DPIs per 100 dropbacks.",
                  "caveat": "Coverage fouls partly reflect the quality of receivers faced."})
    if T.loc[d, "pen_rtp"] >= 2 and rank(T.def_blitz_rate, True)[d] <= 12:
        H.append({"team": d, "risk": "Roughing the passer from an aggressive rush",
                  "evidence": f"{d} has {int(T.loc[d, 'pen_rtp'])} roughing-the-passer penalties ({T.loc[d, 'pd_rtp_per100db']:.2f} per 100 dropbacks) with a {fmt(T.loc[d, 'def_blitz_rate'], 'pct')} blitz rate; {o} time to throw {fmt(T.loc[o, 'time_to_throw'], 'n2')} s.",
                  "caveat": "A quick release reduces late hits but also the number of rushes that reach the quarterback; counts are small."})
    if rk("pd_def_jump_per100", d) <= 8 and rk("pd_def_jump_drawn_per100", o) <= 10:
        H.append({"team": d, "risk": "Neutral-zone, offside and encroachment fouls against an offence that draws them",
                  "evidence": f"{d} jumps {T.loc[d, 'pd_def_jump_per100']:.2f} times per 100 snaps ({ordinal(rk('pd_def_jump_per100', d))} most); {o} draws {T.loc[o, 'pd_def_jump_drawn_per100']:.2f} ({ordinal(rk('pd_def_jump_drawn_per100', o))} most), a hard-count proxy.",
                  "caveat": "Snap-count use is not charted; drawn fouls are an indirect measure."})
    if rk("pd_off_presnap_per100", o) <= 8 and rk("pd_off_presnap_drawn_per100", d) <= 10:
        H.append({"team": o, "risk": "Pre-snap penalties against a defence that induces them",
                  "evidence": f"{o} pre-snap fouls {T.loc[o, 'pd_off_presnap_per100']:.2f} per 100 snaps ({ordinal(rk('pd_off_presnap_per100', o))} most); {d} draws {T.loc[d, 'pd_off_presnap_drawn_per100']:.2f} ({ordinal(rk('pd_off_presnap_drawn_per100', d))} most).",
                  "caveat": "Alignment disguise is not charted; this uses fouls drawn as the only available proxy."})
    return H


def st_hypothesis(a, h, T):
    out = []
    for t, opp in [(a, h), (h, a)]:
        if rank(T.pen_st_n, True)[t] <= 8 and rank(T.st_epa_pg, True)[opp] <= 10:
            out.append({"team": t, "risk": "Special-teams penalties against a strong field-position unit",
                        "evidence": f"{t} has {int(T.loc[t, 'pen_st_n'])} special-teams penalties ({ordinal(rank(T.pen_st_n, True)[t])} most); {opp} special teams {ordinal(rank(T.st_epa_pg, True)[opp])} ({fmt(T.loc[opp, 'st_epa_pg'], 's2')} EPA/game).",
                        "caveat": "Special-teams penalty counts are small (two to twelve per team)."})
    return out


def workload_view(t, T, trv_row):
    r = T.loc[t]
    heavy_last = rank(T.def_snaps_last, True)[t] <= 8
    exposed = rank(T.off_three_out_rate, True)[t] <= 8 or rank(T.def_quick_pg, True)[t] <= 8
    rest = trv_row.get("rest") if trv_row else None
    short = rest is not None and rest <= 5
    lines = [f"Defence played {int(r.def_snaps_last)} snaps in its last game (week {int(r.last_week_played)}; season average {r.def_snaps_pg:.1f}, "
             f"{ordinal(rank(T.def_snaps_last, True)[t])} most last week).",
             f"Offence three-and-out rate {fmt(r.off_three_out_rate, 'pct')} ({ordinal(rank(T.off_three_out_rate, True)[t])} highest); "
             f"{r.def_quick_pg:.1f} quick turnarounds per game for the defence ({ordinal(rank(T.def_quick_pg, True)[t])} most); "
             f"median {r.def_rest_min_median:.1f} real minutes between defensive drives."]
    level = "none"
    if heavy_last and short:
        level = "plausible"
    elif heavy_last or (exposed and short):
        level = "minor"
    return {"lines": lines, "level": level, "heavy_last": bool(heavy_last), "exposed": bool(exposed), "short": bool(short)}


def travel_view(t, trv, study):
    if not trv:
        return None
    lines = []
    rest = trv.get("rest")
    lines.append(f"{int(rest) if rest == rest else 'n/a'} days of rest (previous game {trv.get('prev_weekday') or 'n/a'}"
                 f"{', international: ' + str(trv.get('prev_stadium')) if trv.get('prev_intl') in (True, 'True') else ''}).")
    neutral = trv.get("neutral") in (True, "True")
    if trv.get("side") == "away" or neutral:
        km = trv.get("km")
        lines.append(f"Travels {km:,.0f} km; time-zone change {trv.get('tz_diff'):+.0f} h; kickoff {trv.get('local_time')} local, "
                     f"{trv.get('body_clock')} on the team's home clock; road game {int(trv.get('road_streak'))} in a row.")
        h = trv.get("hist")
        if isinstance(h, str):
            try:
                import ast
                h = ast.literal_eval(h)
            except Exception:
                h = None
        if h:
            lines.append(f"History ({study['seasons'][0]}-{study['seasons'][1]}): away teams in this situation ({h['group']}) did "
                         f"{h['vs_same']:+.1f} points vs same-time-zone trips (95% CI {h['vs_lo']:+.1f} to {h['vs_hi']:+.1f}; {h['n']} games).")
    else:
        lines.append("Home game; no travel.")
    if neutral:
        lines.insert(1, f"Neutral site ({trv.get('stadium')}): both teams travel.")
    if rest == rest and rest is not None:
        if rest >= 13:
            lines.append("Coming off a bye: teams after a bye beat their expected margin by about 1.2 points in 2002-25 (95% CI +0.3 to +2.1).")
        elif rest <= 5:
            lines.append("Short week: in 2002-25 short-week teams performed in line with expectation (no measurable effect), but both teams share the short week in Thursday games.")
    return lines


def structured_reports(T, nxt, MM, games, qbs, trv, study, fat):
    out = {}
    tr_by = {r["team"]: r for r in trv}
    for g in games:
        a, h = g["away"], g["home"]
        roof = next((x for x in [g["venue"]] if x), "")
        parts = {"mismatches": [], "workload": {}, "travel": {}, "penalties": [], "qb": {}, "counter": [], "confidence": ""}
        for o, d in [(a, h), (h, a)]:
            hsign = 0 if g["neutral"] else (1 if o == h else -1)
            qx = qb_context(o, d, MM, qbs, T, hsign)
            parts["qb"][o] = qx
            parts["mismatches"] += [dict(f, offence=o, defence=d) for f in find_mismatches(o, d, T, MM, {o: qx})]
            parts["penalties"] += penalty_hypotheses(o, d, T, h, roof)
        parts["penalties"] += st_hypothesis(a, h, T)
        order = {"strong": 0, "moderate": 1, "limited": 2}
        parts["mismatches"].sort(key=lambda f: order[f["conf"]])
        for t in (a, h):
            parts["workload"][t] = workload_view(t, T, tr_by.get(t))
            parts["travel"][t] = travel_view(t, tr_by.get(t), study)
        cn = []
        for f in parts["mismatches"]:
            cn += [f"{f['kind']} ({f['favours']}): {n}" for n in f["neutralisers"]]
        cn.append(f"League-wide fatigue check ({fat['seasons'][0]}-{fat['seasons'][-1]}): ten extra defensive plays earlier in a game changed EPA allowed per play by "
                  f"{fat['play_epa']['coef']:+.4f} (95% CI {fat['play_epa']['coef'] - 1.96 * fat['play_epa']['se']:+.3f} to {fat['play_epa']['coef'] + 1.96 * fat['play_epa']['se']:+.3f}), "
                  "so workload concerns are context, not an expected effect.")
        parts["counter"] = cn
        ns = sum(f["conf"] == "strong" for f in parts["mismatches"])
        nm = sum(f["conf"] == "moderate" for f in parts["mismatches"])
        parts["confidence"] = (f"{len(parts['mismatches'])} potential mismatch(es): {ns} strong, {nm} moderate, "
                               f"{len(parts['mismatches']) - ns - nm} limited. {WK['word'].capitalize()} weeks of data; every rank carries wide uncertainty.")
        out[g["id"]] = parts
    return out


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
    WK.update(thru=meta["through_week"], word=WORDS.get(meta["through_week"], str(meta["through_week"])))
    NG = load_ngs(meta["season"])
    if NG:
        for t, rec in NG["teams"].items():
            for k, v in rec.items():
                if k in NGS_LABELS and t in T.index:
                    T.loc[t, f"ngs_{k}"] = v
    CAL = meta.get("calibration")
    if CAL:
        NOTABLE["v"] = CAL["edges"]["notable"]
    notes_path = d / "analyst_notes.json"
    notes = json.loads(notes_path.read_text(encoding="utf-8")) if notes_path.exists() else {}
    T = derive(T, G, meta)
    CL = json.loads((d / "callers.json").read_text(encoding="utf-8"))
    T = apply_callers(T, CL)
    T, WR, wr_probs = apply_win_rates(T, meta)
    if wr_probs:
        print("WIN RATES NOT USED:", "; ".join(wr_probs[:6]))
    GT = json.loads((d / "garbage.json").read_text(encoding="utf-8"))
    T = apply_garbage(T, GT)
    DP = json.loads((d / "depth.json").read_text(encoding="utf-8"))
    T = apply_depth(T, DP)
    PL = json.loads((d / "players.json").read_text(encoding="utf-8"))
    US = json.loads((d / "usage.json").read_text(encoding="utf-8"))
    au = {(u["team"], u["player"]): u for u in US["absent_usage"]}
    A["usage"] = [usage_text(au.get((t, n), {})) for t, n in zip(A.team, A.player)]
    T = apply_players(T, PL)
    nxt_up = {(r["team"], r["player"]): r for r in DP["depth"]["absences"]}
    NU = DP.get("nextup", {})
    A["next_up_quality"] = [NU.get(f"{t}|{n}", {}).get("text") for t, n in zip(A.team, A.player)]
    REF = json.loads((d / "referees.json").read_text(encoding="utf-8"))
    rr_file = Path(__file__).resolve().parent / f"referee_rates_{meta['season']}.json"
    if rr_file.exists():                       # this season's rates from a hand-kept, dated source (see the file)
        RR = json.loads(rr_file.read_text(encoding="utf-8"))
        order = sorted(RR["refs"], key=lambda k: -RR["refs"][k]["flags_pg"])
        for i, k in enumerate(order):
            RR["refs"][k]["rank"] = i + 1
        RR["n"] = len(order)
        REF["season_rates"] = RR
    ARR = json.loads((d / "arrivals.json").read_text(encoding="utf-8"))
    UN = json.loads((d / "unusual.json").read_text(encoding="utf-8"))
    WX = json.loads((d / "weather.json").read_text(encoding="utf-8")) if (d / "weather.json").exists() else None
    A["when"] = [absence_when(x) for x in A.itertuples()]
    A["presence"] = [presence(x) if x.term == "long-term" else "" for x in A.itertuples()]
    A = A.assign(**{k: [nxt_up.get((t, n), {}).get(k) for t, n in zip(A.team, A.player)]
                    for k in ("slot", "next_up", "next_up_rank", "next_up_snaps", "next_up_games", "next_up_last_share", "still_first", "note")})
    wr_note = "" if wr_probs else (f" Win rates: {WR['source']['title']} ({WR['source']['updated']}); ESPN Analytics from NFL Next Gen Stats tracking, not in nflverse. ESPN publishes whole percentages, so tied teams share a rank here."
               + ("" if WR["through_week"] == meta["through_week"] else f" STALE: win rates run through week {WR['through_week']}, the report through week {meta['through_week']}.")) if WR else ""
    U = unit_ranks(T)
    profiles = {t: profile(t, T, U, G, meta) for t in T.index}
    MM = json.loads((d / "matchup_models.json").read_text())
    CTX = json.loads((d / "context.json").read_text())
    mm = mismatches(T, nxt, MM, CTX["qb"])
    TRV = pd.read_csv(d / "travel_next_week.csv").replace({np.nan: None}).to_dict("records")
    PEN_T = pd.read_csv(d / "penalties_by_type.csv")
    order = list(T.sort_values("rating_pg", ascending=False).index)

    # ---------------- tables
    tables = []
    tables.append(table("power", "Power rankings: all ten categories", [
        C("record", "Record", "str", 0), C("rating_pg", "Overall team", "s1", 1, "Opponent-adjusted net EPA converted to points per game (offence + defence) plus the kept share of special-teams EPA per game (see Method)"),
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
    ], "def_adj_epa", "Lower is better for every allowed-rate column.", desc=False))
    for side, title, who in (("off", "Garbage time: offences", "offence"), ("def", "Garbage time: defences", "defence")):
        pre = f"gt_{side}_"
        if side == "off":
            trail_l, lead_l = "trailing badly", "protecting a lead"
        else:
            trail_l, lead_l = "vs offences trailing badly", "vs offences protecting a lead"
        tables.append(table(f"gt_{side}", title, [
            C(pre + "lop_play_share", "Lopsided snaps", "pct", 0, "Share of scrimmage snaps with the offence's win probability below 10% or above 90%"),
            C(pre + "trail_plays", f"Plays {trail_l}", "int", 0), C(pre + "trail_yds", "Yards", "int", 0), C(pre + "trail_tds", "TDs", "int", 0),
            C(pre + "lead_plays", f"Plays {lead_l}", "int", 0), C(pre + "lead_yds", "Yards", "int", 0), C(pre + "lead_tds", "TDs", "int", 0),
            C(pre + "lop_yds_share", "Share of yards, lopsided", "pct", 0), C(pre + "lop_td_share", "Share of TDs, lopsided", "pct", 0),
            C(pre + "epa_all", "EPA/play, all snaps" + (" allowed" if side == "def" else ""), "epa", 1 if side == "off" else -1),
            C(pre + "comp_epa", "EPA/play, competitive" + (" allowed" if side == "def" else ""), "epa", 1 if side == "off" else -1),
            C(pre + "gt_effect", "All minus competitive", "epa", 0, "Positive: the all-snap figure is higher than in competitive snaps"),
            C(pre + "flag", "Raw numbers", "str", 0),
        ], pre + "gt_effect", f"Competitive = offence win probability 10-90% (the efficiency tables' check column). Flag at a gap of "
                              f"{GT['flag_epa']:.2f} EPA/play or more. Display only: every rating uses all snaps, because dropping garbage time "
                              "did not improve the project's predictions."))
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
        C("off_sacks", "Sacks taken", "int", -1), C("off_sack_yds_lost", "Sack yards lost", "int", -1),
        C("off_sack_yds_pg", "Sack yards lost/game", "n1", -1), C("off_sack_yds_per_sack", "Yards lost per sack", "n1", -1),
        C("off_pressure_to_sack", "Sacks/pressure", "pct", -1), C("time_to_throw", "Time to throw (s)", "n2", 0, "Next Gen Stats, attempt-weighted"),
        C("off_epa_db_clean", "EPA, no hit/sack", "epa", 1), C("off_epa_db_hit", "EPA, hit or sacked", "epa", 1),
        C("off_early_db_epa", "Early-down EPA/db", "epa", 1), C("off_d3_db_epa", "3rd-down EPA/db", "epa", 1), C("off_rz_db_epa", "Red-zone EPA/db", "epa", 1),
        C("off_yacoe", "YAC over expected", "n2", 1), C("off_drop_rate", "Drop rate", "pct", -1, "FTN drops / catchable balls"),
        C("off_air_per_cmp", "Air yds/completion", "n1", 0, "Completed air yards per completion (play-by-play)"),
        C("off_yac_per_cmp", "YAC/completion", "n1", 1),
        C("off_air_share", "Share of yards in the air", "pct", 0, "Completed air yards / (air yards + YAC): low = a YAC-driven passing game"),
        C("rec_brk_tkl_pg", "Broken tackles after catch/game", "n2", 1, "PFR receiving broken tackles per game with PFR data"),
        C("off_drops_ftn", "Drops (FTN)", "int", -1, "FTN-charted drops; the drop rate uses the same charting"),
        C("rec_drops", "Drops (PFR)", "int", -1), C("rec_drops_pg", "Drops/game (PFR)", "n2", -1, "PFR and FTN chart drops separately and can differ"),
        C("off_pa_rate", "Play-action rate", "pct", 0), C("off_epa_pa", "EPA on play action", "epa", 1), C("off_epa_oop", "EPA out of pocket", "epa", 1),
        C("off_contested_rate", "Contested targets", "pct", -1, "FTN: share of targets thrown into tight coverage"),
        C("off_contested_cmp", "Contested catch rate", "pct", 1), C("off_created_rec", "Created receptions", "int", 1, "FTN: catches the receiver made on a poor or difficult ball"),
        C("off_qb_fault_sacks", "Sacks on the QB (FTN)", "int", -1, "FTN: sacks charted as the quarterback's fault (held the ball, ran into it)"),
        C("off_qb_fault_sack_share", "Share of sacks on the QB", "pct", 0, "High = the sacks say more about the QB than the line"),
        C("off_deep_epa", "EPA, 20+ air yd", "epa", 1), C("cov", "Man/zone splits", "str", 0, "Not available in free data"),
    ], "off_adj_epa_db"))
    tables.append(table("receiving", "Receivers: separation and yards after catch (Next Gen)", [
        C("rec_separation", "Separation at catch/incompletion (yd)", "n2", 1, "Target-weighted average distance to the nearest defender when the ball arrives"),
        C("rec_cushion", "Cushion at snap (yd)", "n2", 0, "Target-weighted distance to the nearest defender at the snap: how far off coverage plays"),
        C("rec_air_yards", "Intended air yards/target", "n1", 0), C("rec_yacoe", "YAC over expected/catch", "s2", 1),
        C("rec_catch_pct", "Catch rate (%)", "n1", 1), C("rec_players", "Receivers tracked", "int", 0),
        C("rec_targets", "Targets covered", "int", 0), C("rec_top", "Most-targeted (his separation)", "str", 0),
    ], "rec_separation", "Next Gen season rows cover qualifying receivers only, so low-volume receivers are missing. Separation rises with "
                         "short, schemed-open throws (compare intended air yards). Offence only: Next Gen does not credit defenders."))
    tables.append(table("tgt_pos_off", "Where the targets go: WR, TE and RB", [
        C("off_tgt_share_WR", "Target share, WRs", "pct", 0), C("off_ypt_WR", "Yds/target, WRs", "n2", 1),
        C("off_epa_tgt_WR", "EPA/target, WRs", "epa", 1), C("off_sr_tgt_WR", "Success, WRs", "pct", 1),
        C("off_tgt_share_TE", "Target share, TEs", "pct", 0), C("off_ypt_TE", "Yds/target, TEs", "n2", 1),
        C("off_epa_tgt_TE", "EPA/target, TEs", "epa", 1), C("off_sr_tgt_TE", "Success, TEs", "pct", 1),
        C("off_tgt_share_RB", "Target share, RBs", "pct", 0), C("off_ypt_RB", "Yds/target, RBs", "n2", 1),
        C("off_epa_tgt_RB", "EPA/target, RBs", "epa", 1), C("off_sr_tgt_RB", "Success, RBs", "pct", 1),
    ], "off_epa_tgt_TE", "Targets by the receiver's position on the weekly roster (fullbacks count as RBs). Slot vs outside receivers needs alignment data, which free sources do not have."))
    tables.append(table("zones_off", "Where the throws go: depth and direction", [
        C("off_zone_share_short_left", "Short left: share", "pct", 0), C("off_epa_short_left", "Short left: EPA/att", "epa", 1),
        C("off_zone_share_short_middle", "Short middle: share", "pct", 0), C("off_epa_short_middle", "Short middle: EPA/att", "epa", 1),
        C("off_zone_share_short_right", "Short right: share", "pct", 0), C("off_epa_short_right", "Short right: EPA/att", "epa", 1),
        C("off_zone_share_deep_left", "Deep left: share", "pct", 0), C("off_epa_deep_left", "Deep left: EPA/att", "epa", 1),
        C("off_zone_share_deep_middle", "Deep middle: share", "pct", 0), C("off_epa_deep_middle", "Deep middle: EPA/att", "epa", 1),
        C("off_zone_share_deep_right", "Deep right: share", "pct", 0), C("off_epa_deep_right", "Deep right: EPA/att", "epa", 1),
    ], "off_zone_share_deep_middle", "nflfastR throw location: deep = 15+ air yards; left, middle and right are where the ball was thrown. Shares add to 100% across the six zones; deep-zone EPA rests on few throws."))
    tables.append(table("pass_def", "Pass defence", [
        C("def_dropbacks", "Dropbacks faced", "int", 0), C("def_epa_db", "EPA/db allowed", "epa", -1), C("def_adj_epa_db", "Adj. EPA/db", "epa", -1),
        C("def_sr_db", "Success allowed", "pct", -1), C("def_cpoe", "CPOE allowed", "n1", -1), C("def_ypa", "Y/A allowed", "n2", -1),
        C("def_nya", "NY/A allowed", "n2", -1), C("def_pass_fd", "1st downs/db", "pct", -1),
        C("def_expl_pass_rate", "20+ yd rate", "pct", -1), C("def_n_expl_pass", "20+ yd allowed", "int", -1),
        C("def_pass_td", "Pass TD allowed", "int", -1), C("int_made", "INTs", "int", 1), C("def_int_worthy_rate", "INT-worthy throws forced", "pct", 1),
        C("def_sack_rate", "Sack rate", "pct", 1), C("def_pressure_rate", "Pressure rate", "pct", 1),
        C("def_sacks", "Sacks", "int", 1), C("def_sack_yds_lost", "Sack yards gained", "int", 1, "Yards opponents lost to this defence's sacks"),
        C("def_sack_yds_pg", "Sack yards gained/game", "n1", 1), C("def_sack_yds_per_sack", "Yards per sack", "n1", 1),
        C("def_contested_rate", "Contested targets forced", "pct", 1, "FTN: share of targets into tight coverage"),
        C("def_contested_cmp", "Contested catches allowed", "pct", -1),
        C("pl_top_cov", "Most-targeted defender (targets, rating allowed)", "str", 0, "PFR nearest defender in coverage"),
        C("pl_tgt_out_share", "Targets on defenders now out", "pct", 0, "Share of targets where the nearest defender is now out (reserve list or Out/Doubtful)"),
        C("def_deep_att", "Deep att. faced", "int", 0), C("def_deep_epa", "EPA allowed, 20+ air yd", "epa", -1), C("def_deep_comp", "Deep comp. allowed", "pct", -1),
        C("def_air_per_cmp", "Air yds/completion allowed", "n1", 0), C("def_yac_per_cmp", "YAC/completion allowed", "n1", -1),
        C("def_air_share", "Share allowed in the air", "pct", 0, "Low = a defence that gives up its yards after the catch (tackling, zone underneath)"),
        C("def_yacoe", "YAC over expected allowed", "n2", -1),
        C("def_rec_brk_tkl_allowed_pg", "Missed tackles after catch/game", "n2", -1, "PFR receiving broken tackles by opponents, per game with PFR data"),
        C("def_epa_pa", "EPA vs play action", "epa", -1), C("def_epa_screen", "EPA vs screens", "epa", -1),
        C("def_early_db_epa", "Early-down EPA/db", "epa", -1), C("def_d3_db_epa", "3rd-down EPA/db", "epa", -1), C("def_rz_db_epa", "Red-zone EPA/db", "epa", -1),
    ], "def_adj_epa_db", desc=False))
    tables.append(table("tgt_pos_def", "Targets allowed by position: WR, TE and RB", [
        C("def_tgt_share_WR", "Target share, WRs", "pct", 0), C("def_ypt_WR", "Yds/target, WRs", "n2", -1),
        C("def_epa_tgt_WR", "EPA/target, WRs", "epa", -1), C("def_sr_tgt_WR", "Success, WRs", "pct", -1),
        C("def_tgt_share_TE", "Target share, TEs", "pct", 0), C("def_ypt_TE", "Yds/target, TEs", "n2", -1),
        C("def_epa_tgt_TE", "EPA/target, TEs", "epa", -1), C("def_sr_tgt_TE", "Success, TEs", "pct", -1),
        C("def_tgt_share_RB", "Target share, RBs", "pct", 0), C("def_ypt_RB", "Yds/target, RBs", "n2", -1),
        C("def_epa_tgt_RB", "EPA/target, RBs", "epa", -1), C("def_sr_tgt_RB", "Success, RBs", "pct", -1),
    ], "def_epa_tgt_TE", "What each defence allows when opponents target each position. Lower is better for every allowed column.", desc=False))
    tables.append(table("zones_def", "Throws allowed by depth and direction", [
        C("def_zone_share_short_left", "Short left: share", "pct", 0), C("def_epa_short_left", "Short left: EPA/att", "epa", -1),
        C("def_zone_share_short_middle", "Short middle: share", "pct", 0), C("def_epa_short_middle", "Short middle: EPA/att", "epa", -1),
        C("def_zone_share_short_right", "Short right: share", "pct", 0), C("def_epa_short_right", "Short right: EPA/att", "epa", -1),
        C("def_zone_share_deep_left", "Deep left: share", "pct", 0), C("def_epa_deep_left", "Deep left: EPA/att", "epa", -1),
        C("def_zone_share_deep_middle", "Deep middle: share", "pct", 0), C("def_epa_deep_middle", "Deep middle: EPA/att", "epa", -1),
        C("def_zone_share_deep_right", "Deep right: share", "pct", 0), C("def_epa_deep_right", "Deep right: EPA/att", "epa", -1),
    ], "def_epa_deep_middle", "Shares show where opponents throw against this defence; EPA is allowed per attempt (lower is better).", desc=False))
    tables.append(table("rush_off", "Rushing offence", [
        C("off_rushes", "Designed rushes", "int", 0), C("off_epa_rush", "EPA/rush", "epa", 1), C("off_adj_epa_rush", "Adj. EPA/rush", "epa", 1),
        C("off_sr_rush", "Success", "pct", 1), C("off_ypc", "Yards/carry", "n2", 1),
        C("off_rb_ypc", "Yards/carry, non-QB runs", "n2", 1, "Designed runs by anyone but a quarterback"), C("off_rush_fd", "1st-down rate", "pct", 1),
        C("off_expl_run_rate", "10+ yd rate", "pct", 1), C("off_stuff_rate", "Stuff rate (<=0 yd)", "pct", -1),
        C("rbwr", "Run block win rate (ESPN)", "pct", 1, "ESPN Analytics run block win rate (tracking data)"),
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
        C("off_box_avg", "Avg box faced", "n2", 0, "FTN: defenders in the box on designed runs"),
        C("off_box7p_rate", "Runs vs 7+ box", "pct", 0), C("off_box8_rate", "Runs vs 8+ box", "pct", 0),
        C("off_epa_rush_box7p", "EPA/run vs 7+ box", "epa", 1), C("off_n_rush_box7p", "Runs vs 7+", "int", 0),
        C("off_epa_rush_box6m", "EPA/run vs 6 or fewer", "epa", 1), C("off_n_rush_box6m", "Runs vs 6 or fewer", "int", 0),
    ], "off_adj_epa_rush"))
    tables.append(table("rush_def", "Run defence", [
        C("def_rushes", "Designed rushes faced", "int", 0), C("def_epa_rush", "EPA/rush allowed", "epa", -1), C("def_adj_epa_rush", "Adj. EPA/rush", "epa", -1),
        C("def_sr_rush", "Success allowed", "pct", -1), C("def_ypc", "Yards/carry", "n2", -1),
        C("def_rb_ypc", "Yards/carry, non-QB runs", "n2", -1), C("def_rush_fd", "1st-down rate", "pct", -1),
        C("def_expl_run_rate", "10+ yd allowed", "pct", -1), C("def_stuff_rate", "Stuff rate", "pct", 1),
        C("rswr", "Run stop win rate (ESPN)", "pct", 1, "ESPN Analytics run stop win rate (tracking data)"),
        C("def_sy_conv", "Short-yardage allowed", "pct", -1), C("def_gl_td", "TD rate inside 3", "pct", -1),
        C("def_ybc_allowed", "Yds before contact allowed", "n2", -1), C("def_yac_allowed", "Yds after contact allowed", "n2", -1),
        C("def_missed_tackle_pct", "Missed tackle %", "pct", -1, "PFR, all plays"),
        C("def_qb_runs", "QB designed runs faced", "int", 0), C("def_qb_run_epa", "EPA vs QB designed runs", "epa", -1),
        C("def_scr_epa", "EPA vs scrambles", "epa", -1),
        C("def_box_avg", "Avg box on runs", "n2", 0, "FTN: defenders in the box on designed runs faced"),
        C("def_box7p_rate", "7+ box rate", "pct", 0), C("def_box8_rate", "8+ box rate", "pct", 0),
        C("def_epa_rush_box7p", "EPA allowed, 7+ box", "epa", -1), C("def_n_rush_box7p", "Runs, 7+", "int", 0),
        C("def_epa_rush_box6m", "EPA allowed, 6 or fewer", "epa", -1), C("def_n_rush_box6m", "Runs, 6 or fewer", "int", 0),
    ], "def_adj_epa_rush", "Box counts are FTN charting on designed runs. 8+ boxes are rare (under 10% of runs), so EPA is split at 7+ vs 6 or fewer; check the run counts beside each split.", desc=False))
    tables.append(table("run_dir_off", "Inside vs outside runs: offences", [
        C("off_in_share", "Share inside", "pct", 0, "Designed runs between the guards (middle, or guard gap)"),
        C("off_epa_in", "EPA/run inside", "epa", 1), C("off_sr_in", "Success inside", "pct", 1),
        C("off_ypc_in", "Yds/carry inside", "n2", 1), C("off_n_in", "Runs inside", "int", 0),
        C("off_epa_out", "EPA/run outside", "epa", 1), C("off_sr_out", "Success outside", "pct", 1),
        C("off_ypc_out", "Yds/carry outside", "n2", 1), C("off_n_out", "Runs outside", "int", 0),
    ], "off_epa_in", "Play-by-play run location: inside = middle or guard gap, outside = tackle or end. A direction split, not the blocking scheme (inside zone, outside zone, duo, power are not in free data). Designed runs only, scrambles excluded."))
    tables.append(table("run_dir_def", "Inside vs outside runs: defences", [
        C("def_in_share", "Share inside", "pct", 0, "Designed runs between the guards (middle, or guard gap)"),
        C("def_epa_in", "EPA/run inside allowed", "epa", -1), C("def_sr_in", "Success inside", "pct", -1),
        C("def_ypc_in", "Yds/carry inside", "n2", -1), C("def_n_in", "Runs inside", "int", 0),
        C("def_epa_out", "EPA/run outside allowed", "epa", -1), C("def_sr_out", "Success outside", "pct", -1),
        C("def_ypc_out", "Yds/carry outside", "n2", -1), C("def_n_out", "Runs outside", "int", 0),
    ], "def_epa_in", "Lower is better for every allowed column.", desc=False))
    tables.append(table("expl_off", "Explosive offence: passes and runs", [
        C("off_expl_rate", "Explosive rate (all)", "pct", 1), C("off_n_explosive", "Explosives", "int", 1),
        C("off_n_expl_pass", "20+ yd passes", "int", 1), C("off_expl_pass_rate", "20+ yd pass rate", "pct", 1, "Per pass attempt"),
        C("off_n_expl_run", "10+ yd runs", "int", 1), C("off_expl_run_rate", "10+ yd run rate", "pct", 1, "Per designed rush"),
        C("off_n_expl_scr", "10+ yd scrambles", "int", 1),
        C("off_expl_pass_share", "Share via passes", "pct", 0, "20+ yd passes / all explosives: how a team gets its big plays"),
        C("off_expl_epa_share", "Share of positive EPA on explosives", "pct", 0, "EPA gained on explosive plays / all positive EPA"),
        C("off_expl_td", "TDs on explosives", "int", 1),
        C("off_epa_nonexpl", "EPA/play, non-explosive", "epa", 1), C("off_sr_nonexpl", "Success, non-explosive", "pct", 1),
    ], "off_expl_rate", "Explosive = completed pass of 20+ yards, designed rush or scramble of 10+ yards (no-play penalties excluded). "
                        "Pass and run rates use their own denominators (attempts, designed rushes)."))
    tables.append(table("expl_def", "Explosive defence: passes and runs allowed", [
        C("def_expl_rate", "Explosive rate allowed", "pct", -1), C("def_n_explosive", "Explosives allowed", "int", -1),
        C("def_n_expl_pass", "20+ yd passes", "int", -1), C("def_expl_pass_rate", "20+ yd pass rate", "pct", -1, "Per pass attempt faced"),
        C("def_n_expl_run", "10+ yd runs", "int", -1), C("def_expl_run_rate", "10+ yd run rate", "pct", -1, "Per designed rush faced"),
        C("def_n_expl_scr", "10+ yd scrambles", "int", -1),
        C("def_expl_pass_share", "Share via passes", "pct", 0, "20+ yd passes allowed / all explosives allowed: where the defence leaks"),
        C("def_expl_td", "TDs on explosives allowed", "int", -1), C("def_epa_on_explosive", "EPA allowed on explosives", "n1", -1),
        C("def_epa_nonexpl", "EPA/play, non-explosive", "epa", -1), C("def_sr_nonexpl", "Success, non-explosive", "pct", -1),
    ], "def_expl_rate", "Lower is better for every allowed column.", desc=False))
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
        C("prwr", "Pass rush win rate (ESPN)", "pct", 1, "Share of pass rushes that beat a block within 2.5 s (ESPN Analytics, tracking data)"),
        C("def_qb_fault_sack_share", "Its sacks on the QB", "pct", 0, "FTN: share of this defence's sacks charted as the quarterback's fault (low = the rush earned them)"),
        C("pl_top_rusher", "Top pass rusher (pressures, share)", "str", 0, "PFR player pressures"),
        C("pl_top3_press_share", "Top-3 share of pressures", "pct", 0, "High = pressure depends on a few players"),
        C("pl_press_out_share", "Pressures by players now out", "pct", 0, "Share of the team's player pressures made by players now out (reserve list or Out/Doubtful)"),
    ], "def_pressure_rate", "Pressure counts the whole play (coverage and the QB's hold time too); win rate isolates the rushers." + wr_note))
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
        C("pbwr", "Pass block win rate (ESPN)", "pct", 1, "Share of pass-blocking snaps where the line holds its blocks for 2.5 s (ESPN Analytics)"),
        C("off_qb_fault_sack_share", "Sacks on the QB", "pct", 0, "FTN: share of sacks charted as the quarterback's fault, not the line's"),
    ], "off_pressure_rate", "Pressure allowed also reflects the QB's hold time and receivers getting open; pass block win rate isolates the line." + wr_note, desc=False))
    if NG:
        cbf = Path(__file__).resolve().parent / "coverage_backtest.json"
        CB = json.loads(cbf.read_text(encoding="utf-8")) if cbf.exists() else None
        src = (f"Next Gen Stats via NFL.com Next Gen Trends ({NG['source']['url']}), read {NG['source']['retrieved']}"
               + ("" if NG["through_week"] == meta["through_week"] else f"; runs through week {NG['through_week']} only") + ". Usage shares, not efficiency.")
        tables.append(table("ngs_off", "Offensive scheme (Next Gen Stats)", [
            C("ngs_off_11p", "11 personnel", "pct", 0, "1 RB, 1 TE, 3 WR"), C("ngs_off_12p", "12 personnel", "pct", 0), C("ngs_off_13p", "13 personnel", "pct", 0),
            C("ngs_off_21p", "21 personnel", "pct", 0), C("ngs_off_called_pass", "Called pass rate", "pct", 0),
            C("ngs_off_ed_play_action", "Early-down play action", "pct", 0), C("ngs_off_motion", "Motion", "pct", 0),
            C("ngs_off_tempo_sec", "Seconds between snaps", "n1", 0), C("ngs_off_quick_pass", "Quick passes", "pct", 0),
            C("ngs_off_in_breaking", "In-breaking targets", "pct", 0), C("ngs_off_out_breaking", "Out-breaking targets", "pct", 0),
            C("ngs_off_10plus_air", "Targets 10+ air yards", "pct", 0), C("ngs_off_inside_zone", "Inside zone", "pct", 0),
            C("ngs_off_outside_zone", "Outside zone", "pct", 0), C("ngs_off_gap", "Gap", "pct", 0), C("ngs_off_man_blocking", "Man blocking", "pct", 0),
        ], "ngs_off_called_pass", "How each offence lines up and calls plays, as charted by Next Gen Stats tracking. " + src
           + (f" Personnel tendencies hold up well within a season (11 personnel: first-half to second-half correlation "
              f"{CB['tendencies']['offence 11 personnel rate']['corr']:.2f}, {CB['seasons'][0]}-{CB['seasons'][-1]})." if CB else ""), desc=False))
        tables.append(table("ngs_def", "Coverage, personnel and pass rush (Next Gen Stats)", [
            C("ngs_def_zone", "Zone", "pct", 0), C("ngs_def_man", "Man", "pct", 0), C("ngs_def_press", "Press", "pct", 0),
            C("ngs_def_single_high", "Single-high", "pct", 0, "One deep safety (middle of the field closed)"),
            C("ngs_def_split_safety", "Split-safety", "pct", 0, "Two deep safeties"), C("ngs_def_cover0", "Cover 0", "pct", 0),
            C("ngs_def_base", "Base", "pct", 0), C("ngs_def_nickel", "Nickel", "pct", 0), C("ngs_def_dime", "Dime", "pct", 0),
            C("ngs_def_blitz", "Blitz rate", "pct", 0, "5+ rushers"), C("ngs_def_pressure_blitz", "Pressure when blitzing", "pct", 1),
            C("ngs_def_pressure_no_blitz", "Pressure without a blitz", "pct", 1, "4 or fewer rushers"),
        ], "ngs_def_zone", "How each defence lines up, covers and rushes, as charted by Next Gen Stats. " + src
           + (f" Tested on {CB['seasons'][0]}-{CB['seasons'][-1]} charting: coverage and personnel tendencies hold up within a season (first-half to "
              f"second-half correlation: zone {CB['tendencies']['defence zone rate']['corr']:.2f}, single-high {CB['tendencies']['defence single-high rate']['corr']:.2f}, "
              f"blitz {CB['tendencies']['defence blitz rate (5+ rushers)']['corr']:.2f}, dime {CB['tendencies']['defence dime rate']['corr']:.2f}); "
              f"pressure rates much less so ({CB['tendencies']['defence pressure rate without blitz']['corr']:.2f} without a blitz). EPA allowed in a given "
              f"coverage did not hold up beyond the defence's overall figure, so it is not shown." if CB else ""), desc=False))
    tables.append(table("presnap", "Pre-snap motion, RPO and tempo", [
        C("off_motion_rate", "Motion rate", "pct", 0, "FTN: share of scrimmage plays with pre-snap motion"),
        C("off_epa_motion", "EPA/play with motion", "epa", 1), C("off_epa_nomotion", "EPA/play without", "epa", 1),
        C("off_rpo_rate", "RPO rate", "pct", 0), C("off_epa_rpo", "EPA/play on RPOs", "epa", 1),
        C("off_nohuddle_rate", "No-huddle rate", "pct", 0),
        C("def_epa_motion", "Def. EPA allowed vs motion", "epa", -1), C("def_epa_nomotion", "Def. EPA allowed, no motion", "epa", -1),
        C("def_epa_rpo", "Def. EPA allowed vs RPOs", "epa", -1),
    ], "off_motion_rate", "FTN charting. Offence columns describe the play-caller's style; the last three describe the defence. RPO samples are small (about 20 plays per team)."))
    rk_common = [C("status", "Status", "str", 0), C("games", "Games", "int", 0), C("snap_pct", "Snap share", "pct", 0, "Average offensive snap share in games played")]
    tables.append(table("rank_rb", f"Running backs ({US['rb_min']}+ carries)", rk_common + [
        C("carries", "Carries", "int", 1), C("car_share", "Carry share", "pct", 1), C("car_share_l3", "Carry share, last 3", "pct", 1),
        C("rush_yds", "Rush yds", "int", 1), C("ypc", "Yds/carry", "n2", 1), C("epa_car", "EPA/carry", "epa", 1),
        C("sr_car", "Success", "pct", 1), C("ryoe_att", "RYOE/att", "s2", 1, "Next Gen rush yards over expected per attempt"),
        C("ybc_att", "Yds before contact/att", "n2", 1, "PFR: mostly the blocking (games PFR has charted)"),
        C("yaco_att", "Yds after contact/att", "n2", 1, "PFR: the runner's power, balance and tackle-breaking"),
        C("brk_tkl_rush", "Broken tackles (runs)", "int", 1), C("brk_per_car", "Broken tackles/carry", "pct", 1),
        C("expl_run", "10+ yd runs", "pct", 1), C("stuff", "Stuffed", "pct", -1), C("rush_td", "Rush TD", "int", 1),
        C("rz_car", "RZ carries", "int", 0), C("gl_car", "Carries inside 5", "int", 0),
        C("targets", "Targets", "int", 1), C("tgt_share", "Target share", "pct", 1), C("rec_yds", "Rec yds", "int", 1),
        C("epa_tgt", "EPA/target", "epa", 1), C("epa_total", "Total EPA (rush + rec)", "s1", 1, "Sum of EPA on his carries and targets"),
    ], "carries", "Season figures only, ranked on usage only (snaps, carries, targets and their shares). Efficiency and production columns are context: "
       "each efficiency value carries a badge for how much of it is likely to last at that sample (Low under 20%, Medium 20-50%). Total EPA rewards volume "
       "and efficiency together; running-back EPA also reflects the blocking and the play call." + player_note("rb"), rows="rb"))
    rec_cols = [
        C("targets", "Targets", "int", 1), C("tgt_share", "Target share", "pct", 1), C("tgt_share_l3", "Target share, last 3", "pct", 1),
        C("air_share", "Air-yards share", "pct", 1, "Share of the team's intended air yards"),
        C("rec", "Rec.", "int", 1), C("rec_yds", "Yards", "int", 1), C("rec_td", "TD", "int", 1),
        C("ypt", "Yds/target", "n2", 1), C("epa_tgt", "EPA/target", "epa", 1), C("sr_tgt", "Success", "pct", 1),
        C("catch_rate", "Catch rate", "pct", 1), C("adot", "aDOT", "n1", 0, "Average depth of target (air yards)"),
        C("yac_pr", "YAC/rec.", "n1", 1), C("yacoe_pr", "YAC over exp./rec.", "s2", 1),
        C("brk_tkl_rec", "Broken tackles after catch", "int", 1, "PFR, games PFR has charted"), C("drops", "Drops", "int", -1, "PFR"),
        C("sep", "Separation (yd)", "n2", 1, "Next Gen, target-weighted over his weekly rows"),
        C("rz_tgt", "RZ targets", "int", 1), C("rz_tgt_share", "RZ target share", "pct", 1),
        C("epa_total", "Total EPA", "s1", 1, "Sum of EPA on his targets (and carries)"),
    ]
    rec_note = ("Season figures only, ranked on usage only (snaps, targets and their shares). Efficiency and production columns are context, each efficiency "
                "value with a badge for how much of it is likely to last at that sample (Low under 20%, Medium 20-50%; tight ends use the wide-receiver fit). "
                "Receiver EPA includes the quarterback's throw and the play call, so it measures usage and production, "
                "not the receiver alone. Yards per route run needs routes, which free data does not record." + player_note("rec"))
    tables.append(table("rank_wr", f"Wide receivers ({US['rec_min']}+ targets)", rk_common + rec_cols, "targets", rec_note, rows="wr"))
    tables.append(table("rank_te", f"Tight ends ({US['rec_min']}+ targets)", rk_common + rec_cols, "targets", rec_note, rows="te"))
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
    tables.append(table("staff", "Staff and play-callers", [
        C("hc", "Head coach", "str", 0), C("off_caller", "Calls the offence", "str", 0), C("def_caller", "Calls the defence", "str", 0),
        C("oc", "Off. coordinator", "str", 0), C("dc", "Def. coordinator", "str", 0), C("stc", "Special teams coord.", "str", 0),
        C("caller_src", "Sources", "str", 0, "Numbered sources listed under this table"),
    ], "team", "Hand-kept from the sources below; 'not confirmed' means only the coordinator's title is known. "
                 "'since wk' marks a mid-season change: that unit's tendencies below use only the current caller's weeks.", desc=False))
    tables.append(table("coach_gm", "Game management (head coach)", [
        C("hc", "Head coach", "str", 0),
        C("fd_decisions", "4th-down decisions", "int", 0, "4th downs with win probability 20-80% and more than 2:00 left in the half"),
        C("fd_go_rate", "Go rate", "pct", 0), C("fd_agree_rate", "Agrees with EP reference", "pct", 1),
        C("fd_clear_go_n", "Clear go spots", "int", 0, "Reference value of going exceeds the best kick by 0.5 EP or more"),
        C("fd_clear_go_rate", "Went for it there", "pct", 1), C("fd_ep_lost_per", "EP lost per decision", "n2", -1),
        C("two_pt_att", "2-pt tries", "int", 0), C("two_pt_rate", "2-pt try rate after TDs", "pct", 0),
        C("eoh_drives", "End-of-half drives", "int", 0), C("eoh_ppd", "End-of-half pts/drive", "n2", 1, "Drives starting in the last 2:00 of the first half (31 s or more left)"),
        C("net_h2_minus_h1", "2nd-half minus 1st-half net EPA", "epa", 1),
        C("bye_week", "Bye week", "int", 0), C("net_after_bye", "Net EPA after bye (1 game)", "epa", 1),
        C("one_score", "One-score record", "str", 0),
    ], "fd_agree_rate", "The head coach owns these calls even when he calls no plays."))
    tables.append(table("coach_off", "Offensive play-calling", [
        C("off_caller", "Play-caller", "str", 0), C("off_caller_weeks", "Weeks", "str", 0),
        C("c_off_pace_sec", "Sec between snaps", "n1", 0, "Median, within drives, win probability 20-80%, quarters 1-3"),
        C("c_off_early_pass_rate", "Neutral early-down pass rate", "pct", 0), C("c_off_proe", "Pass rate over expected", "s1", 0),
        C("c_off_pa_rate", "Play-action rate", "pct", 0), C("c_off_screen_rate", "Screen rate", "pct", 0),
        C("c_off_epa", "EPA/play (raw)", "epa", 1), C("c_off_sr", "Success rate", "pct", 1),
        C("c_off_h2_minus_h1", "2nd-half minus 1st-half EPA", "epa", 1),
        C("off_epa_leading", "EPA leading by 9+", "epa", 1), C("off_epa_close", "within 8", "epa", 1), C("off_epa_trailing", "trailing by 9+", "epa", 1),
    ], "c_off_proe", "Raw, not opponent-adjusted: these describe the caller's choices, not unit quality (use the efficiency section for that). "
                     "Score-state columns cover the full season."))
    tables.append(table("coach_def", "Defensive play-calling", [
        C("def_caller", "Play-caller", "str", 0), C("def_caller_weeks", "Weeks", "str", 0),
        C("c_def_blitz_rate", "Blitz rate", "pct", 0, "FTN charting: dropbacks with five or more pass rushers"),
        C("c_def_epa_blitz", "EPA/db allowed, blitz", "epa", -1),
        C("c_def_epa_noblitz", "EPA/db allowed, no blitz", "epa", -1),
        C("c_def_epa", "EPA/play allowed (raw)", "epa", -1), C("c_def_sr", "Success allowed", "pct", -1),
        C("c_def_h2_minus_h1", "2nd-half minus 1st-half EPA allowed", "epa", -1, "Negative = better after half-time"),
        C("def_pressure_rate", "Pressure rate (PFR, season)", "pct", 1),
    ], "c_def_blitz_rate", "Man/zone rates are not in the free data. Pressure rate covers the full season and the PFR games available."))
    tables.append(table("coach_st", "Special teams (coordinator; the head coach makes fakes and onside calls)", [
        C("stc", "Coordinator", "str", 0), C("st_epa_pg", "ST EPA/game", "s2", 1), C("st_punt_epa_pg", "Punt EPA/g", "s2", 1),
        C("st_kickoff_epa_pg", "Kickoff EPA/g", "s2", 1), C("st_field_goal_epa_pg", "FG EPA/g", "s2", 1),
        C("fg_50p", "FG 50+", "str", 0, "Made/attempted: how far the staff trusts the kicker"),
        C("st_td", "Return TDs", "int", 1), C("blocks_allowed", "Kicks blocked against", "int", -1), C("pen_st_n", "ST penalties", "int", -1),
    ], "st_epa_pg", "Full kicking, punting and return detail is in section 15."))
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
    tables.append(table("work_off", "Offensive workload and possession", [
        C("off_snaps_pg", "Off. snaps/game", "n1", 0, "Team offensive snaps from snap counts (includes no-play penalties)"),
        C("off_snaps_per_drive", "Snaps/drive", "n2", 0), C("off_top_pg", "Possession min/game", "n1", 0),
        C("off_drive_sec", "Avg drive (s)", "n1", 0), C("off_plays_pd", "Plays/drive", "n1", 0),
        C("off_three_out_rate", "Three-and-out rate", "pct", -1, "Drives ending in a punt without a first down"),
        C("off_no_fd_rate", "No first down, no score", "pct", -1), C("off_to_pd", "Turnovers/drive", "pct", -1),
        C("off_series_success", "Drive (series) success", "pct", 1, "Share of first-and-10 series that gain a first down or touchdown"),
        C("off_sustained_pg", "Sustained drives/game", "n2", 1, "8+ plays or 4:00+"),
        C("pts_per_min_poss", "Points per possession minute", "n2", 1),
        C("off_short_poss_pg", "Short possessions/game", "n2", -1, "3 plays or fewer, or 90 s or less, ending in a punt, turnover or downs"),
        C("off_snaps_last", "Off. snaps last game", "int", 0),
    ], "off_three_out_rate", "Possession time and snaps describe workload, not quality. Raw per-game values depend on pace and opponents.", desc=False))
    tables.append(table("work_def", "Defensive workload", [
        C("def_snaps_pg", "Def. snaps/game", "n1", 0), C("def_snaps_last", "Def. snaps last game", "int", 0),
        C("def_snaps_last2", "Avg last 2 games", "n1", 0), C("def_snaps_max", "Most in a game", "int", 0),
        C("def_snaps_per_drive", "Snaps/drive faced", "n2", -1), C("def_top_pg", "Minutes defending/game", "n1", 0),
        C("def_drives_pg", "Drives faced/game", "n2", 0), C("def_drive_sec", "Opp. drive length (s)", "n1", -1),
        C("def_three_out_rate", "Three-and-outs forced", "pct", 1), C("def_stops_pg", "Stops/game", "n2", 1, "Drives faced ending in a punt, turnover, downs or missed FG"),
        C("takeaways", "Takeaways", "int", 1), C("def_series_success", "Series success allowed", "pct", -1),
        C("def_quick_pg", "Quick turnarounds/game", "n2", 0, "Defensive drives starting after the team's own offence held the ball for 3 plays or fewer, or 90 s or less"),
        C("def_rest_min_median", "Median real rest (min)", "n1", 0, "Wall-clock minutes between the end of one defensive drive and the start of the next (same half)"),
        C("def_rest_under8_share", "Drives with under 8 min rest", "pct", 0),
        C("def_max_stretch_avg", "Longest stretch (plays)", "n1", 0, "Average per game of the most defensive plays faced with only short own possessions in between"),
        C("def_short_field_after_to_pg", "Short fields after own turnovers/game", "n2", -1),
        C("def_dropbacks_pg", "Dropbacks faced/game", "n1", 0),
    ], "def_snaps_pg", "Intensity: dropbacks faced per game (pass-rush load). Workload columns are context: see the fatigue study before reading them as fatigue."))
    tables.append(table("fatigue", "Defence through the game (2026)", [
        C("def_epa_q1", "EPA allowed Q1", "epa", -1), C("def_epa_q2", "Q2", "epa", -1), C("def_epa_q3", "Q3", "epa", -1), C("def_epa_q4", "Q4", "epa", -1),
        C("def_epa_close_h1", "1st half, score within 8", "epa", -1), C("def_epa_close_h2", "2nd half, score within 8", "epa", -1),
        C("def_close_h2_minus_h1", "Change (close only)", "epa", -1, "Second-half minus first-half EPA allowed in close-score situations, which removes most game-script effects"),
        C("def_expl_rate_h1", "Explosive allowed H1", "pct", -1), C("def_expl_rate_h2", "Explosive allowed H2", "pct", -1),
        C("def_rush_epa_h1", "Rush EPA allowed H1", "epa", -1), C("def_rush_epa_q4", "Rush EPA allowed Q4", "epa", -1), C("def_ypc_q4", "YPC allowed Q4", "n2", -1),
        C("def_hs_h1", "Hit/sack rate H1", "pct", 1), C("def_hs_h2", "Hit/sack rate H2", "pct", 1),
        C("def_epa_after_three_out", "EPA after own three-and-out", "epa", -1), C("def_n_after_three_out", "Plays", "int", 0),
        C("def_epa_after_to", "EPA after own turnover", "epa", -1), C("def_n_after_to", "Plays", "int", 0),
        C("def_epa_quick", "EPA on quick-turnaround drives", "epa", -1), C("def_epa_not_quick", "EPA on other drives", "epa", -1),
        C("def_ppd_short_field", "Pts/drive on short fields", "n2", -1), C("def_ppd_long_field", "Pts/drive on long fields", "n2", -1),
        C("def_q4_pts_pg", "4th-quarter pts allowed/game", "n2", -1),
    ], "def_close_h2_minus_h1", "Split samples are small (often under 100 plays). Late-game numbers mix fatigue with game script, opponent play-calling and personnel.", desc=False))
    tables.append(table("pen_net", "Flags committed, drawn and net", [
        C("pd_total_pg", "Committed/game", "n2", -1), C("pd_total_yds_pg", "Yards/game", "n1", -1),
        C("pd_drawn_pg", "Drawn/game", "n2", 1, "Accepted fouls by the opponent, all units"), C("pd_drawn_yds_pg", "Drawn yds/game", "n1", 1),
        C("pd_net_pg", "Net flags/game", "s2", 1, "Drawn minus committed: positive = the team gains from flags"),
        C("pd_net_yds_pg", "Net yards/game", "s1", 1, "Penalty yards drawn minus yards conceded"),
        C("pd_presnap_pg", "Pre-snap/game", "n2", -1, "False start, delay of game, illegal formation/shift/motion, offside, neutral zone, encroachment"),
        C("pd_d1_off_pg", "Off. fouls on 1st down/game", "n2", -1, "Put the offence behind schedule from the first snap of a series"),
        C("pd_d34_pg", "Fouls on 3rd/4th down/game", "n2", -1, "Offence or defence, the downs where a flag most often decides a punt, field goal or new set of downs"),
        C("pd_d34_drawn_pg", "Drawn on 3rd/4th/game", "n2", 1),
    ], "pd_net_yds_pg", "Accepted penalties only (declined and offsetting fouls are not counted). Per game played. Counts from nflfastR play-by-play.", desc=True))
    tables.append(table("pen_detail", "Penalty impact and situations", [
        C("pd_total_pg", "Penalties/game", "n2", -1), C("pd_off_pg", "Offence/game", "n2", -1), C("pd_def_pg", "Defence/game", "n2", -1), C("pd_st_pg", "Special teams/game", "n2", -1),
        C("pd_total_yds_pg", "Yards/game", "n1", -1), C("pd_off_yds_per_snap", "Off. yds/snap", "n2", -1), C("pd_def_yds_per_snap", "Def. yds/snap", "n2", -1),
        C("pen_auto_fd", "Auto 1st downs given", "int", -1), C("pd_drive_extending", "3rd/4th-down fouls extending drives", "int", -1),
        C("pd_negated_fd", "Negated 1st downs/TDs", "int", -1, "No-play offensive fouls where the wiped-out play reached the line to gain (text-parsed)"),
        C("pd_negated_success", "Negated successful plays", "int", -1), C("pen_negated_expl", "Negated explosives/TDs", "int", -1),
        C("pd_out_of_fg_range", "Pushed out of FG range", "int", -1, "Offensive fouls from inside the opponent's 37 that moved the ball beyond it"),
        C("pd_created_long", "Created 15+ to go", "int", -1), C("pd_high_leverage", "Q4/OT, score within 8", "int", -1),
        C("pd_while_leading_late", "Q4 while leading by 1-8", "int", -1), C("pd_while_trailing_late", "Q4 while trailing by 1-8", "int", -1),
        C("rz_td_with_off_pen", "RZ TD% with an off. foul", "pct", 1), C("rz_trips_with_off_pen", "Trips", "int", 0), C("rz_td_without_off_pen", "RZ TD% without", "pct", 1),
        C("pd_np_epa_off", "Off. EPA lost (no-play)", "n1", -1), C("pd_np_epa_def", "Def. EPA given (no-play)", "n1", -1),
        C("pd_live_epa_est_off", "Off. EPA lost (live, est.)", "n1", -1, "Accepted fouls on live plays, valued at 0.07 EP per penalty yard (approximation)"),
        C("pd_live_epa_est_def", "Def. EPA given (live, est.)", "n1", -1), C("pd_epa_cost_total", "Total EPA cost/game", "n2", -1),
        C("pd_accepted", "Accepted", "int", 0), C("pd_declined", "Declined", "int", 0), C("pd_multi_plays", "Plays with 2+ fouls", "int", 0),
    ], "pd_epa_cost_total", desc=False))
    tables.append(table("pen_tend", "Penalty tendencies and penalties drawn (per opportunity)", [
        C("pd_off_presnap_per100", "Off. pre-snap per 100 snaps", "n2", -1), C("pd_fs_home_per100", "False starts per 100, home", "n2", -1),
        C("pd_fs_away_per100", "per 100, away", "n2", -1), C("pd_off_holding_per100db", "Off. holding per 100 dropbacks", "n2", -1),
        C("pd_cover_fouls_per100db", "Def. DPI/holding/contact per 100 db", "n2", -1), C("pd_rtp_per100db", "Roughing per 100 db", "n2", -1),
        C("pd_def_jump_per100", "Def. offside/NZI/encroach per 100", "n2", -1),
        C("pd_drawn_def_pg", "Def. fouls drawn/game", "n2", 1), C("pd_dpi_drawn_per100db", "DPI drawn per 100 db", "n2", 1),
        C("pd_def_jump_drawn_per100", "Offside/NZI drawn per 100", "n2", 1, "Proxy for hard counts and tempo"),
        C("pd_off_holding_drawn_per100db", "Holds drawn by pass rush per 100 db", "n2", 1),
        C("pd_off_presnap_drawn_per100", "Off. pre-snap drawn per 100", "n2", 1),
    ], "pd_cover_fouls_per100db", "Rates per relevant opportunity (snaps or dropbacks). Drawn rates describe the opponent's fouls in the team's games.", desc=False))
    tables.append(table("run_style", "Run style: inside and outside runs", [
        C("run_inside_share", "Inside share (non-QB runs)", "pct", 0, "Inside = middle or guard gap; outside = tackle or end"),
        C("off_epa_inside", "Off. EPA inside", "epa", 1), C("off_n_inside", "n", "int", 0), C("off_epa_outside", "Off. EPA outside", "epa", 1), C("off_n_outside", "n", "int", 0),
        C("def_epa_inside", "Def. EPA allowed inside", "epa", -1), C("def_n_inside", "n", "int", 0),
        C("def_epa_outside", "Def. EPA allowed outside", "epa", -1), C("def_n_outside", "n", "int", 0),
    ], "run_inside_share", "Run direction comes from the play-by-play gap and location fields; scheme names (zone, gap, power) are not available."))
    tables.append(table("depth_checks", "Depth chart against who played", [
        C("dc_qb_listed", "QB1 on depth chart", "str", 0), C("dc_qb_last", "QB in latest game", "str", 0),
        C("dc_qb_flag", "QB", "str", 0), C("dc_ol_new", "OL listed but not in last game's top five", "str", 0),
        C("dc_ol_dropped", "OL in last game's top five, not listed", "str", 0),
    ], "team", "Depth charts are ESPN's daily snapshot via nflverse; teams often leave them stale, so a difference is a prompt to "
               "check the news, not proof of a change. Chart snapshot: " + DP["depth"]["as_of"][:16].replace("T", " ") + " UTC.", desc=False))
    tables.append(table("depth", "Availability and depth", [
        C("qb_starts", "QB starts", "str", 0), C("qb_changed_since_prior", "New primary QB vs 2025", "str", 0),
        C("regulars", "Regulars", "int", 0, "Players averaging 50%+ of offensive or defensive snaps in 2+ games"),
        C("absent_n", "Regulars out (confirmed)", "int", -1, "Reserve list on the latest weekly roster, Out/Doubtful in the team's latest report, or inactive for each of the last three games"),
        C("absent_snap_weighted", "Snap-weighted absences", "n2", -1, "Sum of absent regulars' snap shares; 1.0 = one full-time starter"),
        C("absent_QB", "QB", "int", -1), C("absent_OL", "OL", "int", -1), C("absent_WR/TE", "WR/TE", "int", -1), C("absent_RB", "RB", "int", -1),
        C("absent_DL/EDGE", "DL/EDGE", "int", -1), C("absent_LB", "LB", "int", -1), C("absent_DB", "DB", "int", -1),
        C("questionable_n", "Questionable", "int", -1), C("practice_concern_n", "DNP/limited, no status yet", "int", -1),C("unconfirmed_n", "Missed last game, no designation", "int", -1),
        C("ol_starters_used", "OL starters used", "int", -1), C("ol_w1_starters_in_last", "Week-1 OL starters in latest game", "int", 1),
        C("top_rb_carry_share", "Top RB carry share", "pct", 0), C("def_top11_snap_share", "Top-11 share of def. snaps", "pct", 0),
        C("def_players_25pct", "Defenders with 25%+ snaps in a game", "int", 0),
    ], "absent_snap_weighted", desc=True))
    tables.append(table("form", "Recent form: last four games against the season", [
        C("form_off_l4", "Off. adj. EPA/play, last 4", "epa", 1), C("form_off_season", "Season", "epa", 1),
        C("form_off_change", "Change", "epa", 1, "Last four minus season: positive = the offence has improved"),
        C("form_def_l4", "Def. adj. EPA/play allowed, last 4", "epa", -1), C("form_def_season", "Season", "epa", -1),
        C("form_def_change", "Change", "epa", -1, "Last four minus season: negative = the defence has improved"),
        C("form_net_l4", "Net adj. EPA/play, last 4", "epa", 1), C("form_net_season", "Season", "epa", 1),
        C("form_net_change", "Net change", "epa", 1),
        C("form_weeks", "Weeks", "str", 0), C("form_plays_off", "Off. plays, last 4", "int", 0), C("form_plays_def", "Def. plays, last 4", "int", 0),
    ], "form_net_change", "Each play is adjusted with the season's opponent effects and home coefficient (Method), so the season columns equal the "
       "opponent-adjusted EPA/play. Four games are about 250 plays per unit: a change smaller than about 0.05 EPA/play is within ordinary game-to-game noise."
       + "".join(sorted({f" Unusual game inside these figures: {x['label']} ({x['weather']}, {x['dropbacks']} combined dropbacks)." for v in UN["flagged"].values() for x in v}))))
    big_cols = []
    for pos, nm in (("WR", "WRs"), ("TE", "TEs"), ("RB", "RBs")):
        big_cols += [C(f"def_n20_{pos}", f"20+ yd catches, {nm}", "int", -1, f"Completions of 20+ yards to {nm} allowed"),
                     C(f"def_rate20_{pos}", f"Per target, {nm}", "pct", -1), C(f"def_n20pg_{pos}", f"Per game, {nm}", "n2", -1),
                     C(f"def_yac_rec_{pos}", f"YAC/catch, {nm} (yd)", "n1", -1, f"Yards after the catch per completion to {nm}"),
                     C(f"def_epa_tgt_{pos}", f"EPA/target, {nm}", "epa", -1)]
    tables.append(table("big_pos_def", "Big plays allowed by position", big_cols, "def_rate20_WR",
                        "20+ yard receptions and yards after the catch allowed to each position (receiver's weekly-roster position).", desc=False))
    tables.append(table("refs", f"Referee crews: accepted penalties per game, {REF['pool']}", [
        C("games", f"Games {REF['pool']}", "int", 0), C("total", "Penalties/game", "n1", 0), C("yards", "Penalty yards/game", "n1", 0),
        C("off_holding", "Off. holding/game", "n2", 0), C("dpi", "DPI/game", "n2", 0), C("presnap", "Pre-snap/game", "n2", 0),
        C("on_home", "On home team/game", "n2", 0), C("on_away", "On away team/game", "n2", 0),
        C("home_minus_away", "Home minus away", "s2", 0, "Positive = more penalties on the home team"),
        C("games_cur", f"Games {REF['season']}", "int", 0), C("total_cur", f"Penalties/game {REF['season']}", "n1", 0),
    ], "total", f"Crew = the referee's crew in those games (crews change a little each season). League average {REF['league']['total']:.1f} accepted "
       f"penalties per game in {REF['pool']}. nflverse names the {REF['season']} referee for {REF['cur_games_with_ref']} of {REF['cur_games']} games so far "
       f"(weeks {', '.join(map(str, REF['cur_weeks_with_ref']))}). Context only: penalty rates also depend on the teams.", rows="refs", first="Referee"))
    # B: consolidated comparison, consistent team order
    B = [
        ("Record and ratings", [C("record", "Record", "str", 0), C("rating_pg", "Overall rating", "s1", 1), C("stab_rating_pg", "With 2025 prior", "s1", 1),
                                C("off_composite", "Off. composite", "s2", 1), C("def_composite", "Def. composite", "s2", 1), C("st_epa_pg", "ST EPA/g", "s2", 1)]),
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

    tables = finish_tables(tables, T, not wr_probs, bool((A.last_report_week == meta["through_week"] + 1).any()))
    games = build_matchups(T, nxt, MM, A, mm, notes, PL, US, CTX["qb"], REF, ARR, UN, WX, NG)
    pen_types_js = PEN_T.to_dict("records")
    # embed only the team fields the page or the per-game export reads (table columns, sample sizes, keys named in the
    # page's script or the exporter, and the team-chart measures, whose keys the page builds at run time)
    used = {c[x] for tb in tables for c in tb["cols"] for x in ("k", "n", "nk") if c.get(x)}
    for src in (TEMPLATE, (Path(__file__).with_name("export_games.py")).read_text(encoding="utf-8")):
        used |= set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", src))
    used |= {f"{sd}_{m}" for sd in ("off", "def") for m in ("epa_play", "adj_epa", "sr", "adj_sr", "epa_db", "adj_epa_db", "sr_db", "adj_sr_db",
             "epa_rush", "adj_epa_rush", "sr_rush", "adj_sr_rush", "expl_rate", "ypp", "yds_pg", "pts_pg", "ppd", "rz_td_rate", "d3_conv",
             "sack_rate", "pressure_rate", "to_pd")}
    used |= {f"def_{m}_{x}" for m in ("rate20", "n20pg", "yac_rec") for x in ("WR", "TE", "RB")}
    keep = [k for k in T.columns if k in used]
    teams_js = []
    for t in T.index:
        r = T.loc[t, keep]
        rec = {k: (None if (isinstance(v, float) and math.isnan(v)) else (v.item() if hasattr(v, "item") else v)) for k, v in r.items()}
        rec["team"] = t
        rec["cov"] = "n/a"
        teams_js.append(rec)
    qcols = ["name_full", "team", "teams", "games", "dropbacks", "epa_db", "adj_epa_db", "sr", "cpoe", "ypa", "adot", "sack_rate", "int_rate",
             "int_worthy_rate", "pressure_rate", "p2s", "epa_clean", "epa_hit_sack", "epa_vs_blitz", "epa_no_blitz", "blitzed_rate",
             "scr_rate", "epa_scr", "designed_runs", "epa_designed_run", "fd_td_rate", "epa_early", "epa_d3", "epa_rz", "game_sd",
             "time_to_throw", "yacoe", "drop_rate", "db_clean", "db_hit", "db_blitz", "db_noblitz", "scrambles", "hit_sack_rate", "qb_fault_sacks", "qb_fault_sack_share", "team_pressure_allowed", "qb_composite", "team_db_share", "latest_starter", "qualified"]
    qbs = Q[qcols].replace({np.nan: None}).to_dict("records")
    absn = A.replace({np.nan: None}).to_dict("records")

    tm = pd.read_parquet(ROOT / "data" / "cache" / "team_analytics" / "teams__teams_colors_logos.parquet")
    colors = {t: team_colour(c1, c2) for t, c1, c2 in zip(tm.team_abbr, tm.team_color, tm.team_color2) if t in T.index}
    data = {"colors": colors, "takeaways": takeaways(T, mm, A, meta, ARR), "refs": REF["refs"], "ref_meta": {k: v for k, v in REF.items() if k != "refs"},
            "wr": {"ok": not wr_probs, "problems": wr_probs, "corr": win_rate_corr(T) if not wr_probs else [],
                   "source": (WR or {}).get("source"), "through_week": (WR or {}).get("through_week")},
            "nlabels": SAMPLE_LABEL, "teams": teams_js, "qbs": qbs, "absences": absn, "tables": tables, "meta": meta, "profiles": profiles,
            "mismatch": mm, "games": games, "reports": structured_reports(T, nxt, MM, games, CTX["qb"], TRV, CTX["travel"], CTX["fatigue"]),
            "ctx": {"fatigue": CTX["fatigue"], "travel": CTX["travel"], "qb": CTX["qb"], "penalty_groups": CTX["penalty_groups"]},
            "trv": TRV, "pen_types": pen_types_js, "cats": cats, "D": D, "E": E, "F": F, "dis": dis, "notes": notes, "order": order,
            "names": T.team_name.to_dict(), "depth_as_of": DP["depth"]["as_of"], "players": PL["teams"], "players_league": PL["league"],
            "usage": trim_usage(US, tables), "callers": {"sources": CL["sources"], "splits": CL["splits"], "checked": CL["checked"], "league": CL["league"]}}
    nxt_w = meta["through_week"] + 1
    n_rep = A.loc[A.last_report_week == nxt_w, "team"].nunique()
    data["meta"]["inj_note"] = (f"{n_rep} teams already have a week {nxt_w} injury report in the data; other statuses come from each team's latest report and roster."
                                if n_rep else f"Week {nxt_w} injury reports are not out yet: statuses come from each team's latest report and the latest weekly roster.")
    page = TEMPLATE.replace("/*DATA*/", json.dumps(data, default=str).replace("</", "<\\/"))
    page = page.replace("{{WEEK}}", str(meta["through_week"] + 1)).replace("{{THRU}}", str(meta["through_week"]))
    page = page.replace("{{WEEKS_WORD}}", WK["word"]).replace("{{WEEKS_WORD_CAP}}", WK["word"].capitalize())
    page = page.replace("{{METHOD}}", method_html(meta, T, A, data["wr"], REF, ARR, UN, WX, MM))
    page = page.replace("{{EDGE_NOTE}}", edge_note(CAL)).replace("{{CAL_NOTE}}", cal_note(CAL))
    if meta.get("ep_scale_warning"):
        page = page.replace('<div class="tk" id="tk"></div>', f'<div class="callout warn"><b>EPA scale changed.</b> {esc(meta["ep_scale_warning"])}</div>\n  '
                            '<div class="tk" id="tk"></div>', 1)
    (d / "report.html").write_text(page, encoding="utf-8")
    print("wrote", d / "report.html", f"{len(page) / 1e6:.2f} MB")


def weather_method(WX):
    """Method note and history table for the weather line; empty for a report without one."""
    if not WX:
        return ""
    H = WX["history"]
    yrs = f"{H['years'][0]}-{str(H['years'][1])[-2:]}"
    rows = "".join(f"<tr><td>{esc(game_weather.BUCKETS[k].capitalize())}</td><td>{x['games']}</td><td>{x['pass_rate']:.1%}</td><td>{x['epa_db']:+.3f}</td>"
                   f"<td>{x['epa_rush']:+.3f}</td><td>{x['ypc']:.2f}</td></tr>" for k, x in H["groups"].items())
    return (f"<h3>Weather line</h3><p>Each outdoor game shows the National Weather Service forecast (Open-Meteo for other venues or if NWS cannot be read) for the kickoff hour and the next three hours: rain or snow is called likely at a "
            f"{WX['wet_pop']}%+ chance of precipitation in any of those hours, and wind is the mean over them. Early forecasts are rough, and a game whose forecast could not be re-read keeps "
            f"the last one with its read time. Games with rain, snow or {WX['wind_min']}+ mph wind add what similar games did. Those are raw averages from {H['games_used']} outdoor and open-roof "
            f"{yrs} regular-season games with a usable play-by-play weather text, not adjusted for teams; that text describes conditions around kickoff. "
            f"Pass rate uses plays with win probability of 20-80%. Display only: no rating, edge or expected figure changes.</p>"
            f"<div class=\"table-wrap\"><table><thead><tr><th>Conditions, {yrs}</th><th>Games</th><th>Pass rate, close games</th><th>EPA/dropback</th><th>EPA/rush</th>"
            f"<th>Yards per carry</th></tr></thead><tbody>{rows}</tbody></table></div>")


def cal_years(CAL):
    return f"{CAL['fitted_on'][0]}-{str(CAL['fitted_on'][1])[-2:]}"


def edge_note(CAL):
    """What counts as a notable headline edge, with its record in the backtest when the report is calibrated."""
    if not CAL:
        return "1.5 or more is notable"
    e = CAL["edges"]
    txt = (f"{e['notable']:.1f} or more is notable: in {cal_years(CAL)} an edge that size pointed the right way in {e['notable_right']:.0%} of "
           f"{e['notable_cases']:,} cases, against {e['small_right']:.0%} for edges under {e['small']:.1f}")
    bm, bw = e.get("notable_by_measure"), e.get("notable_by_weeks")
    if bm:
        lab = {"pressure": "pass rush vs protection", "epa_rush": "run game", "epa_db": "passing", "expl_pass": "big passing plays",
               "expl_run": "big runs"}
        parts = [f"{lab[m]} {v['right']:.0%} ({v['cases']})" for m, v in sorted(bm.items(), key=lambda kv: -(kv[1]["right"] or 0)) if v["right"] is not None]
        txt += ". By measure: " + ", ".join(parts) + "; big runs are left out of the headlines for that reason"
    if bw and bw.get("4-7"):
        w = bw["4-7"]
        txt += f". Early in a season the record is thinner: weeks 4-7 had {w['cases']} notable edges, {w['right']:.0%} right"
    return txt


def cal_note(CAL):
    if not CAL:
        return "and nothing from earlier seasons is used"
    return (f"and no earlier season's results enter a team's own numbers. Early in a season such expectations have been too extreme, so each is also scaled "
            f"by how well they held up at this week in {cal_years(CAL)} (Method)")


def cal_method(CAL, meta):
    """Method sentence on the calibration; empty for a report built without one."""
    if not CAL:
        return ""
    f, ps = CAL["factors"], CAL["pooled_slope_by_weeks"]
    first, last = list(ps)[0], list(ps)[-1]
    return (f"That weight proved too large early in a season. In a backtest on {cal_years(CAL)} ({CAL['team_games']:,} team-games per measure), fitting on weeks 1 to W "
            f"and predicting week W+1 for W = {CAL['cut_weeks'][0]} to {CAL['cut_weeks'][1]}, the real gap from the league average was {ps[first]:.0%} of the expected gap at weeks "
            f"{first} and {ps[last]:.0%} at weeks {last} (all measures pooled). Each weight is therefore multiplied by a factor for the week and the measure, fitted on those "
            f"seasons and never above 1: after week {meta['through_week']} it is {f['epa_play']:.2f} for EPA per play, {f['epa_db']:.2f} for EPA per dropback, "
            f"{f['epa_rush']:.2f} for EPA per rush, {f['pressure']:.2f} for pressure rate, {f['to_pd']:.2f} for turnovers per drive and {f['rz_td']:.2f} for red-zone TD rate, "
            f"whose team effects did not predict the next game. Checked out of sample (each season from the other four), this lowered the error on "
            f"{CAL['improved']} of {CAL['measures']} measures. ")


def no_signal(MM):
    """Measures whose between-team variance is at zero this week (data-driven; was a fixed list)."""
    if not MM:
        return ""
    lab = {k: l for rows in MATCH_ROWS.values() for (l, k, *_) in rows if k}
    out = [f"{lab.get(k, k)} ({'offence' if s == 'off' else 'defence'})" for k, m in MM.items() for s in ("off", "def") if m[s]["tau2"] <= 1e-8]
    return (" This week that applies to: " + "; ".join(out) + ".") if out else " This week no measure is in that position."


def method_html(meta, T, A, WRI, REF, ARR, UN, WX=None, MM=None):
    ARR_WEEK, UN_WIND, UN_CUT, UN_PCTL, UN_N, UN_MED = ARR.get("roster_week"), UN["wind_min"], UN["cut"], UN["pctl"], UN["hist_games"], UN["hist_median"]
    UN_YEARS = f"{UN['hist_seasons'][0]}-{str(UN['hist_seasons'][1])[-2:]}"
    co, cd = meta["composite_off"], meta["composite_def"]
    po, pdf = meta["prior_off"], meta["prior_def"]
    lg = meta["league"]
    src = "".join(f"<tr><td>{esc(s['url'].split('/download/')[1])}</td><td>{esc(s.get('http_last_modified') or 'n/a')}</td>"
                  f"<td>{esc(s['retrieved_utc'])}</td><td class='mono'>{esc(s['sha256'][:12])}</td></tr>"
                  for s in {s["url"]: s for s in meta["sources"]}.values())
    qc = "".join(f"<li>{esc(q)}</li>" for q in meta["qc"])
    w26 = T.off_w2026.mean()
    # coverage notes follow the data, so a refresh never leaves a stale caveat
    ftn_qc = next((q for q in meta["qc"] if q.startswith("FTN charting")), "")
    ftn_missing = re.search(r"missing: ([^)]*)\)", ftn_qc)
    ftn_missing = ftn_missing.group(1) if ftn_missing else "unknown"
    if ftn_missing == "none":
        ftn_note = "<li><b>FTN charting</b> covers every game in the window.</li>"
    else:
        ftn_note = (f"<li><b>FTN charting</b> is missing {esc(ftn_missing)}, so blitz and expected-INT figures for those teams "
                    f"have fewer games.</li>")
    nxt = meta["through_week"] + 1
    n_nxt = A.loc[A.last_report_week == nxt, "team"].nunique()
    if n_nxt:
        inj_note = (f"<li><b>Week {nxt} injury reports</b>: {n_nxt} teams with a listed absence or practice concern already have a week {nxt} report. "
                    f"Other statuses come from each team's latest report and latest weekly roster; game statuses before the final report are practice participation only.</li>")
    else:
        inj_note = (f"<li><b>Week {nxt} injury reports</b> are not out yet. Statuses come from each team's latest report and the latest weekly roster.</li>")
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
<div class="table-wrap"><table class="mini"><tr><th></th><th>adj. EPA/play</th><th>adj. success</th><th>pts/drive</th><th>R² (combined)</th></tr>
<tr><td>Offence weights</td><td>{co['weights']['o_epa']:.0%}</td><td>{co['weights']['o_sr']:.0%}</td><td>{co['weights']['o_ppd']:.0%}</td><td>{co['r2']:.2f}</td></tr>
<tr><td>Offence single-metric R²</td><td>{co['single_r2']['o_epa']:.2f}</td><td>{co['single_r2']['o_sr']:.2f}</td><td>{co['single_r2']['o_ppd']:.2f}</td><td></td></tr>
<tr><td>Defence weights</td><td>{cd['weights']['d_epa']:.0%}</td><td>{cd['weights']['d_sr']:.0%}</td><td>{cd['weights']['d_ppd']:.0%}</td><td>{cd['r2']:.2f}</td></tr>
<tr><td>Defence single-metric R²</td><td>{cd['single_r2']['d_epa']:.2f}</td><td>{cd['single_r2']['d_sr']:.2f}</td><td>{cd['single_r2']['d_ppd']:.2f}</td><td></td></tr></table></div>
<p>{WORDS.get(meta['through_week'], meta['through_week']).capitalize()}-week defensive numbers explain only about a tenth of rest-of-season defensive performance (R² {cd['r2']:.2f}), against about a third for offence
({co['r2']:.2f}). Read defensive rankings with more caution.</p>
<p><b>Overall team rating</b> = (adj. offensive EPA/play − league mean) × {meta['plays_per_game']:.1f} plays + (league mean − adj. defensive EPA/play) × {meta['plays_per_game']:.1f}
+ the kept share of special-teams EPA per game, in points per game. EPA is in points, so this needs no arbitrary weights. Special-teams EPA is noisy
(first-half to second-half correlation about 0.24 in 2021-25), so the rating keeps w = &tau;² / (&tau;² + s² / games) of it, about {100 * float(T.st_w.median()):.0f}% now
(<code>backtest_special_teams.py</code>; out of sample this predicted the rest of a season better than the full figure or zero). The special-teams tables show the full figure.
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
<h3>Week {meta['through_week'] + 1} matchup expectations</h3>
<p>For each measure in the matchup tables, the same additive fit as the opponent adjustment (offence + defence + home, sum-to-zero) is run on 2026 plays,
drives or PFR team-games. Each team effect is then shrunk by w = τ² / (τ² + σ²/n), where σ²/n is its sampling variance and τ² the between-team variance of the
effects minus their average sampling variance (method of moments). {cal_method(meta.get("calibration"), meta)}Expected value = league mean + w<sub>off</sub> × offence effect + w<sub>def</sub> × defence effect ± home effect.
When τ² is close to zero, the measure has no reliable team-to-team signal yet and the expectation stays at the league average.{no_signal(MM)}
No earlier season's results enter a team's effects, and no score or result is forecast.</p>
<h3>Matchup report rules</h3>
<p>Eleven mismatch types are scanned in both directions for every game: rushing vs run defence, passing vs pass defence, strong protection vs weak rush, weak protection vs elite rush,
mobile quarterback vs scramble containment, explosive passing vs deep-ball defence, four-man pressure vs protection, blitz rate vs passing against five-plus rushers, red zone, turnovers,
and tackling vs yards after contact and catch. A finding needs one unit in roughly the top 8-10 and the other in the bottom 8-10 for that pairing. Each finding lists its evidence, the mechanism,
what could neutralise it, and whether a more specific split supports it: run direction (inside vs outside), deep attempts, or the likely quarterback's own numbers. Confidence is
<i>strong</i> only when both ranks are extreme and the shrinkage step keeps at least half of each team's record, <i>moderate</i> when it keeps at least a third, otherwise <i>limited</i>.
Penalty vulnerabilities are hypotheses built from rates per opportunity (per 100 snaps or dropbacks) and fouls drawn by the opponent. Workload levels: <i>plausible</i> = a top-8 defensive snap count
in the last game plus a short week; <i>minor</i> = one of those, or a top-8 three-and-out or quick-turnaround rate on a short week.</p>
<h3>Workload and fatigue</h3>
<p>Team snaps come from PFR snap counts (the most snaps any player on the unit played). Possession time, plays and three-and-outs come from nflfastR drives. Real rest is wall-clock time between the
last play of one defensive drive and the first play of the next in the same half, so it includes kicks and stoppages. The fatigue study pools {meta['history_seasons'][0]}-{meta['season']} play-by-play. It regresses EPA (and success)
allowed on workload measures with defence-season and offence-season fixed effects (two-way demeaning), quarter and score-state controls, and game-clustered standard errors.</p>
{weather_method(WX)}
<h3>Rest, travel and body clock</h3>
<p>Each team's home stadium sets its home time zone (zone rules applied on the game date, including the end of daylight saving time and Arizona's exception). Neutral-site international venues
are mapped by stadium name. The historical study uses 2002-{meta['season'] - 1} regular-season games at home venues: each game's margin is compared with a leave-one-game-out season rating of both teams plus home field,
and the away team's residual is averaged by time-zone direction (2+ zones east or west, one zone, same zone) and kickoff slot (early before 3pm ET, late, night from 7pm ET), and by kickoff time on the
away team's home clock. Relocated franchises use their city at the time; a few home games played away from the usual stadium are not corrected.</p>
<h3>Quarterback scenarios</h3>
<p>Per-quarterback opponent-adjusted EPA per dropback is shrunk towards the league average, using his own dropbacks as the sample size, then combined with the opposing defence's effect. {qb_method()}
Status comes from each team's latest weekly roster (reserve list) and latest injury report (game status, or practice participation before game statuses are published). Team-level tables are not changed.</p>
{player_method()}
<h3>Not available, and proxies used</h3>
<ul>
<li><b>Depth charts</b>: ESPN's daily team depth charts via nflverse, used only for the next player listed behind an absent regular and for checking the listed QB and offensive line against who played the latest game (snap counts). Teams often leave charts stale, and a few chart rows carry stale player ids, which are repaired from the weekly rosters by team and name. <b>Next Gen receiving</b>: season rows for qualifying receivers, aggregated per team weighted by targets (separation, cushion, air yards) or catches (YAC over expected).</li>
<li><b>Individual pass rushers and coverage</b>: PFR advanced defence, one row per defender per game, summed per player and team (a traded player appears under each team). "Per 100 snaps" uses all defensive snaps, not pass rushes, so it understates pass rushers on defences that face many runs. Coverage figures are for the nearest defender on targeted throws; passer rating allowed is recomputed from the summed targets, completions, yards, TDs and INTs. Status comes from the absences in section 16. <b>FTN box counts, motion, RPO, no-huddle, contested targets and QB-fault sacks</b>: FTN play charting, matched to play-by-play.</li>
<li><b>Offensive player usage, game logs and rankings</b>: from the same play-by-play (rbsdm.com's box scores are built from it too). Targets are pass attempts with a receiver; carries are designed rushes (scrambles excluded; about 3% of designed rushes, mostly aborted snaps, have no ball carrier and are left out); shares are of the team's totals; "last 3" is the team's last three games. Position, name and status come from the weekly roster and the absences; snap share from snap counts; RYOE and separation from Next Gen weekly rows. Rankings need minimum volume and are season figures only.</li>
<li><b>Run direction, targets by position and throw zones</b>: play-by-play run location (inside = middle or guard gap; outside = tackle or end), the targeted receiver's position on the weekly roster (fullbacks count as RBs), and nflfastR throw location (deep = 15+ air yards; left, middle, right). Run direction is not the blocking scheme, and position is not alignment: free data has neither run concepts nor slot vs outside receivers.</li>
<li><b>Win rates</b> (pass block, pass rush, run block, run stop): ESPN Analytics, built from NFL Next Gen Stats tracking. They are not in nflverse, so they are copied by hand each week from ESPN's team table with its date (the win-rates file in the analytics scripts), shown for context only and not used in any rating, composite or matchup expectation. A pass block win means the line held its blocks for 2.5 seconds; a pass rush win means a rusher beat his block within 2.5 seconds.</li>
<li><b>DVOA</b>: FTN's proprietary metric. It is not in nflverse and is not used or shown in this report. The closest computed analogues here are opponent-adjusted EPA and success rate. They are not DVOA.</li>
<li><b>Coverage, personnel and scheme</b>: this season's usage rates (man, zone, press, single-high, split-safety, cover 0, base, nickel, dime, blitz, pressure with and without a blitz; offensive personnel, play action, motion, tempo, quick passes, route direction and run concepts) are read by hand each week from NFL.com's Next Gen Trends team pages, with the date, because nflverse has no 2026 coverage data yet. The 2018-25 test (<code>backtest_coverage.py</code>, nflverse participation charting, weeks 1-9 against 10-18) found the usage tendencies stable within a season but the EPA a defence allows in a given coverage no more predictable than its overall EPA, and weighting an offence's results against man and zone by the defence's coverage mix predicted second-half games slightly worse than the plain matchup. So the tendencies are shown as description and do not change any expectation. Time to pressure and pressure by play remain unavailable; PFR pressures are game-level, so pressure-when-blitzing in the main tables uses the hit-or-sack proxy.</li>
<li><b>Pressure coverage</b>: PFR advanced stats are available for {T.off_pfr_games.sum()/2:.0f} of {meta['games']} games; pressure rates use only those games.</li>
{ftn_note}
<li><b>Participation data</b> (players on field per play) is not published for 2026, so personnel groupings and on/off splits are not possible. Availability uses snap counts, weekly rosters and injury reports.</li>
{inj_note}
<li><b>Timeout use</b> is not scored: there is no defensible free benchmark. <b>Bye effects</b> rest on one game per team.</li>
<li><b>Blitz</b>: FTN's blitz is five or more rushers, so "blitz" and "5+ rushers" are the same split here.</li></ul>
<h3>Small samples</h3>
<p>Rates on very few cases are shown in muted italics with their n, without a rank or colour, and are not used in mismatch findings. Minimums:
{esc("; ".join(sorted({f"{SAMPLE_LABEL.get(c, c)} {m}" for c, m in SAMPLE_MIN.values()})))}. Every other rate shows its sample size when you hover the cell.</p>
<h3>Recent form, replacements, pressure, big plays and referees</h3>
<ul>
<li><b>Recent form</b>: each play of a team's last four games is adjusted with the season's opponent effects and home coefficient (EPA minus the opponent's
defensive or offensive effect and the home term); the average over all of a team's plays equals its opponent-adjusted EPA/play, so the four-game and season figures
are on the same scale. Four games are about 250 plays per unit, so changes under about 0.05 EPA/play are ordinary noise.</li>
<li><b>Next man up</b>: the replacement named by the depth chart, judged on his own 2026 sample (receivers and backs: targets, carries and EPA; pass rushers and
linebackers: snaps and PFR pressures; linemen and defensive backs: the unit's EPA per dropback in games he started, meaning 50%+ of snaps, against the other games).</li>
<li><b>Quarterbacks under pressure</b>: EPA per dropback when hit or sacked against clean dropbacks (play-by-play qb_hit and sack flags), with dropback counts,
sack and scramble rates.</li>
<li><b>Expected starter</b>: where a team's season figures mix quarterbacks, the matchup tables add a line for this week's expected starter: the latest
game's starter (30+ dropbacks) unless he is on the reserve list or listed Out/Doubtful, otherwise the healthy quarterback with the most starts. It uses his own
dropbacks (opponent-adjusted EPA, success, sack and interception-worthy rates); under four starts it is marked low confidence. The rule cannot see a trade,
a signing or a coach's decision, so a small hand-kept file adds those for the coming week, each with its source (a team announcement or a named reporter):
the named starter then replaces the rule, his own 2026 sample counts every team he played for, and a quarterback with no regular-season dropbacks is shown
with no sample. The team rows are not changed: they still describe the quarterbacks who played.</li>
<li><b>Big plays allowed by position</b>: completions of 20+ yards and yards after the catch allowed to the receiver's weekly-roster position, per target and per game.</li>
<li><b>Referee crews</b>: accepted penalties per game (same rules as the team tables) in the games each referee worked in {esc(REF['pool'])}; the referee comes from the
nflverse schedules, which name him for {REF['cur_games_with_ref']} of {REF['cur_games']} {REF['season']} games so far. This week's assignments come from a hand-kept file with
its source and date ({'loaded' if REF['assign_loaded'] else 'not loaded yet'}).{(" This season's rates per referee (accepted flags and yards per game, both teams) are copied by hand from "
+ esc(REF['season_rates']['source']['title']) + " (" + esc(REF['season_rates']['source']['updated']) + "), because nflverse names few of this season's referees; "
+ esc(REF['season_rates']['check'])) if REF.get('season_rates') else ""}</li>
<li><b>Absences</b>: snap-count players are linked to rosters through the nflverse players table (PFR id to gsis id), then the roster's own PFR id, then team and name.
Each player's status is his latest weekly-roster row. A regular inactive (INA) for each of the team's last three games with no injury designation counts as out
("inactive 3+ games"); a player active on a roster dated after a missed game is not flagged; a report for a game the player then played is not counted.</li>
<li><b>Regulars</b>: 50%+ of offensive or defensive snaps in the games he played, at least two games, and at least half of the team's games up to his last
appearance (a starter hurt early stays in; a fill-in with two late games stays out), one row per player at his most-played position. A quarterback counts only when he started the team's latest game or has its most starts (a backup is not an absence).
Each absence shows when he last played and how many team games he has missed: <i>new</i> = 0-1 games, <i>long-term</i> = 2 or more. A long-term absence states how many
of the team's games the player was part of; "mostly reflected in the season numbers" is said only when his current run of missed games is at least half of them, and never for a quarterback.
Only new absences go into the takeaways.</li>
<li><b>Injury statuses</b>: on the Tuesday build the coming week's practice reports do not exist yet, so every status is labelled "last week's report (week N)"
(teams off a bye use an older week). A status refresh after the final injury reports (Friday about 16:30 ET; Thursday for a Thursday game) re-downloads the
injury reports, rosters and depth charts and rebuilds only the absences, next man up, arrivals, quarterback scenarios and the per-game files
(<code>refresh_status.py</code>). The practice-concern column is hidden until the coming week's practice reports exist.</li>
<li><b>New arrivals and departures</b>: active players whose latest roster team differs from an earlier 2026 week, or who joined in season (signing, practice-squad promotion),
shown when they were regulars elsewhere (40%+ of snaps in at least two games) or play 40%+ of snaps for the new team, with their 2026 sample (sacks and QB hits from
play-by-play, PFR pressures, targets and carries, or the unit's numbers in their starts). Departures are former regulars of a team now on another roster; a departure is new
for one team game after his last. Moves come from the weekly rosters (through week {ARR_WEEK}), so a later trade appears after the next roster update.</li>
<li><b>Unusual games</b>: a game is flagged when the play-by-play weather text shows rain, snow or {UN_WIND}+ mph wind (not a dome or closed roof) and combined dropbacks are under {UN_CUT:.0f},
the bottom {UN_PCTL}% of {UN_N} {UN_YEARS} regular-season games (median {UN_MED:.0f}). Season and last-four figures are shown with and without it. A quarterback who threw 2+ interceptions
in his team's latest game gets FTN's interception-worthy and uncatchable counts against his earlier games; that charting cannot separate a wet ball from a bad decision. Display only:
no rating or expectation changes.</li>
<li><b>Headline edges</b> are scored on the matchup models' shrunk effects (each unit's effect times the share the shrinkage keeps, in standard deviations
of the true effects), so a measure with no reliable signal cannot top the list. Blitz tendencies have no shrinkage model and stay as context in the
matchup report.</li>
<li><b>Player rates</b> are shown with their sample and only from a minimum: 10 targets or carries for EPA per target or carry, 20 dropbacks for a
quarterback's EPA against the blitz or when hit, 100 dropbacks on each side of a with/without split.</li>
<li><b>ESPN win rates</b>: the hand-copied file is checked on load (32 teams, four metrics, values 0-100, ranks 1-32, same through-week as the report);
{"it passed, through week " + str(WRI["through_week"]) + " (" + esc((WRI.get("source") or {}).get("updated") or "") + ")" if WRI["ok"] else "it failed (" + esc("; ".join(WRI["problems"][:3])) + "), so the columns are hidden"}.
{("Across the 32 teams: " + "; ".join(f"{esc(lab)} r = {r:+.2f}" for lab, r in WRI["corr"]) + ". Run-block win rate is barely related to yards before contact, so it is context only.") if WRI["corr"] else ""}</li>
</ul>
<h3>Sign conventions</h3>
<p>Defensive EPA, success and yards are what the defence allows, so lower is better (▼ in the header); every composite, rating and situational score is oriented so higher
is better (▲). Ranks are always 1 = best for that unit, and the Team chart flips any lower-is-better axis so up and right are good.</p>
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
