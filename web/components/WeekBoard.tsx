"use client";
import { useEffect, useMemo, useState } from "react";
import type { Manifest, Team, WeekDoc } from "@/lib/types";
import { dateRange, dayKey, fmtDateTime, tzFor, type TzMode } from "@/lib/format";
import GameCard from "./GameCard";

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

  return (
    <>
      <div className="page-head">
        <div>
          <div className="small muted" style={{ fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase" }}>
            {doc.season} season · week {doc.week}
          </div>
          <h1>Weekly projections</h1>
          <div className="meta-line">
            {range && <>{range} · </>}<b>{doc.n_games}</b> games ·{" "}
            {doc.last_release_at ? <>last model update <b>{fmtDateTime(doc.last_release_at, mounted && tzMode !== "stadium" ? tzFor(tzMode, "UTC") : "UTC")}</b></> : "no release yet"}
          </div>
        </div>
        <label className="small ink2">
          Week{" "}
          <select className="select" value={`${doc.season}-${doc.week}`} onChange={(e) => {
            const [s, w] = e.target.value.split("-");
            window.location.href = `${process.env.NEXT_PUBLIC_BASE_PATH ?? ""}/week/${s}/${w}/`;
          }}>
            {weeks.map((w) => (
              <option key={w.week} value={`${w.season}-${w.week}`}>Week {w.week}{w.has_forecasts ? "" : " (no forecasts)"}</option>
            ))}
          </select>
        </label>
      </div>

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

      {grouped.map(({ d, games }) => (
        <section key={d}>
          <div className="day-head">{d}</div>
          <div className="grid">
            {games.map((g) => <GameCard key={g.game_id} g={g} teams={teams} tz={tzOf(g.venue_tz)} />)}
          </div>
        </section>
      ))}
      {grouped.length === 0 && <p className="muted">No games match these filters.</p>}
      <p className="small muted" style={{ marginTop: 28 }}>
        Scores are expected values (means), not predicted final scores. Win probabilities include a small regular-season
        tie probability. Market spread and total are shown for context and, for the combined model, are model inputs.
        Every forecast is frozen with a timestamp before kickoff; results are scored against that frozen version.
      </p>
    </>
  );
}
