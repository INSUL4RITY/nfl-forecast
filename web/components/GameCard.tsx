import Link from "next/link";
import type { LineupSide, Team, WeekGame } from "@/lib/types";
import { f1, fmtDateTime, fmtKickoff, marginText, pct, pctP, spreadText, STATE_LABEL } from "@/lib/format";
import TeamBadge from "./TeamBadge";

function ProbBar({ pAway, pTie, pHome, away, home, awayColor, homeColor }: {
  pAway: number; pTie: number; pHome: number; away: string; home: string; awayColor: string; homeColor: string;
}) {
  return (
    <div>
      <div className="probbar" role="img" aria-label={`${away} ${pct(pAway)}, tie ${pct(pTie, 1)}, ${home} ${pct(pHome)}`}>
        <span style={{ width: `${pAway * 100}%`, background: awayColor }} />
        {pTie > 0.0005 && <span style={{ width: `${Math.max(pTie * 100, 0.6)}%`, background: "#9aa3b2" }} />}
        <span style={{ width: `${pHome * 100}%`, background: homeColor }} />
      </div>
      <div className="prob-labels num">
        <span>{away} {pct(pAway)}</span>
        {pTie > 0 && <span>Tie {pct(pTie, 1)}</span>}
        <span>{home} {pct(pHome)}</span>
      </div>
    </div>
  );
}

export default function GameCard({ g, teams, tz }: { g: WeekGame; teams: Record<string, Team>; tz?: string }) {
  const e = g.forecast;
  const f = e?.forecast;
  const home = teams[g.home], away = teams[g.away];
  const final = g.status === "final" && g.score;
  const rows = [
    { side: "away" as const, abbr: g.away, t: away, rec: e?.away_record, pts: f?.away_pts, fin: g.score?.away },
    { side: "home" as const, abbr: g.home, t: home, rec: e?.home_record, pts: f?.home_pts, fin: g.score?.home },
  ];
  return (
    <article className="card">
      <div className="card-top">
        <span className="num">{fmtKickoff(g.kickoff_utc, tz, g.kickoff_time_known)}</span>
        <span>{g.neutral_site ? "Neutral · " : ""}{g.stadium}</span>
      </div>
      {rows.map((r) => (
        <div className="team-row" key={r.side}>
          <TeamBadge team={r.t} abbr={r.abbr} />
          <div>
            <span className="team-name">{r.t?.nick ?? r.abbr}</span>
            {r.rec && <span className="team-rec">{r.rec}</span>}
            {g.neutral_site ? null : r.side === "home" ? <span className="team-rec">home</span> : null}
          </div>
          <div style={{ textAlign: "right" }}>
            {final ? (
              <>
                <div className="score">{r.fin}</div>
                {f && <div className="small muted num">proj {f1(r.pts)}</div>}
              </>
            ) : (
              <div className="score">{f ? f1(r.pts) : "–"}</div>
            )}
          </div>
        </div>
      ))}
      {f && e ? (
        <>
          <ProbBar pAway={f.p_away} pTie={f.p_tie} pHome={f.p_home} away={g.away} home={g.home}
                   awayColor={away?.color ?? "#555"} homeColor={home?.color ?? "#13213c"} />
          <dl className="kv" style={{ margin: 0 }}>
            <div><dt>Projected winner</dt><dd className="v" style={{ margin: 0 }}>{f.p_home >= f.p_away ? g.home : g.away} {pct(Math.max(f.p_home, f.p_away))}</dd></div>
            <div><dt>Margin</dt><dd className="v" style={{ margin: 0 }}>{marginText(f.margin, g.home, g.away)}</dd></div>
            <div><dt>Total</dt><dd className="v" style={{ margin: 0 }}>{f1(f.total)}</dd></div>
            <div><dt>80% margin range</dt><dd className="v" style={{ margin: 0 }}>{rangeText(f.intervals.margin_80, g.home, g.away)}</dd></div>
            <div><dt>Market line</dt><dd className="v" style={{ margin: 0 }}>{e.market ? spreadText(e.market.home_spread, g.home, g.away) : "none"}</dd></div>
            <div><dt>Market total</dt><dd className="v" style={{ margin: 0 }}>{e.market ? f1(e.market.total) : "—"}</dd></div>
          </dl>
          <div className="small ink2">
            QBs: {qbText(e.lineup.away)} / {qbText(e.lineup.home)}
          </div>
          <div className="tags">
            {e.market_inputs_used
              ? <span className="tag info" title="The combined model uses the market spread and total as inputs">Uses market spread &amp; total</span>
              : e.status === "fallback_after_validation_failure"
                ? <span className="tag warn">Football-only fallback (combined forecast failed validation)</span>
                : <span className="tag warn">Football-only fallback (no line)</span>}
            {e.lineup_uncertain && <span className="tag warn">Lineup uncertain</span>}
            {g.forecast_verification === "generated_pregame_published_after_kickoff" &&
              <span className="tag warn" title="See the correction on the game page">Published after kickoff</span>}
          </div>
        </>
      ) : (
        <div className="pending">
          {g.forecast_state === "not_archived"
            ? "No valid pregame forecast was archived for this game."
            : "Forecast pending: it will appear once a validated release covering this game is published."}
        </div>
      )}
      <div className="card-foot">
        <span>{e ? `${STATE_LABEL[g.forecast_state] ?? g.forecast_state} · generated ${fmtDateTime(g.forecast_generated_at, tz)}` : " "}</span>
        <Link href={`/game/${g.game_id}/`}>Details →</Link>
      </div>
    </article>
  );
}

function qbText(side: LineupSide): string {
  const lead = side.scenarios?.[0];
  if (!lead) return side.expected_qb ?? "unknown";
  return `${lead.qb ?? "unknown"} ${pctP(lead.p)}`;
}

function rangeText(r: [number, number] | undefined, home: string, away: string): string {
  if (!r) return "—";
  const s = (x: number) => (Math.abs(x) < 0.5 ? "even" : x > 0 ? `${home} by ${Math.round(x)}` : `${away} by ${Math.round(-x)}`);
  return `${s(r[0])} to ${s(r[1])}`;
}
