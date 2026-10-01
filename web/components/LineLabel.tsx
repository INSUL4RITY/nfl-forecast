"use client";
import { useEffect, useState } from "react";
import { displayState } from "./StateLabel";

/** `before` until kickoff, `after` once the game has started, even if the site has not been re-exported since kickoff
 *  (the viewer's clock is used only after hydration, like StateLabel). */
export default function LineLabel({ state, kickoff, before = "Line now", after = "Final pre-game line" }:
  { state: string; kickoff: string; before?: string; after?: string }) {
  const [now, setNow] = useState<number | null>(null);
  useEffect(() => setNow(Date.now()), []);
  return <>{displayState(state, kickoff, now) === "latest_pregame" ? before : after}</>;
}
