"use client";
import { useState } from "react";
import type { Team } from "@/lib/types";
import TeamBadge from "./TeamBadge";

const COLS: [string, string, (x: number) => string][] = [
  ["adj_off_epa", "Offense (adj. EPA/play)", (x) => x.toFixed(3)],
  ["adj_def_epa", "Defense (adj., + = better)", (x) => x.toFixed(3)],
  ["off_pts_drive", "Pts / drive", (x) => x.toFixed(2)],
  ["def_pts_drive", "Pts / drive allowed", (x) => x.toFixed(2)],
  ["last_starter_rating", "Last starter QB rating", (x) => x.toFixed(3)],
  ["games_this_season", "Games", (x) => x.toFixed(0)],
];

export default function RatingsTable({ rows, teams }: { rows: any[]; teams: Record<string, Team> }) {
  const [sort, setSort] = useState<string>("net");
  const withNet = rows.map((r) => ({ ...r, net: r.adj_off_epa + r.adj_def_epa }));
  const asc = sort === "def_pts_drive";
  const sorted = [...withNet].sort((a, b) => (asc ? a[sort] - b[sort] : b[sort] - a[sort]));
  return (
    <div className="table-wrap"><table>
      <thead><tr><th>#</th><th>Team</th>
        <th className="r"><button className="chip" aria-pressed={sort === "net"} onClick={() => setSort("net")}>Net</button></th>
        {COLS.map(([k, label]) => <th key={k} className="r"><button className="chip" aria-pressed={sort === k} onClick={() => setSort(k)}>{label}</button></th>)}
        <th>Last starter</th></tr></thead>
      <tbody>{sorted.map((r, i) => (
        <tr key={r.team}><td className="r">{i + 1}</td>
          <td><TeamBadge team={teams[r.team]} abbr={r.team} /> <span style={{ marginLeft: 6 }}>{teams[r.team]?.nick}</span></td>
          <td className="r"><b>{r.net.toFixed(3)}</b></td>
          {COLS.map(([k, , fmt]) => <td key={k} className="r">{fmt(r[k])}</td>)}
          <td>{r.last_starter ?? "—"}</td></tr>))}
      </tbody></table></div>
  );
}
