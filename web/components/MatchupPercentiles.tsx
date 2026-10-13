import type { Matchup } from "@/lib/types";

const GROUPS: [string, string][] = [["offence", "Offence"], ["defence", "Defence"], ["quarterback", "Quarterback"]];
const ord = (n: number) => `${n}${n % 10 === 1 && n % 100 !== 11 ? "st" : n % 10 === 2 && n % 100 !== 12 ? "nd" : n % 10 === 3 && n % 100 !== 13 ? "rd" : "th"}`;

/** How the two teams rate on each measure: percentile (100 = best) among all teams in the same forecast release, as a
 *  dumbbell per measure with one dot per team in its identity colour. Display only (export_web.matchup_percentiles). */
export default function MatchupPercentiles({ m, home, away, homeColor, awayColor, homeName, awayName }:
  { m: Matchup; home: string; away: string; homeColor: string; awayColor: string; homeName?: string; awayName?: string }) {
  return (
    <div className="panel">
      <h2 style={{ marginTop: 0 }}>How they rate</h2>
      <p className="small ink2" style={{ marginTop: 0 }}>Percentile among the {m.n_teams} teams in this forecast: 100 is the best in that
        measure, 50 is average. Defence measures are turned round so that higher is always better.</p>
      <div className="mp-legend">
        <span><i className="swatch" style={{ background: awayColor }} />{awayName ?? away} ({away})</span>
        <span><i className="swatch" style={{ background: homeColor }} />{homeName ?? home} ({home})</span>
      </div>
      {GROUPS.map(([g, title]) => {
        const rows = m.metrics.filter((x) => x.group === g);
        if (!rows.length) return null;
        return (
          <div key={g} className="mp-group">
            <h3 className="caps" style={{ margin: "14px 0 6px" }}>{title}</h3>
            {rows.map((x) => {
              const a = Math.round(x.away), h = Math.round(x.home);
              const lo = Math.min(a, h), hi = Math.max(a, h);
              return (
                <div key={x.key} className="mp-row">
                  <span className="ink2 mp-label">{x.label}</span>
                  <span className="mp-track" aria-hidden="true">
                    <span className="mp-mid" />
                    <span className="mp-span" style={{ left: `${lo}%`, width: `${hi - lo}%` }} />
                    <span className="mp-dot" style={{ left: `${a}%`, background: awayColor }} title={`${away}: ${ord(a)} percentile`} />
                    <span className="mp-dot" style={{ left: `${h}%`, background: homeColor }} title={`${home}: ${ord(h)} percentile`} />
                  </span>
                  <span className="mp-vals">
                    <span className="sr-only">{x.label}: {away} {ord(a)} percentile, {home} {ord(h)} percentile</span>
                    <span aria-hidden="true"><i className="swatch" style={{ background: awayColor }} />{a}</span>
                    <span aria-hidden="true"><i className="swatch" style={{ background: homeColor }} />{h}</span>
                  </span>
                </div>
              );
            })}
          </div>
        );
      })}
      <div className="mp-row mp-axis" aria-hidden="true"><span /><span><span>0 worst</span><span>50</span><span>100 best</span></span><span /></div>
      <p className="small muted" style={{ marginBottom: 0 }}>Per-play efficiency entering the game (EPA = expected points added), weighted
        towards recent games and, early in the season, still partly last season. These are the same football inputs the stats-only
        line is built from. Display only.</p>
    </div>
  );
}
