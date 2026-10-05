import type { Team } from "@/lib/types";
import TeamBadge from "./TeamBadge";

export interface LuckRow {
  team: string; games: number; wins: number; losses: number; ties: number; expected_wins: number; luck: number;
  one_score: [number, number]; turnover_margin: number; fumbles_recovered: number; fumbles_total: number;
  net_epa_play: number; read: "ahead" | "behind" | "in_line";
}

const READ: Record<LuckRow["read"], [string, string]> = {
  ahead: ["Results ahead of play", "tag warn"],
  behind: ["Results behind play", "tag info"],
  in_line: ["In line", "tag"],
};

const signed = (x: number, d = 1) => `${x > 0 ? "+" : x < 0 ? "−" : ""}${Math.abs(x).toFixed(d)}`;

/** Luck and regression watch: wins vs expected wins from play quality, plus the usual luck sources. Display only. */
export default function LuckTable({ rows, teams }: { rows: LuckRow[]; teams: Record<string, Team> }) {
  return (
    <div className="table-wrap"><table>
      <thead><tr><th>Team</th><th className="r">Record</th><th className="r">Expected wins</th><th className="r">Luck</th>
        <th className="r">One-score games</th><th className="r">Turnover margin</th><th className="r">Fumbles recovered</th><th>Read</th></tr></thead>
      <tbody>{rows.map((r) => {
        const [label, cls] = READ[r.read];
        return (
          <tr key={r.team}>
            <td><TeamBadge team={teams[r.team]} abbr={r.team} /></td>
            <td className="r">{r.wins}–{r.losses}{r.ties ? `–${r.ties}` : ""}</td>
            <td className="r">{r.expected_wins.toFixed(1)}</td>
            <td className="r"><b>{signed(r.luck)}</b></td>
            <td className="r">{r.one_score[0]}–{r.one_score[1]}</td>
            <td className="r">{signed(r.turnover_margin, 0)}</td>
            <td className="r">{r.fumbles_total ? `${r.fumbles_recovered} of ${r.fumbles_total}` : "—"}</td>
            <td><span className={cls}>{label}</span></td>
          </tr>
        );
      })}</tbody>
    </table></div>
  );
}
