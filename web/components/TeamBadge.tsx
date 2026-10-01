import type { Team } from "@/lib/types";
import { badgeInk } from "@/lib/format";

export default function TeamBadge({ team, abbr, large }: { team?: Team; abbr: string; large?: boolean }) {
  const bg = team?.color ?? "#3b4760";
  return (
    <span className={`badge${large ? " lg" : ""}`} style={{ background: bg, color: badgeInk(bg) }} title={team?.name ?? abbr}>
      {abbr}
    </span>
  );
}
