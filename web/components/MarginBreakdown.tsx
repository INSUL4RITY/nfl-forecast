import type { ReleaseEntry } from "@/lib/types";

type Breakdown = NonNullable<ReleaseEntry["football_breakdown"]>;

const MIN_SHOWN = 0.05;

/** Where the stats-only (football-only) projected margin comes from: one bar per group, pointing toward the team it
 *  favours (away left, home right). The groups add up exactly to the stats-only margin (predict/breakdown.py). */
export default function MarginBreakdown({ b, home, away, homeColor, awayColor }:
  { b: Breakdown; home: string; away: string; homeColor: string; awayColor: string }) {
  const shown = b.groups.filter((x) => Math.abs(x.margin_points) >= MIN_SHOWN)
    .sort((x, y) => Math.abs(y.margin_points) - Math.abs(x.margin_points));
  const hidden = b.groups.length - shown.length;
  const max = Math.max(...shown.map((x) => Math.abs(x.margin_points)), 0.1);
  const lead = Math.abs(b.margin) < 0.05 ? "even" : `${b.margin > 0 ? home : away} by ${Math.abs(b.margin).toFixed(1)}`;
  return (
    <div className="panel">
      <h2 style={{ marginTop: 0 }}>Where the stats-only margin comes from</h2>
      <div style={{ display: "flex", flexDirection: "column", gap: 8, maxWidth: 760 }} role="list">
        <div className="mbar-ends" aria-hidden="true"><span /><span><span>← {away}</span><span>{home} →</span></span><span /></div>
        {shown.map((x) => {
          const v = x.margin_points, team = v > 0 ? home : away, w = (Math.abs(v) / max) * 50;
          const text = `${team} ${Math.abs(v).toFixed(1)}`;
          return (
            <div className="mbar-row" key={x.group} role="listitem" title={`${x.label}: ${Math.abs(v).toFixed(2)} pts toward ${team}`}>
              <span className="ink2">{x.label}</span>
              <span className="mbar-track" aria-hidden="true">
                <span className="mbar" style={{ background: v > 0 ? homeColor : awayColor, width: `${w}%`,
                  left: v > 0 ? "50%" : `${50 - w}%` }} />
              </span>
              <span className="r" style={{ fontVariantNumeric: "tabular-nums", fontWeight: 700 }}>
                <span className="sr-only">{x.label}: </span>{text}</span>
            </div>
          );
        })}
      </div>
      <p className="small muted" style={{ marginTop: 14, marginBottom: 0 }}>
        Points each group adds to the stats-only projection (the football-only model, which uses no market line), pointing toward
        the team it favours. They add up to the stats-only line: {lead}.{hidden ? ` ${hidden === 1 ? "One group" : `${hidden} groups`} under 0.05 points not shown.` : ""}{" "}
        The groups overlap (a team that passes well also tends to score well), so read them together; this describes the fitted
        model, not football cause and effect. The published model line starts from the market line and is not split this way.
      </p>
    </div>
  );
}
