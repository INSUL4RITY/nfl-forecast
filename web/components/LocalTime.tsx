"use client";
import { useEffect, useState } from "react";
import { fmtDateTime, fmtKickoff, tzFor, type TzMode } from "@/lib/format";

/** Renders in UTC during prerender, then in the time-zone mode chosen on the weekly page (your time zone by default;
 *  "stadium" uses venueTz when given). */
export default function LocalTime({ iso, kickoff, known = true, venueTz }:
  { iso: string | null; kickoff?: boolean; known?: boolean; venueTz?: string }) {
  const [tz, setTz] = useState<string | undefined>("UTC");
  useEffect(() => {
    let mode: TzMode = "local";
    try { mode = (localStorage.getItem("nflcast.tz") as TzMode | null) ?? "local"; } catch { /* storage unavailable */ }
    setTz(mode === "stadium" && !venueTz ? undefined : tzFor(mode, venueTz ?? ""));
  }, [venueTz]);
  if (!iso) return <>—</>;
  return <span className="num">{kickoff ? fmtKickoff(iso, tz, known) : fmtDateTime(iso, tz)}</span>;
}
