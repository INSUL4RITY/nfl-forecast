import type { Deserved, DeservedGroup, DeservedSide, Team, WeekGame } from "@/lib/types";
import { f1, marginText, pct } from "@/lib/format";
import TeamBadge from "./TeamBadge";

/** Display only (predict/deserved.py): the margin each team's plays usually produce, compared with the scoreboard.
 *  Never changes a forecast, the pick or any grade; finished games are never regraded with it. */
export const GROUP: Record<DeservedGroup, [string, string, string]> = {
  right_deserved: ["Right, and deserved", "tag info", "The pick's side finished ahead of the line and its play quality was ahead of the line too."],
  right_fortunate: ["Right, but fortunate", "tag warn", "The pick's side finished ahead of the line, although its play quality was behind the line."],
  wrong_unlucky: ["Wrong, but unlucky", "tag warn", "The pick's side finished behind the line, although its play quality was ahead of the line."],
  wrong_deserved: ["Wrong, and deserved", "tag", "The pick's side finished behind the line and its play quality was behind the line too."],
  close: ["Close on play quality", "tag", "Play quality put the game within 1.5 points of the line, too close to call either way."],
  level: ["Level with the line", "tag", "The final margin landed exactly on the line."],
};
const ORDER: DeservedGroup[] = ["right_deserved", "right_fortunate", "wrong_unlucky", "wrong_deserved", "close", "level"];

const sideSpread = (side: string, line: number, home: string) => {
  const s = side === home ? line : -line;
  return s === 0 ? `${side} even` : `${side} ${s > 0 ? "+" : "−"}${Math.abs(s).toFixed(1)}`;
};

export const METHOD_NOTE = "Deserved margin: each team's success rate (the share of its plays that gained expected points, with "
  + "takeaways counted for the team that made them) and yards per play, turned into points with weights fitted on 2016–2023 games "
  + "(on 2024–25 games it explains about two-thirds of the variation in final margins). It leaves out special teams, field position, "
  + "penalties and red-zone finishing, so those count as luck here. The model line rates teams on similar play-quality numbers, so it "
  + "looks better on this measure partly by construction. Display only: the official record is the scoreboard and is never regraded. "
  + "Method after nfl_simulator by dgrifka (MIT licence), refitted on this project's data; fixed on 10 November 2026.";

export function DeservedTag({ d }: { d: Deserved }) {
  if (!d.pick) return null;
  const [label, cls, title] = GROUP[d.pick.group];
  return <span className={cls} title={title}>{label}</span>;
}

/** One line for the prediction card and the week board. */
export function DeservedLine({ g }: { g: Pick<WeekGame, "deserved" | "score" | "home" | "away"> }) {
  const d = g.deserved;
  if (!d || !g.score) return null;
  return (
    <div className="small"><b>On play quality:</b> {marginText(d.margin, g.home, g.away)}{d.pick ? <> <DeservedTag d={d} /></> : null}</div>
  );
}

/** Game page panel. */
export function DeservedPanel({ g, teams }: { g: WeekGame; teams: Record<string, Team> }) {
  const d = g.deserved;
  if (!d || !g.score) return null;
  const H = g.home, A = g.away;
  const rows: [string, (s: DeservedSide) => string][] = [
    ["Plays", (s) => String(s.plays)],
    ["Success rate", (s) => pct(s.success_rate, 1)],
    ["Yards per play", (s) => f1(s.yards_per_play)],
    ["Takeaways", (s) => String(s.takeaways)],
  ];
  const p = d.pick;
  const board = p ? (p.result === "win" ? "ahead of the line" : p.result === "loss" ? "behind the line" : "level with the line") : "";
  return (
    <div className="panel">
      <h2>Deserved result</h2>
      <p style={{ marginTop: 0 }}>On play quality: <b>{marginText(d.margin, H, A)}</b>. Scoreboard: {marginText(g.score.home - g.score.away, H, A)}.</p>
      {p && <p>Model pick {sideSpread(p.side, p.line_home_spread, H)}: {board} on the scoreboard,{" "}
        {p.quality === "close" ? "within 1.5 points of the line on play quality" : `${f1(Math.abs(p.edge))} points ${p.quality} of the line on play quality`}.{" "}
        <DeservedTag d={d} /></p>}
      <div className="table-wrap"><table>
        <thead><tr><th></th><th className="r"><TeamBadge team={teams[A]} abbr={A} /></th><th className="r"><TeamBadge team={teams[H]} abbr={H} /></th></tr></thead>
        <tbody>{rows.map(([label, fmt]) => (
          <tr key={label}><td>{label}</td><td className="r">{fmt(d.away)}</td><td className="r">{fmt(d.home)}</td></tr>))}</tbody>
      </table></div>
      <p className="small muted" style={{ margin: "6px 0 0" }}>{METHOD_NOTE}</p>
    </div>
  );
}

interface Summary {
  counts: Record<DeservedGroup, number>; n: number; paused?: string | null;
  by_week: ({ week: number } & Record<DeservedGroup, number>)[];
  games: { game_id: string; week: number; home: string; away: string; side: string; line_home_spread: number; result: string;
           actual_margin: number; deserved_margin: number; edge: number; group: DeservedGroup }[];
}

/** Performance page panel: the official Model pick's finished games split by play quality. */
export function DeservedSummary({ d }: { d?: Summary | null }) {
  if (!d) return null;
  if (d.paused) return (
    <div className="panel"><h2>Deserved results</h2>
      <p className="small ink2">Paused: the play-by-play data has moved to a revised expected-points scale, and the deserved-margin
        weights were fitted on the earlier one.</p></div>);
  if (!d.n) return null;
  const c = d.counts;
  const base = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
  return (
    <div className="panel">
      <h2>Deserved results</h2>
      <p className="small ink2">The scoreboard decides the record. This splits the official Model pick&apos;s finished games by whether the
        side it took also played well enough to be ahead of the locked line, so good and bad breaks show in both directions.
        Publicly verifiable locked picks only ({d.n} games).</p>
      <div className="table-wrap"><table>
        <thead><tr><th>Scoreboard</th><th className="r">Ahead on play quality</th><th className="r">Behind on play quality</th>
          <th className="r">Close (within 1.5)</th></tr></thead>
        <tbody>
          <tr><td>Ahead of the line</td><td className="r"><b>{c.right_deserved}</b> deserved</td>
            <td className="r"><b>{c.right_fortunate}</b> fortunate</td><td className="r" rowSpan={2}>{c.close}</td></tr>
          <tr><td>Behind the line</td><td className="r"><b>{c.wrong_unlucky}</b> unlucky</td>
            <td className="r"><b>{c.wrong_deserved}</b> deserved</td></tr>
        </tbody>
      </table></div>
      <p className="small" style={{ margin: "6px 0 0" }}>On play quality the pick&apos;s side was ahead of the line in{" "}
        <b>{c.right_deserved + c.wrong_unlucky}</b> games and behind it in <b>{c.right_fortunate + c.wrong_deserved}</b>; {c.close} were
        too close to call and {c.level} finished level with the line. Bad breaks {c.wrong_unlucky}, good breaks {c.right_fortunate}.</p>
      <details style={{ marginTop: 10 }}>
        <summary className="small">By week</summary>
        <div className="table-wrap"><table>
          <thead><tr><th>Week</th>{ORDER.map((k) => <th key={k} className="r">{GROUP[k][0]}</th>)}</tr></thead>
          <tbody>{d.by_week.map((w) => (
            <tr key={w.week}><td>{w.week}</td>{ORDER.map((k) => <td key={k} className="r">{w[k]}</td>)}</tr>))}</tbody>
        </table></div>
      </details>
      <details style={{ marginTop: 6 }}>
        <summary className="small">Every game, newest first</summary>
        <div className="table-wrap"><table>
          <thead><tr><th>Week</th><th>Game</th><th>Model pick</th><th className="r">Scoreboard</th><th className="r">Play quality</th><th>Verdict</th></tr></thead>
          <tbody>{d.games.map((x) => (
            <tr key={x.game_id}><td>{x.week}</td><td><a href={`${base}/game/${x.game_id}/`}>{x.away} @ {x.home}</a></td>
              <td>{sideSpread(x.side, x.line_home_spread, x.home)}</td>
              <td className="r">{marginText(x.actual_margin, x.home, x.away)}</td>
              <td className="r">{marginText(x.deserved_margin, x.home, x.away)}</td>
              <td><span className={GROUP[x.group][1]}>{GROUP[x.group][0]}</span></td></tr>))}</tbody>
        </table></div>
      </details>
      <p className="small muted" style={{ margin: "6px 0 0" }}>{METHOD_NOTE}</p>
    </div>
  );
}
