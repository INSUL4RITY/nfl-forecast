"""Audit section 4b: does a forecast-time "absent starters" input improve the Model line? (walk-forward, decision rule)

Inputs (from s4_roster.py, reports/audit_2026_11/s4_absences.parquet), known before kickoff only:
  kn_off  own offensive regulars (>= 60% of snaps in >= 2 earlier games this season, non-QB) absent and KNOWN absent:
          Out/Doubtful on the final injury report, or on a reserve list / suspended / off the team in the team's latest
          weekly roster before this week. Sum of their snap shares (1.0 = one full-time starter).
  kn_def  the same for the opponent's defence (enters the team's own points row as an opponent feature).
Candidates: A = core_qb + kn_off/kn_def (all known absences); B = core_qb + roster-only absences (reserve list, released,
traded: the part the injury report never shows). Regular season only (playoffs = 0). Weeks 1-2 have no regulars yet (0).
CAVEAT: weekly-roster files' exact publication time is not recorded; the previous week's file is used as a lag.
Run: .venv\\Scripts\\python.exe scripts\\audit_2026_11\\s4b_adjust.py
"""

import polars as pl

from common import OUT, base_fs, decide, fmt_decision, live_2026, load, point_metrics, save, walk_forward

A = pl.read_parquet(OUT / "s4_absences_players.parquet").filter(pl.col("pfr").is_not_null())
off, de = pl.col("unit") == "off", pl.col("unit") == "def"


def agg(cond):
    return (pl.col("share") * cond).sum()


T = A.group_by("game_id", "team").agg(kn_off=agg(off & pl.col("known")), kn_def=agg(de & pl.col("known")),
                                      ro_off=agg(off & pl.col("roster_prev")), ro_def=agg(de & pl.col("roster_prev")))
data = load("final")
G = data.select("game_id", "home_id", "away_id")
for side in ("home", "away"):
    data = data.join(T.rename({c: f"{side}_{c}" for c in ("kn_off", "kn_def", "ro_off", "ro_def")} | {"team": f"{side}_id"}),
                     on=["game_id", f"{side}_id"], how="left")
data = data.with_columns([pl.col(f"{s}_{c}").fill_null(0.0) for s in ("home", "away") for c in ("kn_off", "kn_def", "ro_off", "ro_def")])
fs = base_fs()
fsA = {**fs, "team": fs["team"] + ["kn_off"], "opp": fs["opp"] + ["kn_def"]}
fsB = {**fs, "team": fs["team"] + ["ro_off"], "opp": fs["opp"] + ["ro_def"]}
info = {}
preds = pl.concat([walk_forward(data, "full", fs, info=info), walk_forward(data, "A_known_absences", fsA, info=info),
                   walk_forward(data, "B_roster_only_absences", fsB, info=info)])
preds.write_parquet(OUT / "s4b_predictions.parquet")
res = {"decisions": [decide(preds, c, "full") for c in ("A_known_absences", "B_roster_only_absences")],
       "decisions_total": [decide(preds, c, "full", loss="ae_total") for c in ("A_known_absences", "B_roster_only_absences")],
       "coverage": {"team_games_with_known_absence": float((pl.concat([data["home_kn_off"] + data["home_kn_def"],
                                                                        data["away_kn_off"] + data["away_kn_def"]]) > 0).mean())}}
# fitted size of the new inputs in the last fold (points per full-time starter, per team-row)
from nflcast.models.core import FootballRidge  # noqa: E402
for nm, f in (("A", fsA), ("B", fsB)):
    tr = data.filter((pl.col("season") >= 2016) & (pl.col("season") < 2024))
    m = FootballRidge(alpha=info[f"{'A_known_absences' if nm == 'A' else 'B_roster_only_absences'}"][2024]["alpha"], feature_set=f).fit(tr)
    c = dict(zip(m.names, m.pipe[-1].coef_ / m.pipe[0].scale_))
    res[f"coef_fold2024_{nm}"] = {k: float(v) for k, v in c.items() if k.endswith(("kn_off", "kn_def", "ro_off", "ro_def"))}
L = pl.concat([live_2026(data, "full", fs), live_2026(data, "A_known_absences", fsA), live_2026(data, "B_roster_only_absences", fsB)])
res["live_2026"] = {v: point_metrics(L.filter(pl.col("model") == v)) for v in L["model"].unique().sort().to_list()}
ind = L.join(data.select("game_id", "home_id", "away_id"), on="game_id").filter((pl.col("home_id") == "IND") | (pl.col("away_id") == "IND"))
res["ind_2026_games"] = ind.select("game_id", "model", "pred_margin", "margin").sort("game_id", "model").to_dicts()
save("s4b_adjust", res)
for d in res["decisions"] + res["decisions_total"]:
    print(fmt_decision(d))
print("coefs fold 2024:", res["coef_fold2024_A"], res["coef_fold2024_B"])
print("2026 live:", {k: (v["n_games"], round(v["margin_mae"], 3)) for k, v in res["live_2026"].items()})
for r in res["ind_2026_games"]:
    print("  IND", r["game_id"], r["model"], round(r["pred_margin"], 1), r["margin"])
