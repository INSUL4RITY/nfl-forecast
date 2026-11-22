"use client";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import type { BandRate, GapBand, Manifest, SeasonRecord, Team, WeekDoc, WLP } from "@/lib/types";
import { dateRange, dayKey, fmtDateTime, isPlayoffWeek, tzFor, weekName, wilson, type TzMode } from "@/lib/format";
import GameCard from "./GameCard";
import { pickExplain, WeekResultsPanel } from "./Pick";

const pctOf = (w: number, l: number) => (w + l ? `${((100 * w) / (w + l)).toFixed(2)}%` : "—");

/** Season record of publicly verifiable pregame forecasts (level results and ties excluded from the percentage). */
const weeksText = (w: number[]) => (w.length < 2 ? weekName(w[0])
  : isPlayoffWeek(w[w.length - 1]) ? `Week ${w[0]} – ${weekName(w[w.length - 1])}` : `Weeks ${w[0]}–${w[w.length - 1]}`);
const wlp = (x: WLP) => `${x.win}–${x.loss}${x.push ? `–${x.push}` : ""}`;

function Tile({ label, x, children }: { label: string; x: WLP | null; children?: ReactNode }) {
  return (
    <div className="tile">
      <span className="caps">{label}</span>
      <span className="tile-big num">{x ? wlp(x) : "—"}</span>
      <span className="small ink2 num">{x ? (x.win + x.loss ? pctOf(x.win, x.loss) : "No finished games yet") : "No finished games yet"}</span>
      {children}
    </div>
  );
}

const NONE: WLP = { win: 0, loss: 0, push: 0 };
const pc0 = (x: number) => `${Math.round(x * 100)}%`;

/** Records as one row of tiles ("Scoreboard rail", the site's own header design, user 2026-11-22): the official model
 *  pick (season and the week on screen), the model line's own record at each lock, and the gap bands 3–4 and 4+ points
 *  (not overlapping) with their 95% range and the retrospective 2019–25 rate for the same band. */
function Records({ r, week, weekLabel }: { r: SeasonRecord; week: WLP | null; weekLabel: string }) {
  const s = r.stats_only && r.stats_only.weeks.length ? r.stats_only : null;
  const band = (b: GapBand) => {
    const x = s?.bands?.[b]?.all ?? (b === "3-4" ? s?.big_gap : s?.biggest_gap) ?? NONE;
    const ci = wilson(x.win, x.win + x.loss), h: BandRate | undefined = s?.band_history?.bands?.[b]?.all;
    return (
      <Tile key={b} label={b === "3-4" ? "Gap 3–4 pts (Big)" : "Gap 4+ pts (Biggest)"} x={x}>
        {ci && <span className="small muted num">95% range {pc0(ci[0])}–{pc0(ci[1])}</span>}
        {h && h.rate != null && <span className="small muted num">2019–25: {pc0(h.rate)} of {h.n}</span>}
      </Tile>);
  };
  return (
    <section className="records" aria-label="Records against the market line">
      <div className="tiles">
        {s && <Tile label="Model line · season" x={s.spread} />}
        <Tile label={`Model pick · ${weekLabel}`} x={week} />
        {s && band("3-4")}
        {s && band("4+")}
        <Tile label="Official record as published" x={r.spread}>
          <span className="small muted">Weeks 3–6 used the market-adjusted line</span>
        </Tile>
      </div>
      <p className="small muted records-note">Against the market line, publicly verifiable forecasts only ({weeksText(r.weeks)}).
        Model line (headline): the side of the locked line the stats-only model fell on, every week; it has been the model
        pick since week 7. Gap tiles: games where the model line was 3–4 or 4+ points from the locked line; 2019–25 is
        retrospective. Official record as published: the model pick exactly as graded at the time; in weeks 3–6 it followed
        the market-adjusted line (the rule then) and those weeks are not regraded.</p>
    </section>
  );
}

export default function WeekBoard({ doc, teams, manifest }: { doc: WeekDoc; teams: Record<string, Team>; manifest: Manifest }) {
  const [tzMode, setTzMode] = useState<TzMode>("local");
  const [day, setDay] = useState<string>("all");
  const [team, setTeam] = useState<string>("all");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    try {
      const saved = localStorage.getItem("nflcast.tz") as TzMode | null;
      if (saved) setTzMode(saved);
    } catch { /* storage unavailable: keep default */ }
    setMounted(true);
  }, []);
  // Before hydration everything renders in UTC so server and client markup match.
  const tzOf = (venueTz: string) => (mounted ? tzFor(tzMode, venueTz) : "UTC");
  const changeTz = (m: TzMode) => {
    setTzMode(m);
    try { localStorage.setItem("nflcast.tz", m); } catch { /* ignore */ }
  };

  // Date range, day headings, day filters and kickoff times all use the selected mode: your time zone, UK time, or each
  // game's own stadium-local date. Days are ordered by their earliest kickoff.
  const dayOf = (g: WeekDoc["games"][number]) => dayKey(g.kickoff_utc, tzOf(g.venue_tz));
  const byKickoff = useMemo(() => [...doc.games].sort((a, b) => a.kickoff_utc.localeCompare(b.kickoff_utc)), [doc]);
  const days = Array.from(new Set(byKickoff.map(dayOf)));
  const teamsInWeek = useMemo(() => Array.from(new Set(doc.games.flatMap((g) => [g.away, g.home]))).sort(), [doc]);
  const shown = byKickoff.filter((g) => (day === "all" || dayOf(g) === day)
    && (team === "all" || g.home === team || g.away === team));
  const grouped = days.map((d) => ({ d, games: shown.filter((g) => dayOf(g) === d) })).filter((x) => x.games.length);
  const range = dateRange(byKickoff.map((g) => [g.kickoff_utc, tzOf(g.venue_tz)] as const));
  const changeMode = (m: TzMode) => { changeTz(m); setDay("all"); };
  const weeks = manifest.weeks.filter((w) => w.season === doc.season);
  const isLatest = manifest.latest.season === doc.season && manifest.latest.week === doc.week;
  const pv = doc.results?.groups?.publicly_verifiable_pregame;
  const hb = manifest.season_record?.stats_only?.band_history?.bands;
  const weekRec: WLP | null = pv && (pv.pick_graded ?? pv.graded)
    ? { win: pv.lean.win, loss: pv.lean.loss, push: pv.lean.push } : null;

  return (
    <>
      <header className="rail">
        <div className="rail-main">
          <div className="caps">{doc.season} · National Football League</div>
          <h1 className="rail-title">{isPlayoffWeek(doc.week) ? weekName(doc.week) : <>Week <span className="rail-num">{doc.week}</span></>}
            <span className="rail-sub"> forecasts</span></h1>
          <div className="caps rail-meta">{range && <>{range} · </>}{doc.n_games} games · {doc.last_release_at
            ? <>updated {fmtDateTime(doc.last_release_at, mounted && tzMode !== "stadium" ? tzFor(tzMode, "UTC") : "UTC")}</>
            : "forecasts publish Tuesday 18:00 UK"}</div>
        </div>
        <div className="rail-links">
          <a href={`${process.env.NEXT_PUBLIC_BASE_PATH ?? ""}/performance/`}>Model history</a>
          <label className="small ink2">
            Week{" "}
            <select className="select" value={`${doc.season}-${doc.week}`} onChange={(e) => {
              const [s, w] = e.target.value.split("-");
              window.location.href = `${process.env.NEXT_PUBLIC_BASE_PATH ?? ""}/week/${s}/${w}/`;
            }}>
              {weeks.map((w) => (
                <option key={w.week} value={`${w.season}-${w.week}`}>{weekName(w.week)}{w.has_forecasts ? "" : " (no forecasts)"}</option>
              ))}
            </select>
          </label>
        </div>
      </header>
      {manifest.season_record && manifest.season_record.weeks.length > 0 &&
        <Records r={manifest.season_record} week={weekRec} weekLabel={isLatest ? "this week" : weekName(doc.week)} />}

      <div className="controls" role="group" aria-label="Filters">
        <button className="chip" aria-pressed={day === "all"} onClick={() => setDay("all")}>All games</button>
        {days.map((d) => (
          <button key={d} className="chip" aria-pressed={day === d} onClick={() => setDay(d)}>{d.split(" ")[0]}</button>
        ))}
        <select className="select" aria-label="Team" value={team} onChange={(e) => setTeam(e.target.value)}>
          <option value="all">All teams</option>
          {teamsInWeek.map((t) => <option key={t} value={t}>{teams[t]?.name ?? t}</option>)}
        </select>
        <span className="spacer" />
        <select className="select" aria-label="Time zone" value={tzMode} onChange={(e) => changeMode(e.target.value as TzMode)}>
          <option value="local">Your time zone</option>
          <option value="london">UK time (Europe/London)</option>
          <option value="stadium">Stadium local time</option>
        </select>
      </div>

      {doc.results && <WeekResultsPanel r={doc.results} />}

      {grouped.map(({ d, games }) => (
        <section key={d}>
          <div className="day-head">{d}</div>
          <div className="grid">
            {games.map((g) => <GameCard key={g.game_id} g={g} teams={teams} tz={tzOf(g.venue_tz)} />)}
          </div>
        </section>
      ))}
      {grouped.length === 0 && <p className="muted">No games match these filters.</p>}
      <div id="pick-explainer" className="panel explainer">
        <h2 style={{ marginTop: 0 }}>How the model pick works</h2>
        {Array.from(new Set(doc.games.map((g) => g.locked_pick?.rule ?? "lock-24h"))).map((r) => (
          <p key={r} className="small ink2" style={{ marginBottom: 6 }}>{pickExplain(r)}</p>))}
        <p className="small muted" style={{ marginBottom: 0 }}>Gap records: the model line&apos;s side of the locked line in
          games where it was 3–4 points and 4 or more points from that line, shown separately, with a 95% range. Beside each, the
          rate for the same band in 2019–2025 (retrospective walk-forward forecasts against untimed, roughly closing, lines).
          {hb && <> In that history the 3–4 point band finished on the model line&apos;s side {pc0(hb["3-4"].all.rate ?? 0)} of the
          time (95% range {pc0(hb["3-4"].all.ci95?.[0] ?? 0)}–{pc0(hb["3-4"].all.ci95?.[1] ?? 0)}, {hb["3-4"].all.n} games) and
          the 4+ band {pc0(hb["4+"].all.rate ?? 0)} ({pc0(hb["4+"].all.ci95?.[0] ?? 0)}–{pc0(hb["4+"].all.ci95?.[1] ?? 0)},{" "}
          {hb["4+"].all.n} games): bigger gaps have not meant better results.</>} A few dozen 2026 games cannot show
          that either band is a signal. More detail, split by the size of the line, is on the Performance page.</p>
      </div>
      <p className="small muted" style={{ marginTop: 28 }}>
        Scores are expected values (means), not predicted final scores. Win probabilities include a small regular-season
        tie probability. Market spread and total are shown for context and, for the combined model, are model inputs.
        Every forecast is frozen with a timestamp before kickoff; results are scored against that frozen version.
      </p>
    </>
  );
}
