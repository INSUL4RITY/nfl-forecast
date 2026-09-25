"""Quarterback availability: who is likely to start, with evidence and uncertainty.

Principles (see docs/methodology.md, "Quarterback availability"):
  * Every relevant QB (depth-chart QB1, QB2, QB3, and the previous starter) gets an availability
    status with an evidence source and an as-of timestamp.
  * Missing or stale information is NOT treated as confirmed availability. A team whose injury report
    for the week has not appeared yet is "report_not_available"; an injury snapshot that is too old is
    "report_stale"; a depth chart older than its freshness limit or older than the team's latest game
    is "depth_chart_stale".
  * Start probabilities are estimated from history (2016+), never assumed: for the depth-chart QB1,
    P(starts | final-report status) and P(starts | no report available), optionally conditioned on
    whether he finished the team's previous game. Backups use P(plays | status) for any position.
  * Documented manual overrides (data/manual/qb_overrides.csv) are applied only if their source was
    published at or before the forecast cutoff. Each must name a source; they are logged in the release.
  * Scenarios: sequential. QB1 starts with probability a1; otherwise the next available QB, etc.
    Scenarios below MIN_SCENARIO_P are folded into the most likely one, and the folded mass is reported.
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
def _beta(k: int, n: int, a: float = 1.0, b: float = 1.0) -> float:
    return (k + a) / (n + a + b)


def estimate_start_rates(team_weeks: pl.DataFrame, max_season: int) -> dict:
    """team_weeks: one row per (team, game) from build_history_team_weeks.

    Only seasons <= max_season are used (as-of). Returns Beta(1,1)-smoothed rates with their counts:
      by_status[s]         P(depth-chart QB1 starts | QB1's final-report status s)
      no_report[k]         P(QB1 starts) ignoring the report, overall and by whether QB1 finished the previous game
      backup_by_status[s]  P(depth-chart QB2 starts | QB1 did not start, QB2's status s)
    Status labels: Out, Doubtful, Questionable, Probable (pre-2016), None (listed, no game designation), NotListed.
    """
    tw = team_weeks.filter(pl.col("season") <= max_season)
    out = {"through_season": max_season, "seasons": sorted(tw["season"].unique().to_list()),
           "by_status": {}, "no_report": {}, "backup_by_status": {}}
    for status, g in tw.group_by("qb1_status"):
        k, n = int(g["started"].sum()), g.height
        out["by_status"][status[0]] = {"p": _beta(k, n), "k": k, "n": n}
    for fin, g in tw.group_by("qb1_finished_prev"):
        k, n = int(g["started"].sum()), g.height
        out["no_report"]["finished_prev" if fin[0] else "did_not_finish_prev"] = {"p": _beta(k, n), "k": k, "n": n}
    k, n = int(tw["started"].sum()), tw.height
    out["no_report"]["all"] = {"p": _beta(k, n), "k": k, "n": n}
    b = tw.filter((pl.col("started") == 0) & pl.col("qb2").is_not_null())
    for status, g in b.group_by("qb2_status"):
        k, n = int(g["qb2_started"].sum()), g.height
        out["backup_by_status"][status[0]] = {"p": _beta(k, n), "k": k, "n": n}
    return out


def build_history_team_weeks(games: pl.DataFrame, qbg: pl.DataFrame, depth: pl.DataFrame, inj: pl.DataFrame) -> pl.DataFrame:
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
    for key in ("by_status", "no_report", "backup_by_status"):
        out[key] = {}
        cats = set(fallback[key]) | (set(primary[key]) if primary else set())
        for c in cats:
            p = (primary or {}).get(key, {}).get(c)
            if p and p["n"] >= min_n:
                out[key][c] = {**p, "source": f"{primary_label} depth charts"}
            elif c in fallback[key]:
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
    return f"historical {entry['p']:.3f} ({entry.get('k', '?')}/{entry.get('n', '?')}, {entry.get('source', 'history')})"


# ------------------------------------------------------------------ overrides
def load_overrides(path: Path = OVERRIDE_FILE) -> pl.DataFrame:
    """Documented manual overrides. Required columns:
    team, season, week, qb_gsis_id, status, source, source_published_at_utc, entered_at_utc
    Optional: p_start (0-1, only with status 'questionable'), note.
    Rows without a source or a valid source timestamp are rejected (raise), so nothing undocumented slips in.
    """
    schema = {"team": pl.Utf8, "season": pl.Int32, "week": pl.Int32, "qb_gsis_id": pl.Utf8, "status": pl.Utf8,
              "p_start": pl.Float64, "source": pl.Utf8, "source_published_at_utc": pl.Utf8, "entered_at_utc": pl.Utf8,
              "note": pl.Utf8}
    if not path.exists():
        return pl.DataFrame(schema={**schema, "published": pl.Datetime("us", "UTC"), "entered": pl.Datetime("us", "UTC")})
    df = pl.read_csv(path, schema_overrides=schema, comment_prefix="#")
    for c in ("team", "season", "week", "qb_gsis_id", "status", "source", "source_published_at_utc", "entered_at_utc"):
        if c not in df.columns or df[c].null_count():
            raise ValueError(f"{path.name}: column '{c}' is required on every row")
    bad = set(df["status"].str.to_lowercase().to_list()) - OVERRIDE_STATUSES
    if bad:
        raise ValueError(f"{path.name}: unknown status values {bad}")
    df = df.with_columns(status=pl.col("status").str.to_lowercase(),
                         published=pl.col("source_published_at_utc").str.to_datetime(time_zone="UTC"),
                         entered=pl.col("entered_at_utc").str.to_datetime(time_zone="UTC"))
    if "p_start" not in df.columns:
        df = df.with_columns(p_start=pl.lit(None, pl.Float64))
    if "note" not in df.columns:
        df = df.with_columns(note=pl.lit(None, pl.Utf8))
    return df


# ------------------------------------------------------------------ resolver
@dataclass
class QBInfo:
    qb_id: str
    rank: int | None                   # depth-chart rank (None if not on chart)
    status: str                        # Out / Doubtful / Questionable / NotListed / Unknown / override:<x>
    evidence: str                      # injury_report / not_on_published_report / report_not_available / report_stale / override
    evidence_at: str | None            # when the evidence was observed/published (UTC ISO)
    p_available: float                 # P(able and chosen to start | this QB is the next in line)
    detail: str = ""


@dataclass
class QBResolution:
    team: str
    scenarios: list[tuple[float, str]]            # (probability, qb_id)
    qbs: list[QBInfo] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    folded_p: float = 0.0
    depth_chart_at: str | None = None
    injury_snapshot_at: str | None = None
    overrides_used: list[dict] = field(default_factory=list)

    @property
    def uncertain(self) -> bool:
        """Material uncertainty: leading QB below 90%, or missing/stale evidence, or QB1 left the last game early."""
        lead = self.scenarios[0][0] if self.scenarios else 0.0
        return lead < 0.9 or any(f.endswith(("missing", "stale", "not_available", "previous_game")) for f in self.flags)

    def to_json(self, name_of: dict) -> dict:
        return {
            "scenarios": [{"p": p, "qb_id": q, "qb": name_of.get(q)} for p, q in self.scenarios],
            "qbs": [{"qb_id": i.qb_id, "qb": name_of.get(i.qb_id), "depth_rank": i.rank, "status": i.status,
                     "evidence": i.evidence, "evidence_at": i.evidence_at, "p_available": i.p_available, "detail": i.detail}
                    for i in self.qbs],
            "flags": self.flags, "folded_probability": self.folded_p, "depth_chart_at": self.depth_chart_at,
            "injury_snapshot_at": self.injury_snapshot_at, "overrides_used": self.overrides_used,
        }


def _iso(dt) -> str | None:
    return dt.isoformat() if dt is not None else None


def resolve_team_qbs(*, team: str, season: int, week: int, now: datetime,
                     depth: list[tuple[str, int]], depth_at: datetime | None,
                     injuries: pl.DataFrame, injury_observed_at: datetime | None,
                     previous_starter: str | None, previous_game_kickoff: datetime | None,
                     previous_share: float | None, rates: dict, p_play: dict[str, float],
                     overrides: pl.DataFrame) -> QBResolution:
    """Resolve expected-starter scenarios for one team at cutoff `now`.

    depth: [(gsis_id, rank)] from the latest depth-chart snapshot at or before `now` (may be empty).
    injuries: this season's injury rows (team already mapped to franchise ids) as observed at injury_observed_at.
    p_play: P(played | status) for any position (backup availability), from earlier seasons.
    """
    flags: list[str] = []
    res = QBResolution(team=team, scenarios=[], depth_chart_at=_iso(depth_at), injury_snapshot_at=_iso(injury_observed_at))

    # ---- depth chart freshness
    stale_dc = (depth_at is None or now - depth_at > DEPTH_CHART_MAX_AGE
                or (previous_game_kickoff is not None and depth_at < previous_game_kickoff))
    if not depth:
        flags.append("depth_chart_missing")
    elif stale_dc:
        flags.append("depth_chart_stale")
    order = [q for q, _ in sorted(depth, key=lambda x: x[1])]
    rank_of = {q: r for q, r in depth}
    if (not depth or stale_dc) and previous_starter:
        # a missing/stale chart is not evidence of the current order: lead with the last actual starter
        order = [previous_starter] + [q for q in order if q != previous_starter]
    elif previous_starter and previous_starter not in order:
        order.append(previous_starter)
    order = order[:4]
    if not order:
        res.flags = flags + ["no_candidate_qb"]
        return res

    # ---- injury report availability for this team-week
    team_rows = injuries.filter((pl.col("team") == team) & (pl.col("week") == week))
    if injury_observed_at is None or now - injury_observed_at > INJURY_SNAPSHOT_MAX_AGE:
        report_state = "report_stale"
    elif team_rows.height == 0:
        report_state = "report_not_available"
    else:
        report_state = "report_published"
    if report_state != "report_published":
        flags.append(report_state)

    ov = overrides.filter((pl.col("team") == team) & (pl.col("season") == season) & (pl.col("week") == week)
                          & (pl.col("published") <= now))

    infos: list[QBInfo] = []
    for i, q in enumerate(order):
        o = ov.filter(pl.col("qb_gsis_id") == q).sort("published")
        if o.height:
            r = o.row(-1, named=True)
            st = r["status"]
            if st in ("starting",):
                p = 1.0
            elif st == "available":
                p = rates["by_status"].get("NotListed", {}).get("p", 0.97) if i == 0 else p_play.get("NotListed", 0.98)
            elif st in ("out", "not_starting"):
                p = 0.0
            elif st == "doubtful":
                p = rates["by_status"].get("Doubtful", {}).get("p", 0.05) if i == 0 else p_play.get("Doubtful", 0.05)
            else:  # questionable
                p = float(r["p_start"]) if r["p_start"] is not None else (
                    rates["by_status"].get("Questionable", {}).get("p", 0.6) if i == 0 else p_play.get("Questionable", 0.6))
            infos.append(QBInfo(q, rank_of.get(q), f"override:{st}", "override", _iso(r["published"]), p,
                                f"{r['source']}" + (f" ({r['note']})" if r["note"] else "")))
            res.overrides_used.append({"qb_gsis_id": q, "status": st, "source": r["source"],
                                       "source_published_at_utc": _iso(r["published"]), "entered_at_utc": _iso(r["entered"])})
            continue
        row = team_rows.filter(pl.col("gsis_id") == q)
        table = rates["by_status"] if i == 0 else rates["backup_by_status"]
        if report_state == "report_published":
            if row.height:
                st = row["report_status"][0]
                pr = row["practice_status"][0] if "practice_status" in row.columns else None
                st = "None" if st in (None, "", "Note") else st
                detail = f"practice: {pr}" if pr else ""
                if st == "None" and pr and "Did Not" in pr:
                    # on the practice report without a game designation yet: evidence of risk -> Questionable rate
                    st, detail = "Questionable", f"no game designation yet; {pr}"
                ev = "injury_report"
            else:
                st, detail, ev = "NotListed", "not on the team's published report", "not_on_published_report"
            rate = table.get(st, table.get("NotListed", {"p": p_play.get(st, 0.9), "source": "generic P(plays|status)"}))
            p = 0.0 if st == "Out" else rate["p"]
            detail = "; ".join(x for x in (detail, "listed Out" if st == "Out" else rate_note(rate)) if x)
            infos.append(QBInfo(q, rank_of.get(q), st, ev, _iso(injury_observed_at), float(p), detail))
        else:
            # no usable report: historical base rates (QB1 conditioned on finishing the previous game)
            if i == 0:
                key = "all" if previous_share is None else ("finished_prev" if previous_share >= FINISHED_SHARE else "did_not_finish_prev")
                rate = rates["no_report"].get(key, rates["no_report"]["all"])
                p = rate["p"]
                detail = f"no current report ({key.replace('_', ' ')}); {rate_note(rate)}"
                if previous_share is not None and previous_share < FINISHED_SHARE:
                    flags.append("qb1_did_not_finish_previous_game")
            else:
                allb = rates["backup_by_status"]
                k = sum(v["k"] for v in allb.values()); n = sum(v["n"] for v in allb.values())
                p = _beta(k, n)
                detail = f"no current report; historical backup rate {p:.3f} ({k}/{n}, all statuses)"
            infos.append(QBInfo(q, rank_of.get(q), "Unknown", report_state, _iso(injury_observed_at), float(p), detail))

    # ---- sequential scenarios
    remaining, raw = 1.0, []
    for info in infos:
        pi = remaining * info.p_available
        raw.append((pi, info.qb_id))
        remaining -= pi
    if remaining > 1e-9:  # nobody on the list is certain: the leftover goes to the last listed QB (emergency starter)
        raw[-1] = (raw[-1][0] + remaining, raw[-1][1])
    # Small alternatives are merged into the most likely ALTERNATIVE, never into the leading QB, so the
    # leader's evidence-based probability is shown as-is (a 95% starter is never displayed as 100%).
    raw = sorted([x for x in raw if x[0] > 1e-12], key=lambda x: -x[0])
    lead, alts = raw[0], raw[1:]
    folded = 0.0
    if alts:
        kept = [a for a in alts if a[0] >= MIN_SCENARIO_P] or [alts[0]]
        folded = sum(p for p, _ in alts) - sum(p for p, _ in kept)
        kept[0] = (kept[0][0] + folded, kept[0][1])
        raw = [lead] + kept
    else:
        raw = [lead]
    res.scenarios = sorted(raw, key=lambda x: -x[0])
    res.qbs, res.flags, res.folded_p = infos, flags, float(folded)
    return res
