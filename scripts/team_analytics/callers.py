"""Play-caller attribution for the team analytics report.

Tendencies are credited to whoever owns the decision: the head coach (game management), the offensive play-caller,
the defensive play-caller and the special-teams coordinator. Names come from the hand-kept play_callers_<season>.json
(every entry has a source). When a play-caller changed mid-season, that unit's tendencies are computed separately for
the weeks under each caller, and the report's caller tables use the current caller's weeks only.

Run on its own (re-uses compute.py's cached downloads):
    python scripts/team_analytics/callers.py --season 2026 --through-week 7
compute.py also calls build() and writes callers.json with the rest of the bundle.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent


def load_callers(season: int) -> dict:
    return json.loads((HERE / f"play_callers_{season}.json").read_text(encoding="utf-8"))


def off_tendencies(p: pd.DataFrame, pf: pd.DataFrame) -> pd.DataFrame:
    """Offensive play-calling tendencies by posteam (raw, not opponent-adjusted)."""
    sc = p[p.sc]
    out = pd.DataFrame(index=sorted(sc.posteam.dropna().unique()))
    out["games"] = sc.groupby("posteam").game_id.nunique()
    out["plays"] = sc.groupby("posteam").size()
    s = sc.sort_values(["game_id", "play_id"]).copy()
    s["gap"] = s.groupby(["game_id", "fixed_drive"]).game_seconds_remaining.diff(-1)
    s["gap"] = s.gap.where(s.gap.between(1, 60))
    out["pace_sec"] = s[s.wp.between(0.2, 0.8) & (s.qtr <= 3)].groupby("posteam").gap.median()
    neu = p[p.sc & p.wp.between(0.2, 0.8) & p.early & (p.half_seconds_remaining > 120)]
    out["early_pass_rate"] = neu.groupby("posteam").db.mean()
    out["proe"] = neu[neu.pass_oe.notna()].groupby("posteam").pass_oe.mean()
    ch = pf[pf.db & pf.is_play_action.notna()]
    out["pa_rate"] = ch.is_play_action.astype(float).groupby(ch.posteam).mean()
    scr = pf[pf.db & pf.is_screen_pass.notna()]
    out["screen_rate"] = scr.is_screen_pass.astype(float).groupby(scr.posteam).mean()
    out["epa"] = sc.groupby("posteam").epa.mean()
    out["sr"] = sc.groupby("posteam").success.mean()
    out["h2_minus_h1"] = (sc[sc.game_half == "Half2"].groupby("posteam").epa.mean()
                          - sc[sc.game_half == "Half1"].groupby("posteam").epa.mean())
    return out


def def_tendencies(p: pd.DataFrame, pf: pd.DataFrame) -> pd.DataFrame:
    """Defensive play-calling tendencies by defteam (raw). EPA columns are allowed: lower is better."""
    sc = p[p.sc]
    out = pd.DataFrame(index=sorted(sc.defteam.dropna().unique()))
    out["games"] = sc.groupby("defteam").game_id.nunique()
    out["plays"] = sc.groupby("defteam").size()
    dbf = pf[pf.db & pf.n_pass_rushers.notna() & (pf.n_pass_rushers > 0)].copy()
    dbf["blitz"] = dbf.n_blitzers > 0
    g = dbf.groupby("defteam")
    out["blitz_rate"] = g.blitz.mean()
    out["charted_db"] = g.size()
    out["epa_blitz"] = dbf[dbf.blitz].groupby("defteam").epa.mean()
    out["epa_noblitz"] = dbf[~dbf.blitz].groupby("defteam").epa.mean()
    out["epa"] = sc.groupby("defteam").epa.mean()
    out["sr"] = sc.groupby("defteam").success.mean()
    out["h2_minus_h1"] = (sc[sc.game_half == "Half2"].groupby("defteam").epa.mean()
                          - sc[sc.game_half == "Half1"].groupby("defteam").epa.mean())
    return out


def game_management_extras(p: pd.DataFrame) -> pd.DataFrame:
    """Head-coach decisions not already in compute.coaching(): two-point tries."""
    k = p[(p.extra_point_attempt == 1) | (p.two_point_attempt == 1)]
    out = pd.DataFrame(index=sorted(p.posteam.dropna().unique()))
    out["two_pt_att"] = k[k.two_point_attempt == 1].groupby("posteam").size()
    out["two_pt_att"] = out.two_pt_att.fillna(0)
    out["two_pt_rate"] = out.two_pt_att / k.groupby("posteam").size()
    return out


def _rec(df: pd.DataFrame, t: str) -> dict:
    if t not in df.index:
        return {}
    return {k: (None if pd.isna(v) else (int(v) if k in ("games", "plays", "charted_db") else float(v)))
            for k, v in df.loc[t].items()}


def build(p: pd.DataFrame, pf: pd.DataFrame, season: int, through_week: int) -> dict:
    cfg = load_callers(season)
    teams = sorted(p.posteam.dropna().unique())
    missing = [t for t in teams if t not in cfg["teams"]]
    assert not missing, f"play_callers_{season}.json is missing {missing}"
    full = {"off": off_tendencies(p, pf), "def": def_tendencies(p, pf)}
    fns = {"off": off_tendencies, "def": def_tendencies}
    current, splits, staff = {}, [], {}
    for t in teams:
        c = cfg["teams"][t]
        cur = {}
        for side in ("off", "def"):
            unit = c[side]
            ch = [x for x in unit.get("changes", []) if x["from_week"] <= through_week]
            if ch:
                last = max(ch, key=lambda x: x["from_week"])
                bounds = [1] + sorted(x["from_week"] for x in ch) + [through_week + 1]
                callers_seq = [ch[0]["previous"]] + [x["caller"] for x in sorted(ch, key=lambda x: x["from_week"])]
                rows = []
                for (w0, w1), who in zip(zip(bounds[:-1], bounds[1:]), callers_seq):
                    mask = (p.week >= w0) & (p.week < w1)
                    fm = (pf.week >= w0) & (pf.week < w1)
                    d = fns[side](p[mask], pf[fm])
                    rows.append({"caller": who, "weeks": f"{w0}-{w1 - 1}" if w1 - 1 > w0 else str(w0), **_rec(d, t)})
                splits.append({"team": t, "side": side, "rows": rows, "note": last.get("note", "")})
                cur[side] = {**rows[-1], "since_week": last["from_week"]}
            else:
                cur[side] = {**_rec(full[side], t), "since_week": None}
        current[t] = cur
        staff[t] = {k: c[k] for k in ("hc", "oc", "dc", "stc")}
        staff[t].update({f"{side}_{k}": c[side].get(k) for side in ("off", "def") for k in ("caller", "conf", "note")})
        staff[t]["src"] = sorted({s for side in ("off", "def") for s in c[side]["src"]},
                                 key=lambda s: int(s[1:]))
    league = {side: {k: (None if pd.isna(v) else float(v)) for k, v in full[side].astype(float).mean().items()}
              for side in ("off", "def")}
    return {"season": season, "through_week": through_week, "checked": cfg["checked"], "sources": cfg["sources"], "staff": staff,
            "current": current, "splits": splits, "league": league,
            "gm": {t: _rec(game_management_extras(p), t) for t in teams}}


def main():
    import compute as cp  # noqa: E402 (re-uses the cached, policy-checked downloads)
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, default=2026)
    ap.add_argument("--through-week", type=int, default=7)
    a = ap.parse_args()
    S, W = a.season, a.through_week
    p = cp.add_unit_flags(cp.load_pbp(S, W))
    ftn = cp.fetch(f"ftn_charting/ftn_charting_{S}.parquet")
    ftn = ftn[ftn.week <= W]
    pf = p.merge(ftn[["nflverse_game_id", "nflverse_play_id", "n_blitzers", "n_pass_rushers", "is_play_action", "is_screen_pass"]],
                 left_on=["game_id", "play_id"], right_on=["nflverse_game_id", "nflverse_play_id"], how="left")
    out = build(p, pf, S, W)
    d = cp.ROOT / "reports" / "team_analytics" / f"{S}_week{W + 1:02d}"
    (d / "callers.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("wrote", d / "callers.json", len(out["splits"]), "split units")


if __name__ == "__main__":
    main()
