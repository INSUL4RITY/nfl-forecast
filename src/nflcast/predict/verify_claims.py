"""Independent re-verification of evaluation labels and publication claims (python -m nflcast verify-claims).

Checks, each PASS/FAIL with detail:
  labels:      retrospective weather and untimed historical lines are labelled in reports, exported data and the built site;
               built game pages show no internal codes or player IDs
  evidence:    every recorded GitHub push-run time is re-fetched from the GitHub API and must match; no publication
               evidence may precede the file's generation time
  site labels: every exported "publicly verifiable" label is recomputed from evidence (< kickoff); every version generated
               before but first evidenced after kickoff has a correction
  archive:     every RFC 3161 token re-verifies with openssl; every Internet Archive copy is re-downloaded and matches sha256;
               every release matches its manifest
Writes reports/claims_verification.md. Returns the list of failures.
"""

from __future__ import annotations

import base64
import hashlib
import html
import json
import re
import subprocess
from datetime import datetime

import requests

from nflcast.config import REPORTS_DIR, ROOT, WEB_OUT_DIR, release_paths, utc_now
from nflcast.predict import archive as A
from nflcast.predict import publication as PUB


def _check(results: list, name: str, ok: bool, detail: str = "") -> None:
    results.append({"check": name, "ok": bool(ok), "detail": detail})


RAW_LABEL_RE = re.compile(r"00-00\d{5}|chain_qb|roster:|_stale\b|stale_(provider|retrieval)|report_not_available|designation_pending|"
                          r"NotListed|nflverse_schedules|replacement_chain|no_candidate|depth_chart_|finished prev\b")


def public_raw_labels(out_dir=None) -> dict[str, list[str]]:
    """Internal codes/player IDs in the VISIBLE text of built game pages (the embedded data payload is excluded)."""
    hits = {}
    for p in sorted(((out_dir or WEB_OUT_DIR) / "game").glob("*/index.html")):
        body = p.read_text(encoding="utf-8").split("<body", 1)[-1]
        vis = html.unescape(re.sub(r"<script.*?</script>", "", body, flags=re.S))
        found = sorted({m.group(0) for m in RAW_LABEL_RE.finditer(vis)})
        if found:
            hits[p.parent.name] = found
    return hits


def market_feed_checks() -> list[tuple[str, bool, str]]:
    """The Odds API feed: key never stored/published, no prices kept, no post-kickoff or post-cutoff lines used."""
    import os

    from nflcast.data import odds_api as OA
    out = []
    key = os.environ.get("ODDS_API_KEY", "").strip()
    if key:
        tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split("\n")
        places = [ROOT / p for p in tracked if p] + list((ROOT / "logs").glob("*")) + list(OA.DIR.rglob("*.json"))
        places += [p for p in WEB_OUT_DIR.rglob("*") if p.suffix in (".html", ".json", ".txt", ".js")]
        places += [p for p in (ROOT / "data" / "backup_repo").rglob("*") if p.is_file() and ".git" not in p.parts]
        leaks = [str(p.relative_to(ROOT)) for p in places if p.is_file() and key.encode() in p.read_bytes()]
        out.append(("API key absent from repository, logs, site, snapshots and backup", not leaks, "; ".join(leaks[:5]) or f"{len(places)} files checked"))
    snaps = sorted(OA.DIR.glob("*/odds_*.json"))
    priced = [p.name for p in snaps if re.search(r'"(price|odds)[^"]*"\s*:', p.read_text(encoding="utf-8"))]
    out.append(("The Odds API snapshots contain point values only (no prices)", not priced, "; ".join(priced[:5]) or f"{len(snaps)} snapshots"))
    bad, n = [], 0
    corrected = {c["id"] for c in PUB.load_corrections()}
    for f in release_paths():
        r = json.loads(f.read_text(encoding="utf-8"))
        gen = datetime.fromisoformat(r["generated_at_utc"])
        for g in r["games"]:
            m = g.get("market") or {}
            if m.get("source") != OA.SOURCE:
                continue
            n += 1
            ko = datetime.fromisoformat(g["kickoff_utc"])
            got, upd = datetime.fromisoformat(m["retrieved_at"]), datetime.fromisoformat(m["provider_updated_at"])
            order_ok = upd <= got or f"odds-retrieval-time:{r['run_id']}" in corrected
            if not (upd < ko and got < ko and upd <= gen and got <= gen and order_ok):
                bad.append(f"{f.name}:{g['game_id']}")
    out.append(("The Odds API lines retrieved and provider-updated before kickoff and before the forecast cutoff", not bad,
                "; ".join(bad[:5]) or f"{n} game forecasts"))
    return out


def run(download_web_archive: bool = True) -> list[dict]:
    R: list[dict] = []
    # ---------------- labels
    fg = sorted((REPORTS_DIR / "feature_groups").glob("feature_groups_*.json"))
    if fg:
        res = json.loads(fg[-1].read_text(encoding="utf-8"))["results"]
        wx = [r for r in res if r["group"].startswith("weather")]
        _check(R, "weather evaluation flagged retrospective", bool(wx) and wx[0]["retrospective"] and "RETROSPECTIVE" in wx[0]["inputs"],
               wx[0]["inputs"] if wx else "missing")
        _check(R, "weather not promoted", bool(wx) and wx[0]["decision"].startswith("not promoted"), wx[0]["decision"] if wx else "")
    bt = (REPORTS_DIR / "backtest" / "LATEST.md").read_text(encoding="utf-8")
    _check(R, "backtest report states untimed historical lines", "timing unknown" in bt and "approximately closing" in bt)
    perf_html = (WEB_OUT_DIR / "performance" / "index.html").read_text(encoding="utf-8") if (WEB_OUT_DIR / "performance" / "index.html").exists() else ""
    _check(R, "site performance page labels retrospective benchmark + untimed lines + actual-starter proxy",
           all(s in perf_html for s in ("Retrospective benchmark, not live results", "untimed", "actual")))
    _check(R, "site performance page shows weather inputs as RETROSPECTIVE", "RETROSPECTIVE" in perf_html)
    meth_html = (WEB_OUT_DIR / "methodology" / "index.html").read_text(encoding="utf-8") if (WEB_OUT_DIR / "methodology" / "index.html").exists() else ""
    _check(R, "methodology page documents approximations", all(s in meth_html for s in ("Actual-starter proxy", "Untimed closing lines")))
    for name, ok, detail in market_feed_checks():
        _check(R, name, ok, detail)
    raw = public_raw_labels()
    _check(R, "game pages show no internal codes or player IDs", not raw,
           "; ".join(f"{k}: {v}" for k, v in list(raw.items())[:5]) if raw else f"{len(list((WEB_OUT_DIR / 'game').glob('*/index.html')))} pages clean")

    # ---------------- GitHub evidence re-fetched
    ev = PUB.load_evidence()
    slug = PUB.repo_slug()
    for path, e in sorted(ev["files"].items()):
        r = subprocess.run(["gh", "api", f"repos/{slug}/actions/runs/{e['run_id']}", "--jq", "{created_at, head_sha}"],
                           capture_output=True, text=True, cwd=ROOT)
        if r.returncode != 0:
            _check(R, f"GitHub run still retrievable: {path}", False, r.stderr.strip()[:200] + " (archived copy retained in evidence log)")
            continue
        api = json.loads(r.stdout)
        same = api["created_at"].replace("Z", "+00:00") == e["first_public_evidence_utc"] and api["head_sha"] == e["pushed_commit"]
        _check(R, f"GitHub push time matches API: {path.split('/')[-1]}", same, f"{api['created_at']} {api['head_sha'][:10]}")
        rel = json.loads((ROOT / path).read_text(encoding="utf-8"))
        _check(R, f"publication not before generation: {path.split('/')[-1]}",
               datetime.fromisoformat(e["first_public_evidence_utc"]) >= datetime.fromisoformat(rel["generated_at_utc"]))

    # ---------------- site labels recomputed from evidence; corrections complete
    corrections = {c["id"] for c in PUB.load_corrections()}
    bad_labels, missing_corr, n = [], [], 0
    for wk in sorted((ROOT / "web" / "public" / "data" / "weeks").glob("*.json")):
        for g in json.loads(wk.read_text(encoding="utf-8"))["games"]:
            ko = datetime.fromisoformat(g["kickoff_utc"])
            for h in g["history"]:
                n += 1
                pub = PUB.public_time(h["run_id"], ev)
                expect = PUB.verification_label(datetime.fromisoformat(h["generated_at"]), ko, pub)
                if h["verification"] != expect or (h["public_evidence_at"] or None) != (pub.isoformat() if pub else None):
                    bad_labels.append(f"{g['game_id']}/{h['run_id']}")
                if expect == "generated_pregame_published_after_kickoff" and f"late-publication:{h['run_id']}:{g['game_id']}" not in corrections:
                    missing_corr.append(f"{g['game_id']}/{h['run_id']}")
    _check(R, f"exported verification labels match evidence ({n} versions)", not bad_labels, ", ".join(bad_labels[:5]))
    _check(R, "every late publication has a correction", not missing_corr, ", ".join(missing_corr[:5]))

    # ---------------- archive
    probs = A.verify()
    _check(R, "every release matches its write-once manifest", not probs, "; ".join(probs))
    certs = A._tsa_certs()
    work = A.ARCHIVE_DIR / ".tmp"
    work.mkdir(exist_ok=True)
    for p in release_paths():
        _, evp = A._paths(p)
        recs = A._evidence(evp)
        tok = [x for x in recs if x["type"] == "rfc3161_timestamp" and x.get("token_base64")]
        if tok:
            (work / "v.tsr").write_bytes(base64.b64decode(tok[0]["token_base64"]))
            (work / "v.tsq").write_bytes(base64.b64decode(tok[0]["query_base64"]))
            # verify the signed token directly against THIS file's bytes (openssl recomputes the sha256 imprint)
            v = A._ossl("ts", "-verify", "-data", A._rel(p), "-in", A._rel(work / "v.tsr"),
                        "-CAfile", A._rel(certs / "cacert.pem"), "-untrusted", A._rel(certs / "tsa.crt"))
            ok = "Verification: OK" in (v.stdout + v.stderr)
            _check(R, f"RFC 3161 token verifies against {p.name}", ok, tok[0].get("tsa_time", "") if ok else (v.stdout + v.stderr)[-200:])
        else:
            _check(R, f"RFC 3161 token present for {p.name}", False, "no token yet")
        wa = [x for x in recs if x["type"] == "web_archive" and x.get("sha256_matches")]
        if wa and download_web_archive:
            got = requests.get(wa[0]["archived_copy"], timeout=120, headers=A.UA).content
            _check(R, f"Web Archive copy matches {p.name}", hashlib.sha256(got).hexdigest() == hashlib.sha256(p.read_bytes()).hexdigest(),
                   wa[0]["capture_time_utc"])
        elif not wa:
            _check(R, f"Web Archive copy present for {p.name}", False, "not captured yet (retried each cycle)")
    for f in ("v.tsr", "v.tsq"):
        (work / f).unlink(missing_ok=True)

    fails = [r for r in R if not r["ok"]]
    L = ["# Claims verification", "", f"Run {utc_now().isoformat()}: {len(R) - len(fails)} passed, {len(fails)} failed.", "",
         "| check | result | detail |", "|---|---|---|"]
    L += [f"| {r['check']} | {'PASS' if r['ok'] else 'FAIL'} | {r['detail']} |" for r in R]
    (REPORTS_DIR / "claims_verification.md").write_text("\n".join(L), encoding="utf-8")
    return R
