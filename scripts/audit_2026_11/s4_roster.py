"""Audit section 4: are the Model line's errors biased when a team is missing high-snap starters?

DIAGNOSTIC (not a feature): "absent" is measured AFTER the game from snap counts: a player who had played >= 60% of his
unit's snaps in the team's earlier games this season (>= 2 of them, games he played) and took no snaps for the team in
this game. QBs, kickers, punters and long snappers are excluded (QBs have their own model inputs). Each absence is tagged:
  * reported      on the team's final injury report for the week as Out or Doubtful
  * roster_prev   not on the team's roster as active in the PREVIOUS week's weekly roster (reserve list, released, traded)
  * known         reported or roster_prev: what a forecast could have known (previous-week roster = conservative lag)
  * new           he played in the team's previous game (the team's form numbers do not reflect his absence yet)
Residuals = actual minus predicted team points from section 3's walk-forward full-model predictions ("full"), 2019-2024
regular season, week >= 3. Writes per-team-game absences for 2016-2026 (s4_absences.parquet) for the adjustment test
(s4b_adjust.py). Run: .venv\\Scripts\\python.exe scripts\\audit_2026_11\\s4_roster.py
"""

import numpy as np
import polars as pl

from common import OUT, REPS, SEED, games, save
from nflcast.data import sources as S
from nflcast.data.games import franchise

ALL = list(range(2016, 2025)) + [2026]          # 2025 not used in this phase
TEST = list(range(2019, 2025))
REG, MIN_G = 0.60, 2
EXCL = {"QB", "K", "P", "LS"}
res = {"threshold_regular": REG, "min_prior_games": MIN_G}

G = games().filter(pl.col("season").is_in(ALL) & (pl.col("game_type") == "REG") & (pl.col("status") == "final"))


def i64(df):
    return df.with_columns(pl.col("season").cast(pl.Int64), pl.col("week").cast(pl.Int64))


snaps = pl.concat([i64(S.fetch("snap_counts", s).filter(pl.col("game_type") == "REG")) for s in ALL], how="diagonal_relaxed")
snaps = snaps.with_columns(team=franchise(pl.col("team"))).filter(~pl.col("position").is_in(list(EXCL)))
snaps = snaps.with_columns(unit=pl.when(pl.col("offense_pct") >= pl.col("defense_pct")).then(pl.lit("off")).otherwise(pl.lit("def")),
                           pct=pl.max_horizontal("offense_pct", "defense_pct"))
ros = pl.concat([i64(S.fetch("rosters_weekly", s)).select("season", "week", "team", "status", "gsis_id") for s in ALL],
                how="diagonal_relaxed").with_columns(team=franchise(pl.col("team"))).drop_nulls("gsis_id")
# pfr -> gsis through the players table (complete; the weekly rosters' pfr_id is missing for about a third of rows)
idmap = S.fetch("players").select(pl.col("pfr_id").alias("pfr"), "gsis_id").drop_nulls().unique("pfr")
roster_weeks = ros.select("season", "team", pl.col("week").alias("rw")).unique()
inj = pl.concat([i64(S.fetch("injuries", s).filter(pl.col("game_type") == "REG")).select("season", "week", "team", "gsis_id", "report_status")
                 for s in ALL], how="diagonal_relaxed").filter(pl.col("report_status").is_in(["Out", "Doubtful"])).with_columns(
    team=franchise(pl.col("team"))).unique(["season", "week", "team", "gsis_id"]).select("season", "week", "team", "gsis_id", reported=pl.lit(True))

tgames = pl.concat([G.select("game_id", "season", "week", "kickoff_utc", pl.col("home_team").alias("team"), pl.col("away_team").alias("opp"), pl.lit(True).alias("is_home")),
                    G.select("game_id", "season", "week", "kickoff_utc", pl.col("away_team").alias("team"), pl.col("home_team").alias("opp"), pl.lit(False).alias("is_home"))])
played = snaps.select("game_id", "team", "pfr_player_id", "player", "position", "unit", "pct", "season")
recs = []
for (season, team), tg in tgames.group_by(["season", "team"]):
    tg = tg.sort("kickoff_utc")
    ps = played.filter((pl.col("season") == season) & (pl.col("team") == team))
    hist: dict[str, dict] = {}
    prev_present: set = set()
    for r in tg.iter_rows(named=True):
        this = ps.filter(pl.col("game_id") == r["game_id"])
        present = set(this.filter(pl.col("pct") > 0)["pfr_player_id"].to_list())
        regs = {pid: v for pid, v in hist.items() if len(v["pcts"]) >= MIN_G and np.mean(v["pcts"]) >= REG}
        recs.append({"game_id": r["game_id"], "season": season, "week": r["week"], "team": team, "opp": r["opp"], "is_home": r["is_home"],
                     "n_regulars": len(regs),
                     "absent": [{"pfr": pid, "share": float(np.mean(v["pcts"])), "unit": v["unit"], "name": v["name"],
                                 "pos": v["pos"], "new": pid in prev_present} for pid, v in regs.items() if pid not in present]})
        for x in this.iter_rows(named=True):
            if x["pct"] > 0:
                h = hist.setdefault(x["pfr_player_id"], {"pcts": [], "unit": x["unit"], "name": x["player"], "pos": x["position"]})
                h["pcts"].append(x["pct"])
                h["unit"] = x["unit"]
        prev_present = present

A = pl.DataFrame(recs).explode("absent", empty_as_null=True).unnest("absent")
A = A.join(idmap, on="pfr", how="left").join(inj, on=["season", "week", "team", "gsis_id"], how="left")
# the team's latest weekly roster BEFORE this week (bye weeks have none); "gone" = on a reserve list / suspended there, or
# not on the team's roster at all (released, traded). Checked on players who did play: 0.4-0.6% wrongly flagged.
last_rw = (A.select("season", "week", "team").unique().join(roster_weeks, on=["season", "team"])
           .filter(pl.col("rw") < pl.col("week")).group_by("season", "week", "team").agg(rw=pl.col("rw").max()))
A = (A.join(last_rw, on=["season", "week", "team"], how="left")
     .join(ros.rename({"week": "rw", "status": "prev_status"}), on=["season", "rw", "team", "gsis_id"], how="left")
     .with_columns(reported=pl.col("reported").fill_null(False),
                   roster_prev=pl.col("pfr").is_not_null() & pl.col("rw").is_not_null()
                   & (pl.col("prev_status").is_null() | pl.col("prev_status").is_in(["RES", "SUS"])))
     .with_columns(known=pl.col("reported") | pl.col("roster_prev")))
A.write_parquet(OUT / "s4_absences_players.parquet")


def s(cond):
    return (pl.col("share") * cond).sum().fill_null(0)


off, de = pl.col("unit") == "off", pl.col("unit") == "def"
per = A.group_by("game_id", "season", "week", "team", "opp", "is_home", "n_regulars").agg(
    off_abs=s(off), def_abs=s(de), off_new=s(off & pl.col("new")), def_new=s(de & pl.col("new")),
    off_known=s(off & pl.col("known")), def_known=s(de & pl.col("known")),
    off_unknown=s(off & ~pl.col("known")), def_unknown=s(de & ~pl.col("known")),
    n_abs=pl.col("pfr").is_not_null().sum())
opp = per.select("game_id", pl.col("team").alias("opp"), *[pl.col(c).alias(f"opp_{c}") for c in
                                                         ("def_abs", "def_new", "def_known", "def_unknown")])
per = per.join(opp, on=["game_id", "opp"], how="left").fill_null(0)
per.write_parquet(OUT / "s4_absences.parquet")

P = pl.read_parquet(OUT / "s3_predictions.parquet").filter(pl.col("model") == "full")
P = pl.concat([P.select("game_id", pl.lit(True).alias("is_home"), (pl.col("home_score") - pl.col("pred_home")).alias("res_pts")),
               P.select("game_id", pl.lit(False).alias("is_home"), (pl.col("away_score") - pl.col("pred_away")).alias("res_pts"))])
D = per.filter(pl.col("season").is_in(TEST) & (pl.col("week") >= 3)).join(P, on=["game_id", "is_home"], how="inner")
D.write_parquet(OUT / "s4_team_games.parquet")
res["n_team_games"] = D.height
res["absent_regulars_distribution"] = D.group_by("n_abs").agg(n=pl.len()).sort("n_abs").to_dicts()
res["mean_regulars"], res["mean_absent"] = float(D["n_regulars"].mean()), float(D["n_abs"].mean())
res["share_team_games_newly_missing_2plus_regulars"] = float((D["off_new"] + D["def_new"] >= 1.2).mean())
pl_ = A.filter(pl.col("pfr").is_not_null() & pl.col("season").is_in(TEST) & (pl.col("week") >= 3))
res["absence_tags_share"] = {"reported": float(pl_["reported"].mean()), "roster_prev": float(pl_["roster_prev"].mean()),
                             "known": float(pl_["known"].mean()), "new": float(pl_["new"].mean()), "n_player_games": pl_.height}


def ols_block(df, ycol, xcols):
    X = np.column_stack([np.ones(df.height)] + [df[c].to_numpy().astype(float) for c in xcols])
    y = df[ycol].to_numpy()
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    blocks = (df["season"] * 100 + df["week"]).to_numpy()
    ub = np.unique(blocks)
    idx = {b: np.where(blocks == b)[0] for b in ub}
    rng = np.random.default_rng(SEED)
    boots = np.array([np.linalg.lstsq(X[p], y[p], rcond=None)[0] for p in
                      (np.concatenate([idx[b] for b in rng.choice(ub, len(ub))]) for _ in range(REPS))])
    names = ["const"] + xcols
    return {"n": df.height, "coef": {c: float(b) for c, b in zip(names, beta)},
            "ci95": {c: [float(np.quantile(boots[:, i], .025)), float(np.quantile(boots[:, i], .975))] for i, c in enumerate(names)}}


# coefficients: points per absent "full-time starter" (share 1.0 = one player who played 100% of the unit's snaps)
res["bias_all"] = ols_block(D, "res_pts", ["off_abs", "opp_def_abs"])
res["bias_weeks_3_16"] = ols_block(D.filter(pl.col("week") <= 16), "res_pts", ["off_abs", "opp_def_abs"])
Dn = D.with_columns(off_cont=pl.col("off_abs") - pl.col("off_new"), opp_def_cont=pl.col("opp_def_abs") - pl.col("opp_def_new"))
res["bias_new_vs_continuing"] = ols_block(Dn, "res_pts", ["off_new", "off_cont", "opp_def_new", "opp_def_cont"])
res["bias_new_vs_continuing_weeks_3_16"] = ols_block(Dn.filter(pl.col("week") <= 16), "res_pts", ["off_new", "off_cont", "opp_def_new", "opp_def_cont"])
res["bias_known_vs_unknown"] = ols_block(D, "res_pts", ["off_known", "off_unknown", "opp_def_known", "opp_def_unknown"])
res["bias_known_vs_unknown_weeks_3_16"] = ols_block(D.filter(pl.col("week") <= 16), "res_pts",
                                                    ["off_known", "off_unknown", "opp_def_known", "opp_def_unknown"])
for nm, col in (("own_offence_absent", "off_abs"), ("opp_defence_absent", "opp_def_abs")):
    b = D.with_columns(b=pl.when(pl.col(col) == 0).then(pl.lit("0")).when(pl.col(col) < 1.2).then(pl.lit("<1.2")).otherwise(pl.lit(">=1.2")))
    res[f"mean_resid_by_{nm}"] = b.group_by("b").agg(n=pl.len(), mean_res=pl.col("res_pts").mean(),
                                                      se=pl.col("res_pts").std() / pl.len().sqrt()).sort("b").to_dicts()

# worked example: IND 2026 (absences only; residuals from the live check model are in s4b)
ind = A.filter((pl.col("season") == 2026) & (pl.col("team") == "IND") & pl.col("pfr").is_not_null())
res["ind_2026_absent_regulars"] = (ind.group_by("name", "pos", "unit").agg(share=pl.col("share").first(),
                                   first_week_absent=pl.col("week").min(), games_absent=pl.len(),
                                   reported_ever=pl.col("reported").any(), roster_prev_ever=pl.col("roster_prev").any())
                                   .sort("first_week_absent").to_dicts())
save("s4_roster", res)
print("team-games", D.height, "mean regulars", round(res["mean_regulars"], 1), "mean absent", round(res["mean_absent"], 2))
print("tags:", res["absence_tags_share"])
for k in ("bias_all", "bias_weeks_3_16", "bias_new_vs_continuing", "bias_new_vs_continuing_weeks_3_16", "bias_known_vs_unknown",
          "bias_known_vs_unknown_weeks_3_16"):
    r = res[k]
    print(k, "n", r["n"], {c: (round(r["coef"][c], 2), [round(x, 2) for x in r["ci95"][c]]) for c in r["coef"]})
print(res["mean_resid_by_own_offence_absent"]); print(res["mean_resid_by_opp_defence_absent"])
print("IND 2026:", [(x["name"], x["pos"], round(x["share"], 2), x["first_week_absent"], x["games_absent"], x["reported_ever"], x["roster_prev_ever"]) for x in res["ind_2026_absent_regulars"]])
