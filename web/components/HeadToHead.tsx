import { LineChart, type Series } from "@/components/charts";
import { weekName } from "@/lib/format";

type WLP = { win: number; loss: number; push: number };
type Keyed = { combined: number; stats_only: number; market: number };
export interface H2HWeek {
  season: number; week: number; n: number; abs_error: Keyed; winner_called: Keyed; winner_correct: Keyed;
  vs_line: { lean: WLP; stats_only: WLP; market_adjusted?: WLP; injury_adjusted?: WLP; v2_trial?: WLP };
  inj?: { n: number; abs_error: { stats_inj: number; stats_only: number; market: number } };
  v2?: { n: number; abs_error: { stats_v2: number; stats_only: number; market: number } };
}

const MODELS: [keyof Keyed, string, string][] = [
  ["stats_only", "Model (stats only)", "var(--series-3)"],
  ["combined", "Market-adjusted", "var(--series-1)"],
  ["market", "Market", "var(--series-2)"],
];

const BEST_TEXT: Record<keyof Keyed, string> =
  { combined: "the market-adjusted line", stats_only: "the model line (stats only)", market: "the market line" };

const Z: WLP = { win: 0, loss: 0, push: 0 };
type Inj = NonNullable<H2HWeek["inj"]>;
const addInj = (x?: Inj, y?: Inj): Inj => {
  const e = (k: keyof Inj["abs_error"]) => (x?.abs_error[k] ?? 0) + (y?.abs_error[k] ?? 0);
  return { n: (x?.n ?? 0) + (y?.n ?? 0), abs_error: { stats_inj: e("stats_inj"), stats_only: e("stats_only"), market: e("market") } };
};
type V2 = NonNullable<H2HWeek["v2"]>;
const addV2 = (x?: V2, y?: V2): V2 => {
  const e = (k: keyof V2["abs_error"]) => (x?.abs_error[k] ?? 0) + (y?.abs_error[k] ?? 0);
  return { n: (x?.n ?? 0) + (y?.n ?? 0), abs_error: { stats_v2: e("stats_v2"), stats_only: e("stats_only"), market: e("market") } };
};
const add = (a: H2HWeek, b: H2HWeek): H2HWeek => {
  const k = (x: Keyed, y: Keyed): Keyed => ({ combined: x.combined + y.combined, stats_only: x.stats_only + y.stats_only, market: x.market + y.market });
  const w = (x: WLP, y: WLP): WLP => ({ win: x.win + y.win, loss: x.loss + y.loss, push: x.push + y.push });
  return { season: b.season, week: b.week, n: a.n + b.n, abs_error: k(a.abs_error, b.abs_error),
    winner_called: k(a.winner_called, b.winner_called), winner_correct: k(a.winner_correct, b.winner_correct),
    vs_line: { lean: w(a.vs_line.lean, b.vs_line.lean), stats_only: w(a.vs_line.stats_only, b.vs_line.stats_only),
      market_adjusted: w(a.vs_line.market_adjusted ?? Z, b.vs_line.market_adjusted ?? Z),
      injury_adjusted: w(a.vs_line.injury_adjusted ?? Z, b.vs_line.injury_adjusted ?? Z),
      v2_trial: w(a.vs_line.v2_trial ?? Z, b.vs_line.v2_trial ?? Z) },
    inj: addInj(a.inj, b.inj), v2: addV2(a.v2, b.v2) };
};
const sum = (x?: WLP) => (x ? x.win + x.loss + x.push : 0);
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
            <th colSpan={3} className="r">Vs market line</th></tr>
          <tr>{MODELS.map(([k, l]) => <th key={`e${k}`} className="r">{l}</th>)}
            <th className="r">Model pick</th><th className="r">Model line</th><th className="r">Market-adj.</th></tr>
        </thead>
        <tbody>
          {weeks.map((r) => (
            <tr key={r.week}><td>{weekName(r.week)}</td><td className="r">{r.n}</td>
              {MODELS.map(([k]) => <td key={`e${k}`} className="r">{mae(r, k)}</td>)}
              <td className="r">{wlp(r.vs_line.lean)}</td><td className="r">{wlp(r.vs_line.stats_only)}</td>
              <td className="r">{wlp(r.vs_line.market_adjusted ?? Z)}</td></tr>
          ))}
          <tr className="hl"><td><b>Season to date</b></td><td className="r"><b>{total.n}</b></td>
            {MODELS.map(([k]) => <td key={`e${k}`} className="r"><b>{mae(total, k)}</b></td>)}
            <td className="r"><b>{wlp(total.vs_line.lean)}</b></td><td className="r"><b>{wlp(total.vs_line.stats_only)}</b></td>
            <td className="r"><b>{wlp(total.vs_line.market_adjusted ?? Z)}</b></td></tr>
        </tbody>
      </table></div>
      {((total.inj?.n ?? 0) > 0 || sum(total.vs_line.injury_adjusted) > 0) && (
        <div style={{ marginTop: 14 }}>
          <h3 style={{ margin: "0 0 4px" }}>Trial: model line + injuries</h3>
          <p className="small ink2" style={{ marginTop: 0 }}>The stats-only model with the non-QB injury report added, from week 7.
            Compared on the same games only. Display and tracking only; it never sets the model pick.</p>
          <div className="table-wrap"><table>
            <thead><tr><th className="r">Games</th><th className="r">Model + injuries</th><th className="r">Model line</th>
              <th className="r">Market</th><th className="r">Vs market line</th></tr></thead>
            <tbody><tr><td className="r">{total.inj?.n ?? 0}</td>
              {(["stats_inj", "stats_only", "market"] as const).map((k) => <td key={k} className="r">
                {total.inj && total.inj.n ? (total.inj.abs_error[k] / total.inj.n).toFixed(2) : "—"}</td>)}
              <td className="r">{wlp(total.vs_line.injury_adjusted ?? Z)}</td></tr></tbody>
          </table></div>
          <p className="small muted" style={{ margin: "6px 0 0" }}>Average margin error in points (lower is better), last forecast
            before kickoff; record vs the market line from the locked version.</p>
        </div>
      )}
      {((total.v2?.n ?? 0) > 0 || sum(total.vs_line.v2_trial) > 0) && (
        <div style={{ marginTop: 14 }}>
          <h3 style={{ margin: "0 0 4px" }}>Trial: model v2 line</h3>
          <p className="small ink2" style={{ marginTop: 0 }}>The stats-only model with penalties, special teams, non-QB injuries,
            regression inputs, fatigue, time of possession and weather added, from week 8. Compared on the same games only. Display and tracking only; it
            never sets the model pick.</p>
          <div className="table-wrap"><table>
            <thead><tr><th className="r">Games</th><th className="r">Model v2</th><th className="r">Model line</th>
              <th className="r">Market</th><th className="r">Vs market line</th></tr></thead>
            <tbody><tr><td className="r">{total.v2?.n ?? 0}</td>
              {(["stats_v2", "stats_only", "market"] as const).map((k) => <td key={k} className="r">
                {total.v2 && total.v2.n ? (total.v2.abs_error[k] / total.v2.n).toFixed(2) : "—"}</td>)}
              <td className="r">{wlp(total.vs_line.v2_trial ?? Z)}</td></tr></tbody>
          </table></div>
          <p className="small muted" style={{ margin: "6px 0 0" }}>Average margin error in points (lower is better), last forecast
            before kickoff; record vs the market line from the locked version.</p>
        </div>
      )}
      {cum.length > 1 && (
        <div style={{ marginTop: 14 }}>
          <h3 style={{ margin: "0 0 4px" }}>Cumulative average margin error</h3>
          <LineChart series={series} xLabels={cum.map((c) => weekName(c.week))} xTickIdx={cum.map((_, i) => i)} yDecimals={2}
            yTitle="Cumulative average margin error (points)" />
        </div>
      )}
      <p className="small muted" style={{ marginBottom: 0 }}>Record vs market line: wins–losses–level results for the model pick and for the side of
        the locked line where each line fell (the model pick follows the model line from week 7 and the market-adjusted line
        before). The market line has no record against itself.</p>
    </div>
  );
}
