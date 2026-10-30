"""One compact Markdown file per game from the built team analytics report, for attaching to a claude.ai chat.

The report page is large (about 2.5 MB), so a chat may read only part of it. This reads the data embedded in
report.html and writes games/<game_id>.md: the matchup tables (with expected values where the report has them),
findings, cautions, coaching, workload, travel, penalties, QB splits, team snapshot ranks, absences with usage, the
main ball carriers and targets, pass rushers and coverage. No model forecasts and no market data.

    python scripts/team_analytics/export_games.py [--dir reports/team_analytics/2026_week08]
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LINK = "https://claude.ai/artifact/YKV6tGCKPRt2mWPFrY5mht"

SNAP = [  # (label, key, higher is better)
    ("Overall rating (pts/game)", "rating_pg", True), ("Off. adj. EPA/play", "off_adj_epa", True), ("Def. adj. EPA/play allowed", "def_adj_epa", False),
    ("Off. adj. EPA/dropback", "off_adj_epa_db", True), ("Off. adj. EPA/rush", "off_adj_epa_rush", True),
    ("Def. adj. EPA/dropback", "def_adj_epa_db", False), ("Def. adj. EPA/rush", "def_adj_epa_rush", False),
    ("Off. success rate", "off_sr", True), ("Def. success allowed", "def_sr", False),
    ("Off. points/drive", "off_ppd", True), ("Def. points/drive", "def_ppd", False),
    ("Off. red-zone TD%", "off_rz_td_rate", True), ("Def. red-zone TD% allowed", "def_rz_td_rate", False),
    ("Off. 3rd-down conv.", "off_d3_conv", True), ("Def. 3rd-down conv. allowed", "def_d3_conv", False),
    ("Off. explosive rate", "off_expl_rate", True), ("Def. explosive rate allowed", "def_expl_rate", False),
    ("Pressure rate allowed", "off_pressure_rate", False), ("Pressure rate (D)", "def_pressure_rate", True),
    ("Blitz rate (D)", "def_blitz_rate", None), ("Sack rate allowed", "off_sack_rate", False),
    ("Pass block win rate", "pbwr", True), ("Pass rush win rate", "prwr", True), ("Run block win rate", "rbwr", True), ("Run stop win rate", "rswr", True),
    ("Turnover margin", "to_margin", True), ("Expected TO margin", "x_to_margin", True),
    ("Penalties/game (offence)", "pen_off_pg", False), ("Penalties/game (defence)", "pen_def_pg", False), ("Special teams EPA/game", "st_epa_pg", True),
]
PCT = {"off_sr", "def_sr", "off_rz_td_rate", "def_rz_td_rate", "off_d3_conv", "def_d3_conv", "off_expl_rate", "def_expl_rate",
       "off_pressure_rate", "def_pressure_rate", "def_blitz_rate", "off_sack_rate", "pbwr", "prwr", "rbwr", "rswr"}


def num(v):
    return isinstance(v, (int, float)) and not (isinstance(v, float) and math.isnan(v))


def fmt(v, f):
    if not num(v):
        return "n/a" if v is None else str(v)
    return {"epa": f"{v:+.3f}", "pct": f"{100 * v:.1f}%", "n1": f"{v:.1f}", "n2": f"{v:.2f}", "s1": f"{v:+.1f}",
            "s2": f"{v:+.2f}", "int": f"{int(round(v))}"}.get(f, str(v))


def ordn(n):
    n = int(n)
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def snap_value(k, v):
    if not num(v):
        return "n/a"
    if k in PCT:
        return f"{100 * v:.1f}%"
    if k in ("rating_pg", "off_proe"):
        return f"{v:+.1f}"
    if k in ("to_margin",):
        return f"{v:+.0f}"
    if k in ("x_to_margin", "st_epa_pg"):
        return f"{v:+.1f}"
    if k in ("off_ppd", "def_ppd", "pen_off_pg", "pen_def_pg"):
        return f"{v:.2f}"
    return f"{v:+.3f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(ROOT / "reports" / "team_analytics" / "2026_week08"))
    d = Path(ap.parse_args().dir)
    h = (d / "report.html").read_text(encoding="utf-8")
    i = h.index("const DATA = ") + len("const DATA = ")
    D, _ = json.JSONDecoder().raw_decode(h[i:])
    M, BY = D["meta"], {t["team"]: t for t in D["teams"]}
    ranks = {}
    for _, k, hi in SNAP:
        if hi is None:
            continue
        vals = sorted([BY[t][k] for t in BY if num(BY[t].get(k))], reverse=hi)
        ranks[k] = {t: vals.index(BY[t][k]) + 1 for t in BY if num(BY[t].get(k))}
    U, PL = D["usage"], D["players"]
    out_dir = d / "games"
    out_dir.mkdir(exist_ok=True)
    for g in D["games"]:
        a, hm = g["away"], g["home"]
        R = D["reports"].get(g["id"], {})
        L = [f"# {g['label']}: team analytics (2026 week {M['through_week'] + 1})", "",
             f"{g['when']} · {g['venue']}" + (" · divisional" if g.get("div") else "") + (" · neutral site" if g.get("neutral") else ""),
             f"Rest: {a} {g['rest'].get(a)} days, {hm} {g['rest'].get(hm)} days." + (f" **{g['final']}**" if g.get("final") else ""),
             f"Data: nflverse games through week {M['through_week']} ({M['games']} games); report generated {M['generated_utc']}; depth charts {D.get('depth_as_of')}. "
             f"Full report: {LINK} (section 'Week {M['through_week'] + 1} matchups'). Ranks are 1-32, 1 = best for that unit.",
             "No model forecasts or market data in this file.", ""]
        if g.get("note"):
            L += ["## Latest news noted in the report", g["note"], ""]
        s = g.get("summary", {})
        L += ["## Overview", "| Team | Record | Overall rating (rank) | With 2025 prior | Offence rank | Defence rank | ST rank | QB starts |", "|---|---|---|---|---|---|---|---|"]
        for t in (a, hm):
            x = s.get(t, {})
            L.append(f"| {t} | {x.get('record')} | {fmt(x.get('rating'), 's1')} ({ordn(x['rating_rank'])}) | {ordn(x['stab_rank'])} | {ordn(x['off_rank'])} | {ordn(x['def_rank'])} | {ordn(x['st_rank'])} | {x.get('qb')} |")
        L += ["", "## Biggest edges (report screen)"] + [f"- {e['what']}: {e['detail']} · edge to {e['favours']} (score {e['score']:+.1f})" for e in g.get("edges", [])] + [""]
        L += ["## Expected in this matchup"] + [f"- {x}" for x in g.get("expect", [])] + [""]
        for sd in g["sides"]:
            L += [f"## {sd['off']} offence vs {sd['def']} defence", "| Metric | Off. (rank) | Def. (rank) | Expected in matchup | League | Lean | Confidence |", "|---|---|---|---|---|---|---|"]
            for grp in sd["groups"]:
                L.append(f"| **{grp['name']}** | | | | | | |")
                for r in grp["rows"]:
                    e = (fmt(r["exp"], r["f"]), fmt(r["lg"], r["f"]), r["lean"], r["conf"]) if "exp" in r else ("season figures only", "", "", "")
                    L.append(f"| {r['lab']} | {fmt(r['o'], r['f'])} ({ordn(r['o_rank'])}) | {fmt(r['d'], r['f'])} ({ordn(r['d_rank'])}) | {e[0]} | {e[1]} | {e[2]} | {e[3]} |")
            L.append("")
        if R.get("mismatches"):
            L.append("## Mismatches (evidence, mechanism, neutralisers)")
            for x in R["mismatches"]:
                L.append(f"- **{x['kind']}** ({x.get('offence')} offence vs {x.get('defence')} defence), favours {x['favours']}, confidence {x['conf']}: {x['evidence']} "
                         f"Mechanism: {x['mechanism']}" + (f" Matchup-specific: {x['specific']}" if x.get("specific") else "")
                         + (" Neutralisers: " + " ".join(x["neutralisers"]) if x.get("neutralisers") else ""))
            L.append("")
        if R.get("counter"):
            L += ["## Counterarguments"] + [f"- {c}" if isinstance(c, str) else f"- {json.dumps(c)}" for c in R["counter"]] + [""]
        L += ["## Be careful with"] + [f"- {c}" for c in g.get("cautions", [])] + [""]
        L += ["## Special teams", f"| Metric | {a} | {hm} |", "|---|---|---|"]
        for r in g.get("st", []):
            L.append(f"| {r['lab']} | {fmt(r['a'], r['f'])}" + (f" ({ordn(r['a_rank'])})" if r.get("a_rank") else "") +
                     f" | {fmt(r['h'], r['f'])}" + (f" ({ordn(r['h_rank'])})" if r.get("h_rank") else "") + " |")
        L += ["", "## Coaching and play-calling"]
        for t in (a, hm):
            c, b = g.get("coach", {}).get(t, {}), BY[t]
            L.append(f"- **{t}**: HC {b.get('hc')}; offence called by {b.get('off_caller')} ({'all weeks' if b.get('off_caller_weeks') == 'all' else 'weeks ' + str(b.get('off_caller_weeks'))}); defence called by {b.get('def_caller')} "
                     f"({'all weeks' if b.get('def_caller_weeks') == 'all' else 'weeks ' + str(b.get('def_caller_weeks'))}); ST {b.get('stc')}. Game management {c.get('agg')} (4th-down go rate {fmt(c.get('go'), 'pct')} on {c.get('n4')} decisions); "
                     f"offence {c.get('lean')} (PROE {fmt(c.get('proe'), 's1')}); defence {c.get('blitz')} ({fmt(c.get('blitz_rate'), 'pct')}); one-score games {c.get('one_score')}.")
        L.append("")
        wl, tr = R.get("workload", {}), R.get("travel", {})
        L.append("## Workload, rest and travel")
        for t in (a, hm):
            L += [f"- **{t}**: " + " ".join(wl.get(t, {}).get("lines", []) + tr.get(t, []))]
        L.append("")
        if R.get("penalties"):
            L += ["## Penalty angles"] + [f"- {p['team']}: {p['risk']}. {p['evidence']} ({p['caveat']})" for p in R["penalties"]] + [""]
        L.append("## Quarterbacks (each passer's own games)")
        for t in (a, hm):
            for q in (R.get("qb", {}).get(t, {}) or {}).get("rows", []):
                L.append(f"- {t} {q['name']}: {q['starts']} starts (weeks {q['start_weeks']}), {q['dropbacks']} dropbacks, EPA/db {fmt(q['epa_db'], 'epa')}, adj. {fmt(q['adj_epa_db'], 'epa')}, "
                         f"sack rate {fmt(q['sack_rate'], 'pct')}, EPA vs blitz {fmt(q.get('epa_vs_blitz'), 'epa')}, hit/sacked EPA {fmt(q.get('epa_hit_sack'), 'epa')}"
                         + (f", expected EPA/db in this matchup {fmt(q['exp_db'], 'epa')}" if q.get("exp_db") is not None else "")
                         + (f"; status {q.get('report_status') or q.get('practice_status')}" if (q.get('report_status') or q.get('practice_status')) else "")
                         + ("; latest starter" if q.get("latest_starter") else ""))
        L += ["", "## Team snapshot (season, rank)", f"| Metric | {a} | {hm} |", "|---|---|---|"]
        for lab, k, hi in SNAP:
            row = [f"{snap_value(k, BY[t].get(k))}" + (f" ({ordn(ranks[k][t])})" if hi is not None and t in ranks.get(k, {}) else "") for t in (a, hm)]
            L.append(f"| {lab} | {row[0]} | {row[1]} |")
        L.append("")
        for t in (a, hm):
            ab = [x for x in D["absences"] if x["team"] == t]
            L += [f"## {t}: absences and practice concerns (latest report)"]
            if ab:
                L += ["| Player | Pos. | Avg snap share | Status | Detail | Usage | Next man up |", "|---|---|---|---|---|---|---|"]
                for x in ab:
                    nu = (f"{x['next_up']} ({x.get('next_up_snaps') or 0} snaps)" if x.get("next_up") else (x.get("note") or ""))
                    L.append(f"| {x['player']} | {x['position']} | {fmt(x['share'], 'pct')} | {x['status_class']} | {x['reason']} | {x.get('usage') or ''} | {nu} |")
            else:
                L.append("No regulars listed.")
            L.append("")
            tp = U["team_players"].get(t, [])[:10]
            L += [f"## {t}: who gets the ball (season, last 3 games)", "| Player | Pos. | Snap share | Targets (share, last 3) | Rec-yds-TD | EPA/target | Carries (share, last 3) | Rush yds-TD | EPA/carry | RZ tgt/car | Status |", "|---|---|---|---|---|---|---|---|---|---|---|"]
            for p in tp:
                L.append(f"| {p['name']} | {p['pos']} | {fmt(p['snap_pct'], 'pct')} | {p['targets']} ({fmt(p['tgt_share'], 'pct')}, {fmt(p['tgt_share_l3'], 'pct')}) | {p['rec']}-{p['rec_yds']}-{p['rec_td']} | {fmt(p['epa_tgt'], 'epa')} | "
                         f"{p['carries']} ({fmt(p['car_share'], 'pct')}, {fmt(p['car_share_l3'], 'pct')}) | {p['rush_yds']}-{p['rush_td']} | {fmt(p['epa_car'], 'epa')} | {p['rz_tgt']}/{p['rz_car']} | {p['status']} |")
            pr = PL.get(t, {})
            L += ["", f"## {t} defence: pass rushers and coverage (PFR)",
                  f"Top three rushers made {fmt(pr.get('top3_press_share'), 'pct')} of {pr.get('pressures')} player pressures; players now out made {fmt(pr.get('press_out_share'), 'pct')}. "
                  f"Defenders now out drew {fmt(pr.get('tgt_out_share'), 'pct')} of {pr.get('targets')} targets."]
            L += ["| Pass rusher | Pos. | Pressures (share) | Sacks | Hits | Status |", "|---|---|---|---|---|---|"]
            L += [f"| {x['name']} | {x['pos']} | {x['pressures']} ({fmt(x['share'], 'pct')}) | {fmt(x['sacks'], 'n1')} | {x['hits']} | {x['status']} |" for x in pr.get("rush", [])[:4]]
            L += ["", "| Cover man | Pos. | Targets (share) | Comp. % | Yds/target | TD/INT | Rating allowed | Status |", "|---|---|---|---|---|---|---|---|"]
            L += [f"| {x['name']} | {x['pos']} | {x['targets']} ({fmt(x['share'], 'pct')}) | {fmt(x['cmp_pct'], 'pct')} | {fmt(x['ypt'], 'n1')} | {x['td']}/{x['ints']} | {fmt(x['rating'], 'n1')} | {x['status']} |" for x in pr.get("cov", [])[:4]]
            L.append("")
        L += ["## Reading notes",
              "- 'Expected in matchup' values are pulled toward the league average by how reliable each stat has been (fitted on 2021-25); rows marked 'season figures only' are raw season values, so check the sample before trusting a big gap.",
              "- Charted stats (pressures, blitzes, drops, contested balls, QB-fault sacks) are FTN / PFR staff judgement. Run direction is not the blocking scheme; targets by position use the roster position, not alignment.",
              "- Statuses are from the latest nflverse injury report at the data pull; verify final statuses and inactives from the official injury reports."]
        (out_dir / f"{g['id']}.md").write_text("\n".join(L) + "\n", encoding="utf-8")
        print("wrote", out_dir / f"{g['id']}.md", f"{len(chr(10).join(L)) / 1e3:.1f} KB")


if __name__ == "__main__":
    main()
