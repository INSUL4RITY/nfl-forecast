import Link from "next/link";
import { notFound } from "next/navigation";
import LocalTime from "@/components/LocalTime";
import TeamBadge from "@/components/TeamBadge";
import { allGames, findGame, getTeams } from "@/lib/data";
import { f1, f2, f3, marginText, pct, spreadText } from "@/lib/format";
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

function Lineup({ side, abbr }: { side: LineupSide; abbr: string }) {
  const src: Record<string, string> = {
    depth_chart_daily: "latest daily depth chart",
    previous_game_starter: "previous game's starter (no depth chart available)",
    depth_chart_weekly: "weekly depth chart",
    none: "unknown",
  };
  return (
    <div>
      <h3>{abbr}: {side.expected_qb ?? "unknown"}</h3>
      <p className="small ink2">
        Source: {src[side.source ?? "none"] ?? side.source}{side.depth_chart_at ? ` (snapshot ${side.depth_chart_at.slice(0, 10)})` : ""}.
        {side.qb1 && side.qb1 !== side.expected_qb ? ` Depth-chart QB1: ${side.qb1}.` : ""}
        {side.qb1_status ? ` Injury report: ${side.qb1_status}.` : ""}
        {side.qb1_practice ? ` Practice: ${side.qb1_practice}.` : ""}
      </p>
      {side.scenarios.length > 1 && (
        <table><thead><tr><th>Scenario</th><th className="r">Weight</th></tr></thead><tbody>
          {side.scenarios.map((s) => <tr key={s.qb_id ?? "x"}><td>{s.qb} starts</td><td className="r">{pct(s.p)}</td></tr>)}
        </tbody></table>
      )}
      {side.note && <p className="small tag warn" style={{ display: "inline-block" }}>{side.note}</p>}
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
            <LocalTime iso={g.kickoff_utc} kickoff known={g.kickoff_time_known} /> · {g.stadium}{g.neutral_site ? " (neutral site)" : ""}
            {g.roof ? ` · ${g.roof}` : ""} · {g.game_type === "REG" ? "Regular season" : "Playoffs"}
          </div>
        </div>
        {g.score && (
          <div className="stat"><span className="lbl">Final</span>
            <span className="big">{A} {g.score.away} – {g.score.home} {H}</span></div>
        )}
      </div>

      {!e || !f ? (
        <div className="panel pending">
          {g.forecast_state === "not_archived"
            ? "No pregame forecast was archived for this game. Nothing is shown rather than a forecast reconstructed after the fact."
            : "Forecast pending."}
        </div>
      ) : (
        <>
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

          {e.lineup_uncertain && (
            <div className="callout warn"><b>Lineup uncertain.</b> This forecast is a probability-weighted mix of starting-QB scenarios.
              Lineup uncertainty is shown here separately from the win probability.
              {e.scenario_forecasts && e.scenario_forecasts.length > 1 && (
                <div className="table-wrap" style={{ marginTop: 8 }}><table>
                  <thead><tr><th>Scenario</th><th className="r">Weight</th><th className="r">Combined margin</th><th className="r">Football-only margin</th></tr></thead>
                  <tbody>{e.scenario_forecasts.map((s, i) => (
                    <tr key={i}><td>{s.away_qb ?? "?"} vs {s.home_qb ?? "?"}</td><td className="r">{pct(s.p)}</td>
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
                Market inputs: {spreadText(e.market.home_spread, H, A)}, total {f1(e.market.total)} · source {e.market.source} · observed{" "}
                <LocalTime iso={e.market.snapshot_at} />. These two numbers are inputs to the combined model; no prices or odds are used.
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
            <thead><tr><th>Generated</th><th>Release</th><th className="r">{A}</th><th className="r">{H}</th><th className="r">Margin</th>
              <th className="r">Total</th><th className="r">P({H})</th><th className="r">Market</th><th>Status</th></tr></thead>
            <tbody>{g.history.map((h) => (
              <tr key={h.run_id} className={h.run_id === g.forecast_run_id ? "hl" : undefined}>
                <td><LocalTime iso={h.generated_at} /></td><td>{h.label}</td><td className="r">{f1(h.away_pts)}</td><td className="r">{f1(h.home_pts)}</td>
                <td className="r">{marginText(h.margin, H, A)}</td><td className="r">{f1(h.total)}</td><td className="r">{pct(h.p_home)}</td>
                <td className="r">{h.market_spread != null ? `${spreadText(h.market_spread, H, A)} / ${f1(h.market_total)}` : "—"}</td>
                <td>{h.before_kickoff ? (h.run_id === g.forecast_run_id ? "frozen (scored)" : "superseded") : "after kickoff (not scored)"}</td>
              </tr>))}</tbody></table></div>
          <p className="small muted" style={{ marginTop: 8 }}>The highlighted version is the last one generated before kickoff; results are scored against it.</p>
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
