// Types mirror the JSON written by `python -m nflcast export-web` (src/nflcast/predict/export_web.py).

export type Intervals = Record<string, [number, number]>; // margin_80, margin_95, total_80, total_95

export interface Forecast {
  home_pts: number;
  away_pts: number;
  margin: number;
  total: number;
  p_home: number;
  p_away: number;
  p_tie: number;
  intervals: Intervals;
  scenario_disagreement_margin: number;
}

export interface QBEvidence {
  qb_id: string;
  qb: string | null;
  depth_rank: number | null;
  status: string;
  evidence: string;
  evidence_at: string | null;
  p_available: number;
  detail: string;
  roster_status?: string | null;
}

export interface SourceFreshness {
  source: string;
  state: "fresh" | "stale_provider" | "stale_retrieval" | "missing";
  observed_at: string | null;
  last_confirmed_at: string | null;
  provider_last_modified: string | null;
  detail: string;
}

export interface ArchiveSummary {
  sha256: string | null;
  rfc3161_time: string | null;
  github_push_time: string | null;
  web_archive_time: string | null;
  web_archive_copy: string | null;
}

export interface LineupSide {
  expected_qb_id: string | null;
  expected_qb: string | null;
  scenarios: { p: number; qb: string | null; qb_id: string | null }[];
  // schema v3 (evidence-based availability)
  team?: string;
  qbs?: QBEvidence[];
  flags?: string[];
  folded_probability?: number;
  depth_chart_at?: string | null;
  injury_snapshot_at?: string | null;
  overrides_used?: { qb_gsis_id: string; status: string; source: string; source_published_at_utc: string; expires_at_utc?: string }[];
  uncertain?: boolean;
  chain_residual?: number;
  freshness?: SourceFreshness[];
  // schema v2 (legacy releases)
  source?: string | null;
  qb1?: string | null;
  qb1_status?: string | null;
  qb1_practice?: string | null;
  note?: string | null;
}

export interface ReleaseEntry {
  game_id: string;
  release_label: "early" | "update" | "final";
  hours_to_kickoff: number;
  status: string;
  validation_problems?: Record<string, string[]>;
  primary_model: string;
  market_inputs_used: boolean;
  home_record: string;
  away_record: string;
  forecast: Forecast;
  combined: Forecast | null;
  football_only: Forecast;
  /** Trial (display and tracking only, from 20 Oct 2026): the stats-only model with non-QB injury inputs. */
  football_only_inj?: Forecast | null;
  /** Expected lost snap share by unit behind the trial line (lost_ol, lost_skill, lost_front, lost_db). */
  injury_inputs?: { home: Record<string, number>; away: Record<string, number> } | null;
  /** Trial (display and tracking only, from week 8 of 2026): the model v2.1 stats-only line. */
  football_only_v2?: Forecast | null;
  /** Which model made the stats-only "Model line" ("v1.0" for all of 2026). */
  stats_model?: string;
  market_only: Forecast | null;
  market: {
    home_spread: number; total: number; source: string; timing: string; snapshot_at: string;
    retrieved_at?: string; provider_updated_at?: string | null; n_bookmakers?: number | null;
    fallback_reason?: string | null; feed_version?: string;
  } | null;
  lineup: { home: LineupSide; away: LineupSide };
  lineup_uncertain: boolean;
  notable_injuries: { team: string; full_name: string; position: string; report_status: string }[];
  contributions: { feature: string; margin_points: number }[];
  /** Football-only (stats-only) margin split into plain groups that add up to it (display only; releases from 6 Oct 2026). */
  football_breakdown?: { groups: { group: string; label: string; margin_points: number }[]; margin: number } | null;
  team_efficiency?: { home: Record<string, number>; away: Record<string, number> };
  scenario_forecasts?: { p: number; home_qb: string | null; away_qb: string | null; combined_margin: number | null;
    combined_total: number | null; football_margin: number; football_total: number }[];
  data_freshness?: { sources: SourceFreshness[]; market_line_age_hours: number | null; qb_flags: Record<string, string[]>;
    problems: string[]; all_fresh: boolean };
  weather?: { available: boolean; model_input: boolean; observed_at_utc?: string; lead_hours?: number; exposure?: number;
    temperature_c?: number | null; wind_kmh?: number | null; gust_kmh?: number | null; precip_mm?: number | null; note?: string };
}

export interface HistoryPoint {
  run_id: string;
  generated_at: string;
  information_cutoff: string | null;
  public_evidence_at: string | null;
  verification: string;
  label: string;
  version_state: string;
  status: string;
  validation_problems: Record<string, string[]>;
  home_pts: number | null;
  away_pts: number | null;
  margin: number | null;
  total: number | null;
  p_home: number | null;
  primary_model: string | null;
  market_spread: number | null;
  market_total: number | null;
  before_kickoff: boolean;
  archive?: ArchiveSummary | null;
}

export interface Correction {
  id: string;
  recorded_at_utc: string;
  summary: string;
  details: Record<string, string>;
}

export interface WeekGame {
  game_id: string;
  season: number;
  week: number;
  game_type: string;
  kickoff_utc: string;
  kickoff_time_known: boolean;
  venue_tz: string;
  stadium: string;
  neutral_site: boolean;
  div_game?: boolean;
  roof: string | null;
  home: string;
  away: string;
  status: "final" | "scheduled";
  score: { home: number; away: number } | null;
  forecast_state: "latest_pregame" | "locked_at_kickoff" | "scored" | "pending" | "not_archived";
  forecast: ReleaseEntry | null;
  forecast_run_id: string | null;
  forecast_generated_at: string | null;
  forecast_public_evidence_at: string | null;
  forecast_verification: string | null;
  model_version?: string | null;
  model_frozen?: boolean | null;
  history: HistoryPoint[];
  corrections: Correction[];
  pick?: Pick | null;
  locked_pick?: LockedPick | null;
  injury_report?: InjuryReport | null;
  staff?: { away: StaffSide | null; home: StaffSide | null };
  result_grade?: ResultGrade | null;
  matchup?: Matchup | null;
  /** Season-to-date matchup detail as of kickoff (display only; predict/matchup.py). */
  matchup_detail?: MatchupDetail | null;
  stats_only_grade?: { spread: "win" | "loss" | "push" | null; big_gap: boolean; biggest_gap?: boolean; market_adjusted?: "win" | "loss" | "push" | null; injury_adjusted?: "win" | "loss" | "push" | null; v2_trial?: "win" | "loss" | "push" | null; total: "win" | "loss" | "push" | null;
                       total_side: "over" | "under" | null } | null;
}

/** Percentile (0-100, 100 = best) of both teams on efficiency measures among all teams in the same forecast release. */
export interface Matchup {
  n_teams: number;
  metrics: { key: string; group: "offence" | "defence" | "quarterback"; label: string; higher_is_better: boolean;
             home: number; away: number; home_value: number; away_value: number }[];
}

/** Head coach and coordinators of one team for the game's season (display only; data/manual/coaching_staff.csv). */
export interface StaffSide {
  head_coach: { name: string | null; seasons: number | null; known_from_2015: boolean };
  off_coordinator: { name: string | null; seasons: number | null; known_from_2015: boolean };
  def_coordinator: { name: string | null; seasons: number | null; known_from_2015: boolean };
}

/** Official NFL injury report data (via nflverse) for one game's teams and week, from the newest snapshot we retrieved
 *  before min(export time, kickoff). Display only (see export_web.injury_report_for). */
export interface InjuryReport {
  players: { team: string; full_name: string; position: string | null; injury: string | null;
             practice_status: string | null; game_status: string | null; depth?: string | null }[];
  content_updated_at: string | null;
  observed_at: string;
  last_checked_at: string | null;
  as_of_kickoff: boolean;
  status_due: string;
  status_due_passed: boolean;
}

/** Pick labels from one forecast version and the market line archived with it (see src/nflcast/predict/picks.py). */
export interface Pick {
  picks_version: string;
  winner: string | null;
  winner_p: number | null;
  projected_margin: number;
  winning_margin: number;
  line_home_spread: number | null;
  lean: { side: string | null; status: "lean" | "no_lean" | "no_line"; side_spread?: number; difference?: number;
          strength?: "none" | "tiny" | "small" | "moderate" | "large" } | null;
  retrospectively_derived: boolean;
}

/** The model pick that is shown and graded, from the version chosen by the rule in force for the game:
 *  "original-pick" (games from 1 Oct 2026): earliest valid version before kickoff with a market line, so later line moves
 *  never change it; "final-pregame" (earlier games): the last valid version before kickoff. */
export interface LockedPick extends Pick {
  run_id: string;
  generated_at: string;
  verification: string;
  rule: "lock-24h" | "original-pick" | "final-pregame";
  /** Which margin the pick compares with the line: "stats_only" (model line, from week 7) or "combined" (market-adjusted). */
  basis?: "stats_only" | "combined";
  /** The locked version's market-adjusted (combined) margin. */
  market_adjusted_margin?: number;
  /** "lock-24h" only: kickoff - 24 h, and whether that time is still ahead (the pick can still change). */
  locks_at?: string;
  provisional?: boolean;
  /** Football-only (stats-only, no market input) margin and total from that same version (display only). */
  stats_only?: { margin: number; total: number; line_total?: number | null } | null;
  /** The trial injury-adjusted model line of the same version (display and tracking only). */
  stats_inj?: { margin: number; total: number } | null;
  /** The trial model v2.1 line of the same version (display and tracking only). */
  stats_v2?: { margin: number; total: number } | null;
}

export interface ResultGrade {
  winner: "win" | "loss" | "tie" | "no_pick";
  lean: "win" | "loss" | "push" | "no_lean" | "no_line";
  abs_margin_error: number;
  actual_margin: number;
}

export interface GroupResults {
  graded: number;
  pick_graded?: number;
  winner: { win: number; loss: number; tie: number; no_pick: number };
  lean: { win: number; loss: number; push: number; no_lean: number; no_line: number };
  mean_abs_margin_error: number | null;
  retro_winner?: number;
  retro_pick?: number;
}

export interface WeekResults {
  state: "final" | "week_to_date";
  n_games: number;
  pending: number;
  graded: number;
  no_forecast: number;
  groups: Record<string, GroupResults>;
  grading_rule?: string;
}

export interface WeekDoc {
  season: number;
  week: number;
  date_range: [string, string] | null;
  n_games: number;
  last_release_at: string | null;
  release_count: number;
  games: WeekGame[];
  results?: WeekResults | null;
}

export interface Team {
  abbr: string;
  name: string;
  nick: string;
  color: string;
  color2: string;
  conf: string;
  division: string;
}

/** Season record of publicly verifiable pregame forecasts (export_web; late-published forecasts are excluded). */
export interface SeasonRecord {
  weeks: number[];
  straight_up: { win: number; loss: number; tie: number };
  spread: { win: number; loss: number; push: number };
  /** Display-only tracking record of the stats-only numbers from each locked version (not the official model pick). */
  stats_only?: { weeks: number[]; spread: WLP; big_gap: WLP; biggest_gap?: WLP; total: WLP; market_adjusted?: WLP; injury_adjusted?: WLP; v2_trial?: WLP };
}

export interface WLP { win: number; loss: number; push: number }

export interface Manifest {
  exported_at: string;
  season_record?: SeasonRecord;
  weeks: { season: number; week: number; n_games: number; has_forecasts: boolean; date_range: [string, string] | null }[];
  latest: { season: number; week: number };
  production: Record<string, any>;
  release_count: number;
  corrections?: Correction[];
}

/** Matchup detail for one game: both teams' season-to-date unit statistics as of kickoff (display only). Rates are
 *  fractions (0.449 = 44.9%), EPA values are per play; ranks run 1 (best) to n_teams. */
export interface MatchupTeam {
  team: string; games: number; record: [number, number, number];
  net_epa: number; off_epa: number; def_epa: number; ppd: number; def_ppd: number;
  adj_net_epa: number; adj_off_epa: number; adj_def_epa: number;
  last3_net_epa: number | null; neutral_db: number | null; tempo: number | null;
  ranks: Record<string, number>;
  qb_starts: { qb: string; games: number }[]; expected_qb: string | null;
}
export interface MatchupUnitRow {
  key: string; label: string; unit: string; off_value: number | null; off_rank: number | null;
  def_value: number | null; def_rank: number | null; edge: "offence" | "defence" | "even" | "none";
}
export interface MatchupLogRow {
  week: number; opp: string; home: boolean; net_epa: number; margin: number; pf: number; pa: number;
  qb: string | null; other_qb: boolean;
}
export interface MatchupDetail {
  available: boolean; n_teams: number;
  league?: Record<string, number | null>;
  teams?: { home: MatchupTeam; away: MatchupTeam };
  units?: { away_offence: MatchupUnitRow[]; home_offence: MatchupUnitRow[] };
  log?: { home: MatchupLogRow[]; away: MatchupLogRow[] };
}
