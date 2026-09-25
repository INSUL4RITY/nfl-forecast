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

export interface LineupSide {
  expected_qb_id: string | null;
  expected_qb: string | null;
  source: string | null;
  depth_chart_at: string | null;
  qb1: string | null;
  qb1_status: string | null;
  qb1_practice: string | null;
  note: string | null;
  scenarios: { p: number; qb: string | null; qb_id: string | null }[];
}

export interface ReleaseEntry {
  game_id: string;
  release_label: "early" | "update" | "final";
  hours_to_kickoff: number;
  status: string;
  primary_model: string;
  market_inputs_used: boolean;
  home_record: string;
  away_record: string;
  forecast: Forecast;
  combined: Forecast | null;
  football_only: Forecast;
  market_only: Forecast | null;
  market: { home_spread: number; total: number; source: string; timing: string; snapshot_at: string } | null;
  lineup: { home: LineupSide; away: LineupSide };
  lineup_uncertain: boolean;
  notable_injuries: { team: string; full_name: string; position: string; report_status: string }[];
  contributions: { feature: string; margin_points: number }[];
  team_efficiency?: { home: Record<string, number>; away: Record<string, number> };
  scenario_forecasts?: { p: number; home_qb: string | null; away_qb: string | null; combined_margin: number | null;
    combined_total: number | null; football_margin: number; football_total: number }[];
}

export interface HistoryPoint {
  run_id: string;
  generated_at: string;
  label: string;
  home_pts: number;
  away_pts: number;
  margin: number;
  total: number;
  p_home: number;
  primary_model: string;
  market_spread: number | null;
  market_total: number | null;
  before_kickoff: boolean;
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
  forecast_state: "published" | "pending" | "not_archived";
  forecast: ReleaseEntry | null;
  forecast_run_id: string | null;
  forecast_generated_at: string | null;
  history: HistoryPoint[];
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
}
