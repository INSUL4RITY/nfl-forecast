"""Copy the newest team analytics report to the public portfolio site.

Adds a line with links to the code and the portfolio, removes host-specific tags, and strips nflverse player IDs from
the embedded data (the page never shows or uses them; the private report and the repository outputs keep them for
matching). Nothing else changes: the report already uses no market data.

    .venv\\Scripts\\python.exe scripts\\team_analytics\\publish_public.py --out ..\\sports-analytics\\docs\\nfl-team-analytics
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODE = "https://github.com/INSUL4RITY/nfl-forecast/tree/team-analytics/scripts/team_analytics"
PORTFOLIO = "https://insul4rity.github.io/sports-analytics/"
ANCHOR = '<div class="meta" id="meta-line"></div>'
PLAYER_ID = re.compile(r"00-00\d{5}")                 # nflverse gsis id
DATA_RE = re.compile(r"const DATA = (\{.*?\});\r?\n", re.S)   # one line of JSON (no indent), so the first "};" + newline ends it


def strip_ids(x):
    """Drop every dict entry whose value is a player ID (gsis_id, a QB row's id, a team's latest or primary passer)."""
    if isinstance(x, dict):
        return {k: strip_ids(v) for k, v in x.items() if not (isinstance(v, str) and PLAYER_ID.fullmatch(v))}
    if isinstance(x, list):
        return [strip_ids(v) for v in x]
    return x


def public_page(html: str, meta: dict) -> str:
    html = re.sub(r'\s*<meta name="claude:[^"]*"[^>]*>', "", html)
    m = DATA_RE.search(html)
    assert m, "report data block changed"
    data = json.dumps(strip_ids(json.loads(m.group(1)))).replace("</", "<\\/")
    html = html[:m.start(1)] + data + html[m.end(1):]
    assert not PLAYER_ID.search(html), "a player ID is still in the public page"
    desc = (f"Opponent-adjusted NFL team analytics entering week {meta['through_week'] + 1} of {meta['season']}, "
            "built in Python from public nflverse data.")
    html = html.replace("</title>", f'</title>\n<meta name="description" content="{desc}">', 1)
    note = (f'\n  <p class="meta">Built in Python from public <a href="https://github.com/nflverse">nflverse</a> data, no market data · '
            f'<a href="{CODE}">Code</a> · <a href="{PORTFOLIO}">Portfolio</a></p>')
    assert html.count(ANCHOR) == 1, "report header changed"
    return html.replace(ANCHOR, ANCHOR + note, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(sorted((ROOT / "reports" / "team_analytics").glob("20*_week*"))[-1]))
    ap.add_argument("--out", required=True, help="folder for index.html")
    a = ap.parse_args()
    d, out = Path(a.dir), Path(a.out)
    meta = json.loads((d / "bundle_meta.json").read_text())
    page = public_page((d / "report.html").read_text(encoding="utf-8"), meta)
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    print("wrote", out / "index.html", f"{len(page.encode()) / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
