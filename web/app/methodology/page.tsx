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
        <p><b>Freshness is checked explicitly.</b> For injury reports, depth charts and rosters, two times are tracked: when the provider last
          updated the file, and when we last confirmed it. Either being more than 36 hours old (8 days for rosters) marks the source stale, and a
          stale source is not used as confirmation. Every game page shows these times and any problems.</p>
        <p><b>Every link in the replacement chain is validated.</b> Each QB in line is checked against the current roster (a QB on injured reserve,
          released, retired, on the practice squad or declared inactive cannot start), his injury designation, and any override. If every listed
          QB has some chance of being out, the remaining probability goes to the last usable QB and is flagged as an exhausted chain.</p>
        <p><b>Probabilities are start probabilities</b>, estimated from history and never assumed, never equal to the chance of <i>playing</i>. An
          audit of the 193 Questionable and 31 Doubtful depth-chart QB1s (2016–2024) found 112 Questionable QB1s started, 6 played without starting,
          53 were declared inactive and 22 dressed but did not play; no Doubtful QB1 started or played. The final practice level matters: Questionable
          with full practice started 36/41, limited 68/131, no practice 8/21. Rates use a Jeffreys prior, cells by practice level are shrunk toward the
          status rate (strength chosen on earlier seasons only), every rate carries a 90% interval, and the estimator was selected by testing each
          season on earlier seasons. Daily depth charts (2025) are used where a category has at least 30 cases; otherwise weekly charts (2016–2024).</p>
        <p><b>Before designations are published</b> (early in the week), a listed QB&apos;s practice line is not the same measurement as the final report
          and there is no intra-week history, so a pooled rate for QB1s on final reports is used and labelled &quot;designation pending&quot;, with the
          final-report rate for the same practice level shown as the low end of the plausible range. Intra-week report versions are now archived so this
          can be calibrated later.</p>
        <p>When the starter is uncertain, the forecast is a probability-weighted mix of QB scenarios, and &quot;lineup uncertain&quot; is shown separately
          from the win probability. Documented overrides need a public source, its publication time and an <b>expiry time</b>; they apply only between
          the two.</p>
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
          <li><b>Durable archive outside GitHub Actions.</b> Every forecast file gets a write-once manifest (SHA-256 hash, information cutoff, generation
            time, model version, input snapshots) and an append-only evidence log: an RFC 3161 trusted timestamp from FreeTSA over the hash (proves the
            exact file existed; only the hash is sent), a copy of GitHub&apos;s push record (preserved because Actions records expire), and an Internet
            Archive capture of the public, commit-pinned file whose bytes are checked against the hash. Evidence is recorded when obtained and never
            back-dated. An integrity check runs before every cycle and stops publishing if any earlier forecast file has changed.</li>
        </ul>
      </div>

      <div className="panel">
        <h2>Candidate features: collection and evaluation</h2>
        <ul>
          <li><b>Weather</b>: a forecast snapshot for the kickoff hour of every upcoming game is archived with the time it was observed (Open-Meteo,
            city-level venue coordinates, roof exposure). Evaluated separately on a retrospective 2019–2024 history (stitched short-lead forecasts, not
            what was knowable days ahead): small, statistically unclear total improvements; <b>not promoted</b>. Shown on game pages for context only.</li>
          <li><b>Non-QB injuries</b>: every injury-report version is now archived with first-observed times, building the as-of history that did not
            exist before. Evaluated separately at the final horizon (final weekly reports): no gain for the combined model; <b>not promoted</b>;
            display only.</li>
          <li>A group is promoted only if, fixed in advance, the combined model improves in the development seasons with a 95% interval below zero and
            also improves in the tuning seasons. <b>Coaching adjustments are deferred.</b></li>
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
