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
export const BIGGEST_GAP = 4;

const STATS_EXPLAIN = "Model line: the stats-only model, built from football data with no market input, so it can disagree " +
  "with the market. Market-adjusted line: the market line nudged by the football data, so it stays close to the market. " +
  "Edge: how far the margin behind the pick was from the line (under 0.5 points is about a coin flip). Big gap: the model " +
  "line was at least 3 points from the line when the pick was locked (Biggest gap: at least 4 points); a prompt to check " +
  "why the market disagrees, not a recommendation.";

export const INJ_EXPLAIN = "Model line + injuries (trial): the same stats-only model with the non-QB injury report added " +
  "(expected share of snaps each unit loses). Shown and tracked for comparison only; it never sets the model pick. Most " +
  "meaningful once the final injury report is out.";

export const V2_EXPLAIN = "Model v2.1 line (trial): the stats-only model with penalties, special teams, non-QB injuries, " +
  "turnover and close-game regression, 3rd/4th-down rates, QB scrambles, 4th-down decisions, divisional games and weather " +
  "added. Tracked from week 8 against the model line; it never sets the model pick.";

/** True when the trial line's injury inputs are all zero (no injury report for this week yet). */
export function noInjuryReport(e: { injury_inputs?: { home: Record<string, number>; away: Record<string, number> } | null }): boolean {
  const ii = e.injury_inputs;
  return !!ii && [...Object.values(ii.home), ...Object.values(ii.away)].every((v) => v === 0);
}

const EDGE: Record<string, string> = { tiny: "Tiny edge · about a coin flip", small: "Small edge", moderate: "Moderate edge", large: "Large edge" };

/** Size of the model pick's edge over the line, e.g. "Tiny edge · about a coin flip (0.10 pts)"; null without a pick. */
export function edgeText(p: Pick): string | null {
  const l = p.lean;
  if (!l || l.status !== "lean" || !l.strength || !EDGE[l.strength]) return null;
  return `${EDGE[l.strength]} (${l.difference!.toFixed(2)} pts)`;
}

/** Model line (stats-only) margin minus the line's margin when the pick was locked (positive: rates the home team higher). */
export function statsGap(lp: LockedPick | null | undefined): number | null {
  if (!lp || lp.line_home_spread == null || !lp.stats_only) return null;
  return lp.stats_only.margin + lp.line_home_spread;
}

/** Model pick against the spread, e.g. "PIT +3.5"; "No pick" when the projection equals the line or no line. */
export function pickText(p: Pick): string {
  const l = p.lean;
  return l && l.status === "lean" ? teamSpread(l.side!, l.side_spread!) : "No pick";
}

export const PICK_EXPLAIN = "Model pick: the side of the market line on which the model line (stats only) fell 24 hours " +
  "before kickoff (the latest forecast at that moment). Until then it is provisional and follows the latest forecast and " +
  "line; after that it does not change, and it is graded against the line it was locked at. It is not a probability of " +
  "finishing on that side of the line. " + STATS_EXPLAIN;

const PICK_EXPLAIN_ORIGINAL = "Model pick: the side of the market line on which the market-adjusted line fell at the first " +
  "forecast with a market line (the rule for games from 1 to 20 October 2026), graded against that line. It is not a " +
  "probability of finishing on that side of the line. " + STATS_EXPLAIN;

const PICK_EXPLAIN_OLD = "Model pick: the side of the market line on which the market-adjusted line of the last forecast " +
  "before kickoff fell, graded against that forecast's line (the rule for games before 1 October 2026). It is not a " +
  "probability of finishing on that side of the line. " + STATS_EXPLAIN;

/** Numerical difference for the version the pick comes from, and its size label (Details page only). */
export function pickDetail(p: LockedPick, home: string, away: string): string {
  const l = p.lean;
  const m = (x: number) => (Math.abs(x) < 0.005 ? "even" : x > 0 ? `${home} by ${x.toFixed(2)}` : `${away} by ${(-x).toFixed(2)}`);
  if (!l || l.status === "no_line" || p.line_home_spread == null) return "No market line was recorded with that forecast, so there is no model pick.";
  const src = p.basis === "stats_only" ? "Model line (stats only)" : "Market-adjusted line";
  const base = `${src}: ${m(p.projected_margin)}; the market line implied ${m(-p.line_home_spread)}.`;
  if (l.status === "no_lean") return `${base} The difference rounds to 0.00 points: no pick.`;
  return `${base} Difference ${l.difference!.toFixed(2)} points toward ${l.side} (${l.strength}). Differences under 0.5 points are ` +
    "labelled tiny and are within normal noise; 0.5–1.5 small, 1.5–3 moderate, 3 or more large.";
}

/** Prediction block for game cards and game pages: the locked model pick (most prominent), then the current market line,
 *  model line (stats only) and market-adjusted line with totals, then the projected winner from the model line.
 *  `lockedAt` / `locksAt` are the formatted times the pick was / will be locked. */
export function PredictionSummary({ g, lockedAt, locksAt }: { g: WeekGame; lockedAt?: ReactNode; locksAt?: ReactNode }) {
  const e = g.forecast, f = e?.forecast;
  if (!e || !f) return null;
  const lp = g.locked_pick, H = g.home, A = g.away;
  const fo = e.football_only;
  const mdl = fo ?? f;                                  // "Model" = stats-only; the combined forecast only if it is missing
  const old = lp?.rule === "final-pregame";
  const prov = !!lp?.provisional;
  const started = g.forecast_state !== "latest_pregame";
  const cur = e.market?.home_spread ?? null;
  const locked = !!lp && lp.line_home_spread != null;
  const lineMoved = locked && cur != null && cur !== lp!.line_home_spread;
  const curBasis = lp?.basis === "stats_only" ? fo?.margin ?? null : f.margin;   // the margin the pick is taken from, now
  // "then" vs "now": shown whenever the line or that margin has changed since the pick was locked
  const changed = locked && !old && !prov && cur != null
    && (lineMoved || (curBasis != null && Math.abs(curBasis - lp!.projected_margin) >= 0.005));
  const explain = old ? PICK_EXPLAIN_OLD : lp?.rule === "original-pick" ? PICK_EXPLAIN_ORIGINAL : PICK_EXPLAIN;
  const pair = (line: number, model?: number | null, adj?: number | null) => <>line {spreadText(line, H, A)}
    {model != null && <> · model {modelLine2(model, H, A)}</>}{adj != null && <> · market-adj. {modelLine2(adj, H, A)}</>}</>;
  const lockPair = () => pair(lp!.line_home_spread!, lp!.stats_only?.margin,
    lp!.market_adjusted_margin ?? (lp!.basis === "stats_only" ? null : lp!.projected_margin));
  const edge = lp ? edgeText(lp) : null;
  const gap = statsGap(lp);
  const winHome = mdl.p_home >= mdl.p_away;
  return (
    <section className="pred" aria-label="Model prediction">
      <div className="pred-pick" title={explain} aria-describedby={`pick-explain-${g.game_id}`}>
        <span className="pick-lbl">Model pick</span>
        <span className="pick-main">{lp ? pickText(lp) : started ? "No pick" : "No pick yet"}{lp?.retrospectively_derived ? " *" : ""}</span>
        {edge && <span className={`pick-edge${lp!.lean?.strength === "tiny" ? " tiny" : ""}`}>{edge}</span>}
        {locked ? (old ? (
          <span className="pick-sub">{lp!.lean?.status === "no_lean" ? "Projection equalled the line · " : ""}From the last forecast
            before kickoff: {lockPair()}</span>
        ) : (<>
          <span className="pick-sub">{lp!.lean?.status === "no_lean" ? "Projection equals the line · " : ""}{prov
            ? <>Provisional · locks {locksAt}</> : <>Locked {lockedAt}</>}{lp!.basis !== "stats_only" ? " · from the market-adjusted line" : ""}</span>
          <span className="pick-sub">{prov ? "Now: " : changed ? "Then: " : "At lock: "}{lockPair()}</span>
          {changed && <span className={`pick-sub${lineMoved ? " moved" : ""}`}>
            <LineLabel state={g.forecast_state} kickoff={g.kickoff_utc} before="Now" after="Final pre-game" />: {pair(cur!, fo?.margin, f.margin)}</span>}
        </>)) : (
          <span className="pick-sub">{started ? "No market line was recorded before kickoff" : "Appears with the first forecast that has a market line"}</span>
        )}
        {gap != null && Math.abs(gap) >= BIG_GAP && (
          <span className="pick-gap">{Math.abs(gap) >= BIGGEST_GAP
            ? <span className="tag warn strong">Biggest gap</span> : <span className="tag warn">Big gap</span>} The model line {prov ? "is" : "was"}{" "}
            {Math.abs(gap).toFixed(1)} pts from the market line, toward {gap > 0 ? H : A}. Check why the market disagrees.</span>
        )}
        <span className="sr-only" id={`pick-explain-${g.game_id}`}>{explain}</span>
      </div>
      <dl className="pred-grid">
        <div><dt>Market line</dt><dd>{cur != null ? spreadText(cur, H, A) : "—"}</dd></div>
        <div><dt>Model line</dt><dd>{modelLineText(mdl.margin, H, A)}</dd></div>
        <div><dt>Market total</dt><dd>{e.market?.total != null ? f1(e.market.total) : "—"}</dd></div>
        <div><dt>Model total</dt><dd>{f1(mdl.total)}</dd></div>
        {fo && <><div><dt>Market-adjusted line</dt><dd>{modelLineText(f.margin, H, A)}</dd></div>
          <div><dt>Market-adjusted total</dt><dd>{f1(f.total)}</dd></div></>}
        {e.football_only_inj && <div className="full" title={INJ_EXPLAIN}><dt>Model line + injuries (trial)</dt>
          <dd>{modelLineText(e.football_only_inj.margin, H, A)}
            {noInjuryReport(e) && <span className="dd-note">No injury report this week yet</span>}</dd></div>}
        {e.football_only_v2 && <div className="full" title={V2_EXPLAIN}><dt>Model v2.1 line (trial)</dt>
          <dd>{modelLineText(e.football_only_v2.margin, H, A)}</dd></div>}
        <div className="full"><dt>Projected winner (model)</dt>
          <dd>{Math.abs(mdl.margin) < 0.05 ? "Toss-up"
            : `${winHome ? H : A} ${pct(winHome ? mdl.p_home : mdl.p_away)} · by ${Math.abs(mdl.margin).toFixed(1)}`}</dd></div>
      </dl>
    </section>
  );
}

const L: Record<ResultGrade["lean"], string> = { win: "correct", loss: "wrong", push: "level with the line", no_lean: "no pick", no_line: "no line" };

/** Result line: the model pick's grade and the model line's (stats-only) margin error; the market-adjusted error if the
 *  game has no stats-only forecast. */
export function gradeText(r: ResultGrade, g?: WeekGame): string {
  const fo = g?.forecast?.football_only;
  const err = fo ? Math.abs(fo.margin - r.actual_margin) : r.abs_margin_error;
  return `Model pick ${L[r.lean]} · model margin error ${err.toFixed(1)}`;
}

export const RETRO_NOTE = "Pick labels derived retrospectively from the archived forecast and its line (the numbers were published; these labels were not).";

const GROUP_TITLE: Record<string, string> = {
  publicly_verifiable_pregame: "Publicly verifiable pregame",
  generated_pregame_published_after_kickoff: "Published after kickoff (separate)",
  generated_pregame_not_yet_evidenced_public: "Publication not yet evidenced",
};

function rec(g: GroupResults) {
  const l = g.lean, pg = g.pick_graded ?? g.graded;
  return {
    lean: pg ? `${l.win}–${l.loss}${l.push ? `, ${l.push} level` : ""}${l.no_lean ? `, ${l.no_lean} no pick` : ""}${l.no_line ? `, ${l.no_line} no line` : ""}` +
      (pg !== g.graded ? ` (${pg} game${pg > 1 ? "s" : ""})` : "") : "—",
  };
}

const RULE_TEXT: Record<string, string> = {
  "lock-24h": "The model pick follows the model line (stats only), locks 24 hours before kickoff (the latest forecast then) and is graded against that line.",
  "original-pick": "The model pick (from the market-adjusted line) is graded against the line it was locked at (the first forecast with a market line; the rule for games from 1 to 20 October 2026).",
  "final-pregame": "The model pick is graded on the last valid forecast before kickoff and that forecast's line (the rule for games before 1 October 2026; finished weeks are not regraded).",
};

export function WeekResultsPanel({ r }: { r: WeekResults }) {
  const groups = Object.entries(r.groups).filter(([, g]) => g.graded > 0 || (g.pick_graded ?? 0) > 0);
  const rp = groups.reduce((s, [, g]) => s + (g.retro_pick ?? 0), 0);
  return (
    <div className="panel" style={{ marginBottom: 16 }}>
      <h2 style={{ marginTop: 0 }}>{r.state === "final" ? "Week results (final)" : "Week to date"}</h2>
      <p className="small ink2" style={{ marginTop: 0 }}>
        {r.graded} graded · {r.pending} pending{r.no_forecast ? ` · ${r.no_forecast} without an archived forecast` : ""}.{" "}
        {(r.grading_rule ?? "").split("+").map((k) => RULE_TEXT[k]).filter(Boolean).join(" ")} The margin error is the
        market-adjusted line's, from the last valid forecast before kickoff.
      </p>
      {groups.length === 0 ? <p className="small muted">No finished games yet.</p> : (
        <div className="table-wrap"><table>
          <thead><tr><th>Forecasts</th><th className="r">Graded</th><th className="r">Model pick vs market line</th>
            <th className="r">Avg. margin error (market-adj.)</th></tr></thead>
          <tbody>{groups.map(([k, g]) => {
            const t = rec(g);
            return (<tr key={k}><td>{GROUP_TITLE[k] ?? k}{g.retro_pick ? " *" : ""}</td><td className="r">{g.graded}</td>
              <td className="r">{t.lean}</td>
              <td className="r">{g.mean_abs_margin_error != null ? `${g.mean_abs_margin_error.toFixed(1)} pts` : "—"}</td></tr>);
          })}</tbody></table></div>
      )}
      {rp > 0 && (
        <p className="small muted" style={{ marginBottom: 0 }}>* Includes {rp} model-pick label{rp > 1 ? "s" : ""} derived retrospectively from
          archived forecasts made before pick labels were published (the forecasts and lines were archived before kickoff; these
          labels were added later by a fixed rule).</p>
      )}
      <p className="small muted" style={{ marginBottom: 0 }}>Model pick vs market line: the model pick against the line it was graded on, as
        described above (level results, no-pick and no-line games listed separately). For analysis and education only.</p>
    </div>
  );
}
