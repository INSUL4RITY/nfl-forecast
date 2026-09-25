export type TzMode = "local" | "london" | "stadium";

export function tzFor(mode: TzMode, venueTz: string): string | undefined {
  if (mode === "london") return "Europe/London";
  if (mode === "stadium") return venueTz;
  return undefined; // viewer's local timezone
}

export function fmtKickoff(iso: string, tz?: string, known = true): string {
  const d = new Date(iso);
  const day = new Intl.DateTimeFormat("en-GB", { weekday: "short", day: "numeric", month: "short", timeZone: tz }).format(d);
  if (!known) return `${day} · time TBD`;
  const time = new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: tz, timeZoneName: "short" }).format(d);
  return `${day} · ${time}`;
}

export function dayKey(iso: string, tz?: string): string {
  return new Intl.DateTimeFormat("en-GB", { weekday: "long", day: "numeric", month: "long", timeZone: tz }).format(new Date(iso));
}

export function fmtDateTime(iso: string | null | undefined, tz?: string): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", timeZone: tz, timeZoneName: "short",
  }).format(new Date(iso));
}

export const f1 = (x: number | null | undefined) => (x == null || Number.isNaN(x) ? "—" : x.toFixed(1));
export const f2 = (x: number | null | undefined) => (x == null || Number.isNaN(x) ? "—" : x.toFixed(2));
export const f3 = (x: number | null | undefined) => (x == null || Number.isNaN(x) ? "—" : x.toFixed(3));
export const pct = (x: number | null | undefined, d = 0) => (x == null ? "—" : `${(x * 100).toFixed(d)}%`);

/** Probability with enough precision at the extremes that 99.5% is never shown as 100% (or 0.5% as 0%). */
export function pctP(x: number | null | undefined): string {
  if (x == null) return "—";
  if (x >= 1) return "100%";
  if (x <= 0) return "0%";
  if (x > 0.99 || x < 0.01) return `${(x * 100).toFixed(1)}%`;
  return `${(x * 100).toFixed(0)}%`;
}

export const STATE_LABEL: Record<string, string> = {
  latest_pregame: "Latest pregame forecast (may still update)",
  locked_at_kickoff: "Locked at kickoff",
  scored: "Scored",
  superseded: "Superseded",
  rejected_failed_validation: "Rejected (failed validation)",
  generated_after_kickoff_not_used: "Generated after kickoff (not used)",
  pending: "Pending",
  not_archived: "No forecast archived",
};

export const VERIFY_LABEL: Record<string, string> = {
  publicly_verifiable_pregame: "Publicly verifiable before kickoff",
  generated_pregame_published_after_kickoff: "Generated before kickoff, published after kickoff",
  generated_pregame_not_yet_evidenced_public: "Generated before kickoff, publication not yet evidenced",
  generated_after_kickoff: "Generated after kickoff",
};

/** Public wording for internal codes. The codes stay in the data files (audit trail); pages show only these texts. */
const ROSTER_TEXT: Record<string, string> = {
  ACT: "Active", RES: "Reserve list", INA: "Inactive", DEV: "Practice squad", CUT: "Released", RET: "Retired",
  EXE: "Exempt", SUS: "Suspended", PUP: "PUP list", NON: "Non-football injury list", TRD: "Traded", UFA: "Free agent",
};
export const rosterText = (s?: string | null) => (s ? ROSTER_TEXT[s] ?? "Other roster status" : "—");

const QB_STATUS_TEXT: Record<string, string> = {
  NotListed: "Not on report", Pending: "Designation pending", Unknown: "No report yet",
  Questionable: "Questionable", Doubtful: "Doubtful", Out: "Out", Available: "Available",
};
export function qbStatusText(s?: string | null): string {
  if (!s) return "—";
  if (s.startsWith("roster:")) return rosterText(s.slice(7));
  if (s.startsWith("override")) return "Documented override";
  return QB_STATUS_TEXT[s] ?? s.replace(/_/g, " ");
}

const QB_PROBLEM_TEXT: Record<string, string> = {
  report_not_available: "injury report not published yet",
  report_stale: "injury report out of date",
  depth_chart_stale: "depth chart out of date",
  depth_chart_missing: "no depth chart",
  roster_missing: "no roster snapshot",
  roster_stale: "roster out of date",
  replacement_chain_exhausted: "every listed QB carries some risk of missing the game",
  no_candidate_qb_prior_used: "no candidate QB identified; generic estimate used",
};
const SOURCE_TEXT: Record<string, string> = {
  injuries: "Injury reports", depth_charts: "Depth charts", rosters_weekly: "Rosters", schedules: "Schedule & market line",
};
const SOURCE_STATE_TEXT: Record<string, string> = {
  stale_provider: "not updated by the provider recently", stale_retrieval: "not re-checked recently", missing: "missing",
};

/** Plain-English version of a data-freshness problem such as "home QB: report_not_available". */
export function problemText(p: string, home: string, away: string): string {
  const [head, ...rest] = p.split(": ");
  const tail = rest.join(": ");
  const qb = head.match(/^(home|away) QB$/);
  if (qb) return `${qb[1] === "home" ? home : away} QB: ${QB_PROBLEM_TEXT[tail.split(":")[0]] ?? "availability evidence incomplete"}`;
  if (head === "market line") return tail === "missing" ? "No market line yet" : `Market line is ${tail}`;
  return `${SOURCE_TEXT[head] ?? "A data source"}: ${SOURCE_STATE_TEXT[tail] ?? "not current"}`;
}

/** "GB by 4.7" from a home-margin number. */
export function marginText(margin: number, home: string, away: string): string {
  if (Math.abs(margin) < 0.05) return "Even";
  return margin > 0 ? `${home} by ${margin.toFixed(1)}` : `${away} by ${(-margin).toFixed(1)}`;
}

/** Market spread in conventional form for the favourite, e.g. "GB −4.5". home_spread < 0 => home favoured. */
export function spreadText(homeSpread: number, home: string, away: string): string {
  if (homeSpread === 0) return "Pick'em";
  return homeSpread < 0 ? `${home} −${Math.abs(homeSpread).toFixed(1)}` : `${away} −${homeSpread.toFixed(1)}`;
}

export const MODEL_NAMES: Record<string, string> = {
  C_resid_noinj: "Combined (selected)",
  C_resid: "Combined + injuries",
  C_resid_nopersonnel: "Combined, no personnel",
  C_resid_hgb: "Combined (boosting)",
  C_direct: "Combined (direct)",
  A_market_raw: "Market only",
  A_market_cal: "Market (calibrated)",
  B_qb: "Football only",
  B_qb_inj: "Football + injuries",
  B_qb_noadj: "Football, no opp. adj.",
  B_core: "Football core",
  N_naive_home: "Naive home average",
};
