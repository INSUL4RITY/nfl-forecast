import type { RosterMoves as Moves, RosterTeamMoves } from "@/lib/types";
import { weekName } from "@/lib/format";

const pct = (x: number) => `${Math.round(x * 100)}%`;

function Team({ abbr, m }: { abbr: string; m: RosterTeamMoves }) {
  const empty = !m.departures.length && !m.arrivals.length && !m.specialists.length;
  return (
    <div>
      <h3 style={{ margin: "0 0 6px" }}>{abbr}</h3>
      {empty && <p className="small muted" style={{ margin: 0 }}>No significant roster moves this season.</p>}
      {m.departures.length > 0 && (
        <div className="table-wrap"><table>
          <thead><tr><th>Departed</th><th>Pos</th><th>Now</th><th className="r">Snap share</th></tr></thead>
          <tbody>{m.departures.map((d) => (
            <tr key={d.player}><td>{d.player}</td><td>{d.pos ?? "—"}</td><td>{d.move}{d.last_active_week ? ` · last active ${weekName(d.last_active_week)}` : ""}</td>
              <td className="r">{pct(d.share)} {d.unit === "offence" ? "off." : "def."}</td></tr>))}</tbody>
        </table></div>
      )}
      {m.arrivals.length > 0 && (
        <div className="table-wrap" style={{ marginTop: 8 }}><table>
          <thead><tr><th>Arrived</th><th>Pos</th><th>From</th><th className="r">Share there</th></tr></thead>
          <tbody>{m.arrivals.map((a) => (
            <tr key={a.player}><td>{a.player}</td><td>{a.pos ?? "—"}</td><td>{a.from} · since {weekName(a.since_week)}</td>
              <td className="r">{a.share_with_old_team ? pct(a.share_with_old_team) : "—"}</td></tr>))}</tbody>
        </table></div>
      )}
      {m.specialists.map((s) => (
        <p className="small" key={s.pos} style={{ margin: "8px 0 0" }}>
          <b>{s.pos === "K" ? "Kicker" : "Punter"} change:</b> {s.now} since {weekName(s.since_week)} (before:{" "}
          {s.before.map((b) => `${b.player}, ${b.weeks[0] === b.weeks[1] ? `week ${b.weeks[0]}` : `weeks ${b.weeks[0]}–${b.weeks[1]}`}`).join("; ")}).
        </p>))}
    </div>
  );
}

/** Display only (predict/roster_moves.py): trades, releases, reserve-list moves and kicker changes the model lines don't
 *  see (both rate teams from their games; QB changes are the exception). */
export default function RosterMoves({ m, away, home }: { m: Moves; away: string; home: string }) {
  return (
    <div className="panel">
      <h2>Roster moves this season</h2>
      <p className="small ink2" style={{ marginTop: 0 }}>Players who took at least 20% of a unit&apos;s snaps for the team this season
        and are no longer on its active roster (traded, released, reserve list), new arrivals from other teams, and kicker or punter
        changes, from nflverse weekly rosters and snap counts. Neither model line sees these: both rate teams from their games, so a
        departed starter&apos;s play still counts in the team&apos;s numbers until newer games replace it. Quarterback changes are the
        exception (the model rates the expected starter). Players on the reserve list (IR) are also missing from the weekly injury
        report.</p>
      <div className="two-col">
        <Team abbr={away} m={m.away} />
        <Team abbr={home} m={m.home} />
      </div>
    </div>
  );
}
