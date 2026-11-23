"""QB layer inputs, exactly as pre-registered (reports/research/qb_layer_v2_3_preregistration_2026-11-23.md).

Research only: imports `nflcast`, never edits it. Run from the worktree root with PYTHONPATH=src.
build(...) -> one row per (game_id, team) of the final-horizon targets with, for each rating configuration `cfg`,
columns `<cfg>|qb_rating`, `<cfg>|qb_log_db`, `<cfg>|qb_delta`, `<cfg>|qb_cpoe`, `<cfg>|qb_cpoe_delta`, plus the
B1 columns `qbs_share`, `qbs_db_gap` (independent of the rating configuration).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

import numpy as np
import polars as pl

from nflcast.config import PROCESSED_DIR, ROOT, settings
from nflcast.data import sources as S
from nflcast.data.games import franchise
from nflcast.features import personnel as P

LAG = timedelta(hours=settings()["pbp_available_after_kickoff_hours"])
TF_HL, TF_CARRY, TF_MAX = float(settings()["features"]["half_life_games"]), float(settings()["features"]["season_carryover"]), 48
PRIOR_ROWS = 3 * 32 * 18          # as personnel.QBModel.prior
OPP_SHRINK, LEAGUE_ROWS = 300.0, 1700
PED_SHRINK = 2000.0
CPOE_SHRINK = 200.0
B1_SHRINK = 150.0
PBP_COLS = ["game_id", "play_id", "posteam", "defteam", "play_type", "qb_dropback", "qb_spike", "qb_kneel", "rush",
            "qb_scramble", "epa", "cpoe", "passer_id", "rusher_id"]
SCRATCH = ROOT / ".scratch"


@dataclass(frozen=True)
class Cfg:
    runs: bool = False
    opp: bool = False
    ped: bool = False
    hl: float = P.QB_HALF_LIFE_GAMES
    carry: float = P.QB_SEASON_CARRY
    k: float = P.QB_SHRINK_DROPBACKS

    @property
    def name(self) -> str:
        base = "".join(x for x, on in (("R", self.runs), ("O", self.opp), ("D", self.ped)) if on) or "cur"
        if (self.hl, self.carry, self.k) != (P.QB_HALF_LIFE_GAMES, P.QB_SEASON_CARRY, P.QB_SHRINK_DROPBACKS):
            base += f"_h{self.hl:g}_c{self.carry:g}_k{self.k:g}"
        return base


# ------------------------------------------------------------------ raw tables
def load_pbp(seasons=range(2011, 2027)) -> pl.DataFrame:
    """Selected play-by-play columns, read as the pipeline reads them (ep_scale.load_pbp). Cached in .scratch."""
    f = SCRATCH / "qb_layer_pbp.parquet"
    if f.exists():
        return pl.read_parquet(f)
    from nflcast.data import ep_scale as EPS
    pbp = pl.concat([EPS.load_pbp(s).select(PBP_COLS) for s in seasons], how="diagonal_relaxed")
    pbp.write_parquet(f)
    return pbp


def qb_positions() -> dict[str, str]:
    pos = S.fetch("players").select("gsis_id", "position").drop_nulls()
    return dict(zip(pos["gsis_id"].to_list(), pos["position"].to_list()))


def draft_bucket() -> dict[str, str]:
    p = S.fetch("players").select("gsis_id", "draft_round").filter(pl.col("gsis_id").is_not_null())
    b = (pl.when(pl.col("draft_round") == 1).then(pl.lit("R1")).when(pl.col("draft_round").is_in([2, 3])).then(pl.lit("R23"))
         .when(pl.col("draft_round").is_between(4, 7)).then(pl.lit("R47")).otherwise(pl.lit("UDFA")))
    p = p.with_columns(b=b)
    return dict(zip(p["gsis_id"].to_list(), p["b"].to_list()))


def qb_game_table(pbp: pl.DataFrame, games: pl.DataFrame, qbg: pl.DataFrame, pos: dict) -> pl.DataFrame:
    """One row per (game, team, QB): dropbacks + EPA (as personnel.qb_games), CPOE sums, designed runs + EPA, opponent,
    starter flag (from the processed qb_games table)."""
    p = pbp.with_columns(team=franchise(pl.col("posteam")), opp=franchise(pl.col("defteam")))
    dbk = p.filter((pl.col("qb_dropback") == 1) & (pl.col("qb_spike").fill_null(0) == 0) & pl.col("passer_id").is_not_null()
                   & (pl.col("play_type") != "no_play"))
    a = dbk.group_by(["game_id", "team", "passer_id"]).agg(
        opp=pl.col("opp").first(), db=pl.len(), epa=pl.col("epa").fill_null(0).sum(),
        cpoe_sum=pl.col("cpoe").drop_nulls().sum(), cpoe_n=pl.col("cpoe").drop_nulls().len()).rename({"passer_id": "qb_id"})
    qbs = [k for k, v in pos.items() if v == "QB"]
    runs = p.filter((pl.col("rush") == 1) & (pl.col("qb_scramble").fill_null(0) == 0) & (pl.col("qb_kneel").fill_null(0) == 0)
                    & (pl.col("play_type") == "run") & pl.col("rusher_id").is_in(qbs))
    r = runs.group_by(["game_id", "team", "rusher_id"]).agg(opp_r=pl.col("opp").first(), runs=pl.len(),
                                                           run_epa=pl.col("epa").fill_null(0).sum()).rename({"rusher_id": "qb_id"})
    t = a.join(r, on=["game_id", "team", "qb_id"], how="full", coalesce=True).with_columns(
        opp=pl.coalesce("opp", "opp_r")).drop("opp_r").with_columns(
        [pl.col(c).fill_null(0) for c in ("db", "epa", "cpoe_sum", "cpoe_n", "runs", "run_epa")])
    # row order of personnel.QBModel (qbg sorted by availability time), so the prior window matches it exactly;
    # rows with designed runs only go after the dropback rows of the same time
    st = (qbg.with_columns(_a=(pl.col("kickoff_utc") + LAG).dt.epoch("us")).sort("_a").with_row_index("qo")
          .select("game_id", "team", "qb_id", "is_starter", pl.col("qo").cast(pl.Float64)))
    t = t.join(st, on=["game_id", "team", "qb_id"], how="left").with_columns(pl.col("is_starter").fill_null(False),
                                                                             pl.col("qo").fill_null(float("inf")))
    g = games.select("game_id", "season", "kickoff_utc")
    t = t.join(g, on="game_id", how="inner").with_columns(avail=(pl.col("kickoff_utc") + LAG).dt.epoch("us"),
                                                         ko_us=pl.col("kickoff_utc").dt.epoch("us"))
    return t.sort(["avail", "qo", "game_id", "team", "qb_id"])


# ------------------------------------------------------------------ opponent defence (B3)
class OppDefence:
    """Defence's EPA per dropback allowed above the as-of league mean, from its earlier games only."""

    def __init__(self, tg: pl.DataFrame):
        d = tg.select("game_id", pl.col("opp").alias("def"), "dropbacks", "epa_db_sum", "season", "kickoff_utc").with_columns(
            avail=(pl.col("kickoff_utc") + LAG).dt.epoch("us")).sort("avail", "game_id", "def")
        self.avail = d["avail"].to_numpy()
        self.cdb = np.concatenate([[0.0], np.cumsum(d["dropbacks"].to_numpy().astype(float))])
        self.cep = np.concatenate([[0.0], np.cumsum(d["epa_db_sum"].to_numpy())])
        self.by = {k[0]: (x["avail"].to_numpy(), x["season"].to_numpy(), x["dropbacks"].to_numpy().astype(float),
                          x["epa_db_sum"].to_numpy()) for k, x in d.group_by(["def"])}

    def league(self, t_us: int) -> float:
        n = int(np.searchsorted(self.avail, t_us, side="right"))
        lo = max(0, n - LEAGUE_ROWS)
        db = self.cdb[n] - self.cdb[lo]
        return float((self.cep[n] - self.cep[lo]) / db) if db > 0 else 0.0

    def quality(self, team: str, t_us: int, season: int) -> float:
        if team not in self.by:
            return 0.0
        av, se, db, ep = self.by[team]
        n = int(np.searchsorted(av, t_us, side="right"))
        lo = max(0, n - TF_MAX)
        if n == lo:
            return 0.0
        L = self.league(t_us)
        k = np.arange(n - lo)[::-1]
        w = 0.5 ** (k / TF_HL) * TF_CARRY ** np.clip(season - se[lo:n], 0, None)
        return float((w * (ep[lo:n] - db[lo:n] * L)).sum() / ((w * db[lo:n]).sum() + OPP_SHRINK))


def add_opp_adjust(qt: pl.DataFrame, od: OppDefence) -> pl.DataFrame:
    q = [od.quality(o, int(t), int(s)) if o is not None else 0.0 for o, t, s in zip(qt["opp"], qt["ko_us"], qt["season"])]
    return qt.with_columns(opp_q=pl.Series(q, dtype=pl.Float64)).with_columns(epa_adj=pl.col("epa") - pl.col("db") * pl.col("opp_q"))


# ------------------------------------------------------------------ rating (generalises personnel.QBModel)
class QBRating:
    def __init__(self, qt: pl.DataFrame, cfg: Cfg, bucket: dict):
        self.cfg = cfg
        q = qt.with_columns(
            v=(pl.col("epa_adj") if cfg.opp else pl.col("epa")) + (pl.col("run_epa") if cfg.runs else 0.0),
            n=(pl.col("db") + (pl.col("runs") if cfg.runs else 0)).cast(pl.Float64))
        q = q.filter(pl.col("n") > 0).sort(["avail", "qo"], maintain_order=True)
        q = q.with_columns(career_before=pl.col("db").cum_sum().over("qb_id") - pl.col("db"),
                           bucket=pl.col("qb_id").replace_strict(bucket, default="UDFA"))
        self.avail_all = q["avail"].to_numpy()
        isdb = (q["db"] > 0).to_numpy()
        self.cnt = np.concatenate([[0], np.cumsum(isdb)])
        v, n = q["v"].to_numpy(), q["n"].to_numpy()
        newc = (q["career_before"] < P.NEWCOMER_CAREER_DB).to_numpy()
        cs = lambda x: np.concatenate([[0.0], np.cumsum(x)])  # noqa: E731
        self.c_n, self.c_v = cs(n), cs(v)
        self.c_nn, self.c_vn = cs(n * newc), cs(v * newc)
        self.bk = {b: (cs(n * newc * (q["bucket"] == b).to_numpy()), cs(v * newc * (q["bucket"] == b).to_numpy()))
                   for b in ("R1", "R23", "R47", "UDFA")}
        cn, csm = q["cpoe_n"].to_numpy().astype(float), q["cpoe_sum"].to_numpy()
        self.c_cn, self.c_cs = cs(cn), cs(csm)
        self.c_cnn, self.c_csn = cs(cn * newc), cs(csm * newc)
        self.bucket = bucket
        self.by_qb = {k[0]: (d["avail"].to_numpy(), d["season"].to_numpy(), d["n"].to_numpy(), d["v"].to_numpy(),
                             d["cpoe_n"].to_numpy().astype(float), d["cpoe_sum"].to_numpy()) for k, d in q.group_by(["qb_id"])}
        self._pc: dict = {}

    def _window(self, cutoff_us: int) -> tuple[int, int]:
        n = int(np.searchsorted(self.avail_all, cutoff_us, side="right"))
        target = self.cnt[n] - PRIOR_ROWS
        lo = 0 if target <= 0 else int(np.searchsorted(self.cnt, target, side="left"))
        return lo, n

    def prior(self, cutoff_us: int, qb_id: str | None) -> float:
        b = self.bucket.get(qb_id, "UDFA") if (self.cfg.ped and qb_id is not None) else None
        key = (cutoff_us, b)
        if key in self._pc:
            return self._pc[key]
        lo, n = self._window(cutoff_us)
        db = self.c_n[n] - self.c_n[lo]
        league = (self.c_v[n] - self.c_v[lo]) / db if db > 0 else 0.0
        dbn = self.c_nn[n] - self.c_nn[lo]
        newc = (self.c_vn[n] - self.c_vn[lo]) / dbn if dbn > 500 else league - 0.1
        if b is not None and dbn > 500:
            cn, cv = self.bk[b]
            nb = cn[n] - cn[lo]
            if nb > 0:
                newc = newc + ((cv[n] - cv[lo]) / nb - newc) * nb / (nb + PED_SHRINK)
        self._pc[key] = float(newc)
        return float(newc)

    def cpoe_prior(self, cutoff_us: int) -> float:
        lo, n = self._window(cutoff_us)
        nn = self.c_cnn[n] - self.c_cnn[lo]
        if nn >= 500:
            return float((self.c_csn[n] - self.c_csn[lo]) / nn)
        na = self.c_cn[n] - self.c_cn[lo]
        return float((self.c_cs[n] - self.c_cs[lo]) / na) if na > 0 else 0.0

    def rating(self, qb_id: str | None, cutoff_us: int, season: int) -> tuple[float, float, float]:
        """(shrunk value per play, weighted plays, shrunk CPOE / 100) as of the cutoff."""
        pr, cp = self.prior(cutoff_us, qb_id), self.cpoe_prior(cutoff_us)
        if qb_id is None or qb_id not in self.by_qb:
            return pr, 0.0, cp / 100
        av, se, n_, v_, cn, cs = self.by_qb[qb_id]
        n = int(np.searchsorted(av, cutoff_us, side="right"))
        if n == 0:
            return pr, 0.0, cp / 100
        k = np.arange(n)[::-1]
        w = 0.5 ** (k / self.cfg.hl) * self.cfg.carry ** np.clip(season - se[:n], 0, None)
        wn = float((w * n_[:n]).sum())
        r = float(((w * v_[:n]).sum() + self.cfg.k * pr) / (wn + self.cfg.k))
        c = float(((w * cs[:n]).sum() + CPOE_SHRINK * cp) / ((w * cn[:n]).sum() + CPOE_SHRINK))
        return r, wn, c / 100


class TeamStarts:
    def __init__(self, qbg: pl.DataFrame, tg: pl.DataFrame):
        st = qbg.filter(pl.col("is_starter")).with_columns(avail=(pl.col("kickoff_utc") + LAG).dt.epoch("us")).sort("avail")
        self.by = {k[0]: (d["avail"].to_numpy(), d["qb_id"].to_list(), d["game_id"].to_list()) for k, d in st.group_by(["team"])}
        g = (tg.select("game_id", "team", "dropbacks", "epa_db_sum", "season", "kickoff_utc")
             .with_columns(avail=(pl.col("kickoff_utc") + LAG).dt.epoch("us")).sort("avail"))
        g = g.join(st.select("game_id", "team", pl.col("qb_id").alias("starter")), on=["game_id", "team"], how="left")
        self.tg = {k[0]: (d["avail"].to_numpy(), d["season"].to_numpy(), d["dropbacks"].to_numpy().astype(float),
                          d["epa_db_sum"].to_numpy(), d["starter"].to_list()) for k, d in g.group_by(["team"])}

    def previous(self, team: str, cutoff_us: int) -> str | None:
        if team not in self.by:
            return None
        av, ids, _ = self.by[team]
        n = int(np.searchsorted(av, cutoff_us, side="right"))
        return ids[n - 1] if n else None

    def baseline(self, R: QBRating, team: str, cutoff_us: int, season: int) -> tuple[float, float]:
        """(rating, CPOE) of the QBs in the team's weighted history, as personnel.QBModel.baseline_rating."""
        if team not in self.by:
            r = R.rating(None, cutoff_us, season)
            return r[0], r[2]
        av, ids, gids = self.by[team]
        n = int(np.searchsorted(av, cutoff_us, side="right"))
        lo = max(0, n - TF_MAX)
        if n == 0:
            r = R.rating(None, cutoff_us, season)
            return r[0], r[2]
        seasons = np.array([int(g[:4]) for g in gids[lo:n]])
        k = np.arange(n - lo)[::-1]
        w = 0.5 ** (k / TF_HL) * TF_CARRY ** np.clip(season - seasons, 0, None)
        cache: dict = {}
        rr, cc = [], []
        for qid in ids[lo:n]:
            if qid not in cache:
                cache[qid] = R.rating(qid, cutoff_us, season)
            rr.append(cache[qid][0])
            cc.append(cache[qid][2])
        return float((w * np.array(rr)).sum() / w.sum()), float((w * np.array(cc)).sum() / w.sum())

    def split_form(self, team: str, qb: str | None, cutoff_us: int, season: int) -> tuple[float, float]:
        """B1: (weighted share of the team's window started by qb, shrunk with-qb EPA/dropback minus all-games value)."""
        if team not in self.tg or qb is None:
            return 0.0, 0.0
        av, se, db, ep, st = self.tg[team]
        n = int(np.searchsorted(av, cutoff_us, side="right"))
        lo = max(0, n - TF_MAX)
        if n == lo:
            return 0.0, 0.0
        k = np.arange(n - lo)[::-1]
        w = 0.5 ** (k / TF_HL) * TF_CARRY ** np.clip(season - se[lo:n], 0, None)
        I = np.array([s == qb for s in st[lo:n]], dtype=float)
        share = float((w * I).sum() / w.sum())
        wdb = (w * db[lo:n]).sum()
        if wdb <= 0 or I.sum() == 0:
            return share, 0.0
        allv = float((w * ep[lo:n]).sum() / wdb)
        withv = float(((w * I * ep[lo:n]).sum() + B1_SHRINK * allv) / ((w * I * db[lo:n]).sum() + B1_SHRINK))
        return share, withv - allv


# ------------------------------------------------------------------ assemble
def targets() -> pl.DataFrame:
    """Final-horizon team-games with the expected QB of the current v1.0 build (actual starter; the v2.2 snapshot of
    27 Oct 2026 predates the current starter rule, so its QB columns are rebuilt for every arm)."""
    f = pl.read_parquet(PROCESSED_DIR / "feature_snapshots.parquet").filter(pl.col("horizon") == "final")
    rows = []
    for r in f.select("game_id", "season", "cutoff_utc", "home_id", "away_id", "home_qb_id", "away_qb_id").iter_rows(named=True):
        for s in ("home", "away"):
            rows.append({"game_id": r["game_id"], "season": r["season"], "cutoff_us": int(r["cutoff_utc"].timestamp() * 1e6),
                         "team": r[f"{s}_id"], "qb_id": r[f"{s}_qb_id"]})
    return pl.DataFrame(rows)


def context(pbp: pl.DataFrame | None = None):
    games = pl.read_parquet(PROCESSED_DIR / "games.parquet")
    tg = pl.read_parquet(PROCESSED_DIR / "team_games.parquet")
    qbg = pl.read_parquet(PROCESSED_DIR / "qb_games.parquet")
    pbp = load_pbp() if pbp is None else pbp
    pos = qb_positions()
    qt = qb_game_table(pbp, games, qbg, pos)
    qt = add_opp_adjust(qt, OppDefence(tg))
    return {"games": games, "tg": tg, "qbg": qbg, "qt": qt, "bucket": draft_bucket()}


def build(ctx: dict, cfgs: list[Cfg], T: pl.DataFrame) -> pl.DataFrame:
    ts = TeamStarts(ctx["qbg"], ctx["tg"])
    out = {"game_id": T["game_id"].to_list(), "team": T["team"].to_list()}
    sf = [ts.split_form(t, q, c, s) for t, q, c, s in zip(T["team"], T["qb_id"], T["cutoff_us"], T["season"])]
    out["qbs_share"] = [x[0] for x in sf]
    out["qbs_db_gap"] = [x[1] for x in sf]
    out["prev_starter"] = [ts.previous(t, c) for t, c in zip(T["team"], T["cutoff_us"])]
    for cfg in cfgs:
        R = QBRating(ctx["qt"], cfg, ctx["bucket"])
        cols = {k: [] for k in ("qb_rating", "qb_log_db", "qb_delta", "qb_cpoe", "qb_cpoe_delta")}
        for t, q, c, s in zip(T["team"], T["qb_id"], T["cutoff_us"], T["season"]):
            r, wn, cp = R.rating(q, c, s)
            br, bc = ts.baseline(R, t, c, s)
            cols["qb_rating"].append(r)
            cols["qb_log_db"].append(float(np.log1p(wn)))
            cols["qb_delta"].append(r - br)
            cols["qb_cpoe"].append(cp)
            cols["qb_cpoe_delta"].append(cp - bc)
        for k, v in cols.items():
            out[f"{cfg.name}|{k}"] = v
    return pl.DataFrame(out)


def career_dropbacks(ctx: dict, T: pl.DataFrame) -> pl.DataFrame:
    """Career dropbacks before each target game (history from 2011) and draft bucket, for the subsets."""
    q = ctx["qt"].select("qb_id", "avail", "db").sort("avail")
    by = {k[0]: (d["avail"].to_numpy(), np.cumsum(d["db"].to_numpy())) for k, d in q.group_by(["qb_id"])}
    car = []
    for qb, c in zip(T["qb_id"], T["cutoff_us"]):
        if qb not in by:
            car.append(0.0)
            continue
        av, cum = by[qb]
        n = int(np.searchsorted(av, c, side="right"))
        car.append(float(cum[n - 1]) if n else 0.0)
    return T.select("game_id", "team").with_columns(career_db=pl.Series(car),
                                                    bucket=T["qb_id"].replace_strict(ctx["bucket"], default="UDFA"))
