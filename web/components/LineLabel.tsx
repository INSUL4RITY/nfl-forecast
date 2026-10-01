"use client";
import { useEffect, useState } from "react";
import { displayState } from "./StateLabel";

/** "Line now" before kickoff, "Final pre-game line" once the game has started, even if the site has not been re-exported
 *  since kickoff (the viewer's clock is used only after hydration, like StateLabel). */
export default function LineLabel({ state, kickoff }: { state: string; kickoff: string }) {
  const [now, setNow] = useState<number | null>(null);
  useEffect(() => setNow(Date.now()), []);
  return <>{displayState(state, kickoff, now) === "latest_pregame" ? "Line now" : "Final pre-game line"}</>;
}
