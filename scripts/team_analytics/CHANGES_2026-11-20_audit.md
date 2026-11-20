# Team analytics audit, phases A and B (20 Nov 2026)

Branch `claude/analytics-audit-ab` (from `claude/nfl-week-8-analytics-554e6d` at 96de354). Not pushed, not published. The week 11
report in `reports/team_analytics/2026_week11/` was rebuilt locally with this code for review.

## What changed

**Phase A**
- **A1 HTML basics.** The template is a full document: `<!DOCTYPE html>`, `<html lang="en-GB">`, `<head>`, `<body>`. The page renders in
  standards mode (`CSS1Compat`). Standards mode exposed one layout bug (rank text for screen readers escaped the table scroll frames and
  caused a sideways page scroll); table frames are now positioned so their contents stay inside.
- **A2 EP scale.** `ep_harmonise.py` repeats the forecast's conversion exactly (pandas port of main's `src/nflcast/data/ep_scale.py`;
  `ep_scale_2026.yaml` is a verbatim copy of main's `configs/ep_scale.yaml`, commit 8ef6b29). The archived snapshot was available: main's
  raw file is checked against its sha256 and copied (not linked) into this worktree's cache. 26,062 plays keep their archived
  original-scale values; 184 (Monday night's LAC @ BAL and nflverse edits) are converted with the frozen line. Residual check (team
  offence EPA per play, converted vs archived): sd 0.0043, mean 0.0000, inside the forecast's limits (0.015, 0.01). The banner is gone;
  Method's quality checks carry the line. If the check ever fails, a warning returns next to the figures. `main` is untouched.
- **A3 Accessibility.** Chart points have `role="img"` and a name; every scrolling table frame and code block is focusable with
  `role="region"` and a unique name from its nearest heading; text links are underlined; each sub-navigation has its own label; no empty
  header cells; ranks read as "+0.180, rank 1 of 32, top five" (visually hidden text, so copy-paste keeps a separator) and the top and
  bottom five carry ▴/▾ as well as colour. `scripts/layout_audit.js` now runs axe-core 4.10.2 in the same pass: serious or critical
  violations fail the audit; minor and moderate ones are listed.
- **A4 Mobile navigation.** At 640 px or below a fixed "Sections" menu and a "Top" button sit at the bottom right. Desktop is unchanged.
- **A5 Records.** Records and scores use a non-breaking hyphen and never wrap ("(3‑7)").
- **A6 QB team labels.** A passer who changed team shows every team in order with games and the current one marked: "LV 9 g, MIN 1 g (now)",
  "ARI 8 g, BAL 1 g (now)".
- **A7 Win rates.** Shown only when the ESPN file is at most one week behind the report; otherwise one line in Method, no repeated notices.
  (This week: file through week 8, report through week 10, so they are not shown.)
- **A8 Sharing.** Open Graph and Twitter card tags (title, description, `og:url`, `en_GB`, image with alt text). The 1200 x 630 image
  (top eight overall ratings) is drawn at build time and screenshotted by headless Edge/Chrome (`og_card.py`); `publish_public.py` copies
  it beside the page. If no browser is found the tags are written without an image.
- **A9 Credits.** A footer lists each source with the licence or terms it publishes (checked 20 Nov): nflverse CC BY 4.0; FTN via nflverse
  CC BY-SA 4.0 (attributed to FTN Data via nflverse); PFR and NGS: no licence stated, their own terms apply; NWS public domain; Open-Meteo
  CC BY 4.0; ESPN: no data licence, Disney/ESPN terms; Hashtag Football: no licence, its terms; Sam Hoppen's dataset: no licence stated.
- **A10 OL absence cost.** New analysis `backtest_line_absences_pregame.py` -> `line_absence_pregame.json`: a starter is missing only if
  that was known before kickoff (no offensive snap, or listed Out/Doubtful). 2021-25, 2,238 team-games: -0.036 EPA per dropback per
  missing starter (95% -0.051 to -0.020), about 23% smaller than the old in-game definition (-0.047); the hit-or-sack change is no longer
  clearly above zero (+0.3 points, 95% -0.1 to +0.7); still no extra cost against strong rushes. The caution and a new Method paragraph
  quote the pre-game figure and say how it differs. The old script and output are kept for history.

**Phase B**
- **B1 One name, one number.** Every EPA-per-dropback label says its variant: "(raw)", "(opp.-adj.)", and in the matchup table "(season,
  raw)" vs "Expected in this matchup (opp.-adjusted, shrunk)"; the rankings header shows "(adj.)"/"(raw)" in view, not only in a tooltip.
  New shared glossary (`glossary.py` -> `glossary.html`, published beside the page at
  https://insul4rity.github.io/sports-analytics/nfl-team-analytics/glossary.html) with each variant on both sites, including the
  forecast's dropback definition (`qb_dropback`) and its weighted-and-shrunk "Team efficiency entering the game".
- **B2 Two luck numbers.** Renamed "Luck index (points and EPA)" with one sentence on how it differs from the forecast's Luck (EPA only)
  and a link to the forecast's ratings page.
- **B3 Two ratings.** A note under the rankings and in Method on how the overall rating (points per game, 2026 only, no prior or shrinkage,
  special teams included) differs from the forecast's Team ratings, with a link. Not merged.

## What did not change
- No fitted file was refitted (`matchup_calibration.json`, `*_shrinkage.json`, `streak_backtest.json` unchanged). The model, `main`,
  releases and the forecast's labels are untouched. Public wording stays neutral; dark theme only.
- The scheduled refresh still runs on `claude/nfl-week-8-analytics-554e6d`; nothing here reaches it until merged.

## For your decision
- **Licence terms found while checking A9.** Hashtag Football's terms say redistribution or republication of any part of the site is
  prohibited, and the page republishes its per-referee flag rates. ESPN/Disney terms prohibit copying except as permitted, and the page
  republishes hand-copied win rates when current. Options: keep with credit, replace with this report's own flag counts from the
  play-by-play (available for games where nflverse names the referee), or ask the sources. Nothing was removed.
- **Private artifact.** The relative `glossary.html` link resolves on the public site; on the private artifact it needs the glossary
  published as a supporting file (one extra file on the next publish).
- **Live audit** is pending publication (not allowed in this task). After you approve and it is published, the live audit runs with axe.
- **Phase C** items C1-C7 await your approval one by one.
