"""Put 2026 play-by-play on the original EP scale, the same way the forecast does (pandas port, read-only reuse).

nflverse re-published 2026 play-by-play on the revised nflfastR expected-points scale on 2026-11-17 (nflfastR PR 618).
This report's historical fits (shrinkage, calibration, composite weights, the 2025 prior, travel and fatigue studies) use
the original scale. The forecast solved this in `main` (src/nflcast/data/ep_scale.py, configs/ep_scale.yaml, commit
8ef6b29; user decision 2026-11-17). This module repeats that conversion exactly, without importing or changing `main`:

  * every play held in the last original-scale snapshot (`reference_snapshot` in ep_scale_2026.yaml, a verbatim copy of
    main's configs/ep_scale.yaml) keeps its archived valuation columns, as long as the play itself is unchanged
    (IDENTITY columns equal, missing equal to missing);
  * any other play (later games, or plays nflverse edited) has `epa` and `qb_epa` converted with the frozen
    per-play-type line old = a + b * new from that file; `success` is re-derived as epa > 0. Its other valuation
    columns (ep, wp, cpoe, xyac, pass_oe) stay as published;
  * a column `ep_scale` says which: "old" or "converted".

The reference snapshot is main's raw file, checked against its recorded sha256 and copied (never linked) into this
worktree's cache the first time. Each call re-checks the frozen line on the overlapping plays (team offence EPA per play,
converted revised value vs archived original value) and reports it; nothing is refitted here.
"""
from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

import ep_scale

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONFIG = HERE / "ep_scale_2026.yaml"
CACHE = ROOT / "data" / "cache" / "team_analytics" / "ep_reference"
SOURCE = "forecast repository main, src/nflcast/data/ep_scale.py and configs/ep_scale.yaml, commit 8ef6b29"
IDENTITY = ["desc", "play_type", "posteam", "defteam", "down", "ydstogo", "yardline_100", "yards_gained", "qtr",
            "game_seconds_remaining", "touchdown", "penalty", "fumble_lost", "interception", "sack",
            "two_point_attempt"]
_VALUATION_RE = re.compile(r"(^|_)(ep|epa|wp|wpa)(_|$)|_prob$|^xyac_|^(success|cp|cpoe|xpass|pass_oe)$")
CONVERTED_COLS = ("epa", "qb_epa")
STATUS: dict = {}


def valuation_columns(columns) -> list[str]:
    return [c for c in columns if _VALUATION_RE.search(c)]


def play_group(df: pd.DataFrame) -> pd.Series:
    """Conversion group of each play (same rules, same order, as the forecast)."""
    pt = df.play_type
    g = pd.Series("other", index=df.index, dtype=object)
    plain = pt.isin(["pass", "run", "punt", "field_goal", "extra_point", "no_play"])
    g[plain] = pt[plain]
    g[df.touchdown.fillna(0) == 1] = "td"
    g[pt == "kickoff"] = "kickoff"
    return g


@lru_cache(maxsize=1)
def config() -> dict:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8")) if CONFIG.exists() else {}


def _main_raw_dir() -> Path | None:
    """The main checkout's raw play-by-play folder (read-only), found through git's common directory."""
    try:
        common = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=HERE, capture_output=True, text=True,
                                check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    d = (HERE / common).resolve().parent / "data" / "raw" / "pbp" / str(config()["season"])
    return d if d.exists() else None


def reference_path() -> Path:
    cfg = config()
    name, sha = cfg["reference_snapshot"], cfg["reference_file_sha256"]
    local = CACHE / name
    if not local.exists():
        src = _main_raw_dir()
        if src is None or not (src / name).exists():
            raise FileNotFoundError(f"EP-scale reference snapshot {name} is not in {CACHE} or the main checkout")
        CACHE.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src / name, local)
    if hashlib.sha256(local.read_bytes()).hexdigest() != sha:
        raise ValueError(f"EP-scale reference snapshot {name} does not match its recorded sha256")
    return local


@lru_cache(maxsize=1)
def _reference() -> pd.DataFrame:
    return pd.read_parquet(reference_path())


def _same(a: pd.Series, b: pd.Series) -> pd.Series:
    return (a == b) | (a.isna() & b.isna())


def _matched_keys(new: pd.DataFrame, ref: pd.DataFrame) -> pd.DataFrame:
    """game_id, play_id and ref's valuation columns (suffixed _ref) for plays of `new` that are in `ref` unchanged."""
    ident = [c for c in IDENTITY if c in new.columns and c in ref.columns]
    vals = [c for c in valuation_columns(ref.columns) if c in new.columns]
    r = ref[["game_id", "play_id"] + ident + vals].rename(columns={c: f"{c}_ref" for c in ident + vals})
    j = new[["game_id", "play_id"] + ident].merge(r, on=["game_id", "play_id"], how="inner")
    keep = pd.Series(True, index=j.index)
    for c in ident:
        keep &= _same(j[c], j[f"{c}_ref"])
    return j.loc[keep, ["game_id", "play_id"] + [f"{c}_ref" for c in vals]]


def _convert(x: pd.Series, grp: pd.Series, maps: dict) -> pd.Series:
    out = x.astype(float).copy()
    for g, (a, b) in maps.items():
        m = grp == g
        out[m] = a + b * x[m]
    return out


def harmonise(df: pd.DataFrame, season: int) -> pd.DataFrame:
    """`df` on the original EP scale where it is on the revised one; any other frame is returned unchanged."""
    global STATUS
    cfg = config()
    if not cfg or season != cfg.get("season") or "epa" not in df.columns:
        return df
    if ep_scale.problem(df, season) is None:
        return df
    ref = _reference()
    maps = cfg["maps"]
    vals = [c for c in valuation_columns(ref.columns) if c in df.columns]
    keys = _matched_keys(df, ref)
    out = df.merge(keys.assign(_old=True), on=["game_id", "play_id"], how="left", validate="many_to_one")
    out["_old"] = out["_old"].astype("boolean").fillna(False).astype(bool)
    grp = play_group(out)
    chk = out[out._old & out.play_type.isin(["pass", "run"]) & out.epa.notna() & out.epa_ref.notna()]
    e = (_convert(chk.epa, grp[chk.index], maps) - chk.epa_ref).groupby(chk.posteam).mean()
    sd = float(e.std()) if len(e) > 2 else None
    mean = float(e.mean()) if len(e) else None
    lim = cfg["check"]
    ok = sd is not None and sd <= lim["team_error_sd_max"] and abs(mean) <= lim["team_error_mean_max"]
    for c in vals:
        if c in CONVERTED_COLS:
            out[c] = np.where(out._old, out[f"{c}_ref"], _convert(out[c], grp, maps))
        else:
            out[c] = out[c].where(~out._old, out[f"{c}_ref"])
    if "success" in out.columns:
        conv = ~out._old & out.epa.notna()
        out.loc[conv, "success"] = (out.loc[conv, "epa"] > 0).astype(float)
    out["ep_scale"] = np.where(out._old, "old", "converted")
    out = out.drop(columns=[f"{c}_ref" for c in vals] + ["_old"])
    n_old = int((out.ep_scale == "old").sum())
    STATUS = {"applied": True, "season": season, "reference_snapshot": cfg["reference_snapshot"],
              "plays_old_values": n_old, "plays_converted": int(len(out) - n_old),
              "check_team_error_sd": None if sd is None else round(sd, 4),
              "check_team_error_mean": None if mean is None else round(mean, 4), "ok": ok,
              "limits": lim, "source": SOURCE}
    return out


def qc_line(st: dict) -> str:
    """Quality-check line for the Method section ('' when no conversion was needed)."""
    if not st.get("applied"):
        return ""
    verdict = "within" if st["ok"] else "OUTSIDE"
    return (f"EP scale: 2026 play-by-play is on the original nflfastR EP valuation, like every historical fit here. nflverse "
            f"re-published 2026 on the revised valuation (nflfastR PR 618) on 17 Nov; {st['plays_old_values']:,} plays keep "
            f"their archived original values from the last original-scale snapshot and {st['plays_converted']:,} later or "
            f"edited plays have EPA converted with the forecast's frozen per-play-type line (old = a + b × new; success "
            f"re-derived as EPA > 0; their other valuation columns as published). Residual check on the overlapping plays, team "
            f"offence EPA per play converted vs archived: sd {st['check_team_error_sd']:.4f}, mean "
            f"{st['check_team_error_mean']:+.4f} ({verdict} the forecast's limits: sd {st['limits']['team_error_sd_max']}, "
            f"mean {st['limits']['team_error_mean_max']}). Same conversion as the forecast ({st['source']}).")
