import type { ReleaseEntry } from "@/lib/types";

type Breakdown = NonNullable<ReleaseEntry["football_breakdown"]>;

const MIN_SHOWN = 0.05;

const lineText = (m: number, home: string, away: string) =>
  Math.abs(m) < 0.05 ? "Even" : m > 0 ? `${home} −${m.toFixed(1)}` : `${away} −${(-m).toFixed(1)}`;

/** The model line in whole tenths of a point, rounded half away from zero (as `lineText` shows it). */
const tenths = (m: number) => Math.sign(m) * Math.round(Math.abs(m) * 10);

/** Each shown group's value in tenths of a point, rounded so that the parts add up exactly to the model line as
 *  displayed (largest-remainder rounding, as when percentages are made to sum to 100). Groups too small to show count
 *  as 0; the parts whose rounding moved them furthest the other way give up or gain the missing tenths. */
export function roundedParts(values: number[], margin: number): number[] {
  const x = values.map((v) => v * 10);
  const r = x.map((v) => Math.sign(v) * Math.round(Math.abs(v)));
  let diff = tenths(margin) - r.reduce((a, b) => a + b, 0);
  while (diff !== 0 && r.length) {
    const step = diff > 0 ? 1 : -1;
    const cand = r.map((_, j) => j).filter((j) => r[j] + step !== 0);   // never round a shown part to zero
    const pool = cand.length ? cand : r.map((_, j) => j);
    const i = pool.reduce((best, j) => ((x[j] - r[j]) * step > (x[best] - r[best]) * step ? j : best), pool[0]);
    r[i] += step;
    diff -= step;
  }
  return r;
}

function Bar({ v, max, homeColor, awayColor, net }: { v: number; max: number; homeColor: string; awayColor: string; net?: boolean }) {
  const w = (Math.abs(v) / max) * 50;
  const right = v > 0;
  return (
    <span className={`mbar-track${net ? " net" : ""}`} aria-hidden="true">
      <span className={`mbar ${right ? "to-home" : "to-away"}`}
        style={{ background: right ? homeColor : awayColor, width: `${w}%`, left: right ? "50%" : `${50 - w}%` }} />
    </span>
  );
}

/** Where the stats-only (football-only) projected margin comes from: one bar per group in the colour of the team it
 *  favours (away left, home right), then the total, which equals the stats-only line (predict/breakdown.py). */
export default function MarginBreakdown({ b, home, away, homeColor, awayColor, homeName, awayName }:
  { b: Breakdown; home: string; away: string; homeColor: string; awayColor: string; homeName?: string; awayName?: string }) {
  const shown = b.groups.filter((x) => Math.abs(x.margin_points) >= MIN_SHOWN)
    .sort((x, y) => Math.abs(y.margin_points) - Math.abs(x.margin_points));
  const hidden = b.groups.length - shown.length;
  const max = Math.max(...shown.map((x) => Math.abs(x.margin_points)), Math.abs(b.margin), 0.5);

  // displayed values (tenths) that add up exactly to the displayed model line; bar lengths use the exact values
  const parts = roundedParts(shown.map((x) => x.margin_points), b.margin);
  const net = tenths(b.margin);
  const toHome = parts.filter((p) => p > 0).reduce((t, p) => t + p, 0) / 10;
  const toAway = -parts.filter((p) => p < 0).reduce((t, p) => t + p, 0) / 10;
  const val = (t: number) => {
    const team = t > 0 ? home : away;
    return <><i className="swatch" style={{ background: t > 0 ? homeColor : awayColor }} />{team} +{(Math.abs(t) / 10).toFixed(1)}</>;
  };
  return (
    <div className="panel">
      <div className="mb-head">
        <div>
          <h2 style={{ margin: 0 }}>Where the model line comes from</h2>
          <p className="small ink2" style={{ margin: "4px 0 0" }}>Points each part of the football data adds, in the colour of the team it favours.</p>
        </div>
        <div className="mb-result">
          <span className="caps">Model line</span>
          <b>{lineText(net / 10, home, away)}</b>
        </div>
      </div>
      <div className="mb-totals">
        <span><i className="swatch" style={{ background: awayColor }} /><b>{awayName ?? away}</b> +{toAway.toFixed(1)} pts</span>
        <span><b>{homeName ?? home}</b> +{toHome.toFixed(1)} pts<i className="swatch" style={{ background: homeColor }} /></span>
      </div>
      <div className="mb-rows" role="list">
        <div className="mbar-ends" aria-hidden="true"><span /><span><span>← {away}</span><span>{home} →</span></span><span /></div>
        {shown.map((x, i) => (
          <div className="mbar-row" key={x.group} role="listitem"
            title={`${x.label}: ${Math.abs(x.margin_points).toFixed(2)} pts toward ${x.margin_points > 0 ? home : away}`}>
            <span className="ink2">{x.label}</span>
            <Bar v={x.margin_points} max={max} homeColor={homeColor} awayColor={awayColor} />
            <span className="mb-val"><span className="sr-only">{x.label}: </span>{val(parts[i])}</span>
          </div>
        ))}
        <div className="mbar-row mbar-net" role="listitem">
          <span>Total = model line</span>
          <Bar v={b.margin} max={max} homeColor={homeColor} awayColor={awayColor} net />
          <span className="mb-val">{net === 0 ? "Even" : val(net)}</span>
        </div>
        <div className="mbar-ends mbar-axis" aria-hidden="true"><span />
          <span><span>{max.toFixed(1)} pts</span><span>0</span><span>{max.toFixed(1)} pts</span></span><span /></div>
      </div>
      <p className="small muted" style={{ marginTop: 14, marginBottom: 0 }}>
        From the model line (stats only), which uses no market input. Each bar points toward the team that part of the data
        favours; together they add up to the model line.{hidden ? ` ${hidden === 1 ? "One group" : `${hidden} groups`} under 0.05 points not shown.` : ""} Values are rounded to the nearest 0.1 so that
        they add up to the model line.{" "}
        The groups overlap (a team that passes well also tends to score well), so read them together; this describes the fitted
        model, not football cause and effect. The market-adjusted line is built from the market line and is not split this way.
      </p>
    </div>
  );
}
