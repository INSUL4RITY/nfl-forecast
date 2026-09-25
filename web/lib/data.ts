// Build-time loaders: read the exported JSON from public/data. No forecast is computed in the frontend.
import fs from "node:fs";
import path from "node:path";
import type { Manifest, Team, WeekDoc, WeekGame } from "./types";

const DATA = path.join(process.cwd(), "public", "data");

function read<T>(rel: string): T {
  return JSON.parse(fs.readFileSync(path.join(DATA, rel), "utf-8")) as T;
}

export function exists(rel: string): boolean {
  return fs.existsSync(path.join(DATA, rel));
}

export const getManifest = () => read<Manifest>("manifest.json");
export const getTeams = () => read<Record<string, Team>>("teams.json");
export const getWeek = (season: number, week: number) =>
  read<WeekDoc>(`weeks/${season}-${String(week).padStart(2, "0")}.json`);
export const getPerformance = () => read<any>("performance.json");
export const getRatings = () => read<any>("ratings.json");
export const getRetro = (season: number) => (exists(`retro_${season}.json`) ? read<any>(`retro_${season}.json`) : null);

export function allGames(): WeekGame[] {
  const m = getManifest();
  return m.weeks.flatMap((w) => getWeek(w.season, w.week).games);
}

export function findGame(id: string): { game: WeekGame; week: WeekDoc } | null {
  const m = getManifest();
  for (const w of m.weeks) {
    const doc = getWeek(w.season, w.week);
    const game = doc.games.find((g) => g.game_id === id);
    if (game) return { game, week: doc };
  }
  return null;
}
