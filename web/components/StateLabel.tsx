"use client";
import { useEffect, useState } from "react";
import { STATE_LABEL } from "@/lib/format";

/** A "latest pregame" forecast whose kickoff has passed is locked, even if the site has not been re-exported since
 *  (e.g. the PC running the pipeline was off). The viewer's clock is used only after hydration. */
export function displayState(state: string, kickoffIso: string, nowMs: number | null): string {
  if (state === "latest_pregame" && nowMs !== null && nowMs >= Date.parse(kickoffIso)) return "locked_at_kickoff";
  return state;
}

export default function StateLabel({ state, kickoff }: { state: string; kickoff: string }) {
  const [now, setNow] = useState<number | null>(null);
  useEffect(() => setNow(Date.now()), []);
  const s = displayState(state, kickoff, now);
  return <>{STATE_LABEL[s] ?? s}</>;
}
