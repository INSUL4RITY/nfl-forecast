"""Archive integrity: forecasts are never overwritten; any change to an archived file is detected."""

import json

import pytest

from nflcast.predict import archive as A
from nflcast.predict import release as R


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs" / "production.yaml").write_text("primary: {model: C}\n", encoding="utf-8")
    rel_dir = tmp_path / "releases"
    monkeypatch.setattr(A, "ROOT", tmp_path)
    monkeypatch.setattr(A, "RELEASES_DIR", rel_dir)
    monkeypatch.setattr(A, "ARCHIVE_DIR", rel_dir / "archive")
    monkeypatch.setattr(R, "RELEASES_DIR", rel_dir)
    return tmp_path


def _release(run_id="rel_20260927T120000Z"):
    return {"schema_version": 3, "run_id": run_id, "season": 2026, "week": 3, "generated_at_utc": "2026-09-27T12:00:00+00:00",
            "information_cutoff_utc": "2026-09-27T12:00:00+00:00", "code_hash": "abc", "games": [{"game_id": "G1"}]}


def test_release_files_are_write_once(sandbox):
    p = R.write_release(_release())
    with pytest.raises(FileExistsError):
        R.write_release(_release())
    assert json.loads(p.read_text(encoding="utf-8"))["run_id"] == "rel_20260927T120000Z"


def test_manifest_records_hash_and_times_and_detects_changes(sandbox):
    p = R.write_release(_release())
    man = json.loads(A.create_manifest(p).read_text(encoding="utf-8"))
    assert man["information_cutoff_utc"] and man["generated_at_utc"] and len(man["sha256"]) == 64
    assert man["model_version"]["code_hash"] == "abc" and man["game_ids"] == ["G1"]
    assert A.verify() == []
    p.write_text(p.read_text(encoding="utf-8").replace("G1", "G2"), encoding="utf-8")     # tamper with a published forecast
    assert any("CONTENT CHANGED" in x for x in A.verify())
    with pytest.raises(RuntimeError):
        A.create_manifest(p)


def test_manifest_is_write_once(sandbox):
    p = R.write_release(_release())
    m1 = A.create_manifest(p).read_text(encoding="utf-8")
    m2 = A.create_manifest(p).read_text(encoding="utf-8")      # second call must not rewrite (same created time)
    assert m1 == m2


def test_evidence_log_is_append_only(sandbox):
    p = R.write_release(_release())
    _, ev = A._paths(p)
    A._append(ev, {"type": "attempt", "what": "x"})
    A._append(ev, {"type": "attempt", "what": "y"})
    lines = ev.read_text(encoding="utf-8").splitlines()
    assert [json.loads(x)["what"] for x in lines] == ["x", "y"]


def test_release_scans_never_pick_up_archive_files(sandbox, monkeypatch):
    import re
    from nflcast import config
    p = R.write_release(_release())
    A.create_manifest(p)                                    # creates releases/archive/2026/rel_....manifest.json
    monkeypatch.setattr(config, "RELEASES_DIR", sandbox / "releases")
    names = [x.name for x in config.release_paths()]
    assert names == ["rel_20260927T120000Z.json"]
    assert re.match(config.RELEASE_PATH_RE, "releases/2026/week_03/rel_20260927T120000Z.json")
    assert not re.match(config.RELEASE_PATH_RE, "releases/archive/2026/rel_20260927T120000Z.manifest.json")


def test_missing_manifest_reported(sandbox):
    R.write_release(_release())
    assert any("no manifest" in x for x in A.verify())
