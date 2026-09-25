import WeekBoard from "@/components/WeekBoard";
import { getManifest, getTeams, getWeek } from "@/lib/data";

export default function Home() {
  const m = getManifest();
  const doc = getWeek(m.latest.season, m.latest.week);
  return <WeekBoard doc={doc} teams={getTeams()} manifest={m} />;
}
