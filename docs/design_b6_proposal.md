# B6: own design for the week header (proposal; nothing built)

**What is derived today.**
- The week header was built "Sasser-style" (PROGRESS.md, 5 Oct): a huge "Week N / Projections." headline on the left
  and a dates/games/updated block on the right.
- The footer, About page and README credit davidsasser.com/nfl.

The credit stays until the replacement is built. All three options below are dark theme only, use the Insularity
colours and mark, and are original layouts.

**Option A: "Scoreboard rail".**
- A slim full-width band with the INSULARITY mark at the left, then "2026 · Week 11", and the date range and game count
  set as small caps.
- Under it, the two record strips become one compact row of stat tiles:
  - model pick record;
  - this week;
  - gap 3–4;
  - gap 4+.
- No giant type: the page opens straight onto the games.
- *Best for phones.*

**Option B: "Yard-line header".**
- The week number sits inside a field graphic: faint yard lines like the site mark, with the week's games plotted along
  it by kickoff time, one tick per game.
- Title "Week 11 forecasts" in normal heading size, with the update time and the time-zone switch on the same line.
- Records sit in a panel to the right on desktop and below on phones.
- *Most distinctive, ties into the logo.*

**Option C: "Forecast ledger".**
- A two-column header. Left: "Week 11" plus a one-line summary generated from the data, e.g. "16 games · 3 big gaps ·
  forecasts locked 24 h before kickoff".
- Right: a small chart of the season's model-line record by week, a running line like the logo's.
- Records become a table-like ledger beneath.
- *Most analytical; suits the CV angle.*

**After you choose.**
1. Build it in the worktree.
2. Run the layout audit at all widths.
3. Then remove the davidsasser.com credit from the footer, About and README in the same change, and record it in
   PROGRESS.md.
