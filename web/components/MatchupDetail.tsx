"use client";
import { useState } from "react";
import type { MatchupDetail as Detail, MatchupLogRow, MatchupTeam, MatchupUnitRow } from "@/lib/types";
import { weekName, weekShort } from "@/lib/format";

const MINUS = "−";
const sgn = (x: number | null | undefined, d = 2) =>
  x == null ? "—" : `${x > 0 ? "+" : x < 0 ? MINUS : ""}${Math.abs(x).toFixed(d)}`;
const pc = (x: number | null | undefined, d = 1) => (x == null ? "—" : `${(100 * x).toFixed(d)}%`);
const ord = (n: number) => `#${n}`;

function unitValue(key: string, v: number | null) {
  if (key === "passing" || key === "rushing") return sgn(v);
  if (key === "ppd") return v == null ? "—" : v.toFixed(2);
  return pc(v);
}

/** Bar length from a rank: rank 1 fills the track, the last rank shows a sliver. */
const rankWidth = (rank: number | null, n: number) => (rank == null ? 0 : Math.max(4, ((n + 1 - rank) / n) * 100));

function TeamCard({ t, side, color, name, n }: { t: MatchupTeam; side: "away" | "home"; color: string; name: string; n: number }) {
  const [w, l, ti] = t.record;
  const trend = t.last3_net_epa == null ? null : t.last3_net_epa - t.net_epa;
  const others = t.qb_starts.filter((q) => q.qb !== t.expected_qb).reduce((s, q) => s + q.games, 0);
  const expStarts = t.qb_starts.find((q) => q.qb === t.expected_qb)?.games ?? 0;
  return (
    <div className="mu-card" style={{ borderTopColor: color }}>
      <div className="mu-card-head">
        <span className="mu-chip" style={{ background: color }}>{t.team}</span>
        <div>
          <b>{name}</b>
          <span className="small muted">{side === "away" ? "Away" : "Home"} · {w}–{l}{ti ? `–${ti}` : ""} · {t.games} game{t.games === 1 ? "" : "s"}</span>
        </div>
      </div>
      <span className="caps">Net EPA per play</span>
      <div className="mu-big" style={{ color }}>{sgn(t.net_epa)}<span className="mu-rank">{ord(t.ranks.net_epa)} of {n}</span></div>
      <span className="small ink2">Opponent-adjusted {sgn(t.adj_net_epa)} ({ord(t.ranks.adj_net_epa)})
        {trend != null && <> · last 3 games {sgn(t.last3_net_epa)}{" "}
          <span className={Math.abs(trend) < 0.05 ? "muted" : trend > 0 ? "mu-up" : "mu-down"}>
            {Math.abs(trend) < 0.05 ? "≈ season" : trend > 0 ? "▲ rising" : "▼ falling"}</span></>}</span>
      <dl className="mu-mini">
        <div><dt>Offence EPA</dt><dd>{sgn(t.off_epa)}</dd><span>{ord(t.ranks.off_epa)}</span></div>
        <div><dt>Defence EPA allowed</dt><dd>{sgn(t.def_epa)}</dd><span>{ord(t.ranks.def_epa)}</span></div>
        <div><dt>Points per drive</dt><dd>{t.ppd.toFixed(2)}</dd><span>{ord(t.ranks.ppd)}</span></div>
      </dl>
      <p className="small mu-qb">
        <span className="muted">QB starts: </span>{t.qb_starts.map((q, i) => <span key={q.qb}>{i ? ", " : ""}{q.qb} ({q.games})</span>)}
        {t.expected_qb && others > 0 && <><br /><span className="mu-warn">{others} of {t.games} games started by a QB other than
          this week&apos;s expected starter ({t.expected_qb}{expStarts ? `, ${expStarts} start${expStarts === 1 ? "" : "s"}` : ", no starts yet"}).
          {others > t.games / 2 && t.qb_starts[0] && t.qb_starts[0].qb !== t.expected_qb
            ? ` Most of these numbers come from ${t.qb_starts[0].qb}.` : ""}</span></>}
      </p>
    </div>
  );
}

function UnitRows({ rows, off, def, offColor, defColor, n }: { rows: MatchupUnitRow[]; off: string; def: string;
  offColor: string; defColor: string; n: number }) {
  return (
    <div className="mu-units" role="list">
      {rows.map((r) => (
        <div className="mu-unit" role="listitem" key={r.key}>
          <div className="mu-unit-label"><b>{r.label}</b><span className="small muted">{r.unit}</span></div>
          <div className="mu-unit-bars">
            {([["off", off, offColor, r.off_value, r.off_rank], ["def", def, defColor, r.def_value, r.def_rank]] as const).map(
              ([k, team, color, v, rank]) => (
                <div className="mu-bar-row" key={k}>
                  <span className="mu-bar-team small">{team} {k === "off" ? "offence" : "defence"}</span>
                  <span className="mu-track" aria-hidden="true"><span style={{ width: `${rankWidth(rank, n)}%`, background: color }} /></span>
                  <span className="mu-rank-sm">{rank ? ord(rank) : "—"}</span>
                  <span className="mu-val">{unitValue(r.key, v)}</span>
                </div>))}
          </div>
          <span className={`mu-edge ${r.edge}`} style={r.edge === "offence" ? { borderColor: offColor }
            : r.edge === "defence" ? { borderColor: defColor } : undefined}>
            {r.edge === "offence" ? `${off} edge` : r.edge === "defence" ? `${def} edge` : r.edge === "even" ? "Even" : "—"}</span>
        </div>
      ))}
    </div>
  );
}

function LogColumn({ t, rows, color, metric, max }: { t: string; rows: MatchupLogRow[]; color: string; metric: "epa" | "margin"; max: number }) {
  return (
    <div className="mu-log-col">
      <div className="mu-log-head"><span className="mu-chip" style={{ background: color }}>{t}</span></div>
      {rows.map((r) => {
        const v = metric === "epa" ? r.net_epa : r.margin;
        const w = Math.min(50, (Math.abs(v) / max) * 50);
        return (
          <div className="mu-log-row" key={r.week}>
            <span className="mu-log-game"><b>{weekShort(r.week)}</b> {r.home ? "vs" : "@"} {r.opp}
              <span className="small muted mu-log-qb">{r.qb ?? "QB unknown"}{r.other_qb && <span className="tag warn mu-tag">Other QB</span>}</span></span>
            <span className="mu-div" aria-hidden="true">
              <span style={{ background: color, width: `${w}%`, left: v >= 0 ? "50%" : `${50 - w}%`, opacity: v >= 0 ? 1 : 0.55 }} />
            </span>
            <span className="mu-val">{metric === "epa" ? sgn(v) : `${v > 0 ? "+" : v < 0 ? MINUS : ""}${Math.abs(v)}`}
              {metric === "margin" && <span className="small muted"> {r.pf}–{r.pa}</span>}</span>
          </div>);
      })}
    </div>
  );
}

/** The matchup section of a game page: season-to-date unit statistics of both teams as of kickoff, in each team's
 *  colour (display only; predict/matchup.py). */
export default function MatchupDetail({ d, home, away, homeColor, awayColor, homeName, awayName }:
  { d: Detail; home: string; away: string; homeColor: string; awayColor: string; homeName?: string; awayName?: string }) {
  const [poss, setPoss] = useState<"away" | "home">("away");
  const [metric, setMetric] = useState<"epa" | "margin">("epa");
  if (!d.available || !d.teams || !d.units || !d.log || !d.league) {
    return (
      <div className="panel"><h2 style={{ marginTop: 0 }}>The matchup</h2>
        <p className="small muted" style={{ margin: 0 }}>No games before this one yet this season, so there are no season numbers to compare.</p></div>);
  }
  const T = d.teams, n = d.n_teams, L = d.league;
  const weeks = [...d.log.away, ...d.log.home].map((r) => r.week);
  const through = weeks.length ? Math.max(...weeks) : 0;
  const offSide = poss, defSide = poss === "away" ? "home" : "away";
  const col = { home: homeColor, away: awayColor }, nm = { home: homeName ?? home, away: awayName ?? away };
  const ab = { home, away };
  const rows = poss === "away" ? d.units.away_offence : d.units.home_offence;
  const all = [...d.log.away, ...d.log.home];
  const max = Math.max(metric === "epa" ? 0.3 : 10, ...all.map((r) => Math.abs(metric === "epa" ? r.net_epa : r.margin)));
  const tempoScale = (s: number) => Math.min(100, Math.max(0, ((s - 25) / 15) * 100));     // 25 s (fast) to 40 s (slow)
  return (
    <section className="panel mu" aria-labelledby="mu-title">
      <div className="mu-head">
        <div>
          <span className="caps">Season to date before kickoff · through {weekName(through).replace(/^Week/, "week")} · ranks out of {n} (1 = best)</span>
          <h2 id="mu-title" style={{ margin: "4px 0 0" }}>The matchup</h2>
        </div>
        <p className="small ink2" style={{ margin: 0 }}>Efficiency on both sides of the ball. EPA (expected points added) measures how much
          each play changed the points a team could expect to score; a defence&apos;s EPA allowed is better when lower.</p>
      </div>

      <div className="mu-cards">
        <TeamCard t={T.away} side="away" color={awayColor} name={nm.away} n={n} />
        <TeamCard t={T.home} side="home" color={homeColor} name={nm.home} n={n} />
      </div>

      <h3 className="mu-sub">Unit against unit</h3>
      <div className="mu-tabs" role="group" aria-label="Which team has the ball">
        {(["away", "home"] as const).map((s) => (
          <button key={s} className="mu-tab" aria-pressed={poss === s} onClick={() => setPoss(s)}
            style={poss === s ? { borderBottomColor: col[s] } : undefined}>
            <i className="swatch" style={{ background: col[s] }} />{ab[s]} has the ball</button>))}
      </div>
      <p className="small ink2" style={{ margin: "10px 0 4px" }}><b>{ab[offSide]} offence</b> against <b>{ab[defSide]} defence</b>.
        Longer bars mean a better league rank; the edge label appears when one side ranks at least 8 places better.</p>
      <UnitRows rows={rows} off={ab[offSide]} def={ab[defSide]} offColor={col[offSide]} defColor={col[defSide]} n={n} />

      <h3 className="mu-sub">How they play</h3>
      <div className="mu-style">
        <div>
          <b className="small">Pass rate in neutral situations</b>
          <span className="small muted">Share of snaps that were dropbacks while the game was still balanced</span>
          {(["away", "home"] as const).map((s) => (
            <div className="mu-split" key={s}>
              <span className="mu-split-team small">{ab[s]}</span>
              <span className="mu-split-bar" aria-hidden="true"><span style={{ width: pc(T[s].neutral_db, 2), background: col[s] }} />
                <i style={{ left: pc(L.neutral_db ?? null, 2) }} /></span>
              <span className="mu-val">{pc(T[s].neutral_db)}</span>
            </div>))}
          <span className="small muted">Line marks the NFL average ({pc(L.neutral_db ?? null)}). The rest of the bar is designed runs.</span>
        </div>
        <div>
          <b className="small">Tempo in neutral situations</b>
          <span className="small muted">Seconds between snaps when the clock keeps running; lower is faster</span>
          {(["away", "home"] as const).map((s) => (
            <div className="mu-split" key={s}>
              <span className="mu-split-team small">{ab[s]}</span>
              <span className="mu-tempo" aria-hidden="true"><i style={{ left: `${tempoScale(L.tempo ?? 33)}%` }} />
                <b style={{ left: `${tempoScale(T[s].tempo ?? 33)}%`, background: col[s] }} /></span>
              <span className="mu-val">{T[s].tempo == null ? "—" : `${T[s].tempo!.toFixed(1)} s`}</span>
            </div>))}
          <span className="small muted">Faster ← → slower. Line marks the NFL average ({L.tempo == null ? "—" : `${L.tempo.toFixed(1)} s`}).
            Style describes pace, not quality.</span>
        </div>
      </div>

      <div className="mu-log-head-row">
        <h3 className="mu-sub" style={{ margin: 0 }}>Game by game</h3>
        <div className="mu-tabs compact" role="group" aria-label="Measure">
          <button className="mu-tab" aria-pressed={metric === "epa"} onClick={() => setMetric("epa")}>Net EPA</button>
          <button className="mu-tab" aria-pressed={metric === "margin"} onClick={() => setMetric("margin")}>Score margin</button>
        </div>
      </div>
      <div className="mu-log">
        <LogColumn t={away} rows={d.log.away} color={awayColor} metric={metric} max={max} />
        <LogColumn t={home} rows={d.log.home} color={homeColor} metric={metric} max={max} />
      </div>
      <p className="small muted" style={{ marginBottom: 0 }}>Each row is one game with its starting quarterback. &quot;Other QB&quot; marks games
        started by someone other than this week&apos;s expected starter, so the season numbers above include those games.</p>

      <details className="mu-defs">
        <summary className="small">Definitions and data</summary>
        <p className="small ink2">Regular-season games completed before this game&apos;s kickoff; not the model&apos;s inputs (the model line
          uses its own recency-weighted ratings). Plays: dropbacks (including sacks and scrambles) and designed runs; kneels, spikes,
          penalty no-plays and two-point tries excluded. <b>Passing</b>: EPA per dropback. <b>Rushing</b>: EPA per designed run.
          <b> Play success</b>: share of plays with positive EPA. <b>Explosive</b>: pass attempts gaining 20+ yards or runs (scrambles
          included) gaining 10+. <b>Sack rate</b>: sacks per dropback (fewer is better for an offence, more for a defence).
          <b> Third down</b>: share of third-down plays converted by a run or pass (first downs by penalty don&apos;t count).
          <b> Red zone</b>: drives reaching the opponent&apos;s 20 that ended in a touchdown. <b>Points per drive</b>: touchdowns,
          conversions and field goals per drive with at least one snap. <b>Neutral situations</b>: 1st or 2nd down, quarters 1–3,
          win probability 20–80%. <b>Tempo</b>: game-clock seconds since the previous snap of the same drive, only after plays that
          kept the clock running. <b>Opponent-adjusted</b>: EPA corrected for how good the defences (and offences) a team has faced
          are, relative to the league. Ranks compare all {n} teams that have played; ties share a rank. Data: nflverse play-by-play.
          These numbers describe performance so far; they are not win probabilities.</p>
      </details>
    </section>
  );
}
