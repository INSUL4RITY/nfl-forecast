import LocalTime from "./LocalTime";
import type { InjuryReport } from "@/lib/types";

const PRACTICE: Record<string, string> = {
  "Did Not Participate In Practice": "Did not practise",
  "Limited Participation in Practice": "Limited",
  "Full Participation in Practice": "Full",
};

/** Usual starters: first at the position, or receivers 1-3 (receivers are ranked as one list on the depth chart). */
function likelyStarter(depth: string): boolean {
  const m = /^([A-Z]+)(\d+)$/.exec(depth);
  return !!m && (Number(m[2]) === 1 || (m[1] === "WR" && Number(m[2]) <= 3));
}

/** Link to the official league report for the game's week (NFL.com is read by people, never harvested automatically). */
function nflUrl(season: number, week: number, gameType: string): string {
  return gameType === "REG" ? `https://www.nfl.com/injuries/league/${season}/reg${week}` : "https://www.nfl.com/injuries/";
}

/** "Wednesday 30 Sept" from an ISO date (a calendar day, so formatted in UTC to avoid shifting it). */
function dayText(isoDate: string): string {
  return new Intl.DateTimeFormat("en-GB", { weekday: "long", day: "numeric", month: "short", timeZone: "UTC" })
    .format(new Date(`${isoDate}T12:00:00Z`));
}

/** What the data feed says, never more: an empty feed is not a clean report, and missing statuses are not "no statuses". */
function summaryText(r: InjuryReport): string {
  const n = r.players.length, due = dayText(r.status_due);
  if (n === 0) return r.as_of_kickoff ? "no report in the data feed at kickoff" : "not in the data feed yet";
  const count = (s: string) => r.players.filter((p) => p.game_status === s).length;
  const parts = [["Out", "out"], ["Doubtful", "doubtful"], ["Questionable", "questionable"]]
    .map(([s, w]) => (count(s) ? `${count(s)} ${w}` : "")).filter(Boolean);
  const players = `${n} player${n === 1 ? "" : "s"}`;
  if (parts.length) return `${players}: ${parts.join(", ")}`;
  if (r.as_of_kickoff) return `${players}: no game statuses in the data feed at kickoff`;
  if (r.status_due_passed) return `${players}: game statuses were due ${due} but are not in the data feed yet`;
  return `${players}: game statuses due ${due}`;
}

/** Every player on the injury report for both teams: game status when published, otherwise practice status. */
export default function InjuryReportTable({ r, season, week, gameType, venueTz }:
  { r: InjuryReport; season: number; week: number; gameType: string; venueTz?: string }) {
  const n = r.players.length;
  const lagging = n > 0 && !r.players.some((p) => p.game_status) && r.status_due_passed;
  const times = [
    r.content_updated_at ? <>data last changed <LocalTime venueTz={venueTz} iso={r.content_updated_at} /></> : null,
    r.last_checked_at ? <>we last checked <LocalTime venueTz={venueTz} iso={r.last_checked_at} /></> : null,
  ].filter(Boolean);
  return (
    <details open style={{ marginTop: 10 }}>
      <summary>Injury report ({summaryText(r)})</summary>
      {lagging && (
        <p className="small" style={{ margin: "6px 0 0", color: "var(--warn-ink)" }}>The official report with game statuses has
          been published but has not reached our data feed. See the{" "}
          <a href={nflUrl(season, week, gameType)} target="_blank" rel="noopener noreferrer">official injury report on NFL.com</a>.</p>
      )}
      {n > 0 && (
        <div className="table-wrap" style={{ marginTop: 8 }}><table>
          <thead><tr><th>Team</th><th>Player</th><th>Pos</th><th>Depth chart</th><th>Injury</th><th>Practice</th><th>Game status</th></tr></thead>
          <tbody>{r.players.map((p, i) => (
            <tr key={`${p.team}-${p.full_name}-${i}`}><td>{p.team}</td><td>{p.full_name}</td><td>{p.position ?? "—"}</td>
              <td>{p.depth ? (likelyStarter(p.depth) ? <b>{p.depth}</b> : p.depth) : "—"}</td>
              <td className="wrap">{p.injury ?? "—"}</td>
              <td>{p.practice_status ? PRACTICE[p.practice_status] ?? p.practice_status : "—"}</td>
              <td>{p.game_status ? <b>{p.game_status}</b> : "—"}</td></tr>
          ))}</tbody>
        </table></div>
      )}
      <p className="small muted" style={{ marginTop: 6, marginBottom: 0 }}>
        From the official NFL injury report as carried by nflverse
        {times.length > 0 && <> ({times.map((t, i) => <span key={i}>{i ? "; " : ""}{t}</span>)})</>}
        {r.as_of_kickoff ? ", shown as of kickoff" : ""}. Most serious first. Depth chart: position and order on the team's latest depth chart before this report (usual starters in bold: first at the position, receivers 1–3). For this game, game statuses (Out, Doubtful,
        Questionable) come with the final report on {dayText(r.status_due)}. The data feed can lag the league&apos;s own report,
        at times by a day or more, so check the{" "}
        <a href={nflUrl(season, week, gameType)} target="_blank" rel="noopener noreferrer">official injury report on NFL.com</a>{" "}
        and team announcements before kickoff. Display only: injuries other than at quarterback are not model inputs (tested;
        the market line usually reflects them).
      </p>
    </details>
  );
}
