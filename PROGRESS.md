# Progress log — nflcast

Spec: `C:\Users\Craig\Downloads\NFL_Forecasting_Claude_Build_Brief.md`. Rules: `CLAUDE.md`. Live site:
https://insul4rity.github.io/nfl-forecast/ (public repo INSUL4RITY/nfl-forecast). Last updated 2026-09-25 ~02:30 UTC.

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

## 3. Tests and checks (2026-09-25)
- `pytest`: **61 passed** (leakage, signs, identities, market policy, probabilities, scoring, validation/states, QB availability
  (25), archive integrity, release-path isolation, freeze).
- `python -m nflcast verify-claims`: **37/37 passed** (retrospective weather + untimed lines labelled in reports and the built
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
- **Does the PC have to stay on? Yes.** All refreshes, releases, final-hour updates, scoring, collection and backups run on
  this PC. If it is off, asleep or logged out: the public site stays up with the last published forecasts (labels switch to
  "locked at kickoff" in the browser at kickoff), but no new forecasts, updates, scores, evidence or backups happen, and any
  missed final-hour window cannot be recreated later.

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
| Private backup repo (working copy) | `data/backup_repo/` → github.com/INSUL4RITY/nfl-forecast-data (private) | private |
| Manual inputs | `data/manual/` (QB overrides, venues) | public repo |
| Logs | `logs/operate.log` | local only |
Not backed up off-PC (re-downloadable or derivable): other raw nflverse snapshots (depth charts, rosters, pbp), processed tables.
Note: depth-chart and roster snapshot *history* is not re-downloadable either; it is local only (large files).

## 6. Operational blockers (need action or attention; not research)
1. PC must be on, awake, online and logged in for the whole season (Task Scheduler interactive logon). Sleep settings are the
   user's choice; if the PC sleeps, runs are missed (catch-up runs when it wakes, but past final-hour windows are lost).
2. GitHub CLI login must stay valid (token in Windows Credential Manager). If pushes fail, `logs/operate.log` shows it:
   run `gh auth login --web` again.
3. External best-effort services: FreeTSA and the Internet Archive can fail or be slow; failures are logged and retried.
4. Depth-chart and roster snapshot history exists only on this PC (not backed up; large). Loss would affect only the audit of
   past QB-availability inputs, not published forecasts.
5. Data freshness depends on nflverse's refresh cadence; there is no official NFL feed.

## 7. Research limitations (need future data; no action this season)
1. Early-horizon (72 h) market validation needs timestamped lines — being collected since 2026-09-24.
2. Mid-week injury practice readings are uncalibrated (no intra-week history) — injury versions being collected.
3. Weather value is untested on strictly as-of data (historical evaluation was retrospective) — snapshots being collected.
4. QB start-rate intervals ignore clustering by injury episode; a downward drift in 2024 is not significant at episode level.
5. Historical backtests use the actual-starter proxy and untimed (≈ closing) lines; they remain optimistic vs live.
6. Coaching/play-caller effects deferred (no dated source). Non-QB injuries display-only (not promoted).
7. Prospective sample is tiny so far; weekly results are noisy.

## 8. Exact next steps
- Weekly (≈5 min): check `logs/operate.log` for FAILED/VIOLATION lines; run `.\.venv\Scripts\python.exe -m nflcast verify-claims`
  and `... -m nflcast backup` (both should pass); glance at the site.
- Do NOT change model code/configs; do not add features. Operational bug fixes only (they must not touch `configs/production.yaml`,
  `configs/settings.yaml` or the frozen artifact; freeze-check enforces this).
- After the Super Bowl (Feb 2027): run `score`; report prospective 2026 results (all generated-pregame and publicly verifiable
  subsets) against market-only and football-only on identical games; then evaluate collected weather, injury-version and line
  data under pre-specified rules; consider an episode-level QB-rate estimator; decide on a v2.0 model for 2027.
- Optional (only if you want to remove the PC dependency): move operation to a cloud runner — needs a decision and setup.

## 9. Releases so far
`releases/2026/week_03/`: 1 baseline (schema v1, not scored) + production releases from 2026-09-24T23:51Z; the first frozen-model
release is `rel_20260925T021501Z`. See `releases/archive/2026/` for per-release evidence.
