"""Has nflverse switched play-by-play to the revised EP valuation (nflfastR PR 618)?

The revision values a score net of the kickoff it gives the opponent: mean ep falls about 0.4, a touchdown is worth about
5.9 instead of 7, and the two-point probability changes from 0.4735 to 0.49. This report's historical fits (shrinkage,
composite weights, the 2025 prior, the fatigue and travel studies) use the old scale, and history files are cached, so a
re-downloaded current season on the new scale would mix the two. Same markers as the forecast's own guard
(src/nflcast/predict/alerts.py, ep_scale_problem). The check only warns: no number is changed.
"""
from __future__ import annotations

import pandas as pd

OLD_TWO_POINT = {0.0, 0.4735}
EP_MEAN_MIN, KICKOFF_EPA_MIN, KICKOFF_MIN_N = 1.80, 0.10, 200   # old scale: mean ep ~1.98, kickoff epa ~+0.23-0.25


KICKOFF_RULE_FROM = 2024   # dynamic kickoff: original-scale kickoff EPA ~+0.25 from 2024, about 0 in 2021-23


def problem(pbp: pd.DataFrame, season: int | None = None) -> str | None:
    """A description of the revised-scale markers found, or None if the file looks unchanged. The kickoff marker is used
    only from 2024: under the earlier kickoff rules kickoff EPA was about 0 on the original scale too."""
    found = []
    if "two_point_conversion_prob" in pbp:
        tp = set(pbp.two_point_conversion_prob.dropna().round(4).unique().tolist()) - OLD_TWO_POINT
        if tp:
            found.append(f"two-point probability {sorted(tp)}")
    ep = pbp["ep"].dropna() if "ep" in pbp else pd.Series(dtype=float)
    if len(ep) and ep.mean() < EP_MEAN_MIN:
        found.append(f"mean EP {ep.mean():.2f}")
    if "play_type" in pbp and "epa" in pbp and (season is None or season >= KICKOFF_RULE_FROM):
        k = pbp.loc[pbp.play_type == "kickoff", "epa"].dropna()
        if len(k) >= KICKOFF_MIN_N and k.mean() < KICKOFF_EPA_MIN:
            found.append(f"kickoff EPA {k.mean():+.2f}")
    return "; ".join(found) or None


def check(frames: dict) -> tuple[str | None, str]:
    """frames: {season: play-by-play}. Returns (warning or None, quality-check line)."""
    bad = {s: m for s, m in ((s, problem(f, s)) for s, f in frames.items()) if m}
    seasons = sorted(frames)
    if not bad:
        return None, (f"EP scale: play-by-play {seasons[0]}-{seasons[-1]} is on the original nflfastR EP valuation "
                      "(two-point probability 0.4735), the scale every historical fit here uses.")
    which = ", ".join(f"{s} ({m})" for s, m in sorted(bad.items()))
    warn = (f"nflverse play-by-play looks like the revised EP valuation (nflfastR PR 618) for {which}. This report's historical "
            "fits use the original scale, so EPA and success-rate figures may mix the two. Treat EPA-based numbers with care "
            "until the report is rebuilt on one scale.")
    return warn, f"EP scale: WARNING. {warn}"
