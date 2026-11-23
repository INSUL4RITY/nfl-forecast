"""Week 12 2026 starters the user named (pre-registration: reported, no results): rating under the current rule and the
QB layer, as of the data on 20 Nov 2026. Writes reports/research/qb_layer/week12_named.json."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import polars as pl  # noqa: E402

import build as B  # noqa: E402
from nflcast.data import sources as S  # noqa: E402

NAMES = ["Kyle McCord", "Jacoby Brissett", "Fernando Mendoza", "Joe Milton"]
ctx = B.context()
pl_ = S.fetch("players").filter((pl.col("display_name").is_in(NAMES) | pl.col("display_name").str.starts_with("Joe Milton")) & (pl.col("position") == "QB"))
now = int(datetime(2026, 11, 24, 18, 0, tzinfo=timezone.utc).timestamp() * 1e6)   # week 12 build (Tue 18:00 UK)
cur, ql = B.QBRating(ctx["qt"], B.Cfg(), ctx["bucket"]), B.QBRating(ctx["qt"], B.Cfg(runs=True, opp=True, ped=True), ctx["bucket"])
q = ctx["qt"]
out = []
for r in pl_.iter_rows(named=True):
    g = r["gsis_id"]
    a, b = cur.rating(g, now, 2026), ql.rating(g, now, 2026)
    mine = q.filter(pl.col("qb_id") == g)
    out.append({"player": r["display_name"], "draft_round": r.get("draft_round"), "draft_pick": r.get("draft_pick"),
                "bucket": ctx["bucket"].get(g, "UDFA"), "career_dropbacks": int(mine["db"].sum()), "designed_runs": int(mine["runs"].sum()),
                "rating_current": round(a[0], 4), "rating_qb_layer": round(b[0], 4), "weighted_plays_current": round(a[1], 1),
                "cpoe_qb_layer": round(b[2] * 100, 2), "prior_current": round(cur.prior(now, g), 4), "prior_qb_layer": round(ql.prior(now, g), 4)})
Path(__file__).with_name("week12_named.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
for o in out:
    print(o)
