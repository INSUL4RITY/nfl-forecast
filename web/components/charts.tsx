"use client";
import { useRef, useState } from "react";

export interface Series { key: string; label: string; color: string; values: (number | null)[] }

const W = 820, H = 300, M = { t: 16, r: 150, b: 34, l: 48 };

function niceTicks(lo: number, hi: number, n = 5): number[] {
  const step = Math.pow(10, Math.floor(Math.log10((hi - lo) / n || 1)));
  const s = [1, 2, 2.5, 5, 10].map((k) => k * step).find((k) => (hi - lo) / k <= n) ?? step * 10;
  const out: number[] = [];
  for (let v = Math.ceil(lo / s) * s; v <= hi + 1e-9; v += s) out.push(Number(v.toFixed(6)));
  return out;
}

/** Multi-series line chart with crosshair tooltip, legend and end-of-line direct labels (<= 4 series). */
export function LineChart({ series, xLabels, xTickIdx, yDecimals = 2, yTitle }: {
  series: Series[]; xLabels: string[]; xTickIdx: number[]; yDecimals?: number; yTitle: string;
}) {
  const yFmt = (v: number) => v.toFixed(yDecimals);
  const [hover, setHover] = useState<number | null>(null);
  const ref = useRef<SVGSVGElement>(null);
  const all = series.flatMap((s) => s.values.filter((v): v is number => v != null));
  const lo = Math.min(...all), hi = Math.max(...all);
  const pad = (hi - lo) * 0.08 || 0.5;
  const y0 = lo - pad, y1 = hi + pad;
  const n = xLabels.length;
  const x = (i: number) => M.l + (i / Math.max(n - 1, 1)) * (W - M.l - M.r);
  const y = (v: number) => M.t + (1 - (v - y0) / (y1 - y0)) * (H - M.t - M.b);
  const ticks = niceTicks(y0, y1);
  const onMove = (ev: React.MouseEvent) => {
    const r = ref.current!.getBoundingClientRect();
    const px = ((ev.clientX - r.left) / r.width) * W;
    const i = Math.round(((px - M.l) / (W - M.l - M.r)) * (n - 1));
    setHover(i >= 0 && i < n ? i : null);
  };
  // end labels, nudged apart to avoid collisions
  const ends = series.map((s) => {
    const idx = s.values.map((v, i) => (v != null ? i : -1)).filter((i) => i >= 0).pop() ?? 0;
    return { s, yy: y(s.values[idx] as number) };
  }).sort((a, b) => a.yy - b.yy);
  for (let i = 1; i < ends.length; i++) if (ends[i].yy - ends[i - 1].yy < 14) ends[i].yy = ends[i - 1].yy + 14;

  return (
    <div style={{ position: "relative" }}>
      <div className="legend">{series.map((s) => <span key={s.key}><i style={{ background: s.color }} />{s.label}</span>)}</div>
      <svg ref={ref} viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label={yTitle}
           onMouseMove={onMove} onMouseLeave={() => setHover(null)} style={{ display: "block" }}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={M.l} x2={W - M.r} y1={y(t)} y2={y(t)} stroke="var(--grid)" strokeWidth={1} />
            <text x={M.l - 8} y={y(t) + 4} textAnchor="end" fontSize={11} fill="var(--muted)" className="num">{yFmt(t)}</text>
          </g>
        ))}
        <line x1={M.l} x2={W - M.r} y1={H - M.b} y2={H - M.b} stroke="var(--axis)" />
        {xTickIdx.map((i) => (
          <text key={i} x={x(i)} y={H - M.b + 18} textAnchor="middle" fontSize={11} fill="var(--muted)">{xLabels[i].split(" ")[0]}</text>
        ))}
        {series.map((s) => {
          const d = s.values.map((v, i) => (v == null ? "" : `${i === 0 || s.values[i - 1] == null ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`)).join("");
          return <path key={s.key} d={d} fill="none" stroke={s.color} strokeWidth={2} strokeLinejoin="round" />;
        })}
        {ends.map(({ s, yy }) => (
          <text key={s.key} x={W - M.r + 8} y={yy + 4} fontSize={12} fill="var(--ink)">{s.label}</text>
        ))}
        {hover != null && (
          <g>
            <line x1={x(hover)} x2={x(hover)} y1={M.t} y2={H - M.b} stroke="var(--axis)" />
            {series.map((s) => s.values[hover] != null && (
              <circle key={s.key} cx={x(hover)} cy={y(s.values[hover] as number)} r={4.5} fill={s.color} stroke="var(--surface)" strokeWidth={2} />
            ))}
          </g>
        )}
      </svg>
      {hover != null && (
        <div className="chart-tip" style={{ left: `${(x(hover) / W) * 100}%`, top: 30, transform: hover > n * 0.6 ? "translateX(-105%)" : "translateX(8px)" }}>
          <div style={{ fontWeight: 700, marginBottom: 4 }}>{xLabels[hover]}</div>
          {series.map((s) => (
            <div key={s.key}><i style={{ display: "inline-block", width: 10, height: 3, background: s.color, marginRight: 6, verticalAlign: "middle" }} />
              {s.label}: <b className="num">{s.values[hover] != null ? yFmt(s.values[hover] as number) : "—"}</b></div>
          ))}
        </div>
      )}
    </div>
  );
}

export interface CalBin { bin_lo: number; bin_hi: number; n: number; mean_pred: number; obs_home_win: number }

/** Reliability diagram: mean predicted vs observed home-win rate per bin; dot area grows with n. */
export function CalibrationChart({ bins, color, label }: { bins: CalBin[]; color: string; label: string }) {
  const [hover, setHover] = useState<CalBin | null>(null);
  const S = 320, P = 40;
  const sc = (v: number) => P + v * (S - 2 * P);
  const maxN = Math.max(...bins.map((b) => b.n));
  return (
    <div style={{ position: "relative", maxWidth: 380 }}>
      <svg viewBox={`0 0 ${S} ${S}`} width="100%" role="img" aria-label={`Calibration: ${label}`}>
        {[0, 0.25, 0.5, 0.75, 1].map((t) => (
          <g key={t}>
            <line x1={sc(t)} x2={sc(t)} y1={sc(0)} y2={sc(1)} stroke="var(--grid)" />
            <line x1={sc(0)} x2={sc(1)} y1={S - sc(t)} y2={S - sc(t)} stroke="var(--grid)" />
            <text x={sc(t)} y={S - P + 16} fontSize={10} textAnchor="middle" fill="var(--muted)">{t * 100}%</text>
            <text x={P - 6} y={S - sc(t) + 3} fontSize={10} textAnchor="end" fill="var(--muted)">{t * 100}%</text>
          </g>
        ))}
        <line x1={sc(0)} y1={S - sc(0)} x2={sc(1)} y2={S - sc(1)} stroke="var(--axis)" strokeDasharray="4 4" />
        <text x={S / 2} y={S - 6} fontSize={11} textAnchor="middle" fill="var(--ink-2)">Predicted P(home win)</text>
        <text x={12} y={S / 2} fontSize={11} textAnchor="middle" fill="var(--ink-2)" transform={`rotate(-90 12 ${S / 2})`}>Observed home-win rate</text>
        {bins.map((b) => (
          <circle key={b.bin_lo} cx={sc(b.mean_pred)} cy={S - sc(b.obs_home_win)} r={4 + 8 * Math.sqrt(b.n / maxN)}
                  fill={color} fillOpacity={0.85} stroke="var(--surface)" strokeWidth={2}
                  onMouseEnter={() => setHover(b)} onMouseLeave={() => setHover(null)} />
        ))}
      </svg>
      {hover && (
        <div className="chart-tip" style={{ left: `${(sc(hover.mean_pred) / S) * 100}%`, top: `${((S - sc(hover.obs_home_win)) / S) * 100}%`, transform: "translate(10px,-50%)" }}>
          Bin {Math.round(hover.bin_lo * 100)}–{Math.round(hover.bin_hi * 100)}%: n={hover.n}<br />
          predicted {(hover.mean_pred * 100).toFixed(1)}% · observed {(hover.obs_home_win * 100).toFixed(1)}%
        </div>
      )}
    </div>
  );
}
