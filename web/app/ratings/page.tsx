import LocalTime from "@/components/LocalTime";
import RatingsTable from "@/components/RatingsTable";
import LuckTable from "@/components/LuckTable";
import { getRatings, getTeams } from "@/lib/data";

export default function RatingsPage() {
  const r = getRatings();
  return (
    <>
      <div className="page-head"><div>
        <div className="small muted" style={{ fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase" }}>{r.season} season</div>
        <h1>Team ratings</h1>
        <p className="ink2" style={{ maxWidth: 760 }}>As of <LocalTime iso={r.as_of} />. Opponent-adjusted efficiency ratings in expected points added
          (EPA) per play, re-fitted using only games completed before this moment. Early in the season these lean heavily on last season
          (down-weighted) and are shrunk toward league average. Net = offense + defense.</p>
      </div></div>
      <div className="panel"><RatingsTable rows={r.teams} teams={getTeams()} /></div>
      {r.luck?.length > 0 && (
        <div className="panel">
          <h2>Luck and regression watch</h2>
          <p className="small ink2" style={{ marginTop: 0 }}>Season to date. <b>Expected wins</b> come from how well each team has actually played (net
            EPA per play in each game, converted to a win chance using earlier seasons). <b>Luck</b> = wins minus expected wins: teams whose
            results are well ahead of their play (+1 or more) tend to regress; teams well behind (−1 or less) tend to improve. One-score
            records, turnover margins and fumble recoveries (about half are recovered in the long run) are the usual sources of luck. Early
            in the season these samples are small. Display only: the model rates teams on play quality, not on wins, so it already
            discounts luck.</p>
          <LuckTable rows={r.luck} teams={getTeams()} />
        </div>
      )}
      <p className="small muted">Ratings are one input to the football-only model. QB rating: shrunk EPA per dropback of the team&apos;s most recent starter.</p>
    </>
  );
}
