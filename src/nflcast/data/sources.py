"""Source adapters with append-only raw snapshots.

Every download is stored as a new immutable file under data/raw/<source>/ together with a JSON
sidecar recording the URL, HTTP Last-Modified/ETag (the provider's publication proxy), the
observed_at (ingestion) time and content hashes. A new snapshot is only written when the content
differs from the most recent one, so repeated refreshes do not duplicate identical data, while
amended data never overwrites what was previously available.

Price-type market columns (moneylines, odds) are stripped before anything is written.
"""

from __future__ import annotations

import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path

import polars as pl
import requests

from nflcast.config import RAW_DIR, utc_now, utc_stamp
from nflcast.data.policy import strip_banned

NFLVERSE_BASE = "https://github.com/nflverse/nflverse-data/releases/download/"
USER_AGENT = "nflcast-portfolio/0.1 (+nflverse data consumer)"


@dataclass(frozen=True)
class Source:
    name: str
    path: str                 # release path; may contain {season}
    min_season: int | None    # earliest season documented by the loader (None = single file)
    provider: str = "nflverse"
    licence_note: str = "nflverse-data releases; see docs/data_sources.md for per-dataset licence/attribution"

    @property
    def per_season(self) -> bool:
        return "{season}" in self.path

    def url(self, season: int | None = None) -> str:
        p = self.path.format(season=season) if self.per_season else self.path
        return f"{NFLVERSE_BASE}{p}.parquet"


SOURCES: dict[str, Source] = {s.name: s for s in [
    Source("schedules", "schedules/games", None),
    Source("teams", "teams/teams_colors_logos", None),
    Source("players", "players/players", None),
    Source("pbp", "pbp/play_by_play_{season}", 1999),
    Source("player_stats_week", "stats_player/stats_player_week_{season}", 1999),
    Source("rosters_weekly", "weekly_rosters/roster_weekly_{season}", 2002),
    Source("depth_charts", "depth_charts/depth_charts_{season}", 2001),
    Source("injuries", "injuries/injuries_{season}", 2009),
    Source("snap_counts", "snap_counts/snap_counts_{season}", 2012),
    Source("participation", "pbp_participation/pbp_participation_{season}", 2016),
    Source("ftn_charting", "ftn_charting/ftn_charting_{season}", 2022),
    Source("pfr_advstats_week_pass", "pfr_advstats/advstats_week_pass_{season}", 2018),
    Source("nextgen_passing", "nextgen_stats/ngs_passing", None),
    Source("officials", "officials/officials", None),
]}


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept": "application/octet-stream, */*"})
    return s


_SESSION = _session()


def head(source: Source, season: int | None = None, timeout: int = 30) -> dict:
    """Cheap existence/recency check without downloading the file."""
    url = source.url(season)
    try:
        r = _SESSION.head(url, allow_redirects=True, timeout=timeout)
        return {
            "url": url, "status": r.status_code, "exists": r.status_code == 200,
            "bytes": int(r.headers.get("content-length", 0) or 0),
            "last_modified": r.headers.get("last-modified"),
        }
    except requests.RequestException as e:
        return {"url": url, "status": None, "exists": False, "error": str(e)}


def _snapshot_dir(source: Source, season: int | None) -> Path:
    d = RAW_DIR / source.name / (str(season) if season is not None else "all")
    d.mkdir(parents=True, exist_ok=True)
    return d


def latest_snapshot(source_name: str, season: int | None = None) -> Path | None:
    d = RAW_DIR / source_name / (str(season) if season is not None else "all")
    if not d.exists():
        return None
    files = sorted(d.glob("*.parquet"))
    return files[-1] if files else None


def fetch(source_name: str, season: int | None = None, refresh: bool = False, timeout: int = 120) -> pl.DataFrame:
    """Return the source data, downloading a new snapshot if `refresh` or none exists locally."""
    source = SOURCES[source_name]
    existing = latest_snapshot(source_name, season)
    if existing is not None and not refresh:
        return pl.read_parquet(existing)

    url = source.url(season)
    r = _SESSION.get(url, timeout=timeout)
    r.raise_for_status()
    content = r.content
    df = pl.read_parquet(io.BytesIO(content))
    df, dropped = strip_banned(df)

    provider_sha = hashlib.sha256(content).hexdigest()
    buf = io.BytesIO()
    df.write_parquet(buf)
    stored_bytes = buf.getvalue()
    stored_sha = hashlib.sha256(df.hash_rows().to_numpy().tobytes()).hexdigest()

    # De-duplicate: only append a snapshot if the (price-stripped) content changed.
    if existing is not None:
        meta_prev = existing.with_suffix(".json")
        if meta_prev.exists():
            prev = json.loads(meta_prev.read_text(encoding="utf-8"))
            if prev.get("content_sha256") == stored_sha:
                # unchanged: log the confirmation so freshness checks know the data was re-verified now
                with open(existing.parent / "checks.jsonl", "a", encoding="utf-8") as fh:
                    fh.write(json.dumps({"checked_at_utc": utc_now().isoformat(), "content_sha256": stored_sha,
                                         "http_last_modified": r.headers.get("last-modified")}) + "\n")
                return pl.read_parquet(existing)

    observed = utc_now()
    stem = f"{source_name}_{season if season is not None else 'all'}__observed_{utc_stamp(observed)}"
    d = _snapshot_dir(source, season)
    (d / f"{stem}.parquet").write_bytes(stored_bytes)
    meta = {
        "source": source_name, "provider": source.provider, "season": season, "url": url,
        "observed_at_utc": observed.isoformat(),
        "http_last_modified": r.headers.get("last-modified"), "http_etag": r.headers.get("etag"),
        "provider_file_sha256": provider_sha, "content_sha256": stored_sha,
        "rows": df.height, "columns": df.columns, "dropped_price_columns": dropped,
    }
    (d / f"{stem}.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return df


def snapshot_asof(source_name: str, season: int | None, when) -> tuple[pl.DataFrame | None, dict | None]:
    """The newest archived snapshot whose observed_at <= `when`, with its metadata (None if none exists).

    `observed_at` is our retrieval time: the data was public no later than that. Provider publication
    times are not known and are never inferred.
    """
    from datetime import datetime
    d = RAW_DIR / source_name / (str(season) if season is not None else "all")
    best = None
    for meta_path in sorted(d.glob("*.json")) if d.exists() else []:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if datetime.fromisoformat(meta["observed_at_utc"]) <= when:
            best = (meta_path, meta)
    if best is None:
        return None, None
    meta = dict(best[1])
    confirmed = datetime.fromisoformat(meta["observed_at_utc"])
    checks = d / "checks.jsonl"
    if checks.exists():
        for line in checks.read_text(encoding="utf-8").splitlines():
            c = json.loads(line)
            t = datetime.fromisoformat(c["checked_at_utc"])
            if c["content_sha256"] == meta["content_sha256"] and confirmed < t <= when:
                confirmed = t
    meta["last_confirmed_at_utc"] = confirmed.isoformat()
    return pl.read_parquet(best[0].with_suffix(".parquet")), meta


def fetch_many(source_name: str, seasons: list[int], refresh: bool = False) -> pl.DataFrame:
    frames = [fetch(source_name, s, refresh=refresh) for s in seasons]
    return pl.concat(frames, how="diagonal_relaxed")
