import { CalibrationChart, LineChart, type Series } from "@/components/charts";
import { getPerformance, getRetro } from "@/lib/data";
import { f1, f2, MODEL_NAMES, pct } from "@/lib/format";

const KEY_MODELS = ["C_resid_noinj", "A_market_raw", "B_qb", "N_naive_home"];
const COLORS: Record<string, string> = { C_resid_noinj: "var(--series-1)", A_market_raw: "var(--series-2)", B_qb: "var(--series-3)", N_naive_home: "var(--series-4)" };
const PERIOD: Record<string, string> = { tune: "2019–21 (tuning)", dev: "2022–24 (development)", locked: "2025 (locked test)" };

function metricsRows(perf: any) {
  const rows: any[] = [];
  for (const src of [perf.walk_forward, perf.locked]) {
    if (!src) continue;
    for (const r of src.summary.overall) {
      if (src === perf.locked && r.period !== "locked") continue;
      rows.push(r);
    }
  }
  return rows;
}

function outcomeRows(perf: any) {
  const rows: any[] = [];
  for (const src of [perf.walk_forward, perf.locked]) {
    if (!src) continue;
    for (const r of src.probabilities.outcome) if (src !== perf.locked || r.period === "locked") rows.push(r);
  }
  return rows;
}

export default function PerformancePage() {
  const perf = getPerformance();
  const rows = metricsRows(perf);
  const get = (period: string, model: string, h = "final") => rows.find((r) => r.period === period && r.model === model && r.horizon === h);
  const lc = get("locked", "C_resid_noinj"), lm = get("locked", "A_market_raw"), lb = get("locked", "B_qb");
  const orow = outcomeRows(perf);
  const lo = (m: string) => orow.find((r) => r.period === "locked" && r.model === m && r.horizon === "final");
  const lockedIntervals = perf.locked?.probabilities.intervals ?? [];
  const cov = (tgt: string, lv: number) => lockedIntervals.find((r: any) => r.period === "locked" && r.model === "C_resid_noinj" && r.target === tgt && r.method === "residual" && r.level === lv && r.horizon === "final");

  // cumulative chart
  const cum: any[] = perf.cumulative ?? [];
  const keys = Array.from(new Set(cum.map((r) => `${r.season}-${String(r.week).padStart(2, "0")}`))).sort();
  const xLabels = keys.map((k) => { const [s, w] = k.split("-"); return `${s} wk ${Number(w)}`; });
  const xTickIdx = keys.map((k, i) => (i === 0 || k.slice(0, 4) !== keys[i - 1].slice(0, 4) ? i : -1)).filter((i) => i >= 0);
  const series: Series[] = KEY_MODELS.map((m) => ({
    key: m, label: MODEL_NAMES[m], color: COLORS[m],
    values: keys.map((k) => { const r = cum.find((c) => c.model === m && `${c.season}-${String(c.week).padStart(2, "0")}` === k); return r && r.cum_n >= 100 ? r.cum_margin_mae : null; }),
  }));
  const calLocked = perf.locked?.probabilities.calibration.find((c: any) => c.model === "C_resid_noinj" && c.horizon === "final");
  const calDev = perf.walk_forward?.probabilities.calibration.find((c: any) => c.model === "C_resid_noinj" && c.horizon === "final");
  const pairedLocked = (perf.locked?.summary.paired ?? []).filter((p: any) => p.period === "locked" && p.b === "A_market_raw" && p.horizon === "final"
    && ["C_resid_noinj", "B_qb", "C_resid", "C_direct", "C_resid_hgb"].includes(p.a) && p.loss.startsWith("ae_"));
  const pairedDev = (perf.walk_forward?.summary.paired ?? []).filter((p: any) => p.period === "dev" && p.b === "A_market_raw" && p.horizon === "final"
    && ["C_resid_noinj", "B_qb", "C_resid", "C_direct", "C_resid_hgb"].includes(p.a) && p.loss.startsWith("ae_"));
  const pros = perf.prospective ?? { n_scored: 0 };
  const retro = getRetro(2025);

  return (
    <>
      <div className="page-head"><div>
        <div className="small muted" style={{ fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase" }}>Results &amp; validation</div>
        <h1>How good are the forecasts?</h1>
        <p className="ink2" style={{ maxWidth: 760 }}>Every number here was produced by the evaluation code on real data. There are two kinds
          of results, reported separately. <b>Retrospective backtests</b> rebuild forecasts for past seasons from team data available before each
          game, but with two approximations: the quarterback who actually started is used as a stand-in for the expected starter, and
          historical market lines are untimed (approximately closing lines). This makes them somewhat optimistic. <b>Prospective results</b> are
          forecasts that were generated before kickoff and archived with timestamps in the 2026 season; only these are genuine live tests.</p>
      </div></div>

      <div className="callout">
        <b>Plain-English verdict.</b> The market point spread and total are very hard to beat. The combined model (market + football) is
        statistically indistinguishable from the market alone: marginally better in 2022–24, marginally worse on the untouched 2025 test.
        The football-only model, which never sees the market, is clearly better than naive baselines but about 0.3 points of margin error
        worse than the market. Probabilities are well calibrated and the 80%/95% ranges cover close to 80%/95% of outcomes.
      </div>

      {lc && lm && (
        <div className="three-col">
          <div className="panel stat"><span className="lbl">2025 locked test · margin error (MAE)</span>
            <span className="big">{f2(lc.margin_mae)}</span>
            <span className="small ink2">combined · market {f2(lm.margin_mae)} · football {f2(lb?.margin_mae)} (n={lc.n_games})</span></div>
          <div className="panel stat"><span className="lbl">2025 locked test · win-probability log loss</span>
            <span className="big">{lo("C_resid_noinj")?.log_loss.toFixed(4)}</span>
            <span className="small ink2">market-only {lo("A_market_raw")?.log_loss.toFixed(4)} · football {lo("B_qb")?.log_loss.toFixed(4)} (lower is better)</span></div>
          <div className="panel stat"><span className="lbl">2025 locked test · interval coverage</span>
            <span className="big">{pct(cov("margin", 0.8)?.coverage)}</span>
            <span className="small ink2">of margins inside the 80% range · 95% range: {pct(cov("margin", 0.95)?.coverage)}</span></div>
        </div>
      )}

      <div className="panel">
        <h2>Live (prospective) results</h2>
        <p className="small ink2">Each game is scored once per horizon, against the latest <i>valid</i> version generated before the cutoff.
          &quot;Publicly verifiable&quot; means GitHub&apos;s own record shows the forecast file was public before kickoff; forecasts generated before
          kickoff on this project&apos;s machine but published later are reported separately and corrected on their game pages.</p>
        {pros.n_scored > 0 ? (
          <>
            {[["All forecasts generated before kickoff", pros.by_horizon], ["Publicly verifiable before kickoff", pros.by_horizon_publicly_verifiable ?? []]].map(([title, rowsP]: any) => (
              <div key={title} style={{ marginTop: 10 }}>
                <h3>{title}</h3>
                {rowsP.length ? (
                  <div className="table-wrap"><table>
                    <thead><tr><th>Horizon</th><th className="r">Games</th><th className="r">Margin MAE</th><th className="r">Market MAE</th>
                      <th className="r">Football MAE</th><th className="r">Total MAE</th><th className="r">Winner acc.</th><th className="r">Log loss</th><th className="r">80% coverage</th></tr></thead>
                    <tbody>{rowsP.map((r: any) => (
                      <tr key={r.horizon_type}><td>{r.horizon_type}</td><td className="r">{r.n}</td><td className="r">{f2(r.margin_mae)}</td><td className="r">{f2(r.market_margin_mae)}</td>
                        <td className="r">{f2(r.football_margin_mae)}</td><td className="r">{f2(r.total_mae)}</td><td className="r">{pct(r.winner_acc, 1)}</td>
                        <td className="r">{r.log_loss?.toFixed(4)}</td><td className="r">{pct(r.cover_m80)}</td></tr>))}</tbody></table></div>
                ) : <p className="small muted">None yet.</p>}
              </div>))}
          </>
        ) : (
          <p className="ink2">No live forecasts have been scored yet. Production releases began in 2026 week 3; results appear here as those games finish.
            Small live samples are noisy: dozens of games say little about skill.</p>
        )}
      </div>

      <div className="callout warn">
        <b>Retrospective benchmark, not live results.</b> The historical tables below are the original walk-forward benchmark (preserved
        unchanged). They rest on two approximations that live forecasts do not have: (1) the <i>actual</i> starting QB stands in for the
        expected starter at the final horizon, and (2) historical market lines are a single untimed line per game, roughly the closing line.
        Both make the historical numbers somewhat optimistic compared with genuinely prospective forecasting, which is reported separately above.
      </div>

      <div className="panel">
        <h2>Point-forecast accuracy (final pregame horizon)</h2>
        <div className="table-wrap"><table>
          <thead><tr><th>Seasons</th><th>Model</th><th className="r">Games</th><th className="r">Margin MAE</th><th className="r">Margin RMSE</th>
            <th className="r">Total MAE</th><th className="r">Total RMSE</th><th className="r">Winner acc.</th></tr></thead>
          <tbody>{["tune", "dev", "locked"].flatMap((p) => KEY_MODELS.map((m) => get(p, m)).filter(Boolean).map((r: any) => (
            <tr key={r.period + r.model} className={r.model === "C_resid_noinj" ? "hl" : undefined}>
              <td>{PERIOD[r.period]}</td><td>{MODEL_NAMES[r.model]}</td><td className="r">{r.n_games}</td><td className="r">{f2(r.margin_mae)}</td>
              <td className="r">{f2(r.margin_rmse)}</td><td className="r">{f2(r.total_mae)}</td><td className="r">{f2(r.total_rmse)}</td><td className="r">{pct(r.winner_accuracy, 1)}</td></tr>)))}
          </tbody></table></div>
        <p className="small muted" style={{ marginTop: 8 }}>Walk-forward: each season is predicted by models trained only on earlier seasons. Historical market lines are a single
          untimed line per game (approximately closing), so market comparisons apply to the final-pregame horizon. The early (72-hour) horizon can only be
          evaluated for the football-only model historically; the table in the full report covers it.</p>
      </div>

      <div className="panel">
        <h2>Cumulative margin error, 2019–2025</h2>
        <p className="small ink2">Running mean absolute margin error across all retrospective walk-forward forecasts (lower is better), shown once at least 100 games have accumulated.</p>
        <LineChart series={series} xLabels={xLabels} xTickIdx={xTickIdx} yDecimals={2} yTitle="Cumulative mean absolute margin error" />
      </div>

      <div className="panel">
        <h2>Paired comparison with the market-only benchmark</h2>
        <p className="small ink2">Difference in mean absolute error on the same games (model minus market; negative = better than the market), with 95%
          intervals from a season-week block bootstrap. Intervals that include zero mean no demonstrated difference.</p>
        <div className="table-wrap"><table>
          <thead><tr><th>Seasons</th><th>Model</th><th>Target</th><th className="r">Games</th><th className="r">Difference</th><th className="r">95% interval</th></tr></thead>
          <tbody>{[...pairedDev.map((p: any) => ({ ...p, per: "dev" })), ...pairedLocked.map((p: any) => ({ ...p, per: "locked" }))].map((p: any) => (
            <tr key={p.per + p.a + p.loss} className={p.a === "C_resid_noinj" ? "hl" : undefined}><td>{PERIOD[p.per]}</td><td>{MODEL_NAMES[p.a] ?? p.a}</td>
              <td>{p.loss === "ae_margin" ? "margin" : "total"}</td><td className="r">{p.n_games}</td><td className="r">{p.mean_diff >= 0 ? "+" : ""}{p.mean_diff.toFixed(3)}</td>
              <td className="r">[{p.ci95[0].toFixed(3)}, {p.ci95[1].toFixed(3)}]</td></tr>))}</tbody></table></div>
      </div>

      <div className="two-col">
        <div className="panel">
          <h2>Probability calibration</h2>
          <p className="small ink2">Combined model, final horizon. Dots on the dashed line mean the probabilities meant what they said; dot size grows with the number of games.</p>
          {calLocked && <><h3>2025 locked test</h3><CalibrationChart bins={calLocked.table} color="var(--series-1)" label="2025" /></>}
          {calDev && <details><summary>2022–24 development</summary><CalibrationChart bins={calDev.table} color="var(--series-1)" label="2022-24" /></details>}
        </div>
        <div className="panel">
          <h2>Win-probability scores</h2>
          <div className="table-wrap"><table>
            <thead><tr><th>Seasons</th><th>Model</th><th className="r">n</th><th className="r">Log loss</th><th className="r">Brier</th></tr></thead>
            <tbody>{orow.filter((r) => r.horizon === "final").map((r) => (
              <tr key={r.period + r.model} className={r.model === "C_resid_noinj" ? "hl" : undefined}><td>{PERIOD[r.period]}</td><td>{MODEL_NAMES[r.model]}</td>
                <td className="r">{r.n}</td><td className="r">{r.log_loss.toFixed(4)}</td><td className="r">{r.brier_3class.toFixed(4)}</td></tr>))}</tbody></table></div>
          <h3 style={{ marginTop: 16 }}>Interval coverage (combined model)</h3>
          <div className="table-wrap"><table>
            <thead><tr><th>Seasons</th><th>Target</th><th className="r">Nominal</th><th className="r">Actual</th><th className="r">Mean width (pts)</th></tr></thead>
            <tbody>{[...(perf.walk_forward?.probabilities.intervals ?? []).filter((r: any) => r.period === "dev"), ...lockedIntervals.filter((r: any) => r.period === "locked")]
              .filter((r: any) => r.model === "C_resid_noinj" && r.method === "residual" && r.horizon === "final").map((r: any) => (
                <tr key={r.period + r.target + r.level}><td>{PERIOD[r.period]}</td><td>{r.target}</td><td className="r">{pct(r.level)}</td>
                  <td className="r">{pct(r.coverage, 1)}</td><td className="r">{f1(r.mean_width)}</td></tr>))}</tbody></table></div>
        </div>
      </div>

      {perf.feature_groups && (
        <div className="panel">
          <h2>Candidate feature groups (evaluated separately before promotion)</h2>
          <p className="small ink2">Promotion rule, fixed before results were seen: the combined model must improve the group&apos;s target loss in
            the development seasons with a 95% interval entirely below zero, and also improve it in the tuning seasons. The 2025 locked season is
            not used. Negative differences mean the group helped.</p>
          {perf.feature_groups.results.map((r: any) => (
            <div key={r.group} style={{ marginTop: 12 }}>
              <h3>{r.group}: {r.decision}</h3>
              <p className="small muted">Inputs: {r.inputs}.{r.early_horizon ? ` Early horizon: ${r.early_horizon}.` : ""}</p>
              <div className="table-wrap"><table>
                <thead><tr><th>Model</th><th>Seasons</th><th className="r">Games</th><th className="r">Loss difference</th><th className="r">95% interval</th>
                  <th className="r">Total RMSE without → with</th></tr></thead>
                <tbody>{(["combined", "football_only"] as const).flatMap((arm) => Object.entries(r[arm] ?? {}).map(([per, x]: any) => (
                  <tr key={arm + per}><td>{arm === "combined" ? "Combined" : "Football only"}</td><td>{per === "dev" ? "development" : "tuning"}</td>
                    <td className="r">{x.paired_target.n_games}</td><td className="r">{x.paired_target.mean_diff.toFixed(3)}</td>
                    <td className="r">[{x.paired_target.ci95[0].toFixed(3)}, {x.paired_target.ci95[1].toFixed(3)}]</td>
                    <td className="r">{x.metrics_base.total_rmse.toFixed(3)} → {x.metrics_candidate.total_rmse.toFixed(3)}</td></tr>)))}</tbody>
              </table></div>
            </div>))}
          <p className="small muted" style={{ marginTop: 8 }}>Coaching changes are deferred (no dated source). Weather forecasts and every injury-report
            version are now collected before each game, so both groups can later be re-evaluated on strictly as-of data.</p>
        </div>
      )}

      {perf.qb_rates && (
        <div className="panel">
          <h2>Quarterback start-probability audit</h2>
          <p className="small ink2">What the historical rates measure: whether the depth-chart QB1 <b>started</b>. That is not the same as playing
            or being active. Rates carry 90% intervals, and each test season is predicted from earlier seasons only.</p>
          <div className="table-wrap"><table>
            <thead><tr><th>Final status</th><th>Final practice</th><th className="r">Cases</th><th className="r">Started</th>
              <th className="r">Played, not started</th><th className="r">Declared inactive</th><th className="r">P(start), 90% interval</th></tr></thead>
            <tbody>{perf.qb_rates.audit.map((a: any) => (
              <tr key={a.status + a.practice}><td>{a.status}</td><td>{a.practice}</td><td className="r">{a.n}</td><td className="r">{a.started}</td>
                <td className="r">{a.played_not_started}</td><td className="r">{a.declared_inactive}</td>
                <td className="r">{a.p_start_jeffreys.toFixed(2)} ({a.ci90[0].toFixed(2)}–{a.ci90[1].toFixed(2)})</td></tr>))}</tbody>
          </table></div>
          <div className="table-wrap" style={{ marginTop: 8 }}><table>
            <thead><tr><th>Estimator</th><th>Cases</th><th className="r">Log loss</th><th className="r">Brier</th><th className="r">Mean predicted</th><th className="r">Observed</th></tr></thead>
            <tbody>{perf.qb_rates.evaluation.uncertain.map((r: any) => (
              <tr key={r.method} className={r.method === "status_x_practice" ? "hl" : undefined}><td>{r.method.replace(/_/g, " ")}</td><td>Questionable + Doubtful ({r.n})</td>
                <td className="r">{r.log_loss.toFixed(4)}</td><td className="r">{r.brier.toFixed(4)}</td><td className="r">{r.mean_pred.toFixed(3)}</td>
                <td className="r">{r.obs_rate.toFixed(3)}</td></tr>))}</tbody>
          </table></div>
          <p className="small muted" style={{ marginTop: 6 }}>The practice-aware estimator (highlighted) is used. Across all QB1 games it is better with a
            95% interval excluding zero; on the 162 Questionable/Doubtful cases the gain is not statistically established. All estimators over-predict
            starts for listed QBs in recent seasons (the rate has drifted down); this is reported, not adjusted.</p>
        </div>
      )}

      {retro && (
        <div className="panel">
          <h2>Archive: 2025 retrospective forecasts</h2>
          <p className="small ink2">{retro.label}. Combined model shown; these were not published before the games.</p>
          <details><summary>Show {retro.rows.filter((r: any) => r.model === "C_resid_noinj").length} games</summary>
            <div className="table-wrap"><table>
              <thead><tr><th>Wk</th><th>Game</th><th className="r">Forecast</th><th className="r">P(home)</th><th className="r">Final</th><th className="r">Margin error</th></tr></thead>
              <tbody>{retro.rows.filter((r: any) => r.model === "C_resid_noinj").map((r: any) => (
                <tr key={r.game_id}><td>{r.week}</td><td>{r.away_team} @ {r.home_team}</td>
                  <td className="r">{f1(r.pred_away)}–{f1(r.pred_home)}</td><td className="r">{pct(r.p_home)}</td>
                  <td className="r">{r.away_score}–{r.home_score}</td><td className="r">{f1(Math.abs(r.pred_margin - (r.home_score - r.away_score)))}</td></tr>))}</tbody>
            </table></div>
          </details>
        </div>
      )}

      <p className="small muted">The 2025 locked test was run once, on {perf.locked?.manifest.generated_at_utc?.slice(0, 10)}, after the production model was frozen.
        Later changes (quarterback availability, validation and publication handling in releases) affect live forecasts only; the evaluated model
        itself is unchanged. Any future evaluation of a revised model on 2025 will be labelled a re-evaluation, not an untouched test.</p>
      <p className="small muted">Evaluation runs: walk-forward {perf.walk_forward?.run_id} · locked test {perf.locked?.run_id} (code {perf.locked?.manifest.code_hash?.slice(0, 12)}).
        Full reports: reports/backtest/LATEST.md and reports/locked_test/LATEST.md in the repository.</p>
    </>
  );
}
