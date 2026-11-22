"""Shared helpers for the big-gap research (PLAN.md, brief of 2026-11-20). Research only: imports `nflcast`, never edits it.

Run every script from the worktree root with the worktree's src first on the path, e.g.
    $env:PYTHONPATH = "src"; & "C:\\Users\\Craig\\NFL MODEL PROJECTIONS\\.venv\\Scripts\\python.exe" reports\\research\\gap_absences\\a1_timing.py
(the venv's editable install points at the main folder; PYTHONPATH makes `nflcast.config.ROOT` the worktree).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import polars as pl

from nflcast.config import PROCESSED_DIR, RAW_DIR, ROOT
from nflcast.data import sources as S
from nflcast.data.games import franchise
from nflcast.features import personnel as P
from nflcast.predict.validation import entry_is_valid

assert ROOT.name == "nflwt-gaps", f"run from the research worktree with PYTHONPATH=src (ROOT is {ROOT})"

OUT = ROOT / "reports" / "research" / "gap_absences"
SEASON = 2026
UNITS = P.UNITS                      # ol, skill, front, db
ET = ZoneInfo("America/New_York")
NOW = datetime.now(timezone.utc)


def save(name: str, obj) -> Path:
    p = OUT / f"{name}.json"
    p.write_text(json.dumps(obj, indent=1, default=str), encoding="utf-8")
    return p


# ------------------------------------------------------------------ releases
@lru_cache(maxsize=1)
def releases() -> list[dict]:
    """Every 2026 release (run_id, generated_at, injury snapshot record, games by id), oldest first."""
    out = []
    for f in sorted((ROOT / "releases" / str(SEASON)).glob("week_*/rel_*.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        out.append({"run_id": r["run_id"], "generated_at": datetime.fromisoformat(r["generated_at_utc"]),
                    "week": r.get("week"), "inj": (r.get("input_snapshots") or {}).get("injuries"),
                    "games": {g["game_id"]: g for g in r["games"]}})
    return sorted(out, key=lambda x: x["generated_at"])


def final_pregame(game_id: str, kickoff: datetime) -> dict | None:
    """Latest valid release version generated before kickoff (the scoring rule's final_pregame)."""
    best = None
    for r in releases():
        g = r["games"].get(game_id)
        if g is not None and r["generated_at"] < kickoff and entry_is_valid(g):
            best = r
    return best


def release(run_id: str) -> dict:
    return next(r for r in releases() if r["run_id"] == run_id)


@lru_cache(maxsize=1)
def locked_games() -> pl.DataFrame:
    """One row per 2026 game with a locked pick (from the exported site data, which verify-claims recomputes)."""
    rows = []
    for f in sorted((ROOT / "web" / "public" / "data" / "weeks").glob(f"{SEASON}-*.json")):
        w = json.loads(f.read_text(encoding="utf-8"))
        for g in w["games"]:
            lp = g.get("locked_pick")
            if not lp or not lp.get("run_id"):
                continue
            so, si = lp.get("stats_only") or {}, lp.get("stats_inj") or {}
            rows.append({"game_id": g["game_id"], "week": g["week"], "home": g["home"]["id"] if isinstance(g["home"], dict) else g["home"],
                         "away": g["away"]["id"] if isinstance(g["away"], dict) else g["away"],
                         "kickoff_utc": datetime.fromisoformat(g["kickoff_utc"]), "status": g["status"],
                         "lock_run_id": lp["run_id"], "lock_at": datetime.fromisoformat(lp["generated_at"]),
                         "rule": lp.get("rule"), "basis": lp.get("basis"), "provisional": bool(lp.get("provisional")),
                         "verification": lp.get("verification"), "line_home_spread": lp.get("line_home_spread"),
                         "stats_margin": so.get("margin"), "stats_inj_margin": si.get("margin")})
    return pl.DataFrame(rows)


# ------------------------------------------------------------------ slots
def slot(kickoff: datetime) -> str:
    """Kickoff slot in US Eastern time."""
    k = kickoff.astimezone(ET)
    d, h = k.strftime("%a"), k.hour + k.minute / 60
    if d == "Sun":
        return "Sunday early international" if h < 12 else "Sunday early" if h < 15 else "Sunday late / night"
    return {"Thu": "Thursday", "Fri": "Friday", "Sat": "Saturday", "Mon": "Monday"}.get(d, d)


# ------------------------------------------------------------------ injury snapshots
@lru_cache(maxsize=1)
def injury_snapshots() -> list[dict]:
    d = RAW_DIR / "injuries" / str(SEASON)
    out = []
    for m in sorted(d.glob("*.json")):
        meta = json.loads(m.read_text(encoding="utf-8"))
        out.append({"observed_at": datetime.fromisoformat(meta["observed_at_utc"]), "sha": meta["content_sha256"],
                    "last_modified": meta.get("http_last_modified"), "path": m.with_suffix(".parquet")})
    return sorted(out, key=lambda x: x["observed_at"])


@lru_cache(maxsize=None)
def _snap_df(path: Path) -> pl.DataFrame:
    return pl.read_parquet(path).with_columns(team=franchise(pl.col("team")))


def snapshot_at(t: datetime) -> dict | None:
    """The newest snapshot observed at or before t (as S.snapshot_asof selects it)."""
    best = None
    for s in injury_snapshots():
        if s["observed_at"] <= t:
            best = s
    return best


def team_rows(snap: dict | None, team: str, week: int) -> pl.DataFrame:
    if snap is None:
        return pl.DataFrame(schema={"gsis_id": pl.Utf8, "full_name": pl.Utf8, "position": pl.Utf8,
                                    "report_status": pl.Utf8, "practice_status": pl.Utf8})
    return (_snap_df(snap["path"]).filter((pl.col("team") == team) & (pl.col("week") == week))
            .select("gsis_id", "full_name", "position", "report_status", "practice_status")
            .unique("gsis_id", keep="last").sort("gsis_id"))


GAME_STATUSES = ("Out", "Doubtful", "Questionable")


def key_rows(df: pl.DataFrame, designated_only: bool = False) -> set:
    if designated_only:
        df = df.filter(pl.col("report_status").is_in(GAME_STATUSES))
        return set(zip(df["gsis_id"], df["report_status"]))
    return set(zip(df["gsis_id"], df["report_status"].fill_null(""), df["practice_status"].fill_null("")))


def first_seen_final(team: str, week: int, kickoff: datetime, designated_only: bool) -> dict:
    """When the team's final pre-kickoff rows (all rows, or game designations only) were first in our data: the first
    snapshot after the last one (before kickoff) whose rows differ from the final rows."""
    snaps = [s for s in injury_snapshots() if s["observed_at"] < kickoff]
    if not snaps:
        return {"first_seen": None}
    final = key_rows(team_rows(snaps[-1], team, week), designated_only)
    first = snaps[-1]
    for s in reversed(snaps):
        if key_rows(team_rows(s, team, week), designated_only) != final:
            break
        first = s
    return {"first_seen": first["observed_at"], "provider_last_modified": first["last_modified"], "n_final": len(final)}


# ------------------------------------------------------------------ per-player expected lost snaps (shadow rule)
class PlayerAvailability(P.Availability):
    """Availability.unit_losses, but returning one row per listed player (same arithmetic), so lock and final versions
    can be matched player by player. Sums equal unit_losses exactly (checked in a1_timing)."""

    def player_losses(self, game_ids: list[str]) -> pl.DataFrame:
        rep = self.inj.filter(pl.col("game_id").is_in(game_ids) & pl.col("unit").is_not_null() & pl.col("pfr_player_id").is_not_null())
        tg = self.team_games.with_columns(idx=pl.int_range(pl.len()).over("team"))
        cur = rep.select("game_id", "team", "gsis_id", "pfr_player_id", "status", "practice_status", "unit", "season").join(
            tg.select("game_id", "team", "idx"), on=["game_id", "team"])
        prev = (cur.select("game_id", "team", "pfr_player_id", "idx")
                .with_columns(pidx=pl.int_ranges(pl.col("idx") - 6, pl.col("idx"))).explode("pidx")
                .filter(pl.col("pidx") >= 0)
                .join(tg.select(pl.col("game_id").alias("pg"), "team", pl.col("idx").alias("pidx")), on=["team", "pidx"]))
        prev = prev.join(self.snaps.select(pl.col("game_id").alias("pg"), "pfr_player_id", "team", "share"),
                         on=["pg", "pfr_player_id", "team"], how="left").with_columns(pl.col("share").fill_null(0.0))
        share = prev.group_by(["game_id", "team", "pfr_player_id"]).agg(recent_share=pl.col("share").mean())
        cur = cur.join(share, on=["game_id", "team", "pfr_player_id"], how="left").with_columns(pl.col("recent_share").fill_null(0.0))
        pmap = {s: self.p_play(s) for s in cur["season"].unique().to_list()}
        pm = [1.0 - pmap[s].get(st, pmap[s].get("None", 0.9)) for s, st in zip(cur["season"], cur["status"])]
        return cur.with_columns(p_miss=pl.Series(pm, dtype=pl.Float64)).with_columns(lost=pl.col("p_miss") * pl.col("recent_share"))


@lru_cache(maxsize=1)
def _live_context():
    games = pl.read_parquet(PROCESSED_DIR / "games.parquet")
    idmap = S.fetch("players").select("gsis_id", pl.col("pfr_id").alias("pfr_player_id")).drop_nulls().unique("gsis_id")
    snaps = P.snap_shares([SEASON - 1, SEASON], games)
    tg = pl.read_parquet(PROCESSED_DIR / "team_games.parquet").select("game_id", "team", "kickoff_utc")
    return games, idmap, snaps, tg


def frozen_p_play() -> dict:
    import yaml
    rec = yaml.safe_load((ROOT / "configs" / "shadow_injury.yaml").read_text(encoding="utf-8"))
    return {str(k): float(v) for k, v in rec["p_play_by_status"].items()}


def live_player_losses(snap: dict | None, week: int, games_rows: list[dict], p_play: dict | None = None) -> pl.DataFrame:
    """Per-player expected lost snaps for the given games, from one injury snapshot, by the shadow line's live rule
    (predict/shadow.live_losses): game status (none = "None"), frozen P(play | status), mean snap share over the team's
    previous 6 games. games_rows: [{game_id, home, away, kickoff_utc}]."""
    games, idmap, snaps, tg_all = _live_context()
    p_play = p_play or frozen_p_play()
    sides = pl.DataFrame([{"game_id": g["game_id"], "team": t, "kickoff_utc": g["kickoff_utc"]}
                          for g in games_rows for t in (g["home"], g["away"])])
    if snap is None:
        return pl.DataFrame()
    inj = _snap_df(snap["path"])
    rep = (inj.filter(pl.col("week") == week)
           .select("team", "gsis_id", "full_name", "position", P._status_key(pl.col("report_status")).alias("status"),
                   "practice_status")
           .unique(["team", "gsis_id"], keep="last")
           .join(idmap, on="gsis_id", how="left")
           .with_columns(unit=pl.col("position").replace_strict(P.UNIT_OF_POSITION, default=None),
                         season=pl.lit(SEASON, dtype=pl.Int32))
           .join(sides.select("game_id", "team"), on="team", how="inner"))
    tg = pl.concat([tg_all.filter(~pl.col("game_id").is_in(sides["game_id"].to_list())),
                    sides.with_columns(pl.col("kickoff_utc").cast(tg_all.schema["kickoff_utc"]))], how="vertical_relaxed")
    av = PlayerAvailability(rep, snaps, tg)
    av._p_cache[SEASON] = p_play
    out = av.player_losses(sides["game_id"].unique().to_list())
    return out.join(rep.select("team", "gsis_id", "full_name", "position").unique(["team", "gsis_id"]), on=["team", "gsis_id"], how="left")


# ------------------------------------------------------------------ frozen shadow coefficients (read only)
@lru_cache(maxsize=1)
def shadow_unit_points() -> dict:
    """Points of MARGIN (own team's view) per 1.0 starter-equivalent of expected lost snaps, from the frozen shadow
    ridge (configs/shadow_injury.yaml artifact; sha256-checked by predict/shadow.load). Own offensive units lower own
    points (team_lost_ol / team_lost_skill coefficient); own defensive units raise the opponent's points
    (opp_lost_front / opp_lost_db coefficient, entering the opponent's points row)."""
    from nflcast.predict import shadow as SH
    m = SH.load()
    if m is None:
        raise RuntimeError("shadow artifact missing or sha256 mismatch")
    mod = m["mod"]
    coef = dict(zip(mod.names, mod.pipe[-1].coef_ / mod.pipe[0].scale_))
    return {"ol": float(coef["team_lost_ol"]), "skill": float(coef["team_lost_skill"]),
            "front": float(-coef["opp_lost_front"]), "db": float(-coef["opp_lost_db"]),
            "_raw": {k: float(v) for k, v in coef.items() if "lost_" in k}, "alpha": float(m["alpha"]),
            "_scale": {n: float(s) for n, s in zip(mod.names, mod.pipe[0].scale_) if "lost_" in n}}


def margin_points(units: dict[str, float]) -> float:
    """Own margin change (points) from a team's lost_<unit> values at the frozen shadow costs."""
    c = shadow_unit_points()
    return float(sum(c[u] * units.get(u, 0.0) for u in UNITS))
