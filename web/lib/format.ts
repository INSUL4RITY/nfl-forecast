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
