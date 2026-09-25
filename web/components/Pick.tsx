import type { GroupResults, Pick, ResultGrade, WeekResults } from "@/lib/types";
import { pct } from "@/lib/format";

/** Signed spread for one team, e.g. "BUF −3.0", "NE +3.0", "CLE pick'em". */
export function teamSpread(team: string, spread: number): string {
  if (spread === 0) return `${team} pick'em`;
  return `${team} ${spread < 0 ? "−" : "+"}${Math.abs(spread).toFixed(1)}`;
}

export function winnerText(p: Pick): string {
  return p.winner ? `${p.winner} ${pct(p.winner_p)} · by ${p.winning_margin.toFixed(1)}` : "Toss-up";
}

/** "Spread lean — margin comparison" text: numerical difference with an honest size label. */
export function leanText(p: Pick): string {
  const l = p.lean;
  if (!l || l.status === "no_line") return "No market line";
  if (l.status === "no_lean") return "No lean (0.00 pts)";
  return `${teamSpread(l.side!, l.side_spread!)} · ${l.difference!.toFixed(2)} pts (${l.strength})`;
}

const W: Record<ResultGrade["winner"], string> = { win: "correct", loss: "wrong", tie: "game tied", no_pick: "no pick (toss-up)" };
const L: Record<ResultGrade["lean"], string> = { win: "correct", loss: "wrong", push: "push", no_lean: "no lean", no_line: "no line" };

export function gradeText(r: ResultGrade): string {
  return `Winner ${W[r.winner]} · spread lean ${L[r.lean]} · margin error ${r.abs_margin_error.toFixed(1)}`;
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
    lean: `${l.win}–${l.loss}${l.push ? `, ${l.push} push${l.push > 1 ? "es" : ""}` : ""}${l.no_lean ? `, ${l.no_lean} no lean` : ""}${l.no_line ? `, ${l.no_line} no line` : ""}`,
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
            <th className="r">Spread-lean record</th><th className="r">Avg. margin error</th></tr></thead>
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
          archived before kickoff; the win/lean labels were added later by a fixed rule).</p>
      )}
      <p className="small muted" style={{ marginBottom: 0 }}>Records exclude actual ties (winner), pushes, no-lean and no-line games, which are listed
        separately. The spread lean compares the projected margin with the line; it is not a betting recommendation.</p>
    </div>
  );
}
