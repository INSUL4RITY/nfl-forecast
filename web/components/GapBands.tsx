import type { BandHistory, GapBand, LineSize, WLP } from "@/lib/types";
import { wilson } from "@/lib/format";

const pc = (x: number | null | undefined) => (x == null ? "—" : `${Math.round(x * 100)}%`);
const SIZE: Record<LineSize, string> = { all: "All lines", lt7: "Line under 7", ge7: "Line 7 or more" };
const BANDS: [GapBand, string][] = [["0-1", "Under 1 pt"], ["1-2", "1–2 pts"], ["2-3", "2–3 pts"], ["3-4", "3–4 pts (Big)"],
  ["4+", "4+ pts (Biggest)"]];
const Z: WLP = { win: 0, loss: 0, push: 0 };

/** Gap records in context (display only; user authorisation 2026-11-20, item B2): the model line's side of the locked
 *  line by gap band (not overlapping; under 1, 1–2 and 2–3 added 2026-11-24) and line size, 2026 against the
 *  retrospective 2019–2025 rate. */
export default function GapBands({ bands, hist }: { bands: Partial<Record<GapBand, Record<LineSize, WLP>>>; hist?: BandHistory | null }) {
  return (
    <div className="panel">
      <h2>Gap records in context</h2>
      <p className="small ink2" style={{ marginTop: 0 }}>How often the result finished on the model line&apos;s side of the market line,
        by how far the model line was from it (separate bands: under 1 point, 1–2, 2–3, 3–4 and 4 or more), split by the size of
        the line. 2026: the
        locked line of each publicly verifiable model pick. 2019–2025: retrospective walk-forward forecasts of the same model against
        untimed (roughly closing) lines, with the actual starting quarterback; somewhat optimistic. Level results are left out. 95%
        ranges are Wilson intervals; a range that includes 50% is no better than a coin flip.</p>
      <div className="table-wrap" tabIndex={0}><table>
        <thead><tr><th>Gap</th><th>Line</th><th className="r">2026 record</th><th className="r">2026 rate (95% range)</th>
          <th className="r">2019–25 games</th><th className="r">2019–25 rate (95% range)</th></tr></thead>
        <tbody>{BANDS.filter(([b]) => bands[b] || hist?.bands?.[b]).flatMap(([b, label]) => (["all", "lt7", "ge7"] as LineSize[]).map((z) => {
          const x = bands[b]?.[z] ?? Z, n = x.win + x.loss, ci = wilson(x.win, n), h = hist?.bands?.[b]?.[z];
          return (
            <tr key={`${b}-${z}`}>
              <td>{z === "all" ? label : ""}</td><td>{SIZE[z]}</td>
              <td className="r">{x.win}–{x.loss}{x.push ? `–${x.push}` : ""}</td>
              <td className="r">{n ? `${pc(x.win / n)} (${pc(ci![0])}–${pc(ci![1])})` : "—"}</td>
              <td className="r">{h?.n ?? "—"}</td>
              <td className="r">{h && h.rate != null ? `${pc(h.rate)} (${pc(h.ci95?.[0])}–${pc(h.ci95?.[1])})` : "—"}</td>
            </tr>);
        }))}</tbody>
      </table></div>
      <p className="small muted" style={{ marginTop: 6, marginBottom: 0 }}>Read the bands together: in 2019–25 only the 3–4 point band
        stood above 50%, and the bands either side of it did not, so a single band at 58% may itself be partly chance. Small 2026
        samples should not be read as a signal: with five games the 95% range runs from roughly 10% to 90%. For analysis and
        education only.</p>
    </div>
  );
}
