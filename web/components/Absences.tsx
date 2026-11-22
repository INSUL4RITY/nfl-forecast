import type { AbsencePlayer, Absences, AbsenceTeam } from "@/lib/types";

/** Display only (predict/absence_display.py; user authorisation 2026-11-20, item B1): who is missing in a Big or Biggest
 *  gap game. No point values: no absence adjustment has passed a test this season. */

const SHORT: Record<string, string> = { Questionable: "Q", Doubtful: "D", Out: "Out",
  "Did not practise (no game status yet)": "DNP", "Limited in practice (no game status yet)": "limited" };
const pct = (x: number) => `${Math.round(x * 100)}%`;
const surname = (n: string) => { const p = n.split(" "); return p.length > 1 ? p.slice(1).join(" ") : n; };

export const LATE_NOTE = "Measured before final injury reports reached the data.";

function teamLine(abbr: string, t: AbsenceTeam) {
  const rep = t.players.filter((p) => p.kind === "injury report");
  const res = t.players.filter((p) => p.kind === "reserve list");
  const left = t.players.filter((p) => p.kind === "left the team");
  const parts: string[] = [];
  if (rep.length) parts.push(rep.slice(0, 5).map((p) => `${surname(p.player)} (${p.pos ?? "?"}, ${SHORT[p.status] ?? p.status})`).join(", ")
    + (rep.length > 5 ? ` +${rep.length - 5}` : ""));
  if (res.length) parts.push(`reserve list: ${res.slice(0, 3).map((p) => surname(p.player)).join(", ")}${res.length > 3 ? ` +${res.length - 3}` : ""}`);
  if (left.length) parts.push(`left: ${left.slice(0, 3).map((p) => `${surname(p.player)}${p.status.startsWith("Now with ") ? ` (${p.status.slice(9)})` : ""}`).join(", ")}${left.length > 3 ? ` +${left.length - 3}` : ""}`);
  return <div><b>{abbr}</b> {parts.length ? parts.join(" · ") : "no regulars listed"}</div>;
}

/** Compact list for game cards. */
export function AbsenceSummary({ a, away, home }: { a: Absences; away: string; home: string }) {
  return (
    <div className="absences small">
      <div className="abs-head"><b>Who is missing</b>{!a.final_at_lock && <span className="abs-note">{LATE_NOTE}</span>}</div>
      {teamLine(away, a.away)}
      {teamLine(home, a.home)}
    </div>
  );
}

function share(p: AbsencePlayer) {
  if (p.kind === "reserve list" && !p.share && p.last_season_share) return `${pct(p.last_season_share)} last season`;
  return pct(p.share);
}

function rows(abbr: string, t: AbsenceTeam) {
  return t.players.map((p) => (
    <tr key={`${abbr}-${p.kind}-${p.player}`}>
      <td>{abbr}</td><td>{p.player}</td><td>{p.pos ?? "—"}</td><td className="wrap">{p.unit}</td><td className="wrap">{p.status}</td>
      <td className="r">{share(p)}</td>
    </tr>));
}

/** Full table for game pages. */
export function AbsencePanel({ a, away, home }: { a: Absences; away: string; home: string }) {
  const others = a.away.others + a.home.others;
  return (
    <div className="panel">
      <h2>Who is missing</h2>
      <p className="small ink2" style={{ marginTop: 0 }}>The model line {a.provisional ? "is" : "was"} {Math.abs(a.gap).toFixed(1)} points
        from the market line {a.provisional ? "" : "when the pick locked "}(a {Math.abs(a.gap) >= 4 ? "Biggest" : "Big"} gap). These are the
        regulars each team is without. Market lines already reflect most of this news; the model line (stats only) has no input for
        players other than quarterbacks, so it sees these absences only through games already played.</p>
      {!a.final_at_lock && <p className="callout warn small" style={{ margin: "0 0 10px" }}><b>{LATE_NOTE}</b> When the pick
        {a.provisional ? " was last updated" : " locked"}, at least one team&apos;s final game statuses (Out, Doubtful, Questionable) were not yet in
        the injury data this site uses, so the model line was measured without them.</p>}
      <div className="table-wrap" tabIndex={0}><table>
        <thead><tr><th>Team</th><th>Player</th><th>Pos</th><th>Unit</th><th>Status</th><th className="r">Snap share</th></tr></thead>
        <tbody>{rows(away, a.away)}{rows(home, a.home)}</tbody>
      </table></div>
      <p className="small muted" style={{ marginTop: 6, marginBottom: 0 }}>
        Injury report: players with a game status for this game, or (before the game statuses are published) players who did not
        practise or were limited. Reserve list: injured reserve and other reserve lists, which the weekly injury report leaves
        out. Left: traded or released this season. Regulars only: at least {pct(a.min_share)} of the team&apos;s offensive or
        defensive snaps this season (reserve lists: this season or last){others > 0 ? `; ${others} more listed with smaller roles` : ""}.
        Quarterbacks are covered in Lineup assumptions. Display only: no point values are shown, because no absence adjustment has
        passed a test this season (an adjustment that also counted reserve lists and departures was tested on 2019–2024 and did
        not improve the model line). Injury data as of {a.measured_at.slice(0, 16).replace("T", " ")} UTC.
      </p>
    </div>
  );
}
