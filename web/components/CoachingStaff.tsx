import type { PlayCaller, PlayCallers, StaffSide } from "@/lib/types";
import { weekName } from "@/lib/format";

const ROLES: [keyof StaffSide, string, string][] = [
  ["head_coach", "Head coach", ""],
  ["off_coordinator", "Offensive coordinator", "None listed: the head coach runs the offence"],
  ["def_coordinator", "Defensive coordinator", "None listed: the head coach runs the defence"],
];
const CALLERS: ["offence" | "defence", string][] = [["offence", "Calls the offence"], ["defence", "Calls the defence"]];

const ord = (n: number) => `${n}${n % 10 === 1 && n % 100 !== 11 ? "st" : n % 10 === 2 && n % 100 !== 12 ? "nd" : n % 10 === 3 && n % 100 !== 13 ? "rd" : "th"}`;

function CallerRow({ label, c }: { label: string; c: PlayCaller }) {
  return (
    <tr>
      <td className="ink2">{label}</td>
      <td className="wrap">{c.name ?? <span className="muted">Not known</span>}
        {c.name && c.head_coach ? <span className="small ink2"> (head coach)</span> : null}</td>
      <td className="r">{c.since_week
        ? <span className="tag warn" title={c.replaced ? `Took over from ${c.replaced}` : undefined}>Since {weekName(c.since_week).toLowerCase()}</span>
        : null}</td>
    </tr>
  );
}

function Side({ abbr, s, pc }: { abbr: string; s: StaffSide | null; pc: PlayCallers | null }) {
  return (
    <div>
      <h3 style={{ marginBottom: 6 }}>{abbr}</h3>
      {!s && !pc ? <p className="small muted">Not available.</p> : (
        <div className="table-wrap"><table><tbody>
          {s && ROLES.map(([k, label, none]) => {
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
          {pc && CALLERS.map(([k, label]) => <CallerRow key={k} label={label} c={pc[k]} />)}
        </tbody></table></div>
      )}
      {pc && pc.based_on === "last_game" ? (
        <p className="small muted" style={{ margin: "4px 0 0" }}>Play callers as of {weekName(pc.as_of_week).toLowerCase()}, their last finished game.</p>
      ) : null}
    </div>
  );
}

/** Head coach, coordinators and play callers for both teams (display only; the model does not use them: tested, no gain). */
export default function CoachingStaff({ away, home, staff, callers }: {
  away: string; home: string; staff: { away: StaffSide | null; home: StaffSide | null };
  callers: { away: PlayCallers | null; home: PlayCallers | null } | null;
}) {
  const anyCallers = !!(callers && (callers.away || callers.home));
  return (
    <div className="panel">
      <h2 style={{ marginTop: 0 }}>Coaching staff</h2>
      <div className="two-col">
        <Side abbr={away} s={staff.away} pc={callers?.away ?? null} />
        <Side abbr={home} s={staff.home} pc={callers?.home ?? null} />
      </div>
      <p className="small muted" style={{ marginBottom: 0 }}>Seasons in that role with this team (&quot;+&quot;: at least, our records start in 2015).
        Staff from Wikipedia season pages (CC BY-SA). The coordinator is not always the one who calls the plays on game day
        {anyCallers ? <>: play callers come from Sam Hoppen&apos;s play-caller data (compiled with Arif Hasan), taken from finished
          games only; &quot;Since week N&quot; marks a change during this season</> : null}. Display only: a test of giving last season
        less weight after coaching or roster changes (2019–2024) did not improve the forecasts, so the model does not use this.</p>
    </div>
  );
}
