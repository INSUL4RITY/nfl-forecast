import type { ReserveList as RL, ReserveShare, ReserveTeam } from "@/lib/types";

const pct = (x: number) => `${Math.round(x * 100)}%`;

function share(s: ReserveShare | null, specialist: boolean, lastYear = false) {
  if (!s) return "—";
  if (specialist) return `${s.games} game${s.games === 1 ? "" : "s"}${lastYear && s.team ? ` (${s.team})` : ""}`;
  return `${pct(s.share)} ${s.unit === "offence" ? "off." : "def."}${lastYear && s.team ? ` (${s.team})` : ""}`;
}

function rows(abbr: string, t: ReserveTeam) {
  return t.players.map((p) => (
    <tr key={`${abbr}-${p.player}`}>
      <td>{abbr}</td><td>{p.player}</td><td>{p.pos ?? "—"}</td><td>{p.list}</td>
      <td>{p.since_week <= 1 ? "Season start" : `Week ${p.since_week}`}</td>
      <td className="r">{share(p.this_season, p.specialist)}</td>
      <td className="r">{share(p.last_season, p.specialist, true)}</td>
    </tr>));
}

function weekText(abbr: string, t: ReserveTeam) {
  return `${abbr} week ${t.roster_week ?? "—"}`;
}

/** Display only (predict/reserve_list.py): players on reserve lists, who are missing from the weekly injury report. */
export default function ReserveList({ r, away, home }: { r: RL; away: string; home: string }) {
  const n = r.away.players.length + r.home.players.length;
  const others = r.away.others + r.home.others;
  const th = pct(r.min_share);
  const counts = `${away} ${r.away.players.length}, ${home} ${r.home.players.length}`;
  return (
    <details open style={{ marginTop: 10 }}>
      <summary>Reserve lists ({n ? counts : `no players with ${th}+ of snaps`})</summary>
      {n > 0 && (
        <div className="table-wrap" style={{ marginTop: 8 }}><table>
          <thead><tr><th>Team</th><th>Player</th><th>Pos</th><th>List</th><th>On list since</th>
            <th className="r">Snap share before</th><th className="r">Last season</th></tr></thead>
          <tbody>{rows(away, r.away)}{rows(home, r.home)}</tbody>
        </table></div>
      )}
      <p className="small muted" style={{ marginTop: 6, marginBottom: 0 }}>
        Players on injured reserve and other reserve lists (physically unable to perform, non-football injury or illness,
        suspended) are not on the weekly injury report. Listed: players with at least {th} of their team&apos;s offensive or
        defensive snaps in either column, and kickers or punters who kicked in either season
        {others > 0 ? ` (${others} more on reserve lists with smaller roles)` : ""}. Snap share before: this season, with this
        team, in its games up to his last game before the list. Last season: regular season, with the team he played most for
        (named when different). From the nflverse weekly roster files ({weekText(away, r.away)}, {weekText(home, r.home)}),
        which can lag the league&apos;s transactions by several days; &ldquo;on list since&rdquo; is the first roster week that
        shows it. Display only: neither model line uses reserve lists. Both rate teams from their games, so a player&apos;s
        earlier play still counts in his team&apos;s numbers; at quarterback the model rates the expected starter.
      </p>
    </details>
  );
}
