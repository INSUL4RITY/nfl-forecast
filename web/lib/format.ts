export type TzMode = "local" | "london" | "stadium";

export function tzFor(mode: TzMode, venueTz: string): string | undefined {
  if (mode === "london") return "Europe/London";
  if (mode === "stadium") return venueTz;
  return undefined; // viewer's local timezone
}

const rgbOf = (hex: string | undefined) => {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex ?? "");
  return m ? [0, 2, 4].map((i) => parseInt(m[1].slice(i, i + 2), 16)) : null;
};
/** WCAG relative luminance of an [r, g, b] colour. */
const lum = (v: number[]) => v.map((x) => { const s = x / 255; return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4; })
  .reduce((t, x, i) => t + x * [0.2126, 0.7152, 0.0722][i], 0);

/** Badge text colour: white or the page's dark ink, whichever contrasts more with the team colour (e.g. dark on NO gold). */
export function badgeInk(hex: string | undefined): string {
  const c = rgbOf(hex);
  if (!c) return "#fff";
  const L = lum(c);
  return 1.05 / (L + 0.05) >= (L + 0.05) / (lum([11, 15, 23]) + 0.05) ? "#fff" : "#0b0f17";
}

/** Team colour lightened just enough to stay visible on the dark page (black, navy); other colours unchanged. */
export function onDark(hex: string | undefined, fallback = "#5d6678"): string {
  let c = rgbOf(hex);
  if (!c) return fallback;
  if (lum(c) >= 0.07) return `#${hex!.replace("#", "")}`;
  for (let k = 0; k < 12 && lum(c) < 0.07; k++) c = c.map((x) => x + (255 - x) * 0.15);
  return `rgb(${c.map((x) => Math.round(x)).join(", ")})`;
}

const PANEL_LUM = lum([20, 26, 37]);   // --surface (#141a25)
const toHex = (c: number[]) => `#${c.map((x) => Math.round(x).toString(16).padStart(2, "0")).join("")}`;

/** A team colour lightened until it has at least 3:1 contrast with the panel (WCAG non-text contrast). */
function visible(hex: string | undefined): number[] | null {
  let c = rgbOf(hex);
  if (!c) return null;
  for (let k = 0; k < 20 && (lum(c) + 0.05) / (PANEL_LUM + 0.05) < 3; k++) c = c.map((x) => x + (255 - x) * 0.12);
  return c;
}
const chroma = (c: number[]) => Math.max(...c) - Math.min(...c);
const dist = (a: number[], b: number[]) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);

const PLAYOFF: Record<number, [string, string]> = {
  19: ["Wild Card", "WC"], 20: ["Divisional round", "DIV"], 21: ["Conference championships", "CONF"], 22: ["Super Bowl", "SB"],
};
/** "Week 7", or the playoff round's name (nflverse numbers the rounds as weeks 19-22). */
export const weekName = (week: number): string => PLAYOFF[week]?.[0] ?? `Week ${week}`;
/** Short form for tight spaces: "Wk 7", "WC", "DIV", "CONF", "SB". */
export const weekShort = (week: number): string => PLAYOFF[week]?.[1] ?? `Wk ${week}`;
export const isPlayoffWeek = (week: number): boolean => week in PLAYOFF;

/** One identity colour per team for charts on the dark page: each team's more vivid colour (primary or secondary), made
 *  visible on the panel; if the two teams would look alike, the away team switches to its other colour (or a neutral). */
export function teamPairColors(home?: { color: string; color2: string }, away?: { color: string; color2: string }): { home: string; away: string } {
  const opts = (t?: { color: string; color2: string }) =>
    [t?.color, t?.color2].map(visible).filter((c): c is number[] => !!c).sort((a, b) => chroma(b) - chroma(a));
  const h = opts(home), a = opts(away);
  const hc = h[0] ?? [57, 135, 229];
  let ac = a[0] ?? [217, 89, 38];
  if (dist(hc, ac) < 110) {
    const alt = a.find((c) => dist(hc, c) >= 110);
    ac = alt ?? (dist(hc, [170, 179, 195]) >= 110 ? [170, 179, 195] : [217, 89, 38]);
  }
  return { home: toHex(hc), away: toHex(ac) };
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

/** Week date range from each kickoff's date in its own display time zone, e.g. "Fri 25 Sept – Tue 29 Sept". */
export function dateRange(items: readonly (readonly [string, string | undefined])[]): string | null {
  if (!items.length) return null;
  const ymd = (iso: string, tz?: string) =>
    new Intl.DateTimeFormat("en-CA", { year: "numeric", month: "2-digit", day: "2-digit", timeZone: tz }).format(new Date(iso));
  const fmt = (iso: string, tz?: string) =>
    new Intl.DateTimeFormat("en-GB", { weekday: "short", day: "numeric", month: "short", timeZone: tz }).format(new Date(iso));
  const s = items.map(([iso, tz]) => ({ k: ymd(iso, tz), iso, tz })).sort((a, b) => a.k.localeCompare(b.k));
  const a = s[0], b = s[s.length - 1];
  return a.k === b.k ? fmt(a.iso, a.tz) : `${fmt(a.iso, a.tz)} – ${fmt(b.iso, b.tz)}`;
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
  listed_out_despite_stale_report: "injury report not re-confirmed; official Out kept",
  listed_doubtful_despite_stale_report: "injury report not re-confirmed; official Doubtful kept",
};
const SOURCE_TEXT: Record<string, string> = {
  injuries: "Injury reports", depth_charts: "Depth charts", rosters_weekly: "Rosters", schedules: "Schedule & market line",
  the_odds_api: "Market line (The Odds API)",
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
  if (homeSpread === 0) return "Even";
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
