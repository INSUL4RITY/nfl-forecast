"""Cross-check of the hand-kept play_callers_<season>.json against Sam Hoppen's public play-caller dataset.

The dataset (github.com/samhoppen/NFL_public, data/all_playcallers.csv) lists the offensive play-caller, the defensive
play-caller and the head coach for every team-game since 1999. It is read at build time and never copied into this
repository (it carries no licence); the hand-kept file, which cites a source for every entry, stays the record. The
check only reports differences for games already played: its rows for future weeks are filled forward, not facts.
A failed download is reported as "not checked" and never stops a build.

    .venv\\Scripts\\python.exe scripts\\team_analytics\\caller_check.py --season 2026 --through-week 9
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import re

import pandas as pd
import requests

import callers

URL = "https://raw.githubusercontent.com/samhoppen/NFL_public/main/data/all_playcallers.csv"
NAME = "Sam Hoppen's play-caller dataset"
SIDES = (("off", "off_play_caller", "offence"), ("def", "def_play_caller", "defence"), ("hc", "head_coach", "head coach"))
TEAM_FIX = {"LAR": "LA"}


def norm(name) -> str:
    """Name key: letters only, without Jr./Sr./II/III, so 'Brian Thomas Jr.' and 'Brian Thomas' match."""
    s = re.sub(r"\b(jr|sr|ii|iii|iv)\b\.?", "", str(name).lower())
    return re.sub(r"[^a-z]", "", s)


def ours_at(team_cfg: dict, side: str, week: int) -> str:
    """The file's caller for this team and side in a given week (changes applied from their first week)."""
    if side == "hc":
        return team_cfg["hc"]
    unit = team_cfg[side]
    ch = sorted(unit.get("changes", []), key=lambda x: x["from_week"])
    if not ch:
        return unit["caller"]
    who = ch[0]["previous"]
    for x in ch:
        if x["from_week"] <= week:
            who = x["caller"]
    return who


def weeks_txt(ws: list[int]) -> str:
    ws = sorted(ws)
    return f"week {ws[0]}" if len(ws) == 1 else f"weeks {ws[0]}-{ws[-1]}" if ws == list(range(ws[0], ws[-1] + 1)) else "weeks " + ", ".join(map(str, ws))


def compare(cfg: dict, data: pd.DataFrame, season: int, through_week: int) -> dict:
    """Differences for games played (week <= through_week). 'unclear' entries in the file are listed, not counted as differences."""
    d = data[(data.season == season) & (data.week <= through_week)].assign(team=lambda x: x.team.replace(TEAM_FIX))
    diffs, unclear, n = [], [], 0
    for t, c in sorted(cfg["teams"].items()):
        g = d[d.team == t]
        for side, col, label in SIDES:
            open_q = side != "hc" and c[side].get("conf") == "unclear"
            bad = {}
            for r in g.itertuples():
                theirs = getattr(r, col)
                if pd.isna(theirs):
                    continue
                n += 0 if open_q else 1
                mine = ours_at(c, side, int(r.week))
                if not open_q and norm(mine) != norm(theirs):
                    bad.setdefault((mine, str(theirs)), []).append(int(r.week))
            for (mine, theirs), ws in bad.items():
                diffs.append({"team": t, "side": label, "weeks": ws, "file": mine, "dataset": theirs})
            if open_q and len(g):
                unclear.append({"team": t, "side": label, "file": c[side]["caller"], "dataset": str(getattr(g.sort_values("week").iloc[-1], col))})
    missing = sorted(set(cfg["teams"]) - set(d.team))
    return {"checked": n, "differences": diffs, "unclear": unclear, "teams_missing": missing}


def fetch(get=requests.get) -> pd.DataFrame:
    r = get(URL, timeout=60, headers={"User-Agent": "nflcast-team-analytics"})
    r.raise_for_status()
    return pd.read_csv(io.BytesIO(r.content))


def qc_line(res: dict | None, through_week: int, when: str = "", error: str = "") -> str:
    if res is None:
        return f"Play-caller check: not checked ({NAME} could not be read: {error})."
    head = f"Play-caller check against {NAME} (read {when}), games through week {through_week}: "
    if res["teams_missing"]:
        return head + f"the dataset has no rows yet for {', '.join(res['teams_missing'])}; {res['checked']} entries compared."
    parts = [f"{x['team']} {x['side']} {weeks_txt(x['weeks'])}: file {x['file']}, dataset {x['dataset']}" for x in res["differences"]]
    out = head + (f"{len(parts)} difference{'s' if len(parts) != 1 else ''} in {res['checked']} entries, to verify against a news source "
                  f"({'; '.join(parts)})." if parts else f"all {res['checked']} entries agree.")
    if res["unclear"]:
        out += " Marked unclear in the file: " + "; ".join(f"{x['team']} {x['side']} ({x['file']}; the dataset lists {x['dataset']})" for x in res["unclear"]) + "."
    return out


def run(season: int, through_week: int, get=requests.get) -> tuple[dict | None, str]:
    """(result or None, quality-check line). Never raises."""
    try:
        data = fetch(get)
        res = compare(callers.load_callers(season), data, season, through_week)
        return res, qc_line(res, through_week, dt.datetime.now(dt.timezone.utc).strftime("%d %b %Y %H:%M UTC"))
    except Exception as e:  # noqa: BLE001
        return None, qc_line(None, through_week, error=type(e).__name__)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, default=2026)
    ap.add_argument("--through-week", type=int, required=True)
    a = ap.parse_args()
    print(run(a.season, a.through_week)[1])
