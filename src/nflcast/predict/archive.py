"""Durable archive of every published forecast file, independent of GitHub Actions retention.

For each release file releases/<season>/week_<wk>/<run_id>.json:
  releases/archive/<season>/<run_id>.manifest.json   WRITE-ONCE: sha256, size, information cutoff, generation time,
                                                      model version (code hash, production config hash, OOF source,
                                                      QB-rate version), input-snapshot hashes, game ids.
  releases/archive/<season>/<run_id>.evidence.jsonl  APPEND-ONLY evidence records:
     rfc3161_timestamp   FreeTSA signed timestamp over the file's sha256 (proves the exact bytes EXISTED at that
                         time; only the hash is sent). Token stored base64; verified with openssl at creation.
     github_push_run     copy of the GitHub Actions run metadata (server clock) for the push that made the file
                         public, preserved here because Actions records expire.
     web_archive         Internet Archive capture of the commit-pinned raw URL; the archived bytes are downloaded
                         and their sha256 compared with the manifest (proves PUBLIC availability at that time).
  verify()               recomputes every release file's sha256 against its manifest; any difference is an
                         integrity violation (previous forecasts must never be overwritten).
Evidence is recorded when obtained; nothing is back-dated. Failures are logged as attempts and retried later.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import shutil
import subprocess
import time
from pathlib import Path

import requests

from nflcast.config import RELEASES_DIR, ROOT, utc_now

ARCHIVE_DIR = RELEASES_DIR / "archive"
TSA_URL = "https://freetsa.org/tsr"
TSA_CERTS = {"cacert.pem": "https://freetsa.org/files/cacert.pem", "tsa.crt": "https://freetsa.org/files/tsa.crt"}
UA = {"User-Agent": "nflcast-archiver/0.1 (+https://github.com/INSUL4RITY/nfl-forecast)"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _openssl() -> str | None:
    for c in (shutil.which("openssl"), r"C:\Program Files\Git\usr\bin\openssl.exe", r"C:\Program Files\Git\mingw64\bin\openssl.exe"):
        if c and Path(c).exists():
            return c
    return None


def release_files() -> list[Path]:
    return sorted(p for p in RELEASES_DIR.glob("[0-9][0-9][0-9][0-9]/week_[0-9][0-9]/rel_*.json"))


def _paths(rel_path: Path) -> tuple[Path, Path]:
    season = rel_path.parent.parent.name
    d = ARCHIVE_DIR / season
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{rel_path.stem}.manifest.json", d / f"{rel_path.stem}.evidence.jsonl"


def _evidence(ev_path: Path) -> list[dict]:
    if not ev_path.exists():
        return []
    return [json.loads(x) for x in ev_path.read_text(encoding="utf-8").splitlines() if x.strip()]


def _append(ev_path: Path, rec: dict) -> None:
    with open(ev_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"recorded_at_utc": utc_now().isoformat(), **rec}, sort_keys=True) + "\n")


# ------------------------------------------------------------------ manifests (write-once)
def create_manifest(rel_path: Path) -> Path:
    man, _ = _paths(rel_path)
    sha = _sha256(rel_path)
    if man.exists():
        old = json.loads(man.read_text(encoding="utf-8"))
        if old["sha256"] != sha:
            raise RuntimeError(f"INTEGRITY VIOLATION: {rel_path} no longer matches its archived manifest")
        return man
    rel = json.loads(rel_path.read_text(encoding="utf-8"))
    prod = (ROOT / "configs" / "production.yaml").read_bytes()
    m = {
        "run_id": rel.get("run_id"), "release_path": rel_path.relative_to(ROOT).as_posix(), "sha256": sha,
        "size_bytes": rel_path.stat().st_size, "schema_version": rel.get("schema_version", 1),
        "information_cutoff_utc": rel.get("information_cutoff_utc"), "generated_at_utc": rel.get("generated_at_utc"),
        "model_version": {"code_hash": rel.get("code_hash"), "stage": rel.get("stage"),
                          "production_config_sha256_at_archiving": hashlib.sha256(prod).hexdigest(),
                          "oof_source_run": (rel.get("models") or {}).get("oof_source_run"),
                          "qb_start_rates": (rel.get("models") or {}).get("qb_start_rates")},
        "input_snapshots": rel.get("input_snapshots"),
        "game_ids": [g["game_id"] for g in rel.get("games", [])],
        "manifest_created_at_utc": utc_now().isoformat(),
        "note": "Manifest creation time is when this archive entry was made; it is not a publication time.",
    }
    man.write_text(json.dumps(m, indent=1, sort_keys=True), encoding="utf-8")
    return man


def verify() -> list[str]:
    """Integrity check: every release file must match its write-once manifest. Returns problems (empty = OK)."""
    problems = []
    for p in release_files():
        man, _ = _paths(p)
        if not man.exists():
            problems.append(f"no manifest: {p.relative_to(ROOT).as_posix()}")
            continue
        if json.loads(man.read_text(encoding="utf-8"))["sha256"] != _sha256(p):
            problems.append(f"CONTENT CHANGED: {p.relative_to(ROOT).as_posix()}")
    return problems


# ------------------------------------------------------------------ RFC 3161 trusted timestamp
def _tsa_certs() -> Path:
    d = ARCHIVE_DIR / "tsa_certs"
    d.mkdir(parents=True, exist_ok=True)
    for name, url in TSA_CERTS.items():
        if not (d / name).exists():
            (d / name).write_bytes(requests.get(url, timeout=60, headers=UA).content)
    return d


def _rel(p: Path) -> str:
    # Git-for-Windows openssl splits arguments at spaces, so always pass paths relative to the project root.
    return p.relative_to(ROOT).as_posix()


def _ossl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([_openssl(), *args], cwd=ROOT, capture_output=True, text=True)


def verify_token(tsr: Path, tsq: Path) -> bool:
    certs = _tsa_certs()
    v = _ossl("ts", "-verify", "-in", _rel(tsr), "-queryfile", _rel(tsq), "-CAfile", _rel(certs / "cacert.pem"),
              "-untrusted", _rel(certs / "tsa.crt"))
    return "Verification: OK" in (v.stdout + v.stderr)


def timestamp(rel_path: Path) -> dict | None:
    """Obtain and verify an RFC 3161 timestamp over the file's sha256 (once per file).

    If an earlier token exists but was not verified, it is re-verified and a verification record is appended
    (no new timestamp is requested, so the earliest token keeps its time)."""
    man, ev = _paths(rel_path)
    evid = _evidence(ev)
    if any((e["type"] == "rfc3161_timestamp" and e.get("verified")) or e["type"] == "rfc3161_verification" and e.get("verified")
           for e in evid):
        return None
    if not _openssl():
        _append(ev, {"type": "attempt", "what": "rfc3161_timestamp", "error": "openssl not found"})
        return None
    work = ARCHIVE_DIR / ".tmp"
    work.mkdir(exist_ok=True)
    tsq, tsr = work / "q.tsq", work / "r.tsr"
    try:
        prior = [e for e in evid if e["type"] == "rfc3161_timestamp" and e.get("token_base64")]
        if prior:
            tsr.write_bytes(base64.b64decode(prior[0]["token_base64"]))
            tsq.write_bytes(base64.b64decode(prior[0]["query_base64"]))
            ok = verify_token(tsr, tsq)
            rec = {"type": "rfc3161_verification", "verified": ok, "token_recorded_at_utc": prior[0]["recorded_at_utc"],
                   "tsa_time": prior[0].get("tsa_time")}
            _append(ev, rec)
            return rec if ok else None
        q = _ossl("ts", "-query", "-data", _rel(rel_path), "-sha256", "-cert", "-out", _rel(tsq))
        if q.returncode != 0:
            raise RuntimeError(q.stderr[-300:])
        r = requests.post(TSA_URL, data=tsq.read_bytes(), headers={**UA, "Content-Type": "application/timestamp-query"}, timeout=60)
        r.raise_for_status()
        tsr.write_bytes(r.content)
        text = _ossl("ts", "-reply", "-in", _rel(tsr), "-text").stdout
        gen = re.search(r"Time stamp: (.+)", text)
        rec = {"type": "rfc3161_timestamp", "tsa": TSA_URL, "sha256": _sha256(rel_path),
               "tsa_time": gen.group(1).strip() if gen else None, "verified": verify_token(tsr, tsq),
               "token_base64": base64.b64encode(r.content).decode(), "query_base64": base64.b64encode(tsq.read_bytes()).decode(),
               "proves": "the exact file bytes existed no later than tsa_time (not publication)"}
        _append(ev, rec)
        return rec
    except Exception as e:  # noqa: BLE001
        _append(ev, {"type": "attempt", "what": "rfc3161_timestamp", "error": str(e)[:300]})
        return None
    finally:
        for f in (tsq, tsr):
            f.unlink(missing_ok=True)


# ------------------------------------------------------------------ GitHub push-run snapshot
def record_github_runs(publication_evidence: dict) -> int:
    """Copy each file's GitHub Actions push-run metadata into its evidence log (once), before Actions retention expires."""
    n = 0
    for path, e in publication_evidence.get("files", {}).items():
        p = ROOT / path
        if not p.exists():
            continue
        _, ev = _paths(p)
        if any(x["type"] == "github_push_run" for x in _evidence(ev)):
            continue
        _append(ev, {"type": "github_push_run", "first_public_evidence_utc": e["first_public_evidence_utc"], "run_id": e["run_id"],
                     "run_url": e["run_url"], "pushed_commit": e["pushed_commit"], "commit_adding_file": e["commit_adding_file"],
                     "file_sha256_at_commit": e["file_sha256_at_commit"],
                     "proves": "GitHub received a push containing the file at this time (GitHub server clock)"})
        n += 1
    return n


# ------------------------------------------------------------------ Internet Archive capture
def web_archive(rel_path: Path, slug: str, commit: str, max_wait_s: int = 90) -> dict | None:
    """Capture the commit-pinned raw URL in the Wayback Machine and verify the archived bytes' sha256."""
    _, ev = _paths(rel_path)
    if any(e["type"] == "web_archive" and e.get("sha256_matches") for e in _evidence(ev)):
        return None
    rel = rel_path.relative_to(ROOT).as_posix()
    url = f"https://raw.githubusercontent.com/{slug}/{commit}/{rel}"
    sha = _sha256(rel_path)
    try:
        r = requests.post("https://web.archive.org/save", data={"url": url}, headers=UA, timeout=180)
        job = re.search(r'spn\.watchJob\("([^"]+)"', r.text)
        ts = None
        if job:
            for _ in range(max_wait_s // 5):
                time.sleep(5)
                s = requests.get(f"https://web.archive.org/save/status/{job.group(1)}", headers=UA, timeout=60).json()
                if s.get("status") == "success":
                    ts = s.get("timestamp")
                    break
                if s.get("status") == "error":
                    break
        if ts is None:  # fall back to the availability API (an existing capture of this exact pinned URL)
            a = requests.get("https://archive.org/wayback/available", params={"url": url}, headers=UA, timeout=60).json()
            ts = ((a.get("archived_snapshots") or {}).get("closest") or {}).get("timestamp")
        if not ts:
            _append(ev, {"type": "attempt", "what": "web_archive", "url": url, "error": f"no capture (HTTP {r.status_code})"})
            return None
        got = requests.get(f"https://web.archive.org/web/{ts}id_/{url}", headers=UA, timeout=120)
        rec = {"type": "web_archive", "url": url, "capture_timestamp": ts,
               "capture_time_utc": f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}T{ts[8:10]}:{ts[10:12]}:{ts[12:14]}+00:00",
               "archived_copy": f"https://web.archive.org/web/{ts}id_/{url}",
               "sha256_matches": hashlib.sha256(got.content).hexdigest() == sha,
               "proves": "a third party retrieved the public file with these exact bytes at capture_time_utc"}
        _append(ev, rec)
        return rec
    except Exception as e:  # noqa: BLE001
        _append(ev, {"type": "attempt", "what": "web_archive", "url": url, "error": str(e)[:300]})
        return None


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def run(capture_public: bool = True) -> dict:
    """Manifest + timestamp every release; copy GitHub run metadata; capture pushed files in the Web Archive."""
    from nflcast.predict import publication as PUB
    out = {"manifests": 0, "timestamps": 0, "github_runs": 0, "web_archive": 0, "problems": []}
    for p in release_files():
        before = _paths(p)[0].exists()
        create_manifest(p)
        out["manifests"] += 0 if before else 1
        out["timestamps"] += 1 if timestamp(p) else 0
    ev = PUB.load_evidence()
    out["github_runs"] = record_github_runs(ev)
    slug = PUB.repo_slug()
    if capture_public and slug:
        for path, e in ev.get("files", {}).items():
            p = ROOT / path
            if p.exists() and web_archive(p, slug, e["pushed_commit"]):
                out["web_archive"] += 1
    out["problems"] = verify()
    return out


def summary_for(run_id: str, season: int | str) -> dict:
    """Evidence summary for display: first time proven to exist, first time proven public (by each source)."""
    ev = _evidence(ARCHIVE_DIR / str(season) / f"{run_id}.evidence.jsonl")
    man_p = ARCHIVE_DIR / str(season) / f"{run_id}.manifest.json"
    man = json.loads(man_p.read_text(encoding="utf-8")) if man_p.exists() else {}
    out = {"sha256": man.get("sha256"), "rfc3161_time": None, "github_push_time": None, "web_archive_time": None,
           "web_archive_copy": None}
    for e in ev:
        if e["type"] in ("rfc3161_timestamp", "rfc3161_verification") and e.get("verified"):
            out["rfc3161_time"] = out["rfc3161_time"] or e.get("tsa_time")
        elif e["type"] == "github_push_run":
            out["github_push_time"] = out["github_push_time"] or e.get("first_public_evidence_utc")
        elif e["type"] == "web_archive" and e.get("sha256_matches"):
            out["web_archive_time"] = out["web_archive_time"] or e.get("capture_time_utc")
            out["web_archive_copy"] = out["web_archive_copy"] or e.get("archived_copy")
    return out
