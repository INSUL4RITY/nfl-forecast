import type { ReactNode } from "react";
import type { GroupResults, LockedPick, Pick, ResultGrade, WeekGame, WeekResults } from "@/lib/types";
import { f1, pct, spreadText } from "@/lib/format";
import LineLabel from "./LineLabel";

/** Signed spread for one team, e.g. "BUF −3.0", "NE +3.0", "CLE even". */
export function teamSpread(team: string, spread: number): string {
  if (spread === 0) return `${team} even`;
  return `${team} ${spread < 0 ? "−" : "+"}${Math.abs(spread).toFixed(1)}`;
}

/** The model's projected margin written as a line, e.g. BUF (home) projected by 6.4 -> "BUF −6.4". */
export function modelLineText(margin: number, home: string, away: string): string {
  const r = Math.round(margin * 10) / 10;
  if (r === 0) return "Even";
  return r > 0 ? `${home} −${r.toFixed(1)}` : `${away} −${(-r).toFixed(1)}`;
}

/** The same with 2 decimals, for comparing with the line inside the pick box (so 2.96 vs 3.0 never displays as equal). */
function modelLine2(margin: number, home: string, away: string): string {
  if (Math.abs(margin) < 0.005) return "Even";
  return margin > 0 ? `${home} −${margin.toFixed(2)}` : `${away} −${(-margin).toFixed(2)}`;
}

export const BIG_GAP = 3;

const STATS_EXPLAIN = "Edge: how far the model's projected margin was from the line (under 0.5 points is about a coin flip). " +
  "Stats-only: the football-only model, which uses no market line. Big gap: the stats-only number was at least 3 points from " +
  "the line when the lean was locked; a prompt to check why the market disagrees, not a recommendation.";

const EDGE: Record<string, string> = { tiny: "Tiny edge · about a coin flip", small: "Small edge", moderate: "Moderate edge", large: "Large edge" };

/** Size of the model pick's edge over the line, e.g. "Tiny edge · about a coin flip (0.10 pts)"; null without a pick. */
export function edgeText(p: Pick): string | null {
  const l = p.lean;
  if (!l || l.status !== "lean" || !l.strength || !EDGE[l.strength]) return null;
  return `${EDGE[l.strength]} (${l.difference!.toFixed(2)} pts)`;
}

/** Stats-only margin minus the line's margin when the pick was locked (positive: stats-only rates the home team higher). */
export function statsGap(lp: LockedPick | null | undefined): number | null {
  if (!lp || lp.line_home_spread == null || !lp.stats_only) return null;
  return lp.stats_only.margin + lp.line_home_spread;
}

/** Model pick against the spread, e.g. "PIT +3.5"; "No pick" when the projection equals the line or no line. */
export function pickText(p: Pick): string {
  const l = p.lean;
  return l && l.status === "lean" ? teamSpread(l.side!, l.side_spread!) : "No lean";
}

export const PICK_EXPLAIN = "Model lean: the side of the market line on which the model's projected margin fell when the lean " +
  "was locked (the first forecast with a market line). It does not change if the line or the forecast moves later, and it is " +
  "graded against that line. It is not a probability of finishing on that side of the line. " + STATS_EXPLAIN;

const PICK_EXPLAIN_OLD = "Model lean: the side of the market line on which the last forecast before kickoff fell, graded " +
  "against that forecast's line (the rule for games before 1 October 2026). It is not a probability of finishing on that side of the line. " + STATS_EXPLAIN;

/** Numerical difference for the version the pick comes from, and its size label (Details page only). */
export function pickDetail(p: Pick, home: string, away: string): string {
  const l = p.lean;
  const m = (x: number) => (Math.abs(x) < 0.005 ? "even" : x > 0 ? `${home} by ${x.toFixed(2)}` : `${away} by ${(-x).toFixed(2)}`);
  if (!l || l.status === "no_line" || p.line_home_spread == null) return "No market line was recorded with that forecast, so there is no model lean.";
  const base = `Projected margin ${m(p.projected_margin)}; the line implied ${m(-p.line_home_spread)}.`;
  if (l.status === "no_lean") return `${base} The difference rounds to 0.00 points: no lean.`;
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
  const locked = !!lp && lp.line_home_spread != null;
  const lineMoved = locked && cur != null && cur !== lp!.line_home_spread;
  // "then" vs "now": shown whenever the line or the model has changed since the pick was locked
  const changed = locked && !old && cur != null && (lineMoved || Math.abs(f.margin - lp!.projected_margin) >= 0.005);
  const explain = old ? PICK_EXPLAIN_OLD : PICK_EXPLAIN;
  const fo = e.football_only;
  const pair = (line: number, margin: number, stats?: number | null) => <>line {spreadText(line, H, A)} · model {modelLine2(margin, H, A)}
    {stats != null && <> · stats-only {modelLine2(stats, H, A)}</>}</>;
  const edge = lp ? edgeText(lp) : null;
  const gap = statsGap(lp);
  return (
    <section className="pred" aria-label="Model prediction">
      <div className="pred-pick" title={explain} aria-describedby={`pick-explain-${g.game_id}`}>
        <span className="pick-lbl">Model lean vs market</span>
        <span className="pick-main">{lp ? pickText(lp) : started ? "No lean" : "No lean yet"}{lp?.retrospectively_derived ? " *" : ""}</span>
        {edge && <span className={`pick-edge${lp!.lean?.strength === "tiny" ? " tiny" : ""}`}>{edge}</span>}
        {locked ? (old ? (
          <span className="pick-sub">{lp!.lean?.status === "no_lean" ? "Projection equalled the line · " : ""}From the last forecast
            before kickoff: {pair(lp!.line_home_spread!, lp!.projected_margin, lp!.stats_only?.margin)}</span>
        ) : (<>
          <span className="pick-sub">{lp!.lean?.status === "no_lean" ? "Projection equalled the line · " : ""}Locked {lockedAt}</span>
          <span className="pick-sub">{changed ? "Then: " : "At lock: "}{pair(lp!.line_home_spread!, lp!.projected_margin, lp!.stats_only?.margin)}</span>
          {changed && <span className={`pick-sub${lineMoved ? " moved" : ""}`}>
            <LineLabel state={g.forecast_state} kickoff={g.kickoff_utc} before="Now" after="Final pre-game" />: {pair(cur!, f.margin, fo?.margin)}</span>}
        </>)) : (
          <span className="pick-sub">{started ? "No market line was recorded before kickoff" : "Locks at the first forecast with a market line"}</span>
        )}
        {gap != null && Math.abs(gap) >= BIG_GAP && (
          <span className="pick-gap"><span className="tag warn">Big gap</span> Stats-only was {Math.abs(gap).toFixed(1)} pts from the
            line, toward {gap > 0 ? H : A}. Check why the market disagrees.</span>
        )}
        <span className="sr-only" id={`pick-explain-${g.game_id}`}>{explain}</span>
      </div>
      <dl className="pred-grid">
        <div><dt>Market line</dt><dd>{cur != null ? spreadText(cur, H, A) : "—"}</dd></div>
        <div><dt>Model line</dt><dd>{modelLineText(f.margin, H, A)}</dd></div>
        <div><dt>Market total</dt><dd>{e.market?.total != null ? f1(e.market.total) : "—"}</dd></div>
        <div><dt>Model total</dt><dd>{f1(f.total)}</dd></div>
        {fo && <><div><dt>Stats-only line</dt><dd>{modelLineText(fo.margin, H, A)}</dd></div>
          <div><dt>Stats-only total</dt><dd>{f1(fo.total)}</dd></div></>}
        <div className="full"><dt>Projected winner</dt>
          <dd>{p?.winner ? `${p.winner} ${pct(p.winner_p)} · by ${p.winning_margin.toFixed(1)}` : "Toss-up"}</dd></div>
      </dl>
    </section>
  );
}

const W: Record<ResultGrade["winner"], string> = { win: "correct", loss: "wrong", tie: "game tied", no_pick: "no call (toss-up)" };
const L: Record<ResultGrade["lean"], string> = { win: "correct", loss: "wrong", push: "level with the line", no_lean: "no lean", no_line: "no line" };

export function gradeText(r: ResultGrade): string {
  return `Winner ${W[r.winner]} · model lean vs market ${L[r.lean]} · margin error ${r.abs_margin_error.toFixed(1)}`;
}

export const RETRO_NOTE = "Lean labels derived retrospectively from the archived forecast and its line (the numbers were published; these labels were not).";

const GROUP_TITLE: Record<string, string> = {
  publicly_verifiable_pregame: "Publicly verifiable pregame",
  generated_pregame_published_after_kickoff: "Published after kickoff (separate)",
  generated_pregame_not_yet_evidenced_public: "Publication not yet evidenced",
};

function rec(g: GroupResults) {
  const w = g.winner, l = g.lean, pg = g.pick_graded ?? g.graded;
  return {
    winner: g.graded ? `${w.win}–${w.loss}${w.tie ? `, ${w.tie} tie${w.tie > 1 ? "s" : ""}` : ""}${w.no_pick ? `, ${w.no_pick} toss-up` : ""}` : "—",
    lean: pg ? `${l.win}–${l.loss}${l.push ? `, ${l.push} level` : ""}${l.no_lean ? `, ${l.no_lean} no lean` : ""}${l.no_line ? `, ${l.no_line} no line` : ""}` +
      (pg !== g.graded ? ` (${pg} game${pg > 1 ? "s" : ""})` : "") : "—",
  };
}

const RULE_TEXT: Record<string, string> = {
  "original-pick": "The model lean is graded against the line it was locked at (the first forecast with a market line).",
  "final-pregame": "The model lean is graded on the last valid forecast before kickoff and that forecast's line (the rule for games before 1 October 2026; finished weeks are not regraded).",
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
            <th className="r">Lean vs market record</th><th className="r">Avg. margin error</th></tr></thead>
          <tbody>{groups.map(([k, g]) => {
            const t = rec(g);
            return (<tr key={k}><td>{GROUP_TITLE[k] ?? k}{g.retro_winner || g.retro_pick ? " *" : ""}</td><td className="r">{g.graded}</td>
              <td className="r">{t.winner}</td><td className="r">{t.lean}</td>
              <td className="r">{g.mean_abs_margin_error != null ? `${g.mean_abs_margin_error.toFixed(1)} pts` : "—"}</td></tr>);
          })}</tbody></table></div>
      )}
      {(rw > 0 || rp > 0) && (
        <p className="small muted" style={{ marginBottom: 0 }}>* Includes {[rw ? `${rw} winner label${rw > 1 ? "s" : ""}` : "",
          rp ? `${rp} model-lean label${rp > 1 ? "s" : ""}` : ""].filter(Boolean).join(" and ")} derived retrospectively from
          archived forecasts made before lean labels were published (the forecasts and lines were archived before kickoff; these
          labels were added later by a fixed rule).</p>
      )}
      <p className="small muted" style={{ marginBottom: 0 }}>Winner record: the projected winner against the result (actual ties listed separately).
        Lean vs market record: the model lean against the line it was graded on, as described above (level results, no-lean and
        no-line games listed separately). Win probabilities apply to the projected winner only, not to the line. For analysis and education only.</p>
    </div>
  );
}
