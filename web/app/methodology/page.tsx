export default function Methodology() {
  return (
    <>
      <div className="page-head"><div>
        <div className="small muted" style={{ fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase" }}>How it works</div>
        <h1>Methodology, data &amp; limitations</h1>
      </div></div>

      <div className="panel">
        <h2>What is forecast</h2>
        <p>For every regular-season and playoff game: expected home and away points (including overtime), the expected margin (home minus away),
          the expected total, win/loss/tie probabilities, and 80% and 95% ranges for the margin and total. Scores are <b>means</b>; a projected 23.7 is
          not a possible final score and does not imply tenth-of-a-point precision. Regular-season games carry a small explicit tie probability
          (the smoothed tie rate since the 2017 overtime change, about 0.35%); playoff games cannot tie.</p>
        <p>Forecasts are released as immutable, timestamped files. The information cutoff is the release time. A game is scored against the last version
          released before kickoff (and, separately, the last version at least 72 hours before kickoff), never against a later model run.</p>
      </div>

      <div className="panel">
        <h2>Three model families</h2>
        <div className="three-col">
          <div><h3>Market only (benchmark)</h3><p className="small">The point spread <i>s</i> (negative when home is favoured) and total <i>t</i> become
            M₀ = −s, T₀ = t, home = (T₀+M₀)/2, away = (T₀−M₀)/2. No prices, moneylines or implied odds are used anywhere in the project.</p></div>
          <div><h3>Football only</h3><p className="small">Ridge regression on each team&apos;s offence against the opponent&apos;s defence: EPA per play,
            passing and rushing efficiency, success and explosive-play rates, sacks, turnovers, pace, points per drive, red-zone and field position,
            opponent-adjusted ratings, the expected starting QB&apos;s rating and experience, change versus the QBs behind the team&apos;s recent stats,
            rest, byes, venue and roof. It is also the fallback when no market line exists.</p></div>
          <div><h3>Combined (selected)</h3><p className="small">Starts from the market line and learns a regularised correction:
            M̂ = M₀ + g(X), T̂ = T₀ + h(X). Strong regularisation (chosen on earlier seasons) keeps it close to the line unless football information
            has shown value. A direct formulation and a gradient-boosting variant were tested and not selected.</p></div>
        </div>
      </div>

      <div className="panel">
        <h2>Preventing look-ahead</h2>
        <ul>
          <li>A completed game only counts once its data would have been available (kickoff + 12 hours) before the forecast cutoff. This applies to team form,
            the league averages used for shrinkage, and opponent-adjusted ratings, which are re-fitted for every information state.</li>
          <li>Validation is walk-forward: each season is predicted by models trained on earlier seasons only. Settings were chosen on 2019–21,
            the models were developed on 2022–24, and 2025 was held back and evaluated once after all choices were frozen.</li>
          <li>Probability calibration and interval widths are learned from earlier seasons&apos; out-of-fold predictions only.</li>
          <li>Neutral-situation filters use the pre-play score and quarter, not a market-informed win probability. Spread-derived
            win-probability columns are removed on ingestion.</li>
          <li>Automated tests check leakage (adding a future game cannot change a frozen feature), spread sign conventions, M = H − A and T = H + A,
            non-negative scores, probabilities summing to one, zero tie probability in playoffs, and interval ordering.</li>
        </ul>
      </div>

      <div className="panel">
        <h2>Injuries and quarterbacks</h2>
        <p>The expected starting QB comes from the latest daily depth-chart snapshot before the cutoff, checked against the current injury report.
          If the starter is listed Out or Doubtful, the backup is expected. If he is Questionable (or missed practice), the forecast becomes a weighted mix
          of two scenarios, using the share of historically Questionable players who actually played. That lineup uncertainty is shown separately from
          the win probability. QB ratings follow players across teams and are shrunk toward a prior for inexperienced QBs.</p>
        <p>Non-QB availability (expected snaps lost by position group, weighted by how often each injury status actually misses games) was built and
          tested. It helped the football-only model slightly but added nothing once the market line was included, so the selected model does not use it.
          Listed injuries are shown for context.</p>
      </div>

      <div className="panel">
        <h2>Data sources and what is missing</h2>
        <ul>
          <li><b>nflverse</b> (CC-BY 4.0): play-by-play with EPA/CPOE, schedules, scores, depth charts, injury reports, snap counts, rosters.
            Advanced FTN charting (CC-BY-SA 4.0, &quot;FTN Data via nflverse&quot;) exists from 2022 but is not used yet.</li>
          <li><b>No free timestamped history of betting lines.</b> Historical lines are one untimed value per game (about the closing line), so market-based
            models are validated only at the final-pregame horizon. From September 2026 this project archives its own line snapshots, which will allow
            early-horizon evaluation over time.</li>
          <li><b>Injury reports:</b> only the final weekly report survives historically, so early-week injury information cannot be backtested.</li>
          <li><b>Weather:</b> archived operational forecasts exist only from about April 2026, so weather is not in the historical model.</li>
          <li><b>Coordinators and play-callers:</b> not available in any free feed; not modelled.</li>
          <li>nflverse republishes EPA with model updates, so historical backtests are close, but not exact, reconstructions of what was knowable at the time.</li>
        </ul>
      </div>

      <div className="panel">
        <h2>Limitations</h2>
        <ul>
          <li>An NFL game is noisy: even the best forecasts miss the margin by about 10 points on average, and the 80% range spans about 32 points.</li>
          <li>Seven seasons of backtests is limited evidence; paired comparisons use week-block bootstrap intervals and many are indistinguishable from zero.</li>
          <li>The early-horizon combined forecast applies a model validated at the final horizon to the line observed at release time; its accuracy is being
            measured live.</li>
          <li>Model &quot;contributions&quot; describe the fitted model, not causes on the field.</li>
        </ul>
      </div>
    </>
  );
}
