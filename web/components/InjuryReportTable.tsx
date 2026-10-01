import LocalTime from "./LocalTime";
import type { InjuryReport } from "@/lib/types";

const PRACTICE: Record<string, string> = {
  "Did Not Participate In Practice": "Did not practise",
  "Limited Participation in Practice": "Limited",
  "Full Participation in Practice": "Full",
};

/** Link to the official league report for the game's week (NFL.com is read by people, never harvested automatically). */
function nflUrl(season: number, week: number, gameType: string): string {
  return gameType === "REG" ? `https://www.nfl.com/injuries/league/${season}/reg${week}` : "https://www.nfl.com/injuries/";
}

/** Every player on the injury report for both teams: game status when published, otherwise practice status. */
export default function InjuryReportTable({ r, season, week, gameType, venueTz }:
  { r: InjuryReport; season: number; week: number; gameType: string; venueTz?: string }) {
  const n = r.players.length;
  const count = (s: string) => r.players.filter((p) => p.game_status === s).length;
  const parts = [["Out", "out"], ["Doubtful", "doubtful"], ["Questionable", "questionable"]]
    .map(([s, w]) => (count(s) ? `${count(s)} ${w}` : "")).filter(Boolean);
  const summary = n === 0 ? "no players listed" : parts.length ? parts.join(", ") : "no game statuses yet";
  return (
    <details open style={{ marginTop: 10 }}>
      <summary>Injury report ({n} player{n === 1 ? "" : "s"}: {summary})</summary>
      {n > 0 && (
        <div className="table-wrap" style={{ marginTop: 8 }}><table>
          <thead><tr><th>Team</th><th>Player</th><th>Pos</th><th>Injury</th><th>Practice</th><th>Game status</th></tr></thead>
          <tbody>{r.players.map((p) => (
            <tr key={p.team + p.full_name}><td>{p.team}</td><td>{p.full_name}</td><td>{p.position ?? "—"}</td>
              <td className="wrap">{p.injury ?? "—"}</td>
              <td>{p.practice_status ? PRACTICE[p.practice_status] ?? p.practice_status : "—"}</td>
              <td>{p.game_status ? <b>{p.game_status}</b> : "—"}</td></tr>
          ))}</tbody>
        </table></div>
      )}
      <p className="small muted" style={{ marginTop: 6, marginBottom: 0 }}>
        Official NFL injury report data via nflverse{r.provider_updated_at ? <>, updated <LocalTime venueTz={venueTz} iso={r.provider_updated_at} /></> : null}
        {r.last_checked_at ? <> (we last checked <LocalTime venueTz={venueTz} iso={r.last_checked_at} />)</> : null}
        {r.as_of_kickoff ? "; shown as of kickoff" : ""}. Game statuses (Out, Doubtful, Questionable) come with the final
        practice report: Wednesday for Thursday games, Friday for Sunday games, Saturday for Monday games. This feed can lag the
        league&apos;s own report by several hours, so check the{" "}
        <a href={nflUrl(season, week, gameType)} target="_blank" rel="noopener noreferrer">official injury report on NFL.com</a>{" "}
        and team announcements before kickoff. Display only: injuries other than at quarterback are not model inputs (tested; the
        betting line usually reflects them).
      </p>
    </details>
  );
}
