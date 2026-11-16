"""Private trials (user decision 2026-11-16): research lines computed with each forecast release but never published.

Their files live under data/private_trials/ (git-ignored, mirrored to the PRIVATE backup repository) and each file gets
an RFC 3161 trusted timestamp over its sha256, so the predictions can later be shown to predate the games without ever
having been public. Nothing here may block a release or touch the release JSON.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
from pathlib import Path

import requests

from nflcast.config import ROOT, utc_now
from nflcast.predict import archive as ARCH

PRIVATE_DIR = ROOT / "data" / "private_trials"


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def timestamp_file(path: Path, evidence: Path | None = None) -> dict | None:
    """RFC 3161 timestamp over `path` (same TSA and checks as the release archive), appended to `evidence`
    (default: <path>.tsa.jsonl). Returns the record, or None on failure (recorded as an attempt). Never raises."""
    evidence = evidence or path.with_name(path.name + ".tsa.jsonl")
    rec: dict
    try:
        if not ARCH._openssl():
            raise RuntimeError("openssl not found")
        work = ROOT / "data" / ".tsa_tmp"
        work.mkdir(parents=True, exist_ok=True)
        tsq, tsr = work / "q.tsq", work / "r.tsr"
        try:
            q = ARCH._ossl("ts", "-query", "-data", ARCH._rel(path), "-sha256", "-cert", "-out", ARCH._rel(tsq))
            if q.returncode != 0:
                raise RuntimeError(q.stderr[-300:])
            r = requests.post(ARCH.TSA_URL, data=tsq.read_bytes(),
                              headers={**ARCH.UA, "Content-Type": "application/timestamp-query"}, timeout=60)
            r.raise_for_status()
            tsr.write_bytes(r.content)
            text = ARCH._ossl("ts", "-reply", "-in", ARCH._rel(tsr), "-text").stdout
            gen = re.search(r"Time stamp: (.+)", text)
            rec = {"type": "rfc3161_timestamp", "file": path.name, "tsa": ARCH.TSA_URL, "sha256": _sha256(path),
                   "tsa_time": gen.group(1).strip() if gen else None, "verified": ARCH.verify_token(tsr, tsq),
                   "token_base64": base64.b64encode(r.content).decode(), "query_base64": base64.b64encode(tsq.read_bytes()).decode(),
                   "recorded_at_utc": utc_now().isoformat(),
                   "proves": "the exact file bytes existed no later than tsa_time (not publication)"}
        finally:
            for f in (tsq, tsr):
                f.unlink(missing_ok=True)
    except Exception as e:  # noqa: BLE001 - a private trial never blocks anything
        rec = {"type": "attempt", "what": "rfc3161_timestamp", "file": path.name, "error": str(e)[:300],
               "recorded_at_utc": utc_now().isoformat()}
    with open(evidence, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
    return rec if rec["type"] == "rfc3161_timestamp" else None
