import type { GroupResults, Pick, ResultGrade, WeekResults } from "@/lib/types";
import { pct } from "@/lib/format";

/** Signed spread for one team, e.g. "BUF −3.0", "NE +3.0", "CLE pick'em". */
export function teamSpread(team: string, spread: number): string {
  if (spread === 0) return `${team} pick'em`;
  return `${team} ${spread < 0 ? "−" : "+"}${Math.abs(spread).toFixed(1)}`;
}

/** Model pick against the recorded spread, e.g. "PIT +3.5"; "No pick" when the projection equals the line or no line. */
export function pickText(p: Pick): string {
  const l = p.lean;
  return l && l.status === "lean" ? teamSpread(l.side!, l.side_spread!) : "No pick";
}

function pickSub(p: Pick): string {
  const l = p.lean;
  if (!l || l.status === "no_line") return "No spread recorded with this forecast";
  if (l.status === "no_lean") return "Projection matches the recorded spread";
  return "Against the recorded spread";
}

export const PICK_EXPLAIN = "Model pick: the side of the market spread recorded with this forecast on which the model's projected margin " +
  "falls. It is not a probability of covering the spread. The size of the difference is on the game's Details page.";

/** Numerical difference and its size label (Details page only). */
export function pickDetail(p: Pick, home: string, away: string): string {
  const l = p.lean;
  const m = (x: number) => (Math.abs(x) < 0.005 ? "even" : x > 0 ? `${home} by ${x.toFixed(2)}` : `${away} by ${(-x).toFixed(2)}`);
  if (!l || l.status === "no_line" || p.line_home_spread == null) return "No market spread was recorded with this forecast, so there is no model pick.";
  const base = `Projected margin ${m(p.projected_margin)}; recorded spread implies ${m(-p.line_home_spread)}.`;
  if (l.status === "no_lean") return `${base} Difference below 0.01 points: no pick.`;
  return `${base} Difference ${l.difference!.toFixed(2)} points toward ${l.side} (${l.strength}). Differences under 0.5 points are ` +
    "labelled tiny and are within normal noise; 0.5–1.5 small, 1.5–3 moderate, 3 or more large.";
}

/** Separate prediction box beneath a game's data: projected winner (with win probability) and model pick. */
export function PickBoxes({ p, id }: { p: Pick; id: string }) {
  return (
    <section className="pick-box" aria-label="Model prediction">
      <div className="pick-sec">
        <span className="pick-lbl">Projected winner</span>
        <span className="pick-val">{p.winner ? `${p.winner} ${pct(p.winner_p)}` : "Toss-up"}</span>
        <span className="pick-sub">{p.winner ? `Win probability · by ${p.winning_margin.toFixed(1)} pts` : "Equal win probabilities"}</span>
      </div>
      <div className="pick-sec" title={PICK_EXPLAIN} aria-describedby={`pick-explain-${id}`}>
        <span className="pick-lbl">Model pick</span>
        <span className="pick-val">{pickText(p)}{p.retrospectively_derived ? " *" : ""}</span>
        <span className="pick-sub">{pickSub(p)}</span>
        <span className="sr-only" id={`pick-explain-${id}`}>{PICK_EXPLAIN}</span>
      </div>
    </section>
  );
}

const W: Record<ResultGrade["winner"], string> = { win: "correct", loss: "wrong", tie: "game tied", no_pick: "no pick (toss-up)" };
const L: Record<ResultGrade["lean"], string> = { win: "correct", loss: "wrong", push: "push", no_lean: "no pick", no_line: "no line" };

export function gradeText(r: ResultGrade): string {
  return `Winner ${W[r.winner]} · model pick (spread) ${L[r.lean]} · margin error ${r.abs_margin_error.toFixed(1)}`;
}

export const RETRO_NOTE = "Pick labels derived retrospectively from the archived forecast and its line (the numbers were published; these labels were not).";

const GROUP_TITLE: Record<string, string> = {
  publicly_verifiable_pregame: "Publicly verifiable pregame",
  generated_pregame_published_after_kickoff: "Published after kickoff (separate)",
  generated_pregame_not_yet_evidenced_public: "Publication not yet evidenced",
};

function rec(g: GroupResults) {
  const w = g.winner, l = g.lean;
  return {
    winner: `${w.win}–${w.loss}${w.tie ? `, ${w.tie} tie${w.tie > 1 ? "s" : ""}` : ""}${w.no_pick ? `, ${w.no_pick} toss-up` : ""}`,
    lean: `${l.win}–${l.loss}${l.push ? `, ${l.push} push${l.push > 1 ? "es" : ""}` : ""}${l.no_lean ? `, ${l.no_lean} no pick` : ""}${l.no_line ? `, ${l.no_line} no line` : ""}`,
  };
}

export function WeekResultsPanel({ r }: { r: WeekResults }) {
  const groups = Object.entries(r.groups).filter(([, g]) => g.graded > 0);
  return (
    <div className="panel" style={{ marginBottom: 16 }}>
      <h2 style={{ marginTop: 0 }}>{r.state === "final" ? "Week results (final)" : "Week to date"}</h2>
      <p className="small ink2" style={{ marginTop: 0 }}>
        {r.graded} graded · {r.pending} pending{r.no_forecast ? ` · ${r.no_forecast} without an archived forecast` : ""}.
        Each game is graded on its locked forecast (the last valid version before kickoff) against the market line archived with
        that same forecast.
      </p>
      {groups.length === 0 ? <p className="small muted">No finished games yet.</p> : (
        <div className="table-wrap"><table>
          <thead><tr><th>Forecasts</th><th className="r">Graded</th><th className="r">Winner record</th>
            <th className="r">Model pick record (spread)</th><th className="r">Avg. margin error</th></tr></thead>
          <tbody>{groups.map(([k, g]) => {
            const t = rec(g);
            return (<tr key={k}><td>{GROUP_TITLE[k] ?? k}{g.retrospectively_derived ? " *" : ""}</td><td className="r">{g.graded}</td>
              <td className="r">{t.winner}</td><td className="r">{t.lean}</td>
              <td className="r">{g.mean_abs_margin_error != null ? `${g.mean_abs_margin_error.toFixed(1)} pts` : "—"}</td></tr>);
          })}</tbody></table></div>
      )}
      {groups.some(([, g]) => g.retrospectively_derived) && (
        <p className="small muted" style={{ marginBottom: 0 }}>* Includes {groups.reduce((s, [, g]) => s + g.retrospectively_derived, 0)} pick(s)
          derived retrospectively from archived forecasts made before pick labels were published (the forecasts and lines were
          archived before kickoff; the winner and model-pick labels were added later by a fixed rule).</p>
      )}
      <p className="small muted" style={{ marginBottom: 0 }}>Winner record: the projected winner against the result (actual ties listed separately).
        Model pick record (spread): the model pick against the spread recorded with that forecast (pushes, no-pick and no-line games
        listed separately). Win probabilities apply to the projected winner only, not to the spread. Not a betting recommendation.</p>
    </div>
  );
}
