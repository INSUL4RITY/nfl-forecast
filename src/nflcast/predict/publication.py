"""Publication evidence and corrections for released forecast files.

Three different times are kept apart:
  * information cutoff  - latest time of information the forecast may use (in the release file)
  * generation time     - when our code produced the file (in the release file; self-reported)
  * publication time    - when the file first became publicly visible, established ONLY from independent
                          server-side evidence: the creation time of the earliest GitHub Actions run
                          triggered by a push whose commit contains the file (GitHub's clock, not ours).
A forecast is "publicly verifiable pregame" only if that evidence predates kickoff. Local commit dates are
self-reported and are never used as publication evidence. No historical timestamp is ever back-filled:
a file with no evidence is "not (yet) evidenced as published".

releases/publication_evidence.json is derived from GitHub and local git; entries are only ever added
(earliest evidence wins). releases/corrections.jsonl is append-only and records errors in earlier claims
without modifying the original release files.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime

from nflcast.config import RELEASES_DIR, ROOT, utc_now

EVIDENCE_FILE = RELEASES_DIR / "publication_evidence.json"
CORRECTIONS_FILE = RELEASES_DIR / "corrections.jsonl"


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")


def repo_slug() -> str | None:
    r = _run(["git", "remote", "get-url", "origin"])
    if r.returncode != 0:
        return None
    url = r.stdout.strip().removesuffix(".git")
    return "/".join(url.split("/")[-2:])


def load_evidence() -> dict:
    if EVIDENCE_FILE.exists():
        return json.loads(EVIDENCE_FILE.read_text(encoding="utf-8"))
    return {"description": "Earliest independent evidence that each release file was publicly visible. "
                           "Source: GitHub Actions push-run creation times (GitHub server clock).", "files": {}}


def _push_runs(slug: str) -> list[dict]:
    r = _run(["gh", "api", "--paginate", f"repos/{slug}/actions/runs?event=push&per_page=100",
              "--jq", ".workflow_runs[] | {id, head_sha, created_at, html_url}"])
    if r.returncode != 0:
        raise RuntimeError(f"gh api failed: {r.stderr.strip()[:300]}")
    return sorted((json.loads(line) for line in r.stdout.splitlines() if line.strip()), key=lambda x: x["created_at"])


def _is_ancestor(a: str, b: str) -> bool:
    return _run(["git", "merge-base", "--is-ancestor", a, b]).returncode == 0


def update_evidence() -> dict:
    """Add evidence for any release file that has none yet. Never removes or moves evidence later."""
    slug = repo_slug()
    ev = load_evidence()
    if not slug:
        return ev
    runs = _push_runs(slug)
    files = [f for f in _run(["git", "ls-files", "releases"]).stdout.splitlines()
             if f.endswith(".json") and "/rel_" in f]
    changed = False
    for f in files:
        if f in ev["files"]:
            continue
        added = _run(["git", "log", "--diff-filter=A", "--format=%H", "--", f]).stdout.split()
        if not added:
            continue
        add_commit = added[-1]
        blob = _run(["git", "show", f"{add_commit}:{f}"]).stdout
        for run in runs:
            if _is_ancestor(add_commit, run["head_sha"]):
                ev["files"][f] = {
                    "first_public_evidence_utc": run["created_at"].replace("Z", "+00:00"),
                    "evidence": "github_actions_push_run", "run_id": run["id"], "run_url": run["html_url"],
                    "pushed_commit": run["head_sha"], "commit_adding_file": add_commit,
                    "file_sha256_at_commit": hashlib.sha256(blob.encode("utf-8")).hexdigest(),
                }
                changed = True
                break
    if changed:
        EVIDENCE_FILE.write_text(json.dumps(ev, indent=1, sort_keys=True), encoding="utf-8")
    return ev


def public_time(run_id: str, ev: dict | None = None) -> datetime | None:
    ev = ev or load_evidence()
    for path, e in ev["files"].items():
        if path.endswith(f"{run_id}.json"):
            return datetime.fromisoformat(e["first_public_evidence_utc"])
    return None


def verification_label(generated_at: datetime, kickoff: datetime, public_at: datetime | None) -> str:
    if generated_at >= kickoff:
        return "generated_after_kickoff"
    if public_at is None:
        return "generated_pregame_not_yet_evidenced_public"
    return "publicly_verifiable_pregame" if public_at < kickoff else "generated_pregame_published_after_kickoff"


# ------------------------------------------------------------------ corrections (append-only)
def load_corrections() -> list[dict]:
    if not CORRECTIONS_FILE.exists():
        return []
    return [json.loads(line) for line in CORRECTIONS_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]


def record_late_publications(ev: dict | None = None) -> int:
    """Append a correction for every (release, game) generated before kickoff but first evidenced public after it.

    The original release files are not modified; the correction records the facts and their sources.
    """
    ev = ev or load_evidence()
    n = 0
    for path, e in sorted(ev["files"].items()):
        rel = json.loads((ROOT / path).read_text(encoding="utf-8"))
        gen = datetime.fromisoformat(rel["generated_at_utc"])
        pub = datetime.fromisoformat(e["first_public_evidence_utc"])
        for g in rel["games"]:
            ko = datetime.fromisoformat(g["kickoff_utc"])
            if gen < ko <= pub:
                n += add_correction(
                    f"late-publication:{rel['run_id']}:{g['game_id']}",
                    f"{g['away_team']} @ {g['home_team']}: forecast {rel['run_id']} was generated before kickoff but was not "
                    f"publicly verifiable before kickoff. It is a locally generated pregame forecast, not a publicly verifiable one.",
                    {"release_file": path, "game_id": g["game_id"], "generated_at_utc (self-reported)": rel["generated_at_utc"],
                     "kickoff_utc": g["kickoff_utc"], "first_public_evidence_utc": e["first_public_evidence_utc"],
                     "evidence": e["run_url"],
                     "effect": "Displayed and scored separately as 'generated pregame, published after kickoff'."})
    return n


def add_correction(correction_id: str, summary: str, details: dict) -> bool:
    """Append a correction once (idempotent by id). Earlier lines are never modified."""
    if any(c["id"] == correction_id for c in load_corrections()):
        return False
    rec = {"id": correction_id, "recorded_at_utc": utc_now().isoformat(), "summary": summary, "details": details}
    with open(CORRECTIONS_FILE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
    return True
