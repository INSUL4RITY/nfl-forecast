"""Keep the current season's play-by-play on the EP scale the frozen model was trained on (data-consistency fix).

On 2026-11-17 nflverse re-published 2026 play-by-play on the revised nflfastR expected-points scale (nflfastR PR 618:
kickoff EPA about -0.07 instead of +0.23, two-point probability 0.49, scrimmage EPA about 20% compressed). The frozen
model's history (2006-2025) and its 2026 inputs up to then are on the old scale. User decision 2026-11-17 ("go with 2"):
  * every play already held in the last old-scale snapshot (`reference_snapshot` in configs/ep_scale.yaml) keeps its
    archived old-scale valuation columns exactly, as long as the play itself is unchanged (`IDENTITY` columns equal);
  * any other play (games after that snapshot, or plays nflverse later edited) has `epa` and `qb_epa` converted back
    with a per-play-type straight line old = a + b * new, fitted once on the overlapping plays and frozen in the config.
    `success` is re-derived as epa > 0 (nflfastR's definition). Other valuation columns of converted plays (ep, wp,
    probabilities) stay as published; the model only reads epa (and v2's garbage-time filter reads wp, which barely moved).
  * a column `ep_scale` says which: "old" (archived values) or "converted".
Raw snapshots are never altered: this runs on read. Only frames that look like the revised scale (alerts.ep_scale_problem)
are touched; any other season or an old-scale frame is returned unchanged. Each call re-checks the frozen line on the
overlapping plays (team offence EPA/play, converted new vs archived old); `status()["ok"]` is False if nflverse changed
the scale again, which raises a desktop alert (alerts.ep_scale_items). It never blocks a cycle.
"""

from __future__ import annotations

import hashlib
import re
from functools import lru_cache
from pathlib import Path

import numpy as np
import polars as pl
import yaml

from nflcast.config import RAW_DIR, ROOT

CONFIG = ROOT / "configs" / "ep_scale.yaml"
# The play itself (who, where, what happened). If any of these differs from the archived play, its archived valuation no
# longer applies and the play is converted instead.
IDENTITY = ["desc", "play_type", "posteam", "defteam", "down", "ydstogo", "yardline_100", "yards_gained", "qtr",
            "game_seconds_remaining", "touchdown", "penalty", "fumble_lost", "interception", "sack",
            "two_point_attempt"]
# nflfastR model outputs (EP, WP, scoring probabilities, completion probability, xyac, xpass) and what is derived from them.
_VALUATION_RE = re.compile(r"(^|_)(ep|epa|wp|wpa)(_|$)|_prob$|^xyac_|^(success|cp|cpoe|xpass|pass_oe)$")
CONVERTED_COLS = ("epa", "qb_epa")
GROUPS = ("kickoff", "td", "pass", "run", "punt", "field_goal", "extra_point", "no_play", "other")
_last_status: dict = {}


def valuation_columns(columns) -> list[str]:
    return [c for c in columns if _VALUATION_RE.search(c)]


def play_group(df: pl.DataFrame) -> pl.Expr:
    """Conversion group of each play (fixed order of rules)."""
    pt = pl.col("play_type")
    return (pl.when(pt == "kickoff").then(pl.lit("kickoff"))
            .when(pl.col("touchdown").fill_null(0) == 1).then(pl.lit("td"))
            .when(pt.is_in(["pass", "run", "punt", "field_goal", "extra_point", "no_play"])).then(pt)
            .otherwise(pl.lit("other")))


def fit_maps(ref: pl.DataFrame, new: pl.DataFrame) -> tuple[dict[str, list[float]], int]:
    """Least-squares old = a + b * new per play group on plays present in both with identical IDENTITY columns."""
    j = _matched(new, ref).drop_nulls(["epa", "epa_ref"])
    j = j.with_columns(grp=play_group(j))
    maps = {}
    for g in GROUPS:
        x = j.filter(pl.col("grp") == g)
        if x.height >= 30:
            b, a = np.polyfit(x["epa"].to_numpy(), x["epa_ref"].to_numpy(), 1)
            maps[g] = [round(float(a), 6), round(float(b), 6)]
    return maps, j.height


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@lru_cache(maxsize=1)
def config() -> dict:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8")) if CONFIG.exists() else {}


@lru_cache(maxsize=2)
def _reference(name: str, sha: str) -> pl.DataFrame:
    path = RAW_DIR / "pbp" / str(config()["season"]) / name
    if file_sha256(path) != sha:
        raise ValueError(f"EP-scale reference snapshot {name} does not match its recorded sha256")
    return pl.read_parquet(path)


def _matched(new: pl.DataFrame, ref: pl.DataFrame) -> pl.DataFrame:
    """Plays of `new` that are in `ref` and unchanged, with ref's valuation columns suffixed _ref."""
    ident = [c for c in IDENTITY if c in new.columns and c in ref.columns]
    vals = [c for c in valuation_columns(ref.columns) if c in new.columns]
    r = ref.select(["game_id", "play_id"] + ident + vals).rename({c: f"{c}_ref" for c in ident + vals})
    j = new.join(r, on=["game_id", "play_id"], how="inner")
    same = pl.lit(True)
    for c in ident:
        same = same & pl.col(c).eq_missing(pl.col(f"{c}_ref"))
    return j.filter(same)


def _convert(expr: pl.Expr, maps: dict) -> pl.Expr:
    out = expr
    for g, (a, b) in maps.items():
        out = pl.when(pl.col("_grp") == g).then(a + b * expr).otherwise(out)
    return out


def harmonise(df: pl.DataFrame, season: int) -> pl.DataFrame:
    """Return `df` on the old EP scale where it is on the revised one (see module docstring)."""
    global _last_status
    cfg = config()
    if not cfg or season != cfg.get("season") or "epa" not in df.columns:
        return df
    from nflcast.predict.alerts import ep_scale_problem
    if ep_scale_problem(df.select([c for c in ("play_type", "ep", "epa", "two_point_conversion_prob") if c in df.columns])) is None:
        return df                                               # still the old scale: nothing to do
    ref = _reference(cfg["reference_snapshot"], cfg["reference_file_sha256"])
    maps = cfg["maps"]
    m = _matched(df, ref)
    vals = [c for c in valuation_columns(ref.columns) if c in df.columns]
    keys = m.select("game_id", "play_id", *[f"{c}_ref" for c in vals], _old=pl.lit(True))
    out = df.join(keys, on=["game_id", "play_id"], how="left").with_columns(_old=pl.col("_old").fill_null(False),
                                                                            _grp=play_group(df))
    # check the frozen line on the overlap before replacing anything: converted new vs archived old, team offence EPA/play
    chk = out.filter(pl.col("_old") & pl.col("play_type").is_in(["pass", "run"]) & pl.col("epa").is_not_null()
                     & pl.col("epa_ref").is_not_null())
    chk = chk.with_columns(conv=_convert(pl.col("epa"), maps)).group_by("posteam").agg(
        e=(pl.col("conv") - pl.col("epa_ref")).mean())
    sd = float(chk["e"].std()) if chk.height > 2 else None
    mean = float(chk["e"].mean()) if chk.height else None
    lim = cfg["check"]
    ok = sd is not None and sd <= lim["team_error_sd_max"] and abs(mean) <= lim["team_error_mean_max"]
    out = out.with_columns(
        *[pl.when(pl.col("_old")).then(pl.col(f"{c}_ref")).otherwise(pl.col(c)).alias(c) for c in vals
          if c not in CONVERTED_COLS],
        *[pl.when(pl.col("_old")).then(pl.col(f"{c}_ref")).otherwise(_convert(pl.col(c), maps)).alias(c)
          for c in CONVERTED_COLS if c in vals],
    )
    if "success" in out.columns:
        out = out.with_columns(success=pl.when(pl.col("_old") | pl.col("epa").is_null()).then(pl.col("success"))
                               .otherwise((pl.col("epa") > 0).cast(out.schema["success"])))
    out = out.with_columns(ep_scale=pl.when(pl.col("_old")).then(pl.lit("old")).otherwise(pl.lit("converted")))
    out = out.drop([f"{c}_ref" for c in vals] + ["_old", "_grp"])
    n_old = int((out["ep_scale"] == "old").sum())
    _last_status = {"applied": True, "season": season, "reference_snapshot": cfg["reference_snapshot"],
                    "plays_old_values": n_old, "plays_converted": out.height - n_old,
                    "check_team_error_sd": None if sd is None else round(sd, 4),
                    "check_team_error_mean": None if mean is None else round(mean, 4), "ok": ok}
    return out


def status() -> dict:
    """What the last harmonise() call did (empty if it had nothing to do)."""
    return dict(_last_status)


def load_pbp(season: int) -> pl.DataFrame:
    """The latest archived play-by-play for `season`, harmonised (use this instead of sources.fetch('pbp', s))."""
    from nflcast.data import sources as S
    return harmonise(S.fetch("pbp", season), season)


def converted_games(df: pl.DataFrame) -> set[str]:
    """Games with at least one converted play (their EPA is an estimate on the old scale)."""
    if "ep_scale" not in df.columns:
        return set()
    return set(df.filter(pl.col("ep_scale") == "converted")["game_id"].unique().to_list())
