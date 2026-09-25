"""Quarterback availability: who is likely to start, with evidence and uncertainty.

Principles (see docs/methodology.md, "Quarterback availability"):
  * Every relevant QB (depth-chart QB1, QB2, QB3, and the previous starter) gets an availability
    status with an evidence source and an as-of timestamp.
  * Missing or stale information is NOT treated as confirmed availability. Each source (injury reports,
    depth charts, rosters) is assessed for freshness twice: when WE last confirmed it, and when the PROVIDER
    last updated the file. A team whose report for the week has not appeared yet is "report_not_available";
    a stale snapshot is "report_stale"; a depth chart older than 4 days, older than the team's last game or
    from a stale provider file is "depth_chart_stale".
  * Every QB in the replacement chain is validated: roster status (reserve/IR, released, retired, exempt,
    practice squad or declared inactive => cannot start), injury designation, and override. If the whole
    chain is exhausted the residual is flagged ("replacement_chain_exhausted").
  * Probabilities are START probabilities estimated from history (2016+), never P(played) and never
    assumed: P(depth-chart QB1 starts | final-report status), P(QB1 starts | no report) by whether he
    finished the previous game, and P(depth-chart QB2 starts | QB1 does not start, QB2's status).
  * Documented manual overrides (data/manual/qb_overrides.csv) must name a source, its publication time and
    an expiry time; they apply only while published <= cutoff < expires, and are logged in the release.
  * Scenarios are sequential. Small alternatives are merged into the most likely alternative (never into
    the leading QB), and the folded mass is reported.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import polars as pl

from nflcast.config import MANUAL_DIR, REPORTS_DIR
from nflcast.data.games import franchise

MIN_SCENARIO_P = 0.05
DEPTH_CHART_MAX_AGE = timedelta(days=4)
INJURY_SNAPSHOT_MAX_AGE = timedelta(hours=36)
FINISHED_SHARE = 0.75   # QB1 "finished" the previous game if he took >= 75% of team dropbacks
OVERRIDE_FILE = MANUAL_DIR / "qb_overrides.csv"
RATES_FILE = REPORTS_DIR / "qb_availability" / "start_rates.json"

OVERRIDE_STATUSES = {"available", "starting", "questionable", "doubtful", "out", "not_starting"}


# ------------------------------------------------------------------ historical start rates
def _beta(k: int, n: int, a: float = 0.5, b: float = 0.5) -> float:
    """Posterior mean with a Jeffreys Beta(0.5, 0.5) prior (chosen by chronological evaluation over Beta(1,1))."""
    return (k + a) / (n + a + b)


def _rate(k: int, n: int, prior_p: float | None = None, m: float = 0.0) -> dict:
    """Smoothed start rate with a 90% interval. With prior_p and m > 0 the rate is shrunk toward prior_p
    (pseudo-count m); the interval is the Beta posterior under that prior."""
    from scipy.stats import beta as _b
    if prior_p is not None and m > 0:
        a, b = m * prior_p, m * (1 - prior_p)
    else:
        a, b = 0.5, 0.5
    lo, hi = _b.ppf([0.05, 0.95], k + a, n - k + b)
    return {"p": (k + a) / (n + a + b), "k": int(k), "n": int(n), "lo": float(lo), "hi": float(hi)}


def practice_bucket(expr: pl.Expr) -> pl.Expr:
    return (pl.when(expr.str.contains("(?i)did not|out \\(")).then(pl.lit("DNP"))
            .when(expr.str.contains("(?i)limited")).then(pl.lit("Limited"))
            .when(expr.str.contains("(?i)full")).then(pl.lit("Full"))
            .otherwise(pl.lit("NoPractice")))


def injury_practice(seasons: list[int]) -> pl.DataFrame:
    """Final weekly practice participation per (season, week, team, gsis_id), bucketed Full/Limited/DNP/NoPractice."""
    from nflcast.data import sources as S
    frames = [S.fetch("injuries", s).select(pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32),
                                            franchise(pl.col("team")).alias("team"), "gsis_id", "practice_status")
              for s in seasons]
    return (pl.concat(frames).unique(["season", "week", "team", "gsis_id"], keep="last")
            .with_columns(practice=practice_bucket(pl.col("practice_status").fill_null(""))).drop("practice_status"))


def estimate_start_rates(team_weeks: pl.DataFrame, max_season: int) -> dict:
    """team_weeks: one row per (team, game) from build_history_team_weeks.

    Only seasons <= max_season are used (as-of). Returns Beta(1,1)-smoothed rates with their counts:
      by_status[s]         P(depth-chart QB1 starts | QB1's final-report status s)
      no_report[k]         P(QB1 starts) ignoring the report, overall and by whether QB1 finished the previous game
      backup_by_status[s]  P(depth-chart QB2 starts | QB1 did not start, QB2's status s)
    Status labels: Out, Doubtful, Questionable, Probable (pre-2016), None (listed, no game designation), NotListed.
    """
    tw = team_weeks.filter(pl.col("season") <= max_season)
    out = {"through_season": max_season, "seasons": sorted(tw["season"].unique().to_list()), "target": "started",
           "prior": "Jeffreys Beta(0.5,0.5); status x practice shrunk toward the status rate",
           "by_status": {}, "by_status_practice": {}, "no_report": {}, "backup_by_status": {}}
    for status, g in tw.group_by("qb1_status"):
        out["by_status"][status[0]] = _rate(int(g["started"].sum()), g.height)
    listed = tw.filter(pl.col("qb1_status") != "NotListed")
    # any appearance on the final report, pooled over designations (used while designations are pending)
    out["by_status"]["ListedAny"] = _rate(int(listed["started"].sum()), listed.height)
    if "qb1_practice" in tw.columns:
        from nflcast.evaluation.qb_rates_eval import choose_m
        m = choose_m(tw)
        out["practice_shrinkage_m"] = m
        mm = min(m, 1e6)
        for (st, pb), g in tw.group_by(["qb1_status", "qb1_practice"]):
            if st in ("NotListed",):
                continue
            prior = out["by_status"][st]["p"]
            out["by_status_practice"][f"{st}|{pb}"] = _rate(int(g["started"].sum()), g.height, prior, mm)
        for (pb,), g in listed.group_by(["qb1_practice"]):
            out["by_status_practice"][f"ListedAny|{pb}"] = _rate(int(g["started"].sum()), g.height,
                                                                  out["by_status"]["ListedAny"]["p"], mm)
    for fin, g in tw.group_by("qb1_finished_prev"):
        out["no_report"]["finished_prev" if fin[0] else "did_not_finish_prev"] = _rate(int(g["started"].sum()), g.height)
    out["no_report"]["all"] = _rate(int(tw["started"].sum()), tw.height)
    b = tw.filter((pl.col("started") == 0) & pl.col("qb2").is_not_null())
    for status, g in b.group_by("qb2_status"):
        out["backup_by_status"][status[0]] = _rate(int(g["qb2_started"].sum()), g.height)
    return out


def build_history_team_weeks(games: pl.DataFrame, qbg: pl.DataFrame, depth: pl.DataFrame, inj: pl.DataFrame,
                             practice: pl.DataFrame | None = None) -> pl.DataFrame:
    """Historical table for estimate_start_rates.

    depth: weekly depth-chart QBs with columns team, season, week, qb_id, rank (1, 2, ...).
    inj: final weekly injury report rows (personnel.injury_player_weeks): game_id, team, gsis_id, status.
    """
    starters = qbg.filter(pl.col("is_starter")).select("game_id", "team", pl.col("qb_id").alias("starter"))
    team_db = qbg.group_by("game_id", "team").agg(team_db=pl.col("db").sum())
    g = pl.concat([
        games.select("game_id", "season", "week", "kickoff_utc", pl.col("home_id").alias("team")),
        games.select("game_id", "season", "week", "kickoff_utc", pl.col("away_id").alias("team"))])
    g = g.join(starters, on=["game_id", "team"], how="inner").sort("team", "kickoff_utc")
    g = g.with_columns(prev_game=pl.col("game_id").shift(1).over("team"))
    for rk, name in ((1, "qb1"), (2, "qb2")):
        d = depth.filter(pl.col("rank") == rk).select("team", "season", "week", pl.col("qb_id").alias(name))
        g = g.join(d, on=["team", "season", "week"], how="inner" if rk == 1 else "left")
    share = qbg.join(team_db, on=["game_id", "team"]).select(
        pl.col("game_id").alias("prev_game"), "team", pl.col("qb_id").alias("qb1"), (pl.col("db") / pl.col("team_db")).alias("prev_share"))
    g = g.join(share, on=["prev_game", "team", "qb1"], how="left").with_columns(pl.col("prev_share").fill_null(0.0))
    for name in ("qb1", "qb2"):
        st = inj.select("game_id", "team", pl.col("gsis_id").alias(name), pl.col("status").alias(f"{name}_status"))
        g = g.join(st, on=["game_id", "team", name], how="left").with_columns(pl.col(f"{name}_status").fill_null("NotListed"))
    if practice is not None:
        pr = practice.select("season", "week", "team", pl.col("gsis_id").alias("qb1"), pl.col("practice").alias("qb1_practice"))
        g = g.join(pr, on=["season", "week", "team", "qb1"], how="left").with_columns(pl.col("qb1_practice").fill_null("NoPractice"))
    return g.with_columns(started=(pl.col("starter") == pl.col("qb1")).cast(pl.Int32),
                          qb2_started=(pl.col("starter") == pl.col("qb2")).cast(pl.Int32),
                          qb1_finished_prev=pl.col("prev_share") >= FINISHED_SHARE)


def weekly_depth_qbs(seasons: list[int]) -> pl.DataFrame:
    """Weekly depth-chart QBs (charts without timestamps, 2016-2024) as team, season, week, qb_id, rank."""
    from nflcast.data import sources as S
    frames = []
    for s in seasons:
        dc = S.fetch("depth_charts", s)
        if "club_code" not in dc.columns:
            continue
        frames.append(dc.filter((pl.col("position") == "QB") & pl.col("gsis_id").is_not_null()
                                & pl.col("depth_team").is_in(["1", "2", "3"]))
                      .select(franchise(pl.col("club_code")).alias("team"), pl.col("season").cast(pl.Int32),
                              pl.col("week").cast(pl.Int32), pl.col("gsis_id").alias("qb_id"),
                              pl.col("depth_team").cast(pl.Int32).alias("rank"))
                      .unique(["team", "season", "week", "rank"], keep="first"))
    return pl.concat(frames)


def daily_depth_qbs(seasons: list[int], games: pl.DataFrame, lead_hours: float) -> pl.DataFrame:
    """Depth-chart QBs from DAILY snapshots (2025+) as they stood `lead_hours` before each kickoff."""
    from datetime import timedelta as _td
    from nflcast.data import sources as S
    rows = []
    for season in seasons:
        dc = S.fetch("depth_charts", season)
        if "dt" not in dc.columns:
            continue
        dc = dc.filter((pl.col("pos_abb") == "QB") & pl.col("gsis_id").is_not_null()).with_columns(
            team=franchise(pl.col("team")), t=pl.col("dt").str.to_datetime(time_zone="UTC"))
        g = pl.concat([games.filter((pl.col("season") == season) & (pl.col("status") == "final"))
                       .select("season", "week", "kickoff_utc", pl.col(c).alias("team")) for c in ("home_id", "away_id")])
        for r in g.iter_rows(named=True):
            s = dc.filter((pl.col("team") == r["team"]) & (pl.col("t") <= r["kickoff_utc"] - _td(hours=lead_hours)))
            if s.height == 0:
                continue
            s = s.filter(pl.col("t") == s["t"].max()).sort("pos_rank").unique("gsis_id", keep="first", maintain_order=True)
            for rk, q in enumerate(s["gsis_id"].to_list()[:3], start=1):
                rows.append({"team": r["team"], "season": season, "week": r["week"], "qb_id": q, "rank": rk})
    if not rows:
        return pl.DataFrame(schema={"team": pl.Utf8, "season": pl.Int32, "week": pl.Int32, "qb_id": pl.Utf8, "rank": pl.Int32})
    return pl.DataFrame(rows).with_columns(pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32),
                                           pl.col("rank").cast(pl.Int32))


def merge_rates(primary: dict | None, fallback: dict, min_n: int = 30, primary_label: str = "daily", fallback_label: str = "weekly") -> dict:
    """Per category, use `primary` (better matched to live data) when it has >= min_n cases, else `fallback`."""
    out = {"through_season": fallback["through_season"], "sources": {primary_label: primary.get("seasons") if primary else None,
                                                                     fallback_label: fallback.get("seasons")}}
    out["practice_shrinkage_m"] = fallback.get("practice_shrinkage_m")
    for key in ("by_status", "by_status_practice", "no_report", "backup_by_status"):
        out[key] = {}
        cats = set(fallback.get(key, {})) | (set(primary.get(key, {})) if primary else set())
        for c in cats:
            p = (primary or {}).get(key, {}).get(c)
            if p and p["n"] >= min_n:
                out[key][c] = {**p, "source": f"{primary_label} depth charts"}
            elif c in fallback.get(key, {}):
                out[key][c] = {**fallback[key][c], "source": f"{fallback_label} depth charts"}
            else:
                out[key][c] = {**p, "source": f"{primary_label} depth charts (n<{min_n})"}
    return out


def save_rates(rates: dict) -> None:
    RATES_FILE.parent.mkdir(parents=True, exist_ok=True)
    RATES_FILE.write_text(json.dumps(rates, indent=1), encoding="utf-8")


def load_rates() -> dict:
    return json.loads(RATES_FILE.read_text(encoding="utf-8"))


def rate_note(entry: dict | None) -> str:
    if not entry:
        return ""
    ci = f", 90% interval {entry['lo']:.2f}-{entry['hi']:.2f}" if "lo" in entry else ""
    return f"historical start rate {entry['p']:.3f} ({entry.get('k', '?')}/{entry.get('n', '?')}{ci}; {entry.get('source', 'history')})"


def _pooled(table: dict) -> dict:
    k = sum(v.get("k", 0) for v in table.values())
    n = sum(v.get("n", 0) for v in table.values())
    return {"p": _beta(k, n), "k": k, "n": n, "source": "pooled over statuses"}


# ------------------------------------------------------------------ overrides
OVERRIDE_COLUMNS = ["team", "season", "week", "qb_gsis_id", "status", "source", "source_published_at_utc",
                    "entered_at_utc", "expires_at_utc"]


def load_overrides(path: Path = OVERRIDE_FILE) -> pl.DataFrame:
    """Documented manual overrides. Required on every row:
    team, season, week, qb_gsis_id, status, source, source_published_at_utc, entered_at_utc, expires_at_utc
    Optional: p_start (0-1, only with status 'questionable'), note.
    An override applies only while source_published_at_utc <= cutoff < expires_at_utc, so stale manual
    information cannot linger. Rows without a source or valid timestamps are rejected (raise).
    """
    schema = {"team": pl.Utf8, "season": pl.Int32, "week": pl.Int32, "qb_gsis_id": pl.Utf8, "status": pl.Utf8,
              "p_start": pl.Float64, "source": pl.Utf8, "source_published_at_utc": pl.Utf8, "entered_at_utc": pl.Utf8,
              "expires_at_utc": pl.Utf8, "note": pl.Utf8}
    ts = {"published": pl.Datetime("us", "UTC"), "entered": pl.Datetime("us", "UTC"), "expires": pl.Datetime("us", "UTC")}
    if not path.exists():
        return pl.DataFrame(schema={**schema, **ts})
    df = pl.read_csv(path, schema_overrides=schema, comment_prefix="#")
    for c in OVERRIDE_COLUMNS:
        if c not in df.columns or df[c].null_count() or (df[c].dtype == pl.Utf8 and (df[c].str.strip_chars() == "").any()):
            raise ValueError(f"{path.name}: column '{c}' is required on every row")
    bad = set(df["status"].str.to_lowercase().to_list()) - OVERRIDE_STATUSES
    if bad:
        raise ValueError(f"{path.name}: unknown status values {bad}")
    df = df.with_columns(status=pl.col("status").str.to_lowercase(),
                         published=pl.col("source_published_at_utc").str.to_datetime(time_zone="UTC"),
                         entered=pl.col("entered_at_utc").str.to_datetime(time_zone="UTC"),
                         expires=pl.col("expires_at_utc").str.to_datetime(time_zone="UTC"))
    if (df["expires"] <= df["published"]).any():
        raise ValueError(f"{path.name}: expires_at_utc must be after source_published_at_utc")
    for c, t in (("p_start", pl.Float64), ("note", pl.Utf8)):
        if c not in df.columns:
            df = df.with_columns(pl.lit(None, t).alias(c))
    return df


# ------------------------------------------------------------------ freshness
PROVIDER_MAX_AGE = {"injuries": timedelta(hours=36), "depth_charts": timedelta(hours=36), "rosters_weekly": timedelta(days=8)}
RETRIEVAL_MAX_AGE = timedelta(hours=36)
ROSTER_UNAVAILABLE = {"RES": "reserve list (e.g. injured reserve)", "CUT": "released", "RET": "retired",
                      "EXE": "exempt list", "DEV": "practice squad (not on active roster)",
                      "INA": "declared inactive for this game"}


@dataclass
class SourceFreshness:
    source: str
    state: str                      # fresh | stale_provider | stale_retrieval | missing
    observed_at: str | None         # our first retrieval of this content
    last_confirmed_at: str | None   # our latest check that the content was unchanged
    provider_last_modified: str | None
    detail: str = ""

    def to_json(self) -> dict:
        return self.__dict__.copy()


def assess_freshness(source: str, meta: dict | None, now: datetime) -> SourceFreshness:
    """Freshness of an archived source snapshot at `now`: both our retrieval and the provider's own update time."""
    from email.utils import parsedate_to_datetime
    if not meta:
        return SourceFreshness(source, "missing", None, None, None, "no snapshot available before the cutoff")
    confirmed = datetime.fromisoformat(meta.get("last_confirmed_at_utc") or meta["observed_at_utc"])
    lm = meta.get("http_last_modified")
    provider = parsedate_to_datetime(lm) if lm else None
    state, detail = "fresh", ""
    if now - confirmed > RETRIEVAL_MAX_AGE:
        state, detail = "stale_retrieval", f"not re-checked for {(now - confirmed).total_seconds() / 3600:.0f} h"
    elif provider is not None and now - provider > PROVIDER_MAX_AGE.get(source, timedelta(hours=36)):
        state, detail = "stale_provider", f"provider file last updated {(now - provider).total_seconds() / 3600:.0f} h before the cutoff"
    return SourceFreshness(source, state, meta.get("observed_at_utc"), confirmed.isoformat(),
                           provider.isoformat() if provider else None, detail)


# ------------------------------------------------------------------ resolver
@dataclass
class QBInfo:
    qb_id: str
    rank: int | None                   # depth-chart rank (None if not on chart)
    status: str                        # Out / Doubtful / Questionable / None / NotListed / Unknown / roster:<code> / override:<x>
    evidence: str                      # injury_report / not_on_published_report / report_not_available / report_stale / roster / override
    evidence_at: str | None            # when the evidence was observed/published (UTC ISO)
    p_available: float                 # P(starts | every QB ahead of him in the chain does not start)
    detail: str = ""
    roster_status: str | None = None   # ACT / RES / CUT / DEV / ... from the latest roster snapshot


@dataclass
class QBResolution:
    team: str
    scenarios: list[tuple[float, str]]            # (probability, qb_id)
    qbs: list[QBInfo] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    folded_p: float = 0.0
    chain_residual: float = 0.0                   # probability left after the whole chain (assigned to the last usable QB)
    depth_chart_at: str | None = None
    injury_snapshot_at: str | None = None
    freshness: list[SourceFreshness] = field(default_factory=list)
    overrides_used: list[dict] = field(default_factory=list)

    @property
    def uncertain(self) -> bool:
        """Material uncertainty: leading QB below 90%, or missing/stale evidence, or an exhausted chain."""
        lead = self.scenarios[0][0] if self.scenarios else 0.0
        return lead < 0.9 or any(f.endswith(("missing", "stale", "not_available", "previous_game", "exhausted"))
                                 or f.startswith("stale") for f in self.flags)

    def to_json(self, name_of: dict) -> dict:
        return {
            "scenarios": [{"p": p, "qb_id": q, "qb": name_of.get(q)} for p, q in self.scenarios],
            "qbs": [{"qb_id": i.qb_id, "qb": name_of.get(i.qb_id), "depth_rank": i.rank, "status": i.status,
                     "evidence": i.evidence, "evidence_at": i.evidence_at, "p_available": i.p_available, "detail": i.detail,
                     "roster_status": i.roster_status} for i in self.qbs],
            "flags": self.flags, "folded_probability": self.folded_p, "chain_residual": self.chain_residual,
            "depth_chart_at": self.depth_chart_at, "injury_snapshot_at": self.injury_snapshot_at,
            "freshness": [f.to_json() for f in self.freshness], "overrides_used": self.overrides_used,
        }


def _iso(dt) -> str | None:
    return dt.isoformat() if dt is not None else None


def _bucket(practice: str | None) -> str:
    s = (practice or "").lower()
    if "did not" in s or "out (" in s:
        return "DNP"
    if "limited" in s:
        return "Limited"
    if "full" in s:
        return "Full"
    return "NoPractice"


def resolve_team_qbs(*, team: str, season: int, week: int, now: datetime,
                     depth: list[tuple[str, int]], depth_at: datetime | None,
                     injuries: pl.DataFrame, injury_observed_at: datetime | None,
                     previous_starter: str | None, previous_game_kickoff: datetime | None,
                     previous_share: float | None, rates: dict, overrides: pl.DataFrame,
                     roster: dict[str, str] | None = None, freshness: list[SourceFreshness] | None = None,
                     p_play: dict | None = None) -> QBResolution:
    """Resolve expected-starter scenarios for one team at cutoff `now`.

    depth:    [(gsis_id, rank)] from the latest depth-chart snapshot at or before `now` (may be empty).
    injuries: this season's injury rows (franchise team ids) as last confirmed at injury_observed_at.
    roster:   {gsis_id: roster status} for the team's QBs from the latest roster snapshot (None = unavailable).
    freshness: SourceFreshness for injuries / depth_charts / rosters_weekly (provider and retrieval age).
    rates:    START rates (never P(played)); see estimate_start_rates. `p_play` is accepted for backward
              compatibility and ignored.
    """
    flags: list[str] = []
    fresh = {f.source: f for f in (freshness or [])}
    res = QBResolution(team=team, scenarios=[], depth_chart_at=_iso(depth_at), injury_snapshot_at=_iso(injury_observed_at),
                       freshness=list(freshness or []))

    # ---- depth chart freshness (team snapshot age, last game, provider file age)
    dc_f = fresh.get("depth_charts")
    stale_dc = (depth_at is None or now - depth_at > DEPTH_CHART_MAX_AGE
                or (previous_game_kickoff is not None and depth_at < previous_game_kickoff)
                or (dc_f is not None and dc_f.state != "fresh"))
    if not depth:
        flags.append("depth_chart_missing")
    elif stale_dc:
        flags.append("depth_chart_stale")
    order = [q for q, _ in sorted(depth, key=lambda x: x[1])]
    rank_of = {q: r for q, r in depth}
    if (not depth or stale_dc) and previous_starter:
        order = [previous_starter] + [q for q in order if q != previous_starter]
    elif previous_starter and previous_starter not in order:
        order.append(previous_starter)
    order = order[:4]
    if not order:
        res.flags = flags + ["no_candidate_qb"]
        return res

    # ---- roster freshness
    ro_f = fresh.get("rosters_weekly")
    roster_usable = roster is not None and (ro_f is None or ro_f.state == "fresh")
    if roster is None or (ro_f is not None and ro_f.state == "missing"):
        flags.append("roster_missing")
    elif not roster_usable:
        flags.append("roster_stale")

    # ---- injury report availability for this team-week (our retrieval age, provider age, team rows)
    inj_f = fresh.get("injuries")
    team_rows = injuries.filter((pl.col("team") == team) & (pl.col("week") == week))
    if injury_observed_at is None or now - injury_observed_at > INJURY_SNAPSHOT_MAX_AGE or (inj_f and inj_f.state != "fresh"):
        report_state = "report_stale"
    elif team_rows.height == 0:
        report_state = "report_not_available"
    else:
        report_state = "report_published"
    if report_state != "report_published":
        flags.append(report_state)

    ov = overrides.filter((pl.col("team") == team) & (pl.col("season") == season) & (pl.col("week") == week)
                          & (pl.col("published") <= now) & (pl.col("expires") > now))
    expired = overrides.filter((pl.col("team") == team) & (pl.col("season") == season) & (pl.col("week") == week)
                               & (pl.col("expires") <= now))
    if expired.height:
        flags.append("override_expired")

    infos: list[QBInfo] = []
    for i, q in enumerate(order):
        table = rates["by_status"] if i == 0 else rates["backup_by_status"]
        rs = roster.get(q, "NOT_ON_ROSTER") if roster_usable else None
        o = ov.filter(pl.col("qb_gsis_id") == q).sort("published")
        if o.height:
            r = o.row(-1, named=True)
            st = r["status"]
            rate = {"starting": {"p": 1.0}, "out": {"p": 0.0}, "not_starting": {"p": 0.0},
                    "available": table.get("NotListed", _pooled(table)),
                    "doubtful": table.get("Doubtful", _pooled(table)),
                    "questionable": ({"p": float(r["p_start"])} if r["p_start"] is not None
                                     else table.get("Questionable", _pooled(table)))}[st]
            infos.append(QBInfo(q, rank_of.get(q), f"override:{st}", "override", _iso(r["published"]), float(rate["p"]),
                                f"{r['source']}" + (f" ({r['note']})" if r["note"] else "") + f"; expires {_iso(r['expires'])}",
                                rs))
            res.overrides_used.append({"qb_gsis_id": q, "status": st, "source": r["source"],
                                       "source_published_at_utc": _iso(r["published"]), "entered_at_utc": _iso(r["entered"]),
                                       "expires_at_utc": _iso(r["expires"])})
            continue
        if rs is not None and (rs in ROSTER_UNAVAILABLE or rs == "NOT_ON_ROSTER"):
            why = ROSTER_UNAVAILABLE.get(rs, "not on the team's current roster")
            infos.append(QBInfo(q, rank_of.get(q), f"roster:{rs}", "roster", fresh["rosters_weekly"].last_confirmed_at
                                if "rosters_weekly" in fresh else None, 0.0, f"{why}; cannot start unless re-signed/elevated", rs))
            flags.append(f"chain_qb_unavailable_roster:{q}")
            continue
        row = team_rows.filter(pl.col("gsis_id") == q)
        if report_state == "report_published":
            # Game designations (Out/Doubtful/Questionable) appear late in the week. Before that, a listed player's
            # practice status is NOT the same measurement as the final report's, and no intra-week history exists
            # to calibrate it, so a pooled rate for QB1s listed on final reports is used and labelled "Pending".
            designations_out = team_rows["report_status"].drop_nulls().filter(team_rows["report_status"].drop_nulls() != "").len() > 0
            pr = None
            if row.height:
                st = row["report_status"][0]
                pr = row["practice_status"][0] if "practice_status" in row.columns else None
                st = ("None" if designations_out else "Pending") if st in (None, "", "Note") else st
                detail = f"practice: {pr}" if pr else ""
                ev = "injury_report"
            else:
                st, detail, ev = "NotListed", "not on the team's published report", "not_on_published_report"
            if st == "Pending":
                # No intra-week history exists to calibrate a mid-week practice reading. Practice status usually
                # improves through the week, so the FINAL-report rate at the same practice level is a lower bound.
                # Full: use that bound (already near-certain). Limited/DNP: use the pooled rate for QBs listed on final
                # reports, and report the bound as the low end of the plausible range.
                pooled = table.get("ListedAny") or _pooled(table)
                cell = rates.get("by_status_practice", {}).get(f"ListedAny|{_bucket(pr)}") if i == 0 else None
                if cell and _bucket(pr) == "Full":
                    rate = {**cell, "source": f"{cell.get('source', 'history')}; final-report rate for full practice "
                                              "(lower bound for a mid-week full practice)"}
                else:
                    bound = f"; plausible range {cell['p']:.2f}-{pooled['p']:.2f} (final-report {_bucket(pr)} rate as lower bound)" if cell else ""
                    rate = {**pooled, "source": f"{pooled.get('source', 'history')}; pooled over QBs on final reports{bound}; "
                                                "no intra-week history to calibrate mid-week practice"}
                detail = f"game designation not yet published; {detail}".rstrip("; ")
            else:
                rate = table.get(st) or _pooled(table)
            if i == 0 and st in ("Questionable", "Doubtful", "None"):
                cell = rates.get("by_status_practice", {}).get(f"{st}|{_bucket(pr)}")
                if cell:
                    rate = {**cell, "source": f"{cell.get('source', 'history')}; by final practice ({_bucket(pr)})"}
            p = 0.0 if st == "Out" else rate["p"]
            detail = "; ".join(x for x in (detail, "listed Out" if st == "Out" else rate_note(rate)) if x)
            infos.append(QBInfo(q, rank_of.get(q), st, ev, _iso(injury_observed_at), float(p), detail, rs))
        else:
            if i == 0:
                key = "all" if previous_share is None else ("finished_prev" if previous_share >= FINISHED_SHARE else "did_not_finish_prev")
                rate = rates["no_report"].get(key, rates["no_report"]["all"])
                detail = f"no usable report ({report_state.replace('_', ' ')}; {key.replace('_', ' ')}); {rate_note(rate)}"
                if previous_share is not None and previous_share < FINISHED_SHARE:
                    flags.append("qb1_did_not_finish_previous_game")
            else:
                rate = _pooled(rates["backup_by_status"])
                detail = f"no usable report ({report_state.replace('_', ' ')}); {rate_note(rate)}"
            infos.append(QBInfo(q, rank_of.get(q), "Unknown", report_state, _iso(injury_observed_at), float(rate["p"]), detail, rs))

    if infos and infos[0].status == "Pending":
        flags.append("designation_pending")
    # ---- sequential chain: P(QB_i starts) = P(no one ahead starts) * p_i; every link is checked above
    remaining, raw = 1.0, []
    for info in infos:
        pi = remaining * info.p_available
        raw.append((pi, info.qb_id))
        remaining -= pi
    usable = [info.qb_id for info in infos if info.p_available > 0]
    if remaining > 1e-9:
        res.chain_residual = float(remaining)
        if remaining >= 0.02:
            flags.append("replacement_chain_exhausted")
        # the unexplained mass goes to the last QB who is not known to be unavailable (an emergency starter)
        target = usable[-1] if usable else infos[-1].qb_id
        raw = [(p + remaining if q == target else p, q) for p, q in raw]
    raw = sorted([x for x in raw if x[0] > 1e-12], key=lambda x: -x[0])
    if not raw:
        res.flags = flags + ["no_available_qb"]
        return res
    lead, alts = raw[0], raw[1:]
    folded = 0.0
    if alts:
        kept = [a for a in alts if a[0] >= MIN_SCENARIO_P] or [alts[0]]
        folded = sum(p for p, _ in alts) - sum(p for p, _ in kept)
        kept[0] = (kept[0][0] + folded, kept[0][1])
        raw = [lead] + kept
    res.scenarios = sorted(raw, key=lambda x: -x[0])
    res.qbs, res.flags, res.folded_p = infos, flags, float(folded)
    return res


