"""Turn the NGS team-page lines (slug;oc;dc;value~percentile x 28) into scripts/team_analytics/ngs_trends_2026.json."""
import json
import sys

KEYS = ("Offensive Personnel|11P,Offensive Personnel|12P,Offensive Personnel|13P,Offensive Personnel|21P,Play Selection|CALLED PASS,"
        "Play Selection|PLAY ACTION,Play Selection|MOTION,Play Selection|TEMPO,Passing Offense|QUICK PASS,Passing Offense|IN-BREAKING,"
        "Passing Offense|OUT-BREAKING,Passing Offense|10+ AIR YARDS,Rushing Offense|INSIDE ZONE,Rushing Offense|OUTSIDE ZONE,Rushing Offense|GAP,"
        "Rushing Offense|MAN,Defensive Personnel|BASE,Defensive Personnel|NICKEL,Defensive Personnel|DIME,Coverage|ZONE,Coverage|MAN,Coverage|PRESS,"
        "Coverage Structure|SINGLE-HIGH,Coverage Structure|SPLIT-SAFETY,Coverage Structure|COVER 0,Pass Rush|BLITZ RATE,Pass Rush|PRESSURE (BLITZ),"
        "Pass Rush|PRESSURE (NO BLITZ)").split(",")
CODE = {"arizona-cardinals": "ARI", "atlanta-falcons": "ATL", "baltimore-ravens": "BAL", "buffalo-bills": "BUF", "carolina-panthers": "CAR",
        "chicago-bears": "CHI", "cincinnati-bengals": "CIN", "cleveland-browns": "CLE", "dallas-cowboys": "DAL", "denver-broncos": "DEN",
        "detroit-lions": "DET", "green-bay-packers": "GB", "houston-texans": "HOU", "indianapolis-colts": "IND", "jacksonville-jaguars": "JAX",
        "kansas-city-chiefs": "KC", "las-vegas-raiders": "LV", "los-angeles-chargers": "LAC", "los-angeles-rams": "LA", "miami-dolphins": "MIA",
        "minnesota-vikings": "MIN", "new-england-patriots": "NE", "new-orleans-saints": "NO", "new-york-giants": "NYG", "new-york-jets": "NYJ",
        "philadelphia-eagles": "PHI", "pittsburgh-steelers": "PIT", "san-francisco-49ers": "SF", "seattle-seahawks": "SEA",
        "tampa-bay-buccaneers": "TB", "tennessee-titans": "TEN", "washington-commanders": "WAS"}
COL = {"11P": "off_11p", "12P": "off_12p", "13P": "off_13p", "21P": "off_21p", "CALLED PASS": "off_called_pass", "PLAY ACTION": "off_ed_play_action",
       "MOTION": "off_motion", "TEMPO": "off_tempo_sec", "QUICK PASS": "off_quick_pass", "IN-BREAKING": "off_in_breaking",
       "OUT-BREAKING": "off_out_breaking", "10+ AIR YARDS": "off_10plus_air", "INSIDE ZONE": "off_inside_zone", "OUTSIDE ZONE": "off_outside_zone",
       "GAP": "off_gap", "BASE": "def_base", "NICKEL": "def_nickel", "DIME": "def_dime", "ZONE": "def_zone", "PRESS": "def_press",
       "SINGLE-HIGH": "def_single_high", "SPLIT-SAFETY": "def_split_safety", "COVER 0": "def_cover0", "BLITZ RATE": "def_blitz",
       "PRESSURE (BLITZ)": "def_pressure_blitz", "PRESSURE (NO BLITZ)": "def_pressure_no_blitz"}


def main(src, out, retrieved, through_week):
    teams = {}
    for line in open(src, encoding="utf-8").read().strip().splitlines():
        f = line.split(";")
        assert len(f) == 3 + len(KEYS), (f[0], len(f))
        rec = {"oc": f[1] or None, "dc": f[2] or None}
        for k, cell in zip(KEYS, f[3:]):
            cat, lab = k.split("|")
            col = ("off_man_blocking" if cat == "Rushing Offense" else "def_man") if lab == "MAN" else COL[lab]
            v, p = cell.split("~")
            rec[col] = round(float(v.rstrip("s")) / (1 if col == "off_tempo_sec" else 100), 3)
            rec[col + "_pct"] = int(p) if p else None
        teams[CODE[f[0]]] = rec
    assert len(teams) == 32, len(teams)
    d = {"season": 2026, "through_week": through_week,
         "source": {"title": "NFL Next Gen Stats, Next Gen Trends team pages (NFL.com)", "url": "https://www.nfl.com/stats/ngs/trends",
                    "retrieved": retrieved,
                    "note": "Season usage rates (share of snaps or plays) and NFL percentiles (0-100, higher = uses it more), read from the 32 team pages."},
         "definitions": {"off_ed_play_action": "Play action on early downs", "off_tempo_sec": "Average seconds between snaps (lower = faster)",
                         "off_quick_pass": "Quick passes", "off_10plus_air": "Targets 10+ air yards downfield",
                         "def_single_high": "One deep safety (middle of the field closed)", "def_split_safety": "Two deep safeties",
                         "def_blitz": "5+ rushers", "def_pressure_blitz": "Pressure rate when blitzing",
                         "def_pressure_no_blitz": "Pressure rate with 4 or fewer rushers"},
         "how_to_update": "Hand-kept. Each Tuesday, read the 32 team pages: the hidden 'Team tendency statistics' lists hold the usage values and the "
                          "chart labels the percentiles. Save them as slug;oc;dc;value~percentile lines and run scripts/team_analytics/ngs_trends.py (lines file, output, retrieved date, through week). Usage only: the "
                          "per-trait EPA on the league page is not copied, because coverage-specific EPA did not hold up (coverage_backtest.json).",
         "teams": teams}
    open(out, "w", encoding="utf-8").write(json.dumps(d, indent=1) + "\n")
    print("wrote", out, "SEA zone", teams["SEA"]["def_zone"], "LV 11p", teams["LV"]["off_11p"], "SEA tempo", teams["SEA"]["off_tempo_sec"])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]))
