"""Audit section 1: home field and neutral sites. Run: .venv\\Scripts\\python.exe scripts\\audit_2026_11\\s1_venue.py"""

import numpy as np
import polars as pl

from common import (FOLDS, base_fs, decide, fmt_decision, games, live_2026, load, point_metrics, save, walk_forward)
from nflcast.predict import freeze

res = {}
data = load("final")
G = games()

# ---- 1a. what home field is in the frozen artifact (Model line = bmod; market-adjusted = cmod)
M = freeze.load()
b = M["bmod"]
cb = dict(zip(b.names, b.pipe[-1].coef_ / b.pipe[0].scale_))
res["frozen_model_line_home_field_margin_pts"] = 2 * cb["venue"]
cm = M["cmod"]
try:
    mm = cm.margin_model if hasattr(cm, "margin_model") else None
    names = getattr(cm, "names", None)
    res["frozen_cmod_attrs"] = [a for a in dir(cm) if not a.startswith("_")][:40]
except Exception as e:  # noqa: BLE001
    res["frozen_cmod_attrs"] = str(e)
res["frozen_training"] = {"games": M["training_games"], "last_training_game": M["last_training_game"], "alpha": b.alpha}

# ---- 1b. empirical home margin by season (non-neutral, regular season + playoffs), 2016-2024 and 2026 to date
gg = G.filter((pl.col("status") == "final") & (pl.col("season") >= 2016) & (pl.col("season") != 2025))
hm = (gg.filter(~pl.col("neutral_site")).group_by("season")
      .agg(n=pl.len(), home_margin=pl.col("margin").mean(), sd=pl.col("margin").std()).sort("season")
      .with_columns(se=pl.col("sd") / pl.col("n").sqrt()))
res["empirical_home_margin_by_season"] = hm.to_dicts()
res["neutral_games_by_season"] = (gg.filter(pl.col("neutral_site")).group_by("season").agg(n=pl.len()).sort("season").to_dicts())

# ---- 1c. home field per walk-forward fold (current method: one league-wide coefficient on all training seasons)
fs = base_fs()
info = {}
base = walk_forward(data, "current", fs, info=info)
from nflcast.models.core import FootballRidge, select_alpha_chronologically  # noqa: E402
fold_hfa = {}
for S in FOLDS:
    tr = data.filter((pl.col("season") >= 2016) & (pl.col("season") < S))
    m = FootballRidge(alpha=info["current"][S]["alpha"], feature_set=fs).fit(tr)
    c = dict(zip(m.names, m.pipe[-1].coef_ / m.pipe[0].scale_))
    fold_hfa[S] = {"train_seasons": f"2016-{S-1}", "home_field_margin_pts": 2 * c["venue"], "alpha": info["current"][S]["alpha"]}
res["home_field_by_fold"] = fold_hfa


# ---- 1d. variants
def _hfa_offset(tr: pl.DataFrame, seasons_back: int | None) -> float:
    nn = tr.filter(~pl.col("neutral_site"))
    if seasons_back:
        last = int(tr["season"].max())
        nn = nn.filter(pl.col("season") > last - seasons_back)
    return float(nn["margin"].mean())


fs_nov = {**fs, "context": [c for c in fs["context"] if c != "venue"]}


def recent_fit(tr):
    h = _hfa_offset(tr, 3)
    neu = tr["neutral_site"].to_numpy()
    tr2 = tr.with_columns(home_score=pl.col("home_score") - pl.Series(np.where(neu, 0, h / 2)),
                          away_score=pl.col("away_score") + pl.Series(np.where(neu, 0, h / 2)))
    return tr2, {"h": h, "report": {"hfa": h}}


def recent_pred(te, p, st):
    neu = te["neutral_site"].to_numpy()
    add = np.where(neu, 0.0, st["h"])
    H, A = p["home_pts"] + add / 2, p["away_pts"] - add / 2
    return {"home_pts": H, "away_pts": A, "margin": H - A, "total": H + A}


def team_fit(tr):
    """Current model + empirical-Bayes team-specific home-field deviation (variance components; no tuning)."""
    a = select_alpha_chronologically(tr, feature_set=fs)[0]
    m = FootballRidge(alpha=a, feature_set=fs).fit(tr)
    p = m.predict(tr)
    r = tr.select("home_id", "neutral_site", "margin").with_columns(res=pl.col("margin") - pl.Series(p["margin"]))
    r = r.filter(~pl.col("neutral_site"))
    sig2 = float(r["res"].var())
    t = r.group_by("home_id").agg(n=pl.len(), mean=pl.col("res").mean())
    tau2 = max(0.0, float(t["mean"].var()) - float((sig2 / t["n"]).mean()))
    t = t.with_columns(d=pl.col("mean") * tau2 / (tau2 + sig2 / pl.col("n")))
    return tr, {"d": dict(zip(t["home_id"], t["d"])), "report": {"tau": tau2 ** 0.5, "sigma": sig2 ** 0.5,
                                                                   "max_abs_d": float(t["d"].abs().max())}}


def team_pred(te, p, st):
    neu = te["neutral_site"].to_numpy()
    add = np.array([0.0 if n else st["d"].get(h, 0.0) for h, n in zip(te["home_id"].to_list(), neu)])
    H, A = p["home_pts"] + add / 2, p["away_pts"] - add / 2
    return {"home_pts": H, "away_pts": A, "margin": H - A, "total": H + A}


P = [base,
     walk_forward(data, "no_home_field", fs_nov, info=info),
     walk_forward(data, "recent3_constant", fs_nov, fit_hook=recent_fit, pred_hook=recent_pred, info=info),
     walk_forward(data, "team_specific_eb", fs, fit_hook=team_fit, pred_hook=team_pred, info=info)]
preds = pl.concat(P)
res["variants"] = [decide(preds, v, "current") for v in ("no_home_field", "recent3_constant", "team_specific_eb")]
res["variant_fold_info"] = {k: v for k, v in info.items() if k != "current"}

# ---- 1e. neutral-site games in the backtest (current model)
neu = base.filter(pl.col("neutral_site"))
res["neutral_site_games_backtest"] = {"n": neu.height, **point_metrics(neu)} if neu.height else {"n": 0}
res["non_neutral_games_backtest"] = point_metrics(base.filter(~pl.col("neutral_site")))

# ---- 1f. 2026 live check (train 2016-2024, predict 2026 weeks 3-10)
L = pl.concat([live_2026(data, "current", fs), live_2026(data, "no_home_field", fs_nov),
               live_2026(data, "recent3_constant", fs_nov, recent_fit, recent_pred),
               live_2026(data, "team_specific_eb", fs, team_fit, team_pred)])
res["live_2026"] = {v: point_metrics(L.filter(pl.col("model") == v)) for v in L["model"].unique().sort().to_list()}

save("s1_venue", res)
preds.write_parquet(__import__("common").OUT / "s1_venue_predictions.parquet")
print("frozen Model line home field (margin pts):", round(res["frozen_model_line_home_field_margin_pts"], 3))
print("per fold:", {k: round(v["home_field_margin_pts"], 2) for k, v in fold_hfa.items()})
print("empirical home margin:", [(r["season"], r["n"], round(r["home_margin"], 2), round(r["se"], 2)) for r in res["empirical_home_margin_by_season"]])
for d in res["variants"]:
    print(fmt_decision(d))
print("variant info:", {k: {S: x.get("state") for S, x in v.items()} for k, v in res["variant_fold_info"].items()})
print("neutral backtest games:", res["neutral_site_games_backtest"].get("n"), "MAE", res["neutral_site_games_backtest"].get("margin_mae"))
print("2026 live:", {k: (v["n_games"], round(v["margin_mae"], 3)) for k, v in res["live_2026"].items()})
