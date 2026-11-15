"""Team analytics: deciding when the unattended refresh needs a browser layout audit."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "team_analytics"))
import layout_audit_state as las  # noqa: E402


def files(tmp_path, template="<html>a</html>\n"):
    (tmp_path / "template.html").write_bytes(template.encode())
    (tmp_path / "build_html.py").write_bytes(b"x = 1\n")
    return {"template.html": tmp_path / "template.html", "build_html.py": tmp_path / "build_html.py"}


def test_needed_until_both_audits_pass_with_these_files(tmp_path):
    p, state = files(tmp_path), tmp_path / "state.json"
    now = las.fingerprint(p)
    assert las.needed({}, now)[0]
    las.record("local", "build 1", state, now)
    need, why = las.needed(las.load(state), now)
    assert need and "live" in why
    las.record("live", "page 1", state, now)
    need, why = las.needed(las.load(state), now)
    assert not need and "unchanged" in why


def test_a_template_change_makes_it_needed_again(tmp_path):
    p, state = files(tmp_path), tmp_path / "state.json"
    now = las.fingerprint(p)
    las.record("local", "", state, now)
    las.record("live", "", state, now)
    p2 = files(tmp_path, template="<html>b</html>\n")
    need, why = las.needed(las.load(state), las.fingerprint(p2))
    assert need and "template.html" in why
    las.record("local", "", state, las.fingerprint(p2))                # new inputs: the old passes are dropped
    assert set(json.loads(state.read_text())["passed"]) == {"local"}


def test_line_endings_do_not_force_an_audit(tmp_path):
    a = las.fingerprint(files(tmp_path, template="<html>\n</html>\n"))
    b = las.fingerprint(files(tmp_path, template="<html>\r\n</html>\r\n"))
    assert a == b
