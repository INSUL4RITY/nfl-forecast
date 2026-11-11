"""Team analytics: the public copy drops player IDs and keeps everything else."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "team_analytics"))
import publish_public as pp  # noqa: E402

DATA = {"absences": [{"team": "ARI", "player": "A Player", "gsis_id": "00-0038540", "share": 0.9}],
        "qb": {"ARI": {"latest": "00-0035289", "primary": None, "qbs": [{"id": "00-0033119", "name": "Q B", "starts": 8}]}},
        "tables": [{"id": "zones_off"}], "games": [{"id": "2026_10_LA_ARI", "label": "LA at ARI </b>"}]}


def page(data):
    body = json.dumps(data).replace("</", "<\\/")
    return ('<title>x</title><div class="meta" id="meta-line"></div>\r\n<script>\r\nconst DATA = ' + body
            + ';\r\nconst TEAMS = DATA.teams;\r\n</script>')


def test_player_ids_are_removed_and_other_ids_kept():
    out = pp.public_page(page(DATA), {"through_week": 9, "season": 2026})
    got = json.loads(pp.DATA_RE.search(out).group(1))
    assert "00-00" not in out
    assert "gsis_id" not in got["absences"][0] and got["absences"][0]["player"] == "A Player"
    assert "latest" not in got["qb"]["ARI"] and got["qb"]["ARI"]["primary"] is None
    assert got["qb"]["ARI"]["qbs"] == [{"name": "Q B", "starts": 8}]
    assert got["tables"] == [{"id": "zones_off"}] and got["games"][0]["id"] == "2026_10_LA_ARI"
    assert "<\\/b>" in out and "</b>" not in out.split("const DATA")[1].split(";")[0]
    assert "const TEAMS = DATA.teams;" in out
