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
}

export interface WeekDoc {
  season: number;
  week: number;
  date_range: [string, string] | null;
  n_games: number;
  last_release_at: string | null;
  release_count: number;
  games: WeekGame[];
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

export interface Manifest {
  exported_at: string;
  weeks: { season: number; week: number; n_games: number; has_forecasts: boolean; date_range: [string, string] | null }[];
  latest: { season: number; week: number };
  production: Record<string, any>;
  release_count: number;
  corrections?: Correction[];
}
