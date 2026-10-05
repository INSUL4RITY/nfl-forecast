import type { StaffSide } from "@/lib/types";

const ROLES: [keyof StaffSide, string, string][] = [
  ["head_coach", "Head coach", ""],
  ["off_coordinator", "Offensive coordinator", "None listed: the head coach runs the offence"],
  ["def_coordinator", "Defensive coordinator", "None listed: the head coach runs the defence"],
];

const ord = (n: number) => `${n}${n % 10 === 1 && n % 100 !== 11 ? "st" : n % 10 === 2 && n % 100 !== 12 ? "nd" : n % 10 === 3 && n % 100 !== 13 ? "rd" : "th"}`;

function Side({ abbr, s }: { abbr: string; s: StaffSide | null }) {
  return (
    <div>
      <h3 style={{ marginBottom: 6 }}>{abbr}</h3>
      {!s ? <p className="small muted">Not available.</p> : (
        <div className="table-wrap"><table><tbody>
          {ROLES.map(([k, label, none]) => {
            const c = s[k];
            return (
              <tr key={k}>
                <td className="ink2">{label}</td>
                <td className="wrap">{c.name ?? <span className="muted">{none}</span>}</td>
                <td className="r">{c.name && c.seasons
                  ? (c.seasons === 1 ? <span className="tag warn">New this season</span>
                    : <span className="small ink2">{ord(c.seasons)}{c.known_from_2015 ? "+" : ""} season</span>)
                  : null}</td>
              </tr>
            );
          })}
        </tbody></table></div>
      )}
    </div>
  );
}

/** Head coach and coordinators for both teams (display only; the model does not use them: tested, no gain). */
export default function CoachingStaff({ away, home, staff }: { away: string; home: string; staff: { away: StaffSide | null; home: StaffSide | null } }) {
  return (
    <div className="panel">
      <h2 style={{ marginTop: 0 }}>Coaching staff</h2>
      <div className="two-col">
        <Side abbr={away} s={staff.away} />
        <Side abbr={home} s={staff.home} />
      </div>
      <p className="small muted" style={{ marginBottom: 0 }}>Seasons in that role with this team (&quot;+&quot;: at least, our records start in 2015).
        Staff from Wikipedia season pages (CC BY-SA); who calls the plays on game day is not always the coordinator. Display only: a
        test of giving last season less weight after coaching or roster changes (2019–2024) did not improve the forecasts, so the
        model does not use this.</p>
    </div>
  );
}
