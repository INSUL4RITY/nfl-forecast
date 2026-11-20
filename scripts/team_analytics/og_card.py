"""Sharing card for the report: Open Graph and Twitter tags, and a 1200 x 630 preview image made at build time.

The image is the top of that week's overall ratings, drawn as a small HTML page and screenshotted by a headless Chromium
browser (Microsoft Edge or Google Chrome, both on the build machine). No imaging library is needed. If no browser is found
or the screenshot fails, the tags are written without an image and the build carries on.
"""
from __future__ import annotations

import html
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pandas as pd

PUBLIC_URL = "https://insul4rity.github.io/sports-analytics/nfl-team-analytics/"
IMAGE = "og.png"
W, H = 1200, 630
BROWSERS = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe", "msedge", "google-chrome", "chromium", "chrome"]


def title(meta: dict) -> str:
    return f"NFL Week {meta['through_week'] + 1} Team Analytics, {meta['season']}"


def description(meta: dict) -> str:
    return (f"Opponent-adjusted NFL team analytics entering week {meta['through_week'] + 1} of {meta['season']}: ratings, "
            "matchups, quarterbacks, coaching and context, built in Python from public nflverse data. For analysis and education only.")


def card_html(T: pd.DataFrame, meta: dict, n: int = 8) -> str:
    """The preview image as a fixed-size page: the top `n` teams by overall rating (points per game)."""
    top = T.sort_values("rating_pg", ascending=False).head(n)
    hi = max(float(top.rating_pg.max()), 1.0)
    rows = "".join(
        f'<div class="r"><span class="k">{i}</span><span class="t">{html.escape(str(t))}</span>'
        f'<span class="b"><i style="width:{max(2.0, 100 * max(float(v), 0) / hi):.1f}%"></i></span>'
        f'<span class="v">{float(v):+.1f}</span></div>'
        for i, (t, v) in enumerate(top.rating_pg.items(), 1))
    return f"""<!DOCTYPE html><html lang="en-GB"><head><meta charset="utf-8"><style>
html, body {{ margin: 0; width: {W}px; height: {H}px; background: #0b0f17; color: #e8ecf3; font-family: "Segoe UI", system-ui, sans-serif; overflow: hidden; }}
.w {{ box-sizing: border-box; width: {W}px; height: {H}px; padding: 46px 64px; display: grid; grid-template-rows: auto auto 1fr auto; gap: 8px; border-top: 8px solid #79aefc; }}
.brand {{ font-size: 20px; font-weight: 800; letter-spacing: 0.12em; color: #aab3c3; text-transform: uppercase; }}
h1 {{ margin: 0; font-size: 50px; letter-spacing: -0.02em; }}
.list {{ display: grid; gap: 9px; align-content: center; }}
.r {{ display: grid; grid-template-columns: 34px 84px 1fr 96px; gap: 16px; align-items: center; font-size: 27px; }}
.k {{ color: #8a94a6; font-variant-numeric: tabular-nums; }}
.t {{ font-weight: 800; }}
.b {{ height: 22px; background: #1b2230; border-radius: 4px; overflow: hidden; }}
.b i {{ display: block; height: 100%; background: #79aefc; }}
.v {{ text-align: right; font-variant-numeric: tabular-nums; font-weight: 700; }}
.foot {{ font-size: 19px; color: #8a94a6; }}
</style></head><body><div class="w"><div class="brand">Insularity NFL Forecast · team analytics</div>
<h1>{html.escape(title(meta))}</h1><div class="list">{rows}</div>
<div class="foot">Overall rating, points per game vs an average team (opponent-adjusted EPA), through week {meta['through_week']}. Data: nflverse.</div>
</div></body></html>"""


def _browser() -> str | None:
    for b in BROWSERS:
        p = b if os.path.isabs(b) else shutil.which(b)
        if p and Path(p).exists():
            return p
    return None


def render(T: pd.DataFrame, meta: dict, out_png: Path) -> str | None:
    """Write the preview image; returns a problem description, or None when the image was written."""
    exe = _browser()
    if exe is None:
        return "no headless browser found"
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "card.html"
        page.write_text(card_html(T, meta), encoding="utf-8")
        shot = Path(tmp) / IMAGE
        cmd = [exe, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
               f"--user-data-dir={Path(tmp) / 'profile'}", f"--window-size={W},{H}", f"--screenshot={shot}", page.as_uri()]
        try:
            subprocess.run(cmd, capture_output=True, timeout=90, check=False)
        except (OSError, subprocess.TimeoutExpired) as e:
            return f"screenshot failed: {e}"
        if not shot.exists() or shot.stat().st_size < 2000:
            return "screenshot failed: no image written"
        shutil.copyfile(shot, out_png)
    return None


def head_tags(meta: dict, has_image: bool) -> str:
    """Open Graph and Twitter card tags. The image URL is the public page's copy (publish_public.py copies it)."""
    t, d = html.escape(title(meta)), html.escape(description(meta))
    tags = [f'<meta name="description" content="{d}">', '<meta property="og:type" content="website">',
            f'<meta property="og:title" content="{t}">', f'<meta property="og:description" content="{d}">',
            f'<meta property="og:url" content="{PUBLIC_URL}">', '<meta property="og:locale" content="en_GB">',
            f'<meta name="twitter:card" content="{"summary_large_image" if has_image else "summary"}">',
            f'<meta name="twitter:title" content="{t}">', f'<meta name="twitter:description" content="{d}">']
    if has_image:
        img = f"{PUBLIC_URL}{IMAGE}?w={meta['season']}{meta['through_week'] + 1:02d}"
        alt = html.escape(f"Top eight NFL teams by overall rating entering week {meta['through_week'] + 1}, {meta['season']}")
        tags += [f'<meta property="og:image" content="{img}">', f'<meta property="og:image:width" content="{W}">',
                 f'<meta property="og:image:height" content="{H}">', f'<meta property="og:image:alt" content="{alt}">',
                 f'<meta name="twitter:image" content="{img}">', f'<meta name="twitter:image:alt" content="{alt}">']
    return "\n".join(tags)
