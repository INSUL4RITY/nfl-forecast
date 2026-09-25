import WeekBoard from "@/components/WeekBoard";
import { getManifest, getTeams, getWeek } from "@/lib/data";

export function generateStaticParams() {
  return getManifest().weeks.map((w) => ({ season: String(w.season), week: String(w.week) }));
}

export default async function WeekPage({ params }: { params: Promise<{ season: string; week: string }> }) {
  const { season, week } = await params;
  return <WeekBoard doc={getWeek(Number(season), Number(week))} teams={getTeams()} manifest={getManifest()} />;
}
