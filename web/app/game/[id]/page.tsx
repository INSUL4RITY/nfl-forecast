import Link from "next/link";
import { notFound } from "next/navigation";
import LocalTime from "@/components/LocalTime";
import TeamBadge from "@/components/TeamBadge";
import { dataProblems } from "@/components/GameCard";
import StateLabel from "@/components/StateLabel";
import { gradeText, pickDetail, PickBoxes, RETRO_NOTE } from "@/components/Pick";
import { allGames, findGame, getTeams } from "@/lib/data";
import { f1, f2, f3, marginText, pct, pctP, problemText, qbStatusText, rosterText, spreadText, VERIFY_LABEL } from "@/lib/format";
import type { Forecast, LineupSide } from "@/lib/types";

export function generateStaticParams() {
  return allGames().map((g) => ({ id: g.game_id }));
}

const EFF_ROWS: [string, string, "hi" | "lo", (x: number) => string][] = [
  ["off_epa_play", "Offense EPA / play", "hi", f3],
  ["def_epa_play", "Defense EPA / play allowed", "lo", f3],
  ["off_epa_db", "Passing EPA / dropback", "hi", f3],
  ["def_epa_db", "Pass defense EPA / dropback", "lo", f3],
  ["off_epa_rush", "Rushing EPA / rush", "hi", f3],
  ["def_epa_rush", "Run defense EPA / rush", "lo", f3],
  ["off_pts_drive", "Points / drive", "hi", f2],
  ["def_pts_drive", "Points / drive allowed", "lo", f2],
  ["off_sack_rate", "Sack rate taken", "lo", (x) => pct(x, 1)],
  ["def_sack_rate", "Sack rate generated", "hi", (x) => pct(x, 1)],
  ["adj_off_epa", "Opponent-adjusted offense", "hi", f3],
  ["adj_def_epa", "Opponent-adjusted defense", "hi", f3],
  ["expected_qb_rating", "Expected QB (EPA / dropback, shrunk)", "hi", f3],
  ["games_this_season", "Games this season", "hi", (x) => x.toFixed(0)],
];

function rangeFmt(r: [number, number] | undefined, home: string, away: string) {
  if (!r) return "—";
  const s = (x: number) => (Math.abs(x) < 0.5 ? "even" : x > 0 ? `${home} by ${x.toFixed(0)}` : `${away} by ${(-x).toFixed(0)}`);
  return `${s(r[0])} to ${s(r[1])}`;
}

const FLAG_TEXT: Record<string, string> = {
  report_not_available: "This team's injury report for the week has not been published yet; availability is estimated from history, not assumed.",
  report_stale: "The injury-report snapshot is older than 36 hours; it is not treated as current.",
  depth_chart_stale: "The depth chart is stale (older than 4 days or older than the team's last game); the last actual starter leads.",
  depth_chart_missing: "No depth chart was available; the last actual starter leads.",
  qb1_did_not_finish_previous_game: "QB1 took under 75% of the team's dropbacks last game, which historically lowers the chance he starts.",
  no_candidate_qb_prior_used: "No candidate QB could be identified; a generic prior was used.",
  roster_missing: "No current roster snapshot: roster status (reserve, released, practice squad, inactive) could not be checked.",
  roster_stale: "The roster snapshot is stale; roster status was not used.",
  replacement_chain_exhausted: "Every listed QB has some chance of being unavailable; the remaining probability is assigned to the last usable QB (an emergency option).",
  designation_pending: "Game designations (Questionable/Doubtful/Out) for this week are not published yet; a pooled historical rate is used and labelled.",
  override_expired: "A manual override for this game has expired and is no longer applied.",
};

/** Plain-English note for a lineup flag; internal codes and player IDs are never shown. Unknown codes are hidden. */
function flagText(fl: string, side: LineupSide): string | null {
  if (FLAG_TEXT[fl]) return FLAG_TEXT[fl];
  const m = fl.match(/^chain_qb_unavailable_roster:(.+)$/);
  if (m) {
    const q = side.qbs?.find((x) => x.qb_id === m[1]);
    const where = q?.roster_status ? rosterText(q.roster_status).toLowerCase() : "an inactive roster list";
    return `${q?.qb ?? "A listed quarterback"} is on the ${where} and cannot start, so he is skipped in the order of replacements.`;
  }
  return null;
}

/** Public name of the market-line source actually recorded in each release (spread and total only). */
const MARKET_SOURCE: Record<string, string> = {
  nflverse_schedules_archived: "nflverse schedule data (free; snapshot archived by this project)",
  the_odds_api: "The Odds API (median of US bookmakers)",
};

const LEGACY_SOURCE: Record<string, string> = {
  depth_chart_daily: "the daily depth chart", depth_chart_weekly: "the weekly depth chart", depth_chart: "the depth chart",
  last_starter: "the team's most recent starter", override: "a documented override",
};

/** Evidence detail with internal shorthand spelled out. */
const detailText = (s?: string) => (s ?? "").replace("finished prev", "QB1 finished his previous game");
const EVIDENCE_TEXT: Record<string, string> = {
  injury_report: "injury report",
  not_on_published_report: "not on published report",
  report_not_available: "no report yet",
  report_stale: "stale report",
  override: "documented override",
  roster: "roster status",
};

const SOURCE_NAME: Record<string, string> = {
  injuries: "Injury reports", depth_charts: "Depth charts", rosters_weekly: "Rosters", schedules: "Schedule & market line",
  the_odds_api: "Market line (The Odds API)",
};
const STATE_TEXT: Record<string, string> = {
  fresh: "fresh", stale_provider: "STALE (provider not updated)", stale_retrieval: "STALE (not re-checked)", missing: "MISSING",
};

function iso16(s?: string | null) {
  return s ? s.slice(0, 16).replace("T", " ") + " UTC" : "—";
}

function Lineup({ side, abbr }: { side: LineupSide; abbr: string }) {
  if (!side.qbs) {
    // legacy (schema v2) releases, shown as published at the time
    return (
      <div>
        <h3>{abbr}: {side.expected_qb ?? "unknown"}</h3>
        <p className="small ink2">Legacy release: expected starter from {LEGACY_SOURCE[side.source ?? ""] ?? "the available team information"}
          {side.qb1_status ? `; QB1 report status ${side.qb1_status}` : "; missing injury information was treated as available"}.</p>
        <table><thead><tr><th>Scenario</th><th className="r">Weight</th></tr></thead><tbody>
          {side.scenarios.map((s) => <tr key={s.qb_id ?? "x"}><td>{s.qb} starts</td><td className="r">{pctP(s.p)}</td></tr>)}
        </tbody></table>
      </div>
    );
  }
  return (
    <div>
      <h3>{abbr}: {side.expected_qb ?? "unknown"} {pctP(side.scenarios[0]?.p)}</h3>
      <table><thead><tr><th>Start scenario</th><th className="r">Probability</th></tr></thead><tbody>
        {side.scenarios.map((s) => <tr key={s.qb_id ?? "x"}><td>{s.qb ?? "unknown"}</td><td className="r">{pctP(s.p)}</td></tr>)}
      </tbody></table>
      <details style={{ marginTop: 6 }}>
        <summary className="small">Evidence for each quarterback</summary>
        <table style={{ marginTop: 6 }}><thead><tr><th>QB</th><th>Chart</th><th>Roster</th><th>Status</th><th>Evidence</th><th className="r">P(starts if next in line)</th></tr></thead><tbody>
          {side.qbs.map((q) => (
            <tr key={q.qb_id} title={detailText(q.detail)}><td>{q.qb ?? "Unnamed QB"}</td><td>{q.depth_rank ? `QB${q.depth_rank}` : "—"}</td>
              <td>{rosterText(q.roster_status)}</td><td>{qbStatusText(q.status)}</td>
              <td>{EVIDENCE_TEXT[q.evidence] ?? "other evidence"}</td><td className="r">{pctP(q.p_available)}</td></tr>))}
        </tbody></table>
        <p className="small muted" style={{ marginTop: 4 }}>
          {side.qbs.map((q) => `${q.qb ?? "Unnamed QB"}: ${detailText(q.detail)}`).join(" · ")}
          {side.depth_chart_at ? ` · Depth chart snapshot ${side.depth_chart_at.slice(0, 16).replace("T", " ")} UTC.` : ""}
          {side.injury_snapshot_at ? ` Injury data observed ${side.injury_snapshot_at.slice(0, 16).replace("T", " ")} UTC.` : ""}
        </p>
        {side.overrides_used && side.overrides_used.length > 0 && (
          <p className="small">Documented overrides: {side.overrides_used.map((o) => `${o.status} (${o.source}, published ${o.source_published_at_utc}${o.expires_at_utc ? `, expires ${o.expires_at_utc}` : ""})`).join("; ")}</p>
        )}
      </details>
      {(side.flags ?? []).map((fl) => [fl, flagText(fl, side)] as const).filter(([, t]) => t).map(([fl, t]) =>
        <p key={fl} className="small tag warn" style={{ display: "inline-block", whiteSpace: "normal" }}>{t}</p>)}
    </div>
  );
}

export default async function GamePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const found = findGame(id);
  if (!found) notFound();
  const { game: g } = found;
  const teams = getTeams();
  const e = g.forecast;
  const f = e?.forecast;
  const H = g.home, A = g.away;
  const models: [string, Forecast | null | undefined, string][] = e ? [
    ["Combined (selected)", e.combined, "Market spread & total + football features; residual ridge"],
    ["Football only", e.football_only, "No market inputs; also the fallback model"],
    ["Market only", e.market_only, "Spread & total mapped to scores (benchmark)"],
  ] : [];

  return (
    <>
      <p className="small"><Link href={`/week/${g.season}/${g.week}/`}>← Week {g.week}</Link></p>
      <div className="page-head">
        <div>
          <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
            <TeamBadge team={teams[A]} abbr={A} large /><span className="muted" style={{ fontWeight: 700 }}>at</span>
            <TeamBadge team={teams[H]} abbr={H} large />
            <h1 style={{ margin: 0 }}>{teams[A]?.nick} at {teams[H]?.nick}</h1>
          </div>
          <div className="meta-line" style={{ marginTop: 8 }}>
            <LocalTime venueTz={g.venue_tz} iso={g.kickoff_utc} kickoff known={g.kickoff_time_known} /> · {g.stadium}{g.neutral_site ? " (neutral site)" : ""}
            {g.roof ? ` · ${g.roof}` : ""} · {g.game_type === "REG" ? "Regular season" : "Playoffs"}
          </div>
        </div>
        {g.score && (
          <div className="stat"><span className="lbl">Final</span>
            <span className="big">{A} {g.score.away} – {g.score.home} {H}</span></div>
        )}
      </div>

      {g.corrections.length > 0 && (
        <div className="small ink2" style={{ margin: "4px 0 12px" }}>
          <b>Generated before kickoff; published after kickoff.</b> Kickoff {iso16(g.kickoff_utc)}; first public evidence{" "}
          {iso16(g.corrections[0].details.first_public_evidence_utc)} (<a href={g.corrections[0].details.evidence}>GitHub record</a>).
          Scored separately from publicly verifiable pregame forecasts.
          <details style={{ marginTop: 4 }}>
            <summary>Audit history ({g.corrections.length} {g.corrections.length === 1 ? "record" : "records"})</summary>
            <ul style={{ margin: "4px 0 0", paddingLeft: 18 }}>
              {g.corrections.map((c) => (
                <li key={c.id}>Version generated {iso16(c.details["generated_at_utc (self-reported)"])}; first public evidence{" "}
                  {iso16(c.details.first_public_evidence_utc)}; recorded {iso16(c.recorded_at_utc)}.</li>
              ))}
            </ul>
            <p className="muted" style={{ margin: "4px 0 0" }}>The original files are unchanged; these records are kept in the
              append-only corrections log.</p>
          </details>
        </div>
      )}

      {!e || !f ? (
        <div className="panel pending">
          {g.forecast_state === "not_archived"
            ? "No valid pregame forecast was archived for this game. Nothing is shown rather than a forecast reconstructed after the fact."
            : "Forecast pending."}
        </div>
      ) : (
        <>
          <p className="small ink2">
            <b><StateLabel state={g.forecast_state} kickoff={g.kickoff_utc} /></b> · generated <LocalTime venueTz={g.venue_tz} iso={g.forecast_generated_at} /> ·{" "}
            {g.forecast_verification ? VERIFY_LABEL[g.forecast_verification] : ""}
            {g.forecast_public_evidence_at ? <> (first public evidence <LocalTime venueTz={g.venue_tz} iso={g.forecast_public_evidence_at} />)</> : null}
            {g.model_version ? <> · {g.model_frozen ? `model ${g.model_version} (frozen)` : `pre-freeze model build ${g.model_version.replace(/^unfrozen-/, "").slice(0, 8)}`}</> : null}
          </p>
          <div className="three-col">
            <div className="panel stat">
              <span className="lbl">Expected score ({e.primary_model})</span>
              <span className="big">{A} {f1(f.away_pts)} – {f1(f.home_pts)} {H}</span>
              <span className="small muted">Means, not a predicted final score.</span>
            </div>
            <div className="panel stat">
              <span className="lbl">Projected winner</span>
              <span className="big">{f.p_home >= f.p_away ? `${H} ${pct(f.p_home)}` : `${A} ${pct(f.p_away)}`}</span>
              <span className="small ink2">{f.p_home >= f.p_away ? `${A} ${pct(f.p_away)}` : `${H} ${pct(f.p_home)}`} · tie {pct(f.p_tie, 1)}</span>
            </div>
            <div className="panel stat">
              <span className="lbl">Projected margin · total</span>
              <span className="big">{marginText(f.margin, H, A)} · {f1(f.total)}</span>
              <span className="small ink2">80%: {rangeFmt(f.intervals.margin_80, H, A)} · total {f1(f.intervals.total_80[0])}–{f1(f.intervals.total_80[1])}</span>
            </div>
          </div>

          {g.pick && (
            <div className="panel">
              <h2 style={{ marginTop: 0 }}>Prediction</h2>
              <PickBoxes p={g.pick} id={g.game_id} />
              <dl className="kv" style={{ margin: "10px 0 0" }}>
                <div><dt>Market spread with this forecast</dt><dd className="v" style={{ margin: 0 }}>
                  {g.pick.line_home_spread != null ? spreadText(g.pick.line_home_spread, H, A) : "none"}</dd></div>
                <div><dt>Forecast updated</dt><dd className="v" style={{ margin: 0 }}><LocalTime venueTz={g.venue_tz} iso={g.forecast_generated_at} /></dd></div>
              </dl>
              <details style={{ marginTop: 10 }}>
                <summary className="small">Details: how the model pick is derived</summary>
                <p className="small" style={{ margin: "6px 0 0" }}>{pickDetail(g.pick, H, A)}</p>
                <p className="small muted" style={{ margin: "6px 0 0" }}>The model pick is the side of the market spread recorded with this
                  forecast version on which the unrounded projected margin falls. The win probability belongs to the projected winner
                  only; it is not a probability of covering the spread. Not a betting recommendation.
                  {g.forecast_state === "latest_pregame" ? " Before kickoff this may change with each new forecast version; at kickoff it locks." : ""}</p>
              </details>
              {g.result_grade && <p style={{ marginBottom: 0 }}><b>Result:</b> {gradeText(g.result_grade)} (actual margin{" "}
                {marginText(g.result_grade.actual_margin, H, A)}).</p>}
              {g.pick.retrospectively_derived && <p className="small muted" style={{ marginBottom: 0 }}>{RETRO_NOTE}</p>}
            </div>
          )}

          {e.lineup_uncertain && (
            <div className="callout warn"><b>Lineup uncertain.</b> This forecast is a probability-weighted mix of starting-QB scenarios.
              Lineup uncertainty is shown here separately from the win probability.
              {e.scenario_forecasts && e.scenario_forecasts.length > 1 && (
                <div className="table-wrap" style={{ marginTop: 8 }}><table>
                  <thead><tr><th>Scenario</th><th className="r">Weight</th><th className="r">Combined margin</th><th className="r">Football-only margin</th></tr></thead>
                  <tbody>{e.scenario_forecasts.map((s, i) => (
                    <tr key={i}><td>{s.away_qb ?? "?"} vs {s.home_qb ?? "?"}</td><td className="r">{pctP(s.p)}</td>
                      <td className="r">{s.combined_margin != null ? marginText(s.combined_margin, H, A) : "—"}</td>
                      <td className="r">{marginText(s.football_margin, H, A)}</td></tr>))}</tbody></table></div>
              )}
              <p className="small" style={{ margin: "8px 0 0" }}>The combined model keeps the same market line in every scenario (the line is a single observed
                number), so it moves little between scenarios; if the market has not yet priced the QB news, the football-only column shows the size of the effect.</p>
            </div>
          )}

          <div className="panel">
            <h2>Model comparison</h2>
            <div className="table-wrap"><table>
              <thead><tr><th>Model</th><th className="r">{A}</th><th className="r">{H}</th><th className="r">Margin</th><th className="r">Total</th>
                <th className="r">P({H} win)</th><th className="r">95% margin range</th><th className="r">80% total range</th></tr></thead>
              <tbody>{models.map(([name, m, desc]) => m ? (
                <tr key={name} className={name.startsWith("Combined") && e.market_inputs_used ? "hl" : undefined}>
                  <td title={desc}>{name}</td><td className="r">{f1(m.away_pts)}</td><td className="r">{f1(m.home_pts)}</td>
                  <td className="r">{marginText(m.margin, H, A)}</td><td className="r">{f1(m.total)}</td><td className="r">{pct(m.p_home)}</td>
                  <td className="r">{rangeFmt(m.intervals.margin_95, H, A)}</td>
                  <td className="r">{f1(m.intervals.total_80[0])}–{f1(m.intervals.total_80[1])}</td>
                </tr>) : (
                <tr key={name}><td>{name}</td><td colSpan={7} className="muted">Not available (no market line before the cutoff)</td></tr>))}
              </tbody></table></div>
            {e.market && (
              <p className="small ink2" style={{ marginTop: 10 }}>
                Market inputs: {spreadText(e.market.home_spread, H, A)}, total {f1(e.market.total)} · source:{" "}
                {e.market.source === "the_odds_api" && e.market.n_bookmakers
                  ? `The Odds API (median of ${e.market.n_bookmakers} US bookmakers)`
                  : MARKET_SOURCE[e.market.source] ?? "recorded in the release file"}
                {e.market.provider_updated_at ? <> · provider updated <LocalTime venueTz={g.venue_tz} iso={e.market.provider_updated_at} /></> : null}
                {" "}· retrieved by us <LocalTime venueTz={g.venue_tz} iso={e.market.retrieved_at ?? e.market.snapshot_at} />.
                These two numbers are inputs to the combined model; no prices or odds are used.
                {e.market.source !== "the_odds_api" && e.market.fallback_reason && e.market.feed_version
                  ? <> Fallback line: {e.market.fallback_reason}.</> : null}
              </p>
            )}
          </div>

          <div className="two-col">
            <div className="panel">
              <h2>Lineup assumptions</h2>
              <div className="two-col">
                <Lineup side={e.lineup.away} abbr={A} />
                <Lineup side={e.lineup.home} abbr={H} />
              </div>
              {e.notable_injuries.length > 0 && (
                <details style={{ marginTop: 10 }}>
                  <summary>Listed injuries ({e.notable_injuries.length})</summary>
                  <table style={{ marginTop: 8 }}><thead><tr><th>Team</th><th>Player</th><th>Pos</th><th>Status</th></tr></thead><tbody>
                    {e.notable_injuries.map((i) => <tr key={i.team + i.full_name}><td>{i.team}</td><td>{i.full_name}</td><td>{i.position}</td><td>{i.report_status}</td></tr>)}
                  </tbody></table>
                  <p className="small muted" style={{ marginTop: 6 }}>
                    Shown for context. Non-QB injury features were tested and not selected (no measurable gain once the market line is known).
                  </p>
                </details>
              )}
            </div>
            <div className="panel">
              <h2>What moved the combined model</h2>
              {e.contributions.length ? (
                <>
                  <table><thead><tr><th>Feature</th><th className="r">Effect on margin (pts)</th></tr></thead><tbody>
                    {e.contributions.map((c) => <tr key={c.feature}><td>{c.feature}</td><td className="r">{c.margin_points >= 0 ? "+" : ""}{f2(c.margin_points)}</td></tr>)}
                  </tbody></table>
                  <p className="small muted" style={{ marginTop: 8 }}>
                    Largest contributions to the model&apos;s adjustment of the market margin (positive favours {H}). This explains the fitted
                    model, not football cause and effect. The adjustments are small because validation showed the market line is hard to improve on.
                  </p>
                </>
              ) : <p className="muted">Not available for the football-only fallback.</p>}
            </div>
          </div>

          <div className="two-col">
            <div className="panel">
              <h2>Data freshness at this forecast</h2>
              {e.data_freshness ? (
                <>
                  <p className={dataProblems(e).length === 0 ? "small ink2" : "small tag warn"} style={{ whiteSpace: "normal" }}>
                    {dataProblems(e).length === 0 ? "All sources were fresh and complete at the cutoff."
                      : `Incomplete at the cutoff: ${dataProblems(e).map((p) => problemText(p, H, A)).join("; ")}. Documented fallbacks were used (see Lineup assumptions).`}</p>
                  <div className="table-wrap"><table>
                    <thead><tr><th>Source</th><th>State</th><th>Provider updated</th><th>Last checked by us</th></tr></thead>
                    <tbody>{e.data_freshness.sources.map((s) => (
                      <tr key={s.source} title={s.detail}><td>{SOURCE_NAME[s.source] ?? s.source}</td><td>{STATE_TEXT[s.state] ?? s.state}</td>
                        <td>{iso16(s.provider_last_modified)}</td><td>{iso16(s.last_confirmed_at)}</td></tr>))}</tbody>
                  </table></div>
                  <p className="small muted" style={{ marginTop: 6 }}>
                    Market line age at the cutoff: {e.data_freshness.market_line_age_hours ?? "—"} h. A source counts as stale if the
                    provider has not updated it for 36 h (8 days for rosters) or we have not re-checked it for 36 h.</p>
                </>
              ) : <p className="small muted">Freshness was not recorded for this (older) release version.</p>}
            </div>
            <div className="panel">
              <h2>Weather (display only)</h2>
              {e.weather?.available ? (
                <>
                  <p>{e.weather.exposure === 0 ? "Closed roof: weather does not apply." :
                    `${f1(e.weather.temperature_c)} °C, wind ${f1(e.weather.wind_kmh)} km/h (gusts ${f1(e.weather.gust_kmh)}), precipitation ${f1(e.weather.precip_mm)} mm at kickoff${e.weather.exposure === 0.5 ? " (retractable roof, status unknown)" : ""}.`}</p>
                  <p className="small muted">Open-Meteo forecast observed {iso16(e.weather.observed_at_utc)}, {f1(e.weather.lead_hours)} h before kickoff.
                    Weather is not a model input: it did not pass the feature-group evaluation (see Performance).</p>
                </>
              ) : <p className="small muted">{e.weather?.note ?? "No weather snapshot for this release version."}</p>}
            </div>
          </div>

          {e.team_efficiency && (
            <div className="panel">
              <h2>Team efficiency entering the game</h2>
              <p className="small ink2">As-of values at the forecast cutoff: exponentially weighted, shrunk toward league average, prior-season games down-weighted.</p>
              <div className="table-wrap"><table>
                <thead><tr><th>Measure</th><th className="r">{A}</th><th className="r">{H}</th></tr></thead>
                <tbody>{EFF_ROWS.map(([k, label, better, fmt]) => {
                  const a = e.team_efficiency!.away[k], h = e.team_efficiency!.home[k];
                  const aBetter = better === "hi" ? a > h : a < h;
                  return <tr key={k}><td>{label}</td>
                    <td className="r" style={{ fontWeight: aBetter && k !== "games_this_season" ? 800 : 400 }}>{fmt(a)}</td>
                    <td className="r" style={{ fontWeight: !aBetter && k !== "games_this_season" ? 800 : 400 }}>{fmt(h)}</td></tr>;
                })}</tbody></table></div>
            </div>
          )}
        </>
      )}

      {g.history.length > 0 && (
        <div className="panel">
          <h2>Forecast history</h2>
          <div className="table-wrap"><table>
            <thead><tr><th>Generated (cutoff)</th><th>Public evidence</th><th className="r">{A}</th><th className="r">{H}</th><th className="r">Margin</th>
              <th className="r">Total</th><th className="r">P({H})</th><th className="r">Market</th><th>State</th><th>Verification</th><th>Archive</th></tr></thead>
            <tbody>{g.history.map((h) => (
              <tr key={h.run_id} className={h.run_id === g.forecast_run_id ? "hl" : undefined}>
                <td><LocalTime venueTz={g.venue_tz} iso={h.generated_at} /></td>
                <td>{h.public_evidence_at ? <LocalTime venueTz={g.venue_tz} iso={h.public_evidence_at} /> : "not yet evidenced"}</td>
                <td className="r">{f1(h.away_pts)}</td><td className="r">{f1(h.home_pts)}</td>
                <td className="r">{h.margin != null ? marginText(h.margin, H, A) : "—"}</td><td className="r">{f1(h.total)}</td><td className="r">{pct(h.p_home)}</td>
                <td className="r">{h.market_spread != null ? `${spreadText(h.market_spread, H, A)} / ${f1(h.market_total)}` : "—"}</td>
                <td title={Object.values(h.validation_problems ?? {}).flat().length ? "Failed the automatic consistency checks; kept for the audit record only" : undefined}><StateLabel state={h.version_state} kickoff={g.kickoff_utc} /></td>
                <td className="small">{VERIFY_LABEL[h.verification] ?? h.verification}</td>
                <td className="small" title={h.archive?.sha256 ? `SHA-256 ${h.archive.sha256}` : ""}>
                  {h.archive?.sha256 ? <>sha {h.archive.sha256.slice(0, 10)}…
                    {h.archive.rfc3161_time ? <> · timestamped {h.archive.rfc3161_time}</> : null}
                    {h.archive.web_archive_copy ? <> · <a href={h.archive.web_archive_copy}>Web Archive copy</a></> : null}</> : "—"}
                </td>
              </tr>))}</tbody></table></div>
          <p className="small muted" style={{ marginTop: 8 }}>
            Every version is kept. The information cutoff of each version is its generation time. The highlighted row is the current version:
            the latest <i>valid</i> version generated before kickoff. Before kickoff it may still be replaced; at kickoff it is locked; once
            the game is final it is scored. Versions that failed validation are never shown as current or scored. &quot;Public evidence&quot; is
            GitHub&apos;s own record of when the file was first pushed, independent of this project&apos;s clock. Each version is also archived
            outside GitHub Actions: its SHA-256 hash, an RFC 3161 trusted timestamp (proves the exact file existed at that time) and an
            Internet Archive copy of the public file (checked byte-for-byte against the hash).</p>
        </div>
      )}

      {g.score && f && (
        <div className="panel">
          <h2>Result vs forecast</h2>
          <p>Actual margin {marginText(g.score.home - g.score.away, H, A)} (forecast {marginText(f.margin, H, A)}, error {f1(Math.abs(f.margin - (g.score.home - g.score.away)))} pts);
            actual total {g.score.home + g.score.away} (forecast {f1(f.total)}, error {f1(Math.abs(f.total - (g.score.home + g.score.away)))}).</p>
        </div>
      )}
    </>
  );
}
