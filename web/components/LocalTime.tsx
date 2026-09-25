"use client";
import { useEffect, useState } from "react";
import { fmtDateTime, fmtKickoff } from "@/lib/format";

/** Renders in UTC during prerender, then in the viewer's timezone after hydration. */
export default function LocalTime({ iso, kickoff, known = true }: { iso: string | null; kickoff?: boolean; known?: boolean }) {
  const [tz, setTz] = useState<string | undefined>("UTC");
  useEffect(() => setTz(undefined), []);
  if (!iso) return <>—</>;
  return <span className="num">{kickoff ? fmtKickoff(iso, tz, known) : fmtDateTime(iso, tz)}</span>;
}
