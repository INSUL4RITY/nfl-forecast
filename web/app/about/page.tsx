export default function About() {
  return (
    <>
      <div className="page-head"><div>
        <div className="small muted" style={{ fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase" }}>Project case study</div>
        <h1>About nflcast</h1>
      </div></div>
      <div className="panel" style={{ maxWidth: 820 }}>
        <p>nflcast is a sports-analytics portfolio project: a reproducible pipeline that forecasts every NFL game and publishes its forecasts before kickoff,
          then scores them honestly. The aim is prediction quality and transparency, not betting. The site shows projected outcomes and uncertainty,
          not &quot;picks&quot;, and it has no bookmaker links.</p>
        <h2>Design decisions</h2>
        <ul>
          <li><b>Benchmarks first.</b> Market-only, football-only and naive models were built and evaluated before any combined model, on identical games and cutoffs.</li>
          <li><b>Honest validation.</b> Walk-forward folds, a tuning period, a development period and a locked test season evaluated once. The headline
            finding is that the market line is very hard to beat; that result is reported rather than hidden.</li>
          <li><b>As-of data.</b> Every feature is built from what was available before the cutoff, and raw data snapshots are append-only.</li>
          <li><b>Frozen releases.</b> Forecasts are immutable JSON files with model, data and code versions; the website only renders them.</li>
        </ul>
        <h2>Stack</h2>
        <p>Python (nflreadpy, Polars, scikit-learn, NumPy) for data, features, models and evaluation; versioned JSON as the interface; Next.js and
          TypeScript for this static site.</p>
        <h2>Inspiration</h2>
        <p>The weekly board layout is inspired by the clarity of <a href="https://davidsasser.com/nfl">davidsasser.com/nfl</a>. This project is independent: it does
          not reproduce that site&apos;s model or assets and makes no claim about how it works.</p>
      </div>
    </>
  );
}
