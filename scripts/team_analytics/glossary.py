"""Shared glossary of metric definitions for the team analytics page and the Insularity NFL Forecast.

One file of definitions (GLOSSARY below) rendered to glossary.html next to the report; publish_public.py copies it to the
public site, so both sites can link to one URL:
    https://insul4rity.github.io/sports-analytics/nfl-team-analytics/glossary.html
Each entry names the variant (raw, opponent-adjusted, weighted and shrunk), which plays count, and where it appears.
The forecast's own labels are changed by the forecast's separate task; its entries here describe what its pages state.
"""
from __future__ import annotations

import html
from pathlib import Path

FORECAST = "https://insul4rity.github.io/nfl-forecast/"
A, F = "Team analytics", "Forecast"

# (term, [(site, variant, definition)])
GLOSSARY = [
    ("EPA (expected points added)", [
        (A + " and " + F, "all", "Change in nflfastR's expected points from before to after a snap, from down, distance, field position and time. "
         "2026 play-by-play is kept on the original nflfastR EP valuation on both sites (nflverse re-published it on a revised scale on 17 Nov 2026; "
         "plays already archived keep their original values, later plays are converted with one frozen per-play-type line).")]),
    ("Dropback", [
        (A, "", "A scrimmage play with nflfastR's pass flag: pass attempts, sacks and scrambles. Plays without EPA or a down, kneel-downs and spikes are left out."),
        (F, "", "nflfastR qb_dropback = 1 (includes sacks and scrambles), spikes left out. Nearly the same plays; counts can differ by a few per team.")]),
    ("EPA per dropback", [
        (A, "raw", "Mean EPA over the team's (or allowed by the defence's) 2026 dropbacks. Labelled (raw)."),
        (A, "opponent-adjusted", "League mean plus the team's effect from one least-squares fit on 2026 dropbacks: EPA = intercept + home + offence + defence, "
         "team effects summing to zero, no shrinkage, no earlier seasons. Labelled (opp.-adj.)."),
        (A, "quarterback, opponent-adjusted", "A passer's raw EPA per dropback minus the average dropback-defence effect of the defences he faced."),
        (A, "expected in a matchup", "League mean plus each unit's opponent-adjusted effect, each first shrunk towards zero by how little data supports it "
         "(empirical Bayes) and scaled by the 2021-25 calibration for that week. Labelled (opp.-adjusted, shrunk)."),
        (F, "weighted and shrunk", "\"Team efficiency entering the game\" on a forecast game page: as-of values at the forecast cutoff, exponentially weighted "
         "towards recent games, prior-season games down-weighted, shrunk towards league average. Expected to differ from both analytics variants.")]),
    ("Success rate", [
        (A, "raw / opponent-adjusted", "Share of plays with EPA above zero; the adjusted version uses the same least-squares fit as EPA.")]),
    ("Overall rating", [
        (A, "points per game", "(adjusted offensive EPA per play - league mean) x plays per game + (league mean - adjusted defensive EPA per play) x plays per game "
         "+ the kept share of special-teams EPA per game. 2026 plays only, no prior, no shrinkage of the team effects."),
        (A, "with 2025 prior", "The same, with each unit's 2026 value shrunk towards a prior from its 2025 value (year-to-year slope fitted on 2021-25)."),
        (F, "Team ratings", "Opponent-adjusted efficiency in EPA per play, net = offence + defence, re-fitted using only games completed before each moment, "
         "leaning on last season early in the year (down-weighted) and shrunk towards league average.")]),
    ("Luck", [
        (A, "Luck index (points and EPA)", "Mean of (wins - Pythagorean expected wins from points) and (wins - EPA-expected wins). +0.75 or more = potentially "
         "overperforming, -0.75 or less = potentially underperforming."),
        (F, "Luck", "Wins minus expected wins from net EPA per play in each game (a logistic fitted on earlier seasons). +1 or more / -1 or less get a label. "
         "Because the analytics index also averages in the points-based gap, the two can differ by a win or more.")]),
    ("Hit-or-sack rate and pressure rate", [
        (A, "hit-or-sack rate", "Share of dropbacks with a quarterback hit or a sack in the play-by-play (a proxy: free play-by-play has no pressure flag)."),
        (A, "pressure rate", "Pro Football Reference pressures (hurries, hits, sacks) per dropback, from game totals.")]),
    ("Reliability (High / Medium / Low)", [
        (A, "", "How much of a figure is likely to last at its sample size, from the fitted shrinkage weight: High 50%+ kept, Medium 20-50%, Low under 20%.")]),
]

PAGE = """<!DOCTYPE html>
<html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Metric glossary</title>
<meta name="description" content="Definitions of the metrics shared by the Insularity NFL team analytics page and the Insularity NFL Forecast.">
<style>
:root {{ --page: #0b0f17; --surface: #141a25; --surface-2: #1b2230; --ink: #e8ecf3; --ink-2: #aab3c3; --muted: #8a94a6; --rule: #283142; --accent: #79aefc; color-scheme: dark; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--page); color: var(--ink); font: 15px/1.55 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }}
.wrap {{ max-width: 980px; margin: 0 auto; padding: 24px 16px 60px; }}
h1 {{ font-size: 1.9rem; margin: 0 0 6px; }}
h2 {{ font-size: 1.15rem; margin: 28px 0 8px; border-top: 1px solid var(--rule); padding-top: 18px; }}
p {{ max-width: 78ch; color: var(--ink-2); }}
a {{ color: var(--accent); text-decoration: underline; text-underline-offset: 2px; }}
dl {{ margin: 0; display: grid; gap: 8px; }}
dl div {{ background: var(--surface); border: 1px solid var(--rule); border-radius: 8px; padding: 10px 12px; }}
dt {{ font-weight: 700; }}
dt small {{ color: var(--muted); font-weight: 600; margin-left: 6px; }}
dd {{ margin: 4px 0 0; color: var(--ink-2); }}
</style></head><body><main class="wrap">
<p><a href="./">Team analytics</a> · <a href="{forecast}">Insularity NFL Forecast</a></p>
<h1>Metric glossary</h1>
<p>One name, one definition: each entry says which variant a number is (raw, opponent-adjusted, weighted and shrunk) and which plays it counts.
The same label on the two sites can show different numbers when the variants differ; this page says how. For analysis and education only.</p>
{body}
</main></body></html>
"""


def render() -> str:
    parts = []
    for term, rows in GLOSSARY:
        items = "".join(f"<div><dt>{html.escape(site)}{f' <small>{html.escape(var)}</small>' if var else ''}</dt><dd>{html.escape(d)}</dd></div>"
                        for site, var, d in rows)
        parts.append(f'<h2 id="{html.escape(term.split(" (")[0].lower().replace(" ", "-"))}">{html.escape(term)}</h2><dl>{items}</dl>')
    return PAGE.format(forecast=FORECAST, body="\n".join(parts))


def write(folder: Path) -> Path:
    out = folder / "glossary.html"
    out.write_text(render(), encoding="utf-8")
    return out
