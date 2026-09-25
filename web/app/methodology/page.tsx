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
        <h2>Quarterback availability (live forecasts)</h2>
        <p>Every relevant quarterback is checked: the depth-chart QB1, QB2 and QB3 (from the latest daily depth-chart snapshot at or before the cutoff)
          and the team&apos;s most recent actual starter. Each gets a status with its evidence and observation time: listed on the team&apos;s published injury
          report, not on a published report, <b>no report published yet</b>, <b>stale report</b>, or a documented manual override.
          Missing or stale information is never treated as confirmed availability.</p>
        <p>Start probabilities come from history, not assumptions. From 2016–2025 depth charts, injury reports and actual starters:
          for example, with daily depth charts a QB1 not on the report started 99.5% of the time (416/417), a Questionable QB1 about 58% (weekly
          charts, 112/193), Doubtful 0/31 and Out 0/153. With no report yet, a QB1 who finished the previous game started 97% of the time, but one who
          took under 75% of his team&apos;s dropbacks started only about 60%. Backups are checked the same way; a backup is never promoted without
          checking his own availability. The starter is chosen sequentially: QB1 starts with his probability, otherwise the next available QB, and so on.</p>
        <p>When the starter is uncertain, the forecast is a probability-weighted mix of QB scenarios, and &quot;lineup uncertain&quot; is shown separately
          from the win probability (when the leading QB is below 90%, or evidence is missing or stale). A stale depth chart (older than 4 days or than
          the team&apos;s last game) is flagged and the last actual starter leads. Documented overrides (a public source and its publication time are
          required) apply only to forecasts made after that publication time.</p>
      </div>

      <div className="panel">
        <h2>Historical approximations in the backtest</h2>
        <ul>
          <li><b>Actual-starter proxy.</b> For the final-pregame horizon, historical backtests use the QB who actually started as the &quot;expected&quot;
            starter. Starters are usually known from inactive lists about 90 minutes before kickoff, but this is an approximation that knows the answer in
            the rare late switch. Live forecasts use the evidence-based availability model above instead, so live accuracy may be slightly worse.
            The early (72-hour) horizon uses the weekly depth chart or the previous starter.</li>
          <li><b>Untimed closing lines.</b> Historical spreads and totals are a single untimed line per game, roughly the closing line. Market-based
            models are therefore validated only at the final-pregame horizon, and they may benefit from information that arrived close to kickoff.
            Live forecasts use the line observed at release time.</li>
          <li><b>Non-QB injuries are display-only.</b> A non-QB availability feature was built and tested; it added nothing once the market line was
            included, so no current model uses it. Listed injuries are shown for context only.</li>
          <li><b>Not modelled:</b> weather (archived operational forecasts exist only from about April 2026) and coaching or play-caller changes
            (no free source with dates).</li>
        </ul>
      </div>

      <div className="panel">
        <h2>Releases, versions and publication</h2>
        <ul>
          <li>The pipeline checks every 30 minutes. A new release is made when any game&apos;s inputs change (market spread or total, quarterback
            availability, the injury report, team form from newly completed games, or the model version), in the hour before each kickoff, and at least
            daily. Every version is kept; no game is updated after kickoff.</li>
          <li>Each forecast is validated before it can be shown or scored: non-negative scores, margin = home − away, total = home + away, probabilities
            in [0, 1] summing to 1, no playoff ties, ordered and nested intervals containing the forecast. If the combined forecast fails, a validated
            football-only forecast is used and labelled; if nothing passes, the previous valid version stays current.</li>
          <li><b>States:</b> <i>latest pregame</i> (may still update), <i>locked at kickoff</i>, and <i>scored</i> (the locked version against the result).</li>
          <li><b>Three different times:</b> the information cutoff and generation time (recorded by the pipeline) and the publication time, which is
            taken only from independent evidence: GitHub&apos;s own record of when the file was first pushed. A forecast counts as <i>publicly verifiable
            pregame</i> only if that evidence predates kickoff. Errors in earlier claims are recorded in an append-only corrections log; original release
            files are never edited. For example, the first Falcons–Packers forecasts were generated before kickoff but first made public 16 minutes after it.</li>
        </ul>
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
