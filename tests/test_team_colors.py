"""Two teams in one game never share a colour family on the site (web/lib/format.ts teamPairColors; user, 2026-11-16)."""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which("node") is None or not (ROOT / "web" / "node_modules" / "typescript").exists(),
                    reason="needs node and web/node_modules (npm ci in web/)")
def test_every_pairing_gets_distinct_team_colours():
    r = subprocess.run(["node", str(ROOT / "scripts" / "check_team_colors.js")], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "992 pairings, 0 with colours that look alike" in r.stdout
