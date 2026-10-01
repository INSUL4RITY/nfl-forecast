import type { ReactNode } from "react";
import type { GroupResults, Pick, ResultGrade, WeekGame, WeekResults } from "@/lib/types";
import { f1, pct, spreadText } from "@/lib/format";
import LineLabel from "./LineLabel";

/** Signed spread for one team, e.g. "BUF −3.0", "NE +3.0", "CLE pick'em". */
export function teamSpread(team: string, spread: number): string {
  if (spread === 0) return `${team} pick'em`;
  return `${team} ${spread < 0 ? "−" : "+"}${Math.abs(spread).toFixed(1)}`;
}

/** The model's projected margin written as a line, e.g. BUF (home) projected by 6.4 -> "BUF −6.4". */
export function modelLineText(margin: number, home: string, away: string): string {
  const r = Math.round(margin * 10) / 10;
  if (r === 0) return "Pick'em";
  return r > 0 ? `${home} −${r.toFixed(1)}` : `${away} −${(-r).toFixed(1)}`;
}

/** Model pick against the spread, e.g. "PIT +3.5"; "No pick" when the projection equals the line or no line. */
export function pickText(p: Pick): string {
  const l = p.lean;
  return l && l.status === "lean" ? teamSpread(l.side!, l.side_spread!) : "No pick";
}

export const PICK_EXPLAIN = "Model pick: the side of the market spread on which the model's projected margin fell when the pick " +
  "was locked (the first forecast with a market line). It does not change if the line or the forecast moves later, and it is " +
  "graded against that line. It is not a probability of covering the spread. The size of the difference is on the game's Details page.";

const PICK_EXPLAIN_OLD = "Model pick: the side of the market spread on which the last forecast before kickoff fell, graded " +
  "against that forecast's line (the rule for games before 1 October 2026). It is not a probability of covering the spread.";

/** Numerical difference for the version the pick comes from, and its size label (Details page only). */
export function pickDetail(p: Pick, home: string, away: string): string {
  const l = p.lean;
  const m = (x: number) => (Math.abs(x) < 0.005 ? "even" : x > 0 ? `${home} by ${x.toFixed(2)}` : `${away} by ${(-x).toFixed(2)}`);
  if (!l || l.status === "no_line" || p.line_home_spread == null) return "No market spread was recorded with that forecast, so there is no model pick.";
  const base = `Projected margin ${m(p.projected_margin)}; the line implied ${m(-p.line_home_spread)}.`;
  if (l.status === "no_lean") return `${base} The difference rounds to 0.00 points: no pick.`;
  return `${base} Difference ${l.difference!.toFixed(2)} points toward ${l.side} (${l.strength}). Differences under 0.5 points are ` +
    "labelled tiny and are within normal noise; 0.5–1.5 small, 1.5–3 moderate, 3 or more large.";
}

/** Prediction block for game cards and game pages: the locked model pick (most prominent), then the current market and
 *  model lines and totals, then the projected winner. `lockedAt` is the formatted time the pick was locked. */
export function PredictionSummary({ g, lockedAt }: { g: WeekGame; lockedAt?: ReactNode }) {
  const e = g.forecast, f = e?.forecast;
  if (!e || !f) return null;
  const lp = g.locked_pick, p = g.pick, H = g.home, A = g.away;
  const old = lp?.rule === "final-pregame";
  const started = g.forecast_state !== "latest_pregame";
  const cur = e.market?.home_spread ?? null;
  const moved = !!lp && lp.line_home_spread != null && cur != null && cur !== lp.line_home_spread;
  const explain = old ? PICK_EXPLAIN_OLD : PICK_EXPLAIN;
  let sub: ReactNode;
  if (lp && lp.line_home_spread != null) {
    const at = spreadText(lp.line_home_spread, H, A);
    sub = <>{lp.lean?.status === "no_lean" ? "Projection equalled the line · " : ""}
      {old ? <>From the last forecast before kickoff, at {at}</> : <>Locked {lockedAt} at {at}</>}</>;
  } else {
    sub = started ? "No market line was recorded before kickoff" : "Locks at the first forecast with a market line";
  }
  return (
    <section className="pred" aria-label="Model prediction">
      <div className="pred-pick" title={explain} aria-describedby={`pick-explain-${g.game_id}`}>
        <span className="pick-lbl">Model pick</span>
        <span className="pick-main">{lp ? pickText(lp) : started ? "No pick" : "No pick yet"}{lp?.retrospectively_derived ? " *" : ""}</span>
        <span className="pick-sub">{sub}</span>
        {moved && <span className="pick-sub moved"><LineLabel state={g.forecast_state} kickoff={g.kickoff_utc} /> {spreadText(cur!, H, A)}</span>}
        <span className="sr-only" id={`pick-explain-${g.game_id}`}>{explain}</span>
      </div>
      <dl className="pred-grid">
        <div><dt>Market line</dt><dd>{cur != null ? spreadText(cur, H, A) : "—"}</dd></div>
        <div><dt>Model line</dt><dd>{modelLineText(f.margin, H, A)}</dd></div>
        <div><dt>Market total</dt><dd>{e.market?.total != null ? f1(e.market.total) : "—"}</dd></div>
        <div><dt>Model total</dt><dd>{f1(f.total)}</dd></div>
        <div className="full"><dt>Projected winner</dt>
          <dd>{p?.winner ? `${p.winner} ${pct(p.winner_p)} · by ${p.winning_margin.toFixed(1)}` : "Toss-up"}</dd></div>
      </dl>
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
  const w = g.winner, l = g.lean, pg = g.pick_graded ?? g.graded;
  return {
    winner: g.graded ? `${w.win}–${w.loss}${w.tie ? `, ${w.tie} tie${w.tie > 1 ? "s" : ""}` : ""}${w.no_pick ? `, ${w.no_pick} toss-up` : ""}` : "—",
    lean: pg ? `${l.win}–${l.loss}${l.push ? `, ${l.push} push${l.push > 1 ? "es" : ""}` : ""}${l.no_lean ? `, ${l.no_lean} no pick` : ""}${l.no_line ? `, ${l.no_line} no line` : ""}` +
      (pg !== g.graded ? ` (${pg} game${pg > 1 ? "s" : ""})` : "") : "—",
  };
}

const RULE_TEXT: Record<string, string> = {
  "original-pick": "The model pick is graded against the line it was locked at (the first forecast with a market line).",
  "final-pregame": "The model pick is graded on the last valid forecast before kickoff and that forecast's line (the rule for games before 1 October 2026; finished weeks are not regraded).",
};

export function WeekResultsPanel({ r }: { r: WeekResults }) {
  const groups = Object.entries(r.groups).filter(([, g]) => g.graded > 0 || (g.pick_graded ?? 0) > 0);
  const rw = groups.reduce((s, [, g]) => s + (g.retro_winner ?? 0), 0), rp = groups.reduce((s, [, g]) => s + (g.retro_pick ?? 0), 0);
  return (
    <div className="panel" style={{ marginBottom: 16 }}>
      <h2 style={{ marginTop: 0 }}>{r.state === "final" ? "Week results (final)" : "Week to date"}</h2>
      <p className="small ink2" style={{ marginTop: 0 }}>
        {r.graded} graded · {r.pending} pending{r.no_forecast ? ` · ${r.no_forecast} without an archived forecast` : ""}.{" "}
        {(r.grading_rule ?? "").split("+").map((k) => RULE_TEXT[k]).filter(Boolean).join(" ")} The projected winner and margin
        error use the last valid forecast before kickoff.
      </p>
      {groups.length === 0 ? <p className="small muted">No finished games yet.</p> : (
        <div className="table-wrap"><table>
          <thead><tr><th>Forecasts</th><th className="r">Graded</th><th className="r">Winner record</th>
            <th className="r">Model pick record (spread)</th><th className="r">Avg. margin error</th></tr></thead>
          <tbody>{groups.map(([k, g]) => {
            const t = rec(g);
            return (<tr key={k}><td>{GROUP_TITLE[k] ?? k}{g.retro_winner || g.retro_pick ? " *" : ""}</td><td className="r">{g.graded}</td>
              <td className="r">{t.winner}</td><td className="r">{t.lean}</td>
              <td className="r">{g.mean_abs_margin_error != null ? `${g.mean_abs_margin_error.toFixed(1)} pts` : "—"}</td></tr>);
          })}</tbody></table></div>
      )}
      {(rw > 0 || rp > 0) && (
        <p className="small muted" style={{ marginBottom: 0 }}>* Includes {[rw ? `${rw} winner label${rw > 1 ? "s" : ""}` : "",
          rp ? `${rp} model-pick label${rp > 1 ? "s" : ""}` : ""].filter(Boolean).join(" and ")} derived retrospectively from
          archived forecasts made before pick labels were published (the forecasts and lines were archived before kickoff; these
          labels were added later by a fixed rule).</p>
      )}
      <p className="small muted" style={{ marginBottom: 0 }}>Winner record: the projected winner against the result (actual ties listed separately).
        Model pick record (spread): the model pick against the line it was graded on, as described above (pushes, no-pick and
        no-line games listed separately). Win probabilities apply to the projected winner only, not to the spread. Not a betting recommendation.</p>
    </div>
  );
}
