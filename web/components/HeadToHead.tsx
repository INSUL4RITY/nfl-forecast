import { LineChart, type Series } from "@/components/charts";

type WLP = { win: number; loss: number; push: number };
type Keyed = { combined: number; stats_only: number; market: number };
export interface H2HWeek {
  season: number; week: number; n: number; abs_error: Keyed; winner_called: Keyed; winner_correct: Keyed;
  vs_line: { lean: WLP; stats_only: WLP };
}

const MODELS: [keyof Keyed, string, string][] = [
  ["combined", "Model", "var(--series-1)"],
  ["stats_only", "Stats-only", "var(--series-3)"],
  ["market", "Market", "var(--series-2)"],
];

const BEST_TEXT: Record<keyof Keyed, string> =
  { combined: "the model line", stats_only: "the stats-only forecast", market: "the market line" };

const add = (a: H2HWeek, b: H2HWeek): H2HWeek => {
  const k = (x: Keyed, y: Keyed): Keyed => ({ combined: x.combined + y.combined, stats_only: x.stats_only + y.stats_only, market: x.market + y.market });
  const w = (x: WLP, y: WLP): WLP => ({ win: x.win + y.win, loss: x.loss + y.loss, push: x.push + y.push });
  return { season: b.season, week: b.week, n: a.n + b.n, abs_error: k(a.abs_error, b.abs_error),
    winner_called: k(a.winner_called, b.winner_called), winner_correct: k(a.winner_correct, b.winner_correct),
    vs_line: { lean: w(a.vs_line.lean, b.vs_line.lean), stats_only: w(a.vs_line.stats_only, b.vs_line.stats_only) } };
};
const mae = (r: H2HWeek, m: keyof Keyed) => (r.n ? (r.abs_error[m] / r.n).toFixed(2) : "—");
const wlp = (x: WLP) => (x.win + x.loss + x.push ? `${x.win}–${x.loss}${x.push ? `–${x.push}` : ""}` : "—");

/** Live 2026 head-to-head of the combined forecast, the stats-only forecast and the market line on the same finished games
 *  (publicly verifiable pregame forecasts only), by week and season to date. Display only. */
export default function HeadToHead({ weeks }: { weeks: H2HWeek[] }) {
  if (!weeks.length) return null;
  const total = weeks.reduce(add);
  const cum: H2HWeek[] = [];
  weeks.forEach((w, i) => cum.push(i ? add(cum[i - 1], w) : w));
  const series: Series[] = MODELS.map(([k, label, color]) => ({
    key: k, label, color, values: cum.map((c) => (c.n ? c.abs_error[k] / c.n : null)),
  }));
  const best = MODELS.map(([k]) => k).reduce((b, k) => (total.abs_error[k] < total.abs_error[b] ? k : b));
  return (
    <div className="panel">
      <h2>Live head-to-head, {weeks[0].season}</h2>
      <p className="small ink2">The three forecasts on the same finished games, using only forecasts that were publicly verifiable before
        kickoff. Margin error uses the last forecast before kickoff (the market forecast is the line&apos;s own margin); the
        record vs the market line uses the locked version of each pick. Lower margin error is better. So far the lowest
        season-to-date margin error is <b>{BEST_TEXT[best]}</b> ({mae(total, best)} points over {total.n} games):
        too few games to separate the forecasts with confidence.</p>
      <div className="table-wrap"><table>
        <thead>
          <tr><th rowSpan={2}>Week</th><th rowSpan={2} className="r">Games</th>
            <th colSpan={3} className="r">Average margin error (points)</th>
            <th colSpan={2} className="r">Vs market line</th></tr>
          <tr>{MODELS.map(([k, l]) => <th key={`e${k}`} className="r">{l}</th>)}
            <th className="r">Model pick</th><th className="r">Stats-only</th></tr>
        </thead>
        <tbody>
          {weeks.map((r) => (
            <tr key={r.week}><td>Week {r.week}</td><td className="r">{r.n}</td>
              {MODELS.map(([k]) => <td key={`e${k}`} className="r">{mae(r, k)}</td>)}
              <td className="r">{wlp(r.vs_line.lean)}</td><td className="r">{wlp(r.vs_line.stats_only)}</td></tr>
          ))}
          <tr className="hl"><td><b>Season to date</b></td><td className="r"><b>{total.n}</b></td>
            {MODELS.map(([k]) => <td key={`e${k}`} className="r"><b>{mae(total, k)}</b></td>)}
            <td className="r"><b>{wlp(total.vs_line.lean)}</b></td><td className="r"><b>{wlp(total.vs_line.stats_only)}</b></td></tr>
        </tbody>
      </table></div>
      {cum.length > 1 && (
        <div style={{ marginTop: 14 }}>
          <h3 style={{ margin: "0 0 4px" }}>Cumulative average margin error</h3>
          <LineChart series={series} xLabels={cum.map((c) => `Week ${c.week}`)} xTickIdx={cum.map((_, i) => i)} yDecimals={2}
            yTitle="Cumulative average margin error (points)" />
        </div>
      )}
      <p className="small muted" style={{ marginBottom: 0 }}>Record vs market line: wins–losses–level results for the model pick and for the side of the locked line where the
        stats-only margin fell (a tracking record, not the official model pick). The market line has no record against itself.</p>
    </div>
  );
}
