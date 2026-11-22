"""RFC 3161 timestamp for a research file (FreeTSA), written as <file>.tsa.jsonl next to it (same record format as
qb_v3c_preregistration_2026-11-16.md.tsa.jsonl). Proves the exact bytes existed no later than the TSA time.
Usage (worktree root, PYTHONPATH=src): python reports/research/gap_absences/tsa_stamp.py reports/research/<file>
"""
import base64
import hashlib
import json
import re
import sys
from pathlib import Path

import requests

from nflcast.config import ROOT, utc_now
from nflcast.predict import archive as A

rel = Path(sys.argv[1])
f = ROOT / rel
out = f.with_name(f.name + ".tsa.jsonl")
if out.exists():
    raise SystemExit(f"{out.name} exists: a file is timestamped once")
work = ROOT / ".scratch"
work.mkdir(exist_ok=True)
tsq, tsr = work / "q.tsq", work / "r.tsr"
A._tsa_certs()
q = A._ossl("ts", "-query", "-data", rel.as_posix(), "-sha256", "-cert", "-out", ".scratch/q.tsq")
if q.returncode != 0:
    raise SystemExit(q.stderr)
r = requests.post(A.TSA_URL, data=tsq.read_bytes(), headers={**A.UA, "Content-Type": "application/timestamp-query"}, timeout=60)
r.raise_for_status()
tsr.write_bytes(r.content)
text = A._ossl("ts", "-reply", "-in", ".scratch/r.tsr", "-text").stdout
gen = re.search(r"Time stamp: (.+)", text)
rec = {"type": "rfc3161_timestamp", "file": f.name, "tsa": A.TSA_URL, "sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
       "tsa_time": gen.group(1).strip() if gen else None, "verified": A.verify_token(tsr, tsq),
       "token_base64": base64.b64encode(r.content).decode(), "query_base64": base64.b64encode(tsq.read_bytes()).decode(),
       "recorded_at_utc": utc_now().isoformat(), "proves": "the exact file bytes existed no later than tsa_time (not publication)"}
out.write_text(json.dumps(rec) + "\n", encoding="utf-8")
tsq.unlink(missing_ok=True)
tsr.unlink(missing_ok=True)
print(rec["file"], rec["sha256"][:16], rec["tsa_time"], "verified", rec["verified"])
