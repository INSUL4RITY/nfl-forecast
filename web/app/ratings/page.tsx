import LocalTime from "@/components/LocalTime";
import RatingsTable from "@/components/RatingsTable";
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
      <p className="small muted">Ratings are one input to the football-only model. QB rating: shrunk EPA per dropback of the team&apos;s most recent starter.</p>
    </>
  );
}
