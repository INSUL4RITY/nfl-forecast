type Acc = { n: number; toward: number; against: number; unchanged: number; points: number; chance: number };
export interface LineMove {
  model_pick: Acc; model_line: Acc; v2_trial: Acc;
  model_line_bands: { under_1_5: Acc; "1_5_to_3": Acc; "3_plus": Acc };
}

const pts = (a: Acc) => (a.n ? `${a.points / a.n >= 0 ? "+" : "−"}${Math.abs(a.points / a.n).toFixed(2)}` : "—");
const pct = (a: Acc) => (a.n ? `${a.chance >= 0 ? "+" : "−"}${Math.abs((100 * a.chance) / a.n).toFixed(1)}%` : "—");

/** Display only (predict/linemove.py): how the market line moved between each pick's lock and the last line recorded
 *  before kickoff, from the side each line was on at the lock; the value weighs moves through 3 and 7 more. */
export default function LineMovement({ lm }: { lm?: LineMove | null }) {
  if (!lm || !lm.model_line.n) return null;
  const rows: [string, Acc, boolean][] = [
    ["Model pick", lm.model_pick, false],
    ["Model line (stats only)", lm.model_line, false],
    ["· model line under 1.5 pts from the line", lm.model_line_bands.under_1_5, true],
    ["· 1.5 to 3 pts", lm.model_line_bands["1_5_to_3"], true],
    ["· 3 pts or more", lm.model_line_bands["3_plus"], true],
    ...(lm.v2_trial.n ? [["Model v2.1 line (trial)", lm.v2_trial, false] as [string, Acc, boolean]] : []),
  ];
  return (
    <div className="panel">
      <h2>Line movement after the lock</h2>
      <p className="small ink2">When the market line moves after a pick locks, it usually reflects new information or other models
        agreeing. A line that keeps moving toward the model&apos;s side is a steadier sign of signal than a few weeks of results.
        Finished games with a publicly verifiable locked line; the later line is the last one recorded before kickoff.</p>
      <div className="table-wrap"><table>
        <thead><tr><th>Side at the lock</th><th className="r">Games</th><th className="r">Moved toward</th>
          <th className="r">Moved away</th><th className="r">No move</th><th className="r">Avg points</th>
          <th className="r">Avg value</th></tr></thead>
        <tbody>{rows.map(([label, a, sub]) => (
          <tr key={label}><td className={sub ? "ink2" : undefined}>{label}</td><td className="r">{a.n}</td>
            <td className="r">{a.toward}</td><td className="r">{a.against}</td><td className="r">{a.unchanged}</td>
            <td className="r">{pts(a)}</td><td className="r">{pct(a)}</td></tr>))}</tbody>
      </table></div>
      <p className="small muted" style={{ margin: "6px 0 0" }}>Avg points: how far the line moved toward that side per game (negative =
        away). Avg value: the change in the chance that the result lands on that side, at the locked line compared with the later
        line, with key numbers counted (final margins of 3, 7, 6, 10 and 14 are more common than a smooth curve suggests, so a move
        through 3 is worth about twice a move from 5.5 to 6.5). Key-number frequencies from 2,761 games, 2016–2025. Display only.</p>
    </div>
  );
}
