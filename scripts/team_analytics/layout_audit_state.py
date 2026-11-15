"""Is a browser layout audit needed for this build? Lets the unattended status refresh skip it when nothing that shapes the
page has changed since the last audited build.

The page's layout comes from template.html and build_html.py; the public copy adds publish_public.py; the audit itself is
scripts/layout_audit.js. Their SHA-256 hashes are stored in layout_audit_state.json after an audit passes. A later run whose
files hash the same does not need a new browser audit (data-only refreshes); any change means it does.

    python scripts/team_analytics/layout_audit_state.py check        # prints AUDIT NEEDED or AUDIT NOT NEEDED; exit code 3 or 0
    python scripts/team_analytics/layout_audit_state.py record --where local --note "build abc1234"
    python scripts/team_analytics/layout_audit_state.py record --where live --note "public page 3758b68"
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATE = HERE / "layout_audit_state.json"
INPUTS = {"template.html": HERE / "template.html", "build_html.py": HERE / "build_html.py",
          "publish_public.py": HERE / "publish_public.py", "layout_audit.js": ROOT / "scripts" / "layout_audit.js"}


def fingerprint(paths: dict | None = None) -> dict:
    """SHA-256 of each input, with line endings normalised so a checkout's CRLF/LF setting does not force an audit."""
    return {k: hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest() for k, p in (paths or INPUTS).items()}


def load(state: Path = STATE) -> dict:
    return json.loads(state.read_text(encoding="utf-8")) if state.exists() else {}


def needed(state: dict, now: dict) -> tuple[bool, str]:
    """(audit needed?, reason). Needed unless both the local and the live audit passed with these exact inputs."""
    if not state:
        return True, "no audited build on record"
    changed = [k for k in now if state.get("inputs", {}).get(k) != now[k]]
    if changed:
        return True, "changed since the last audited build: " + ", ".join(changed)
    missing = [w for w in ("local", "live") if not state.get("passed", {}).get(w)]
    if missing:
        return True, "the last audit with these files did not pass for: " + ", ".join(missing)
    p = state["passed"]
    return False, (f"template.html, build_html.py, publish_public.py and layout_audit.js are unchanged since the audited build "
                   f"(local {p['local']['at']}, {p['local'].get('note', '')}; live {p['live']['at']}, {p['live'].get('note', '')})")


def record(where: str, note: str, state_path: Path = STATE, now: dict | None = None, at: str | None = None) -> dict:
    """Store a passing audit. Recording with different inputs from the stored ones starts a fresh record."""
    now = now or fingerprint()
    st = load(state_path)
    if st.get("inputs") != now:
        st = {"inputs": now, "passed": {}}
    st.setdefault("passed", {})[where] = {"at": at or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "note": note}
    state_path.write_text(json.dumps(st, indent=1) + "\n", encoding="utf-8")
    return st


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    r = sub.add_parser("record")
    r.add_argument("--where", choices=["local", "live"], required=True)
    r.add_argument("--note", default="")
    r.add_argument("--at", help="when the audit passed, if not now (e.g. '2026-11-13 12:30 UTC')")
    a = ap.parse_args()
    if a.cmd == "check":
        need, why = needed(load(), fingerprint())
        print(("AUDIT NEEDED: " if need else "AUDIT NOT NEEDED: ") + why)
        sys.exit(3 if need else 0)
    record(a.where, a.note, at=a.at)
    print(f"recorded a passing {a.where} audit")


if __name__ == "__main__":
    main()
