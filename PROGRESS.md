# Progress log — nflcast

Spec: `C:\Users\Craig\Downloads\NFL_Forecasting_Claude_Build_Brief.md`. Rules: `CLAUDE.md`. Live site:
https://insul4rity.github.io/nfl-forecast/ (public repo INSUL4RITY/nfl-forecast). Last updated 2026-09-25 (session 7).
Market feed: **v2 from 2026-09-25 13:23 UTC** — The Odds API (median of US bookmakers, spreads/totals only) when valid and
fresh, nflverse schedule line as fallback. Forecasts before `rel_20260925T132351Z` used nflverse lines and are unchanged.

## 1. Current model version (FROZEN for the rest of the 2026 season)
| Item | Value |
|---|---|
| Version | **v1.0-2026-rest-of-season**, frozen 2026-09-25T02:13:28Z, valid through the end of the 2026 postseason |
| Record / artifact | `configs/model_freeze.yaml`; `artifacts/frozen/v1.0-2026-rest-of-season/production.joblib` (sha256 66e9d500c8b4a8c1…) |
| Primary | Combined residual-to-market ridge (C_resid, feature set core_qb): market spread/total + football features incl. QB layer |
| Fallback | Football-only ridge (B, core_qb) when no line or when the combined forecast fails validation |
| Benchmark | Market-only (spread/total mapped to scores) |
| Training data | 2,793 completed final-horizon games, 2016 → 2026_02_NYG_LA |
| Probabilities / intervals | Logistic on predicted margin + smoothed tie rate; OOF residual quantiles (locked-test run locked_20260924T234835Z) |
| QB start rates | key v3_start_practice_listed_through_2025 (Jeffreys; status × practice shrinkage m=10; daily charts where n ≥ 30) |
| Verified | fitted-vs-frozen forecasts identical (max abs diff 0.0 on 15 games); `python -m nflcast freeze-check` OK |
While frozen: no refit, retune or feature change. Scheduled runs only refresh inputs (as-of team form from completed games,
market lines, QB availability, injury display, weather display). A changed artifact/config blocks publishing.

## 2. Completed work (summary)
- M1–M7 (session 1): data audit, as-of features, market/football/combined models, probabilities/intervals, locked 2025 test
  (once), Next.js site, scheduled operation, GitHub Pages.
- Session 2 (review fixes): evidence-based QB availability; validation gate (invalid forecasts never current/scored);
  input-fingerprint releases; publication evidence from GitHub server times; append-only corrections (3 for ATL@GB, generated
  before but public after kickoff); state labels (latest pregame / locked at kickoff / scored).
- Session 3: source freshness (provider + retrieval), roster-validated QB replacement chain, expiring overrides, start≠play
  audit, practice-aware start rates with 90% intervals, designation-pending handling; durable archive (write-once manifests,
  FreeTSA RFC 3161 tokens, GitHub push-run copies, Internet Archive copies, integrity check); weather snapshot + injury-version
  collection; separate pre-specified feature-group evaluations (weather and non-QB injuries **not promoted**).
- Session 4 (this): private off-PC backup (`INSUL4RITY/nfl-forecast-data`); QB drift investigation
  (`reports/qb_availability/drift_investigation.md`: no data/calculation error; no retune); `verify-claims` re-verification;
  model freeze; client-side "locked at kickoff" label when the site is stale; CLAUDE.md.
- Session 5 (finishing, display/operations only; model untouched, freeze-check OK):
  - ATL@GB page: the three yellow "Correction" banners replaced by one compact note ("Generated before kickoff; published after
    kickoff", kickoff + first public evidence times, GitHub record) with a collapsible audit history of the 3 records.
    `releases/corrections.jsonl` and the release files are unchanged; the game stays "generated pregame, published after
    kickoff" (label comes from publication evidence) and is scored separately from publicly verifiable forecasts.
  - Every game page: internal codes and player IDs (e.g. `chain_qb_unavailable_roster:00-0040704`, `roster:RES`,
    `home QB: report_not_available`, `nflverse_schedules_archived`, `depth_chart_daily`) replaced by plain English
    ("Dillon Gabriel is on the reserve list and cannot start…", "Reserve list", "CLE QB: injury report not published yet").
    Underlying data and validation logic unchanged. `verify-claims` now fails if any built game page shows such a code
    (272 pages clean); 2 new tests.
  - Path error fixed: `nflcast.cmd` launcher runs any command from any folder (the earlier error was the relative
    `.\.venv\...` path typed in `C:\Users\Craig`).
  - Full-slate check (dry run, nothing written): the first cycle after week 3's last kickoff produces a validated forecast
    for all 16 week-4 games, even with every source deliberately stale (problems flagged, documented fallbacks used).
- Session 6 (final checks; display only, model untouched):
  - Market source: `ODDS_API_KEY` (The Odds API) exists only in the Claude session environment; the key is valid (free tier,
    0 of 500 monthly requests used) but was **never integrated** (no code reads it; the scheduled task cannot see it). All 154
    archived game forecasts record `nflverse_schedules_archived`; the game page now shows the source recorded in each release
    ("nflverse schedule data (free; snapshot archived by this project)") rather than fixed text. Nothing added. See
    `docs/data_sources.md`.
  - Performance page introduction: now states the two backtest approximations (actual starter as proxy; untimed ≈ closing
    lines) and separates retrospective backtests from genuinely prospective 2026 forecasts. Results and detailed text unchanged.
  - Time zones: the weekly date range, day headings, day filters and kickoff times are computed from each kickoff in the
    selected mode (your time zone / UK / stadium-local; stadium mode groups by each stadium's local date). Game pages follow
    the same saved mode. Week 3: UK "Fri 25 Sept – Tue 29 Sept"; stadium-local "Thu 24 Sept – Mon 28 Sept".
- Session 7 (market-feed change, user-authorised; model weights/features/calibration unchanged, freeze-check OK):
  - **Feed version change (dated): market-feed-v2, 2026-09-25.** The Odds API connected (`src/nflcast/data/odds_api.py`,
    `configs/market_feed.yaml`, not a frozen config). One request per refresh for the whole slate
    (`regions=us&markets=spreads,totals`, 2 credits); prices discarded before saving; selection rule = median home-team
    point spread and median total across valid pre-kickoff US bookmakers (>= 2), rounded to 0.5, cross-checked with
    nflverse; nflverse line used when the API line is missing, > 36 h old, fails the check, or credits are low. Rule and
    budget in `docs/data_sources.md`.
  - Key saved to git-ignored `.env`, loaded by every nflcast process (so by the scheduled task after restarts); verified a
    process without the session variable loads it. verify-claims checks the key is absent from tracked files, logs, the
    site, snapshots and the backup.
  - Budget: routine refresh when the last success is >= 6 h old (<= 4/day, ~248 credits/month); budget-checked pregame
    refresh within 100 min of a kickoff; floor 12 credits; after downtime one request (no replay).
  - Releases record source, our retrieval time, the provider's latest update time, bookmaker count, fallback reason and
    feed version; the market fingerprint now includes the source. Game pages show the source actually used.
  - **Verified through the scheduled task (13:23 UTC):** request ok (29 events, 2 credits, **498 credits remaining**);
    release `rel_20260925T132351Z` used The Odds API for all 15 remaining week-3 games (9 bookmakers each); all 29 events
    matched nflverse games, home-spread signs agree 29/29, spread/total differences <= 1 point (mean 0.17 / 0.29).
  - Found and fixed: that first release's `retrieved_at` is the request-SENT time, ~1 s before some bookmakers' update time
    (13:23:47). Recorded as correction `odds-retrieval-time:rel_20260925T132351Z` (labelling only; release unchanged). Retrieval
    time is now the response-received time and a line counts as available only from max(receipt, provider update).
- Session 8 (picks and weekly results; display/reporting only — model, feed schedule and credit budget unchanged):
  - `src/nflcast/predict/picks.py` (picks-v1): projected winner (higher win probability; equal = toss-up), winning margin,
    and "Spread lean — margin comparison" = unrounded projected margin minus the line margin (-home_spread) of the SAME
    version; side + difference in points, labelled tiny (< 0.5) / small (< 1.5) / moderate (< 3) / large; < 0.01 = "No lean".
  - New releases store their pick labels (`games[].picks`, `published_with_forecast`). For older versions the same rule is
    applied at export and the label is flagged `retrospectively_derived` (card asterisk, detail note, week footnote).
  - Grading = the scoring rule's final_pregame version (latest valid version generated before kickoff) with its own line;
    stored picks are used verbatim, never recomputed. Winner: win/loss/tie(actual)/no-pick; lean: win/loss/push/no-lean/
    no-line; mean absolute margin error. Weekly panel "Week to date" until every game is final, then "Week results
    (final)"; graded, pending and no-forecast counts; groups kept separate by publication evidence (ATL@GB stays in
    "published after kickoff").
  - Site: game cards and detail pages show projected winner + probability + margin, the market spread recorded with that
    forecast, the spread lean, forecast update time and (when final) the result grade; methodology section added.
  - Checks: 6 new tests (signs for home favourite/underdog, exact match, pushes, actual ties, toss-ups, record counts, group
    separation, post-kickoff line move cannot change the locked pick, stored pick used verbatim); verify-claims adds 4
    (stored picks match rule; graded picks use locked version + own archived line; retrospective flag; records add up).
  - First graded game: ATL@GB (ATL 35–14): pick GB (wrong), lean GB −4.5 by 0.19 pts, tiny (wrong), margin error 25.7;
    reported separately as generated pregame / published after kickoff, pick label retrospectively derived.
  - Existing performance metrics and prospective scoring (`reports/prospective/`) unchanged.
- Session 9 (presentation only; calculations, pick rules, archived lines, locking, grading and classifications unchanged):
  - Game cards: a separate prediction box beneath each game's statistics with two sections, "Projected winner" (team, win
    probability, projected winning margin) and "Model pick" (signed spread side, e.g. PIT +3.5, subtitle "Against the
    recorded spread"; "No pick" when the projection matches the line or no line was recorded). Side by side on wider
    screens, stacked below 480 px (checked at 1280 px and 375 px: all 16 week-3 boxes inside their cards, no overflow).
    Duplicate winner/lean rows removed from the statistics; the win probability appears only with the projected winner.
  - The heading "Spread lean — margin comparison" is replaced by "Model pick"; the numerical difference and its
    tiny/small/moderate/large label moved to the detail page's collapsible "Details: how the model pick is derived", with an
    explanation also given to screen readers and as a tooltip on each card.
  - Consistent wording on detail pages, results lines ("model pick (spread)") and the weekly table ("Winner record" vs
    "Model pick record (spread)"; "no pick" / "no line" / pushes listed separately); methodology text updated.
    Retrospective and publication notes kept.
- Session 10 (2026-09-28, operational input-processing fixes; model artifact/configs unchanged, freeze-check OK):
  - Bug: `snapshot_asof` kept the provider Last-Modified from the FIRST upload of unchanged content, although nflverse
    re-uploads daily (checks.jsonl had Mon 06:01 and 15:18 GMT uploads). The injury file therefore looked "stale" 36 h after
    Sunday's content change, and the resolver (correctly, by its rule) ignored it. For 2026_03_PHI_CHI, versions
    rel_20260928T181556Z, T224603Z and T231615Z lost both teams' final reports: CHI Williams 97% (he was listed Out),
    PHI Hurts 97% (vs 99.6%). Sunday's versions had it right (Bagent 54%, Keenum 46%).
  - Evidenced timeline: a first fix (resolver special case for final reports) plus a sourced override (NFL.com, published
    2026-09-28T11:32:21Z, NFL Network's Ian Rapoport: Keenum expected to start; Bagent backs up; Williams out) produced
    rel_20260928T233941Z (generated 23:39:41Z; first public evidence 23:39:49Z, GitHub run 36499179881; kickoff 00:15Z):
    CHI Keenum 100%, PHI Hurts 99.6%. Combined forecast PHI by 3.37 (was 3.36; line CHI +3.5 already priced it), football-only
    benchmark moved from CHI by 2.13 to PHI by 3.63. Picks unchanged (PHI; model pick CHI +3.5, tiny).
  - Adversarial review (3 independent reviewers) found the special case treated a symptom, contradicted the published
    methodology and misread early mid-week "Out" designations as a final report. Replaced by the root-cause fix: the provider
    time is the latest Last-Modified for the same content seen by our checks up to the cutoff (as-of). Also fixed: overrides now
    also require `entered_at_utc <= cutoff`, so rebuilds never use information entered later. Methodology texts updated.
    Tests 83 (snapshot latest-upload regression; override entry as-of; mid-week stale report still stale).
  - Earlier versions kept unchanged (superseded). Correction `qb-input:stale-final-report:2026_03_PHI_CHI` appended
    (+ a clarification: Keenum's 100% came from the NFL Network report override, not the official report).
  - Guard added (2026-09-29): a stale report still cannot confirm availability, but a QB listed Out (or Doubtful) on the
    official report for that game week keeps that status (flags `listed_out/doubtful_despite_stale_report`). Counterfactual
    with the original bug re-created: Williams 0% (Bagent 80%, Keenum 20%) instead of 97%. Week-3 replay: no other change.
    Tests 85.
- Session 11 (2026-09-29, display only): the game page's "Evidence for each quarterback" table (6 columns in a quarter-width
  column, no scroll wrapper, global no-wrap cells) spilled into the other team's column on every game page; on phones pages
  scrolled sideways (707 px on a 375 px screen) and "What moved the combined model" overflowed. Fix: "Lineup assumptions" is
  now a full-width panel; compact 4-column evidence table (QB, chart, status, if next in line) with per-QB explanations as a
  list; every table on the game page wrapped for horizontal scroll; long feature names wrap; roster wording fixed ("declared
  inactive for this game"). New `scripts/layout_audit.js` (run in the browser on the site): loads every page in hidden
  iframes at chosen widths, opens all collapsible sections and reports sideways page scroll or elements sticking out of their
  panel/card/column. Positive control: it flags the old live page (tables +388/+415 px; 707 px page at 375 px). Fixed build:
  0 issues on all 295 pages at 1280, 768, 414, 375 and 320 px (1,475 page views); live site after deploy: also 0 of 1,475.
- Research (2026-09-29, user question: should 2026 games outweigh 2025 because of coaching changes/trades?). Experiment in
  `.scratch/weighting/` (git-ignored; production untouched), walk-forward on tune 2019-21 and dev 2022-24 only:
  carry-over 0.3/0.45/0.75, half-life 12 + carry 0.45, NC (carry 0.3 for teams with a new head coach, from nflverse
  home_coach/away_coach, known before week 1; 61 team-seasons) and NQ (carry 0.3 when the expected week-1 QB differs from last
  season's primary starter). Pre-specified rule (combined model, margin loss lower than current in BOTH periods, 95% CI below
  zero): NO variant passes; none even had a lower mean in both periods. The published forecast barely responds (0.006-0.11 pts
  per game) because it is anchored to the market line, which already prices coaching/roster changes. Football-only with
  carry 0.3 was worse on average in 2019-21 (esp. weeks 1-4) but not statistically clear (review: CI depends on the bootstrap
  draw). Exploratory only: NQ lowered early-season total error (not pre-specified; re-check after the season). Independent
  review confirmed features, pairing, seasons and leakage; decision: keep half-life 8 / carry 0.6.
- Desktop alerts (2026-09-29, user-requested; no model or forecast change): `src/nflcast/predict/alerts.py` +
  `scripts/toast.ps1`, called from `operate` after publishing (best effort, never blocks a cycle). Flags, for games within
  48 h: no QB identified / no valid new forecast / injury report not current (<= 36 h; one combined alert if >= 6 teams) /
  designations pending (<= 24 h) / official Out kept despite unconfirmed data / lead QB < 90% / no line (<= 24 h); plus
  credits < 60, failed or blocked runs (separate keys per kind) and a "caught up" notice after >= 6 h without a completed run
  (states whether the upload actually succeeded). Stable keys; re-alert on change (>= 2 h apart) or after 12 h; forgotten
  after 1 h absent; only shown toasts count, failed ones retried (max 3 per 12 h). Adversarial review (3 reviewers) found 12
  issues, all fixed; tests 100. Week-3 replay (fake sender, every 30 min): 7 alerts, all genuine (WAS Daniels 70%; CHI Williams 70%, then Bagent 54% / Keenum 46% with 12 h reminders); a first version sent 33 because the countdown text counted as a change (fixed, regression test). Windows reports notifications
  DisabledForUser on this PC: the user must turn them on (Settings > System > Notifications); until then alerts are logged
  as NOT SHOWN in logs/alerts.log.
- Evaluation fix: `metrics.block_bootstrap_diff` resampled season-week blocks in polars' non-deterministic group order, so a
  fixed seed gave slightly different CIs each call (found by the review). Blocks are now sorted; regression test added
  (86 tests). Forecasts are unaffected; stored reports keep their original intervals.
- Post-outage check (2026-09-29 19:30 UTC, after the Claude app went down): all work committed and pushed (HEAD = origin),
  task running every 30 min ("operate: done", alerts open=0), freeze-check OK, tests pass, Pages deploys succeeding (the
  release-commit deploy is cancelled by the evidence commit 30 s later, by design). Fixed verify-claims reporting: an
  archive.org error page (HTTP 404/429) was hashed and reported as a content mismatch. It is now "could not check, retry
  later"; after a refusal/rate limit it stops re-downloading for that run (hammering prolongs the block). The flagged
  rel_20260926T164605Z copy re-downloaded on retry and matches byte-for-byte (the 404 was a temporary playback error).
  Re-downloading every copy back-to-back trips archive.org's rate limit, so those checks often end "retry later"; all
  other checks pass. Windows notifications still DisabledForUser (user action). Cosmetic: performance.json's
  `cumulative` rows come out in varying order (the page looks rows up by model; no effect).
- Notifications ON (2026-09-30 ~14:00 UTC): the user switched on Windows notifications; the PowerShell sender reports
  Enabled. A test toast (`scripts/toast.ps1`, exit 0) was shown and seen by the user, which also registered "Windows
  PowerShell" in Settings > System > Notifications (an app is listed only after its first toast). The 13:49 UTC caught-up
  notice (13.1 h gap) was NOT SHOWN because notifications were still off at that time. The overnight catch-up itself
  worked: release rel_20260930T134704Z (QB changes PIT@CLE, MIA@MIN; line changes on 4 games), pushed and deployed.
- Session 12 (2026-10-01, display/grading rule only; model artifact/configs unchanged). User requests:
  - **Locked model pick (rule "original-pick", games kicking off from 2026-10-01 = week 4 on)**: the spread pick is
    locked at the earliest valid version generated before kickoff with a market line and graded against that version's
    line; later line moves and forecasts never change it. Earlier games keep "final-pregame" (the rule in force when
    played): finished weeks are NOT regraded (week 3 stays 8-6-1 publicly verifiable; 9-6 under the new rule, stated on
    the Method page). Projected winner and margin error always use final_pregame. `picks.RULE_START`, `lock_rule`,
    `select_locked`, `grade_game`, `weekly_summary` (`graded`/`retro_winner` by the final version's publication label,
    `pick_graded`/`retro_pick` by the locked version's label, `grading_rule`), `export_web.locked_pick_for` (item
    `locked_pick` with rule, run_id, generated_at, verification). Stored per-release picks (picks-v1) unchanged and
    used verbatim. verify-claims recomputes everything from the release files + evidence (version, labels incl.
    re-derived unstored ones, line, publication label, grades, results tables); mutation-tested.
  - **Card**: model pick first and most prominent ("Locked <time> at <line>", plus "Line now" / "Final pre-game line"
    when the line moved), then market line, model line (projected margin as a line), market total, model total,
    projected winner. 80% range removed from the card (still on the game page). Game page: Prediction panel first.
  - **Dark theme only** (tokens in `web/app/globals.css`; chart series = reference palette dark steps, validator passes
    on #141a25; team colours lightened on dark via `onDark` for the probability bar; badges keep the team colour with
    a light inset ring).
  - **Name: "Insularity NFL Forecast"** (header, title, About, README, alert titles). URL and repo unchanged; the
    internal package/CLI stays `nflcast`.
  - Built in a separate git worktree (C:\Users\Craig\nflwt, data copied, own node_modules) so the scheduled task kept
    publishing; paused only to merge. Layout audit 0 issues (295 pages x 5 widths). Independent 4-reviewer pass found
    11 distinct issues, all fixed: week 3 regrade (now not regraded), verify-claims gaps (publication label of the locked
    pick, unstored labels not re-derived, results tables not recomputed), retro footnote over-counting, results counts,
    "No pick yet" / "Line now" after kickoff, badge text contrast (dark ink on light team colours, e.g. NO 1.85:1 ->
    dark), a white default 404 page (site-styled not-found added), Method page no-pick threshold (0.005), docs.
  - Published 2026-10-01 ~01:18 UTC (commits 7b4fbc1 code, 05024d9 site data; Pages deploy success). Live site checked:
    title "Insularity NFL Forecast", locked picks present; live layout audit 0 issues (296 pages x 5 widths).
    verify-claims: all checks pass except 27 archive.org re-downloads refused by its rate limit ("retry later").
    The user wants this design kept as the main site until they ask for a change.
  - Follow-up (user-approved, same day): the pick box shows the line AND the model margin at lock time ("At lock" /
    "Then", model to 2 decimals) and, when either has changed, the latest pair ("Now"; "Final pre-game" after kickoff),
    because "Model line PIT -2.9" next to a pick locked at PIT -2.5 looked contradictory (the model moves with the line).
    Display only; layout audit 0 issues (296 pages x 5 widths).
- Injury report on game pages (2026-10-01, user request; display only, model unchanged): the old "Listed injuries" list showed
  only players with a game status, so PIT@CLE (Thursday) showed nothing: nflverse had practice rows but none of the
  Wednesday game statuses that NFL.com already listed (5 Out, 2 Questionable). Each game now exports `injury_report`
  (`export_web.injury_report_for`/`injury_rows`): every listed player for both teams that week (injury, practice status,
  game status), from the newest snapshot retrieved before min(now, kickoff), with provider update and last-check times.
  The game page shows it (most serious first) with a link to the week's official NFL.com report. NFL.com is NOT fetched
  automatically: its terms (section 1.3) prohibit systematic retrieval to compile a database without written consent
  (earlier note said "commercial use" only; corrected in docs/data_sources.md). Schefter/Underdog (ESPN/X) stay manual
  sources for documented QB overrides.
- Weekly publication time (2026-10-05, user decision; operational, model unchanged): from week 5 a week is first
  published at Thursday 09:00 UK before its first game (`predict/schedule.py`, gate in `release.build_candidate`,
  logged as "no release: week N is held back until ..."); the locked model pick is set then. Week 4 graded so far
  (publicly verifiable): 9-6 straight up, 7-7-1 model picks; week 3 8-7 / 8-6-1. Sasser's published week 4 picks graded
  on the same results: 10-5 / 11-3-1 (his model lines differ from the market by several points; ours stays close by design).
  The user chose to TEST model options (more 2026 weight, less market anchoring) on 2019-2025 against the spread before
  any change; a change would be model v1.1 from that week on, with its record kept separate.
  - Test result (.scratch/ats_options.py; exploratory; historical lines ~closing; final horizon uses the actual starter):
    against-the-spread win % (pushes excluded), 2019-21 / 2022-24 / 2025 blind: combined v1.0 48.8 / 51.2 / 51.1;
    football-only 51.1 / 49.9 / 46.1; football-only only when >= 3 pts from the line 52.2 / 57.5 / 51.5; carry 0.3 (more
    current-season weight) combined 49.1 / 51.0, football-only 52.6 / 50.1; new-coach carry rule 48.8 / 51.5 and 51.9 / 50.1;
    half-way blend 50.9 / 50.1. ~800 picks per cell (~280 in 2025). No option beats the line consistently (break-even ~52.4%).
    Model left at v1.0 pending the user's decision.
- Weekly page header (2026-10-05, user request, Sasser-style): "Week N Projections." headline, dates/games/update time,
  model-history link, and a season record strip (straight up and against the spread, publicly verifiable pregame forecasts
  only; manifest.season_record from export_web). Layout audit 0 issues (296 pages x 5 widths).
- Divisional tag (2026-10-05, user request; display only): `div_game` exported per game; "Divisional" tag next to the
  kickoff time on cards and "Divisional game" on game pages. Data check 2019-2025: divisional underdogs covered 53.4% (687
  games) vs 51.2% non-divisional (1,273); within chance, not a model feature (no new features this season).
- Luck and regression watch + depth chart in injury tables (2026-10-05, user request; display only, model unchanged):
  `predict/luck.py` (expected wins from per-game net EPA/play via a logistic fit on earlier seasons; luck = wins - expected;
  one-score record, turnover margin, fumble recovery share from our own pbp) shown on the Team ratings page; injury rows
  carry the player's position/order on the latest depth chart before the report (`export_web.depth_labels`, e.g. WR1, LT2;
  usual starters bold). Next: test a targeted carry-over adjustment (returning production, then play-caller changes) on
  2019-2025; adopt only if it helps, dated on the site (user prefers it framed as an adjustment, not a new model).
- Targeted carry-over test DONE (2026-10-05; pre-registered; reports/research/carryover_staff_production_2026-10-05.md):
  staff change (HC/OC/DC, data/manual/coaching_staff.csv from Wikipedia), returning snap share, and both. None passed
  (combined model differences tiny, CIs span zero; football-only worse in weeks 1-4). MODEL UNCHANGED AND FINAL for 2026
  (user: "finalise ... then we won't change anything after"). Game pages show each team's head coach and coordinators with
  seasons in role and a "New this season" tag (display only).
- Stats-only display additions (2026-10-06, user request "do 1-4" after comparing with another public model; display only,
  model, forecasts, pick rule and grading unchanged): (1) the pick box shows the stats-only (football-only, no market)
  line at the lock and now, and the grid shows stats-only line/total; `locked_pick.stats_only` = that version's
  football_only margin/total (export_web.stats_only_for; verify-claims checks it). (2) "Big gap" tag when the locked
  version's stats-only margin is >= 3 pts from its line (backtest 52.2 / 57.5 / 51.5% ATS; a prompt, not a pick).
  (3) Edge size under the pick ("Tiny edge · about a coin flip" under 0.5 pts). (4) New releases store
  `football_breakdown` (predict/breakdown.py): the football-only margin split exactly into plain groups (home field, rest,
  QBs, passing, rushing, efficiency, scoring, turnovers/field position, pace, other); omitted unless the groups add up to
  the published margin within 1e-6 (dry run on week 5: 15/15 exact). Shown on game pages as a bar chart; earlier
  releases have no breakdown. Method page states all of this.

## 3. Tests and checks (2026-09-25)
- `pytest`: **107 passed** (leakage, signs, identities, market policy, probabilities, scoring, validation/states, QB availability
  (25), archive integrity, release-path isolation, freeze, public-page wording (2), The Odds API feed (11), picks/results (6),
  alerts (15), verify-claims archive re-download (1), locked picks (+5 in test_picks)).
- `python -m nflcast verify-claims`: **38/38 passed** (no internal codes on 272 game pages; retrospective weather + untimed lines labelled in reports and the built
  site; every GitHub push time re-fetched and matching; no publication before generation; 77 exported verification labels
  recomputed from evidence; corrections complete; all RFC 3161 tokens verify against the files; all Web Archive copies match).
  Report: `reports/claims_verification.md`.
- `python -m nflcast backup`: private repo verified, all files present with identical git blob hashes.
- Demonstration (Task Scheduler, 02:14–02:15 UTC): refresh → collect → backup push → frozen-model release
  `rel_20260925T021501Z` → manifest + trusted timestamp → push → GitHub evidence + Web Archive copy → push → site build;
  Pages deploy succeeded; live page shows "model v1.0-2026-rest-of-season (frozen)" and the evidence chain.

## 4. Automation schedule
- Windows Task Scheduler `nflcast-operate` → `scripts/operate.ps1` every 30 min, **only while the user is logged in** (S4U
  "run whether logged on or not" needs admin rights). Each cycle: integrity + freeze checks → ingest (nflverse) → build →
  collect (weather snapshots; injury versions) → backup push → score → publication evidence → candidate release; publish if
  any input fingerprint changed, a game is < 60 min from kickoff, or ≥ 20 h since the last release → archive (manifest,
  RFC 3161) → export → push (public repo) → evidence + Web Archive → push → local site build. GitHub Actions deploys Pages.
- **PC off is acceptable (user decision 2026-09-25).** All refreshes, releases, scoring, collection and backups run on this
  PC, so they pause while it is off, asleep or logged out. The public site stays up with the last published forecasts
  (labels switch to "locked at kickoff" in the browser at kickoff). After Windows login the task catches up within minutes
  (StartWhenAvailable) and then runs every 30 min. Claude does not need to be open. Missed updates (e.g. a final-hour
  version) are never recreated or back-dated; the original published versions remain the evaluated forecasts.
- Full slate: each release covers every unplayed game of the upcoming week; the next week is published by the first cycle
  after the previous week's last kickoff (≈3 days before the Thursday game), provided the PC is on at some point in between.

## 5. Data locations
| What | Where | Public? |
|---|---|---|
| Forecast releases (immutable) | `releases/<season>/week_<nn>/rel_*.json` | public repo |
| Archive manifests / evidence logs / TSA certs | `releases/archive/` | public repo |
| Publication evidence; corrections | `releases/publication_evidence.json`; `releases/corrections.jsonl` | public repo |
| Frozen model | `artifacts/frozen/…/production.joblib`; `configs/model_freeze.yaml` | public repo |
| Reports (backtests, locked test, QB audit/drift, feature groups, claims) | `reports/` | public repo |
| Site data (exported) | `web/public/data/` | public repo |
| Raw nflverse snapshots (all sources, append-only) | `data/raw/<source>/<season>/` | local only |
| Weather snapshots | `data/raw/weather/<season>/<game_id>/` | local + **private backup** |
| Injury snapshots + version table | `data/raw/injuries/2026/`, `data/processed/injury_versions.parquet` | local + **private backup** |
| Schedule/market-line snapshots | `data/raw/schedules/all/` | local + **private backup** |
| The Odds API snapshots (points only) + request/credit log | `data/raw/odds_api/<year>/odds_*.json`, `data/raw/odds_api/state.json` | local + **private backup** |
| API key | `.env` (git-ignored) | local only, never published |
| Private backup repo (working copy) | `data/backup_repo/` → github.com/INSUL4RITY/nfl-forecast-data (private) | private |
| Manual inputs | `data/manual/` (QB overrides, venues) | public repo |
| Logs | `logs/operate.log` | local only |
Not backed up off-PC (re-downloadable or derivable): other raw nflverse snapshots (depth charts, rosters, pbp), processed tables.
Note: depth-chart and roster snapshot *history* is not re-downloadable either; it is local only (large files).

## 6. Operational blockers (need action or attention; not research)
1. Updates run only while the PC is on, awake, online and logged in (Task Scheduler interactive logon). Accepted by the user:
   updates pause and resume after login. The one thing to avoid is the PC being off for the whole gap between a week's last
   kickoff and the next week's first kickoff (then that week's early games get no forecast; nothing is recreated later).
2. GitHub CLI login must stay valid (token in Windows Credential Manager). If pushes fail, `logs/operate.log` shows it:
   run `gh auth login --web` again.
3. External best-effort services: FreeTSA and the Internet Archive can fail or be slow; failures are logged and retried.
   The Odds API: free plan (500 credits/month); if the key is revoked or credits run low, forecasts continue on nflverse
   lines automatically (see `operate: odds ...` lines in `logs/operate.log`).
4. Depth-chart and roster snapshot history exists only on this PC (not backed up; large). Loss would affect only the audit of
   past QB-availability inputs, not published forecasts.
5. Data freshness depends on nflverse's refresh cadence; there is no official NFL feed.

## 7. Research limitations (need future data; no action this season)
1. Early-horizon (72 h) market validation needs timestamped lines — collected since 2026-09-24 (nflverse snapshots) and,
   with provider update times, from The Odds API since 2026-09-25. The model was trained on nflverse (≈ closing) lines;
   whether API consensus lines change accuracy is untested and must be evaluated after the season on identical games.
2. Mid-week injury practice readings are uncalibrated (no intra-week history) — injury versions being collected.
3. Weather value is untested on strictly as-of data (historical evaluation was retrospective) — snapshots being collected.
4. QB start-rate intervals ignore clustering by injury episode; a downward drift in 2024 is not significant at episode level.
5. Historical backtests use the actual-starter proxy and untimed (≈ closing) lines; they remain optimistic vs live.
6. Coaching/play-caller effects deferred (no dated source). Non-QB injuries display-only (not promoted).
6b. Team form does not separate games by quarterback, and `qb_change` cannot tell a returning starter from a backup coming
   in. ATL@GB 2026 wk 3 (decomposed 2026-09-25): ATL's weeks 1–2 without Penix (−0.40 EPA/play, 8 ppg) dragged ATL's form, and the
   QB-change input added ~+1.2 pts toward GB although the change was the starter returning. Early-season form was ~74% 2025 games
   (GB's strong 2025 offence outweighed its poor 2026 start). Candidate v2 research: QB-aware team form and a
   "returning starter" distinction, evaluated under the pre-specified rule after the season.
7. Prospective sample is tiny so far; weekly results are noisy.

## 8. Exact next steps
- Weekly (optional, ≈5 min, from any folder): `& "C:\Users\Craig\NFL MODEL PROJECTIONS\nflcast.cmd" verify-claims` and
  `... nflcast.cmd backup` (both should pass); `Get-Content "C:\Users\Craig\NFL MODEL PROJECTIONS\logs\operate.log" -Tail 5`
  (should end "operate: done"); glance at the site.
- Do NOT change model code/configs; do not add features. Operational bug fixes only (they must not touch `configs/production.yaml`,
  `configs/settings.yaml` or the frozen artifact; freeze-check enforces this).
- After the Super Bowl (Feb 2027): run `score`; report prospective 2026 results (all generated-pregame and publicly verifiable
  subsets) against market-only and football-only on identical games; then evaluate collected weather, injury-version and line
  data under pre-specified rules; consider an episode-level QB-rate estimator; decide on a v2.0 model for 2027.
- Optional (only if you want to remove the PC dependency): move operation to a cloud runner — needs a decision and setup.

## 9. Releases so far
`releases/2026/week_03/`: 1 baseline (schema v1, not scored) + production releases from 2026-09-24T23:51Z; the first frozen-model
release is `rel_20260925T021501Z`. See `releases/archive/2026/` for per-release evidence.
