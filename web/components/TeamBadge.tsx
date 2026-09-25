import type { Team } from "@/lib/types";

export default function TeamBadge({ team, abbr, large }: { team?: Team; abbr: string; large?: boolean }) {
  return (
    <span className={`badge${large ? " lg" : ""}`} style={{ background: team?.color ?? "#13213c" }} title={team?.name ?? abbr}>
      {abbr}
    </span>
  );
}
