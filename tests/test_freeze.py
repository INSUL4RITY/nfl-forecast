"""Model freeze: a changed artifact or changed production/settings config must block loading and publication."""

import hashlib

import joblib
import pytest
import yaml

from nflcast.predict import freeze as F


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    (tmp_path / "configs").mkdir()
    for f in F.WATCHED:
        (tmp_path / f).write_text("x: 1\n", encoding="utf-8")
    art = tmp_path / "artifacts" / "frozen" / "vTest" / "production.joblib"
    art.parent.mkdir(parents=True)
    joblib.dump({"cmod": "C", "bmod": "B"}, art)
    rec = {"version": "vTest", "artifact": "artifacts/frozen/vTest/production.joblib",
           "artifact_sha256": hashlib.sha256(art.read_bytes()).hexdigest(),
           "watched_configs": {f: hashlib.sha256((tmp_path / f).read_bytes()).hexdigest() for f in F.WATCHED}}
    (tmp_path / "configs" / "model_freeze.yaml").write_text(yaml.safe_dump(rec), encoding="utf-8")
    monkeypatch.setattr(F, "ROOT", tmp_path)
    monkeypatch.setattr(F, "FREEZE_FILE", tmp_path / "configs" / "model_freeze.yaml")
    return tmp_path, art


def test_frozen_artifact_loads_with_version(sandbox):
    assert F.check() == []
    M = F.load()
    assert M["frozen"] and M["model_version"] == "vTest" and M["cmod"] == "C"


def test_changed_artifact_blocks(sandbox):
    _, art = sandbox
    joblib.dump({"cmod": "retrained"}, art)
    assert "frozen artifact changed" in F.check()
    with pytest.raises(RuntimeError):
        F.load()


def test_changed_production_config_blocks(sandbox):
    root, _ = sandbox
    (root / "configs" / "production.yaml").write_text("x: 2\n", encoding="utf-8")
    assert any("production.yaml changed" in p for p in F.check())


def test_refreeze_refused(sandbox):
    with pytest.raises(SystemExit):
        F.freeze("vOther", "2027-02-15")
