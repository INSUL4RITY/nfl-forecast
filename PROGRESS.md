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

## 3. Tests and checks (2026-09-25)
- `pytest`: **80 passed** (leakage, signs, identities, market policy, probabilities, scoring, validation/states, QB availability
  (25), archive integrity, release-path isolation, freeze, public-page wording (2), The Odds API feed (11), picks/results (6)).
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
