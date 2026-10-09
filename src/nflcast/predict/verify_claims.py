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


def _redownload(url: str, local: bytes, get=requests.get) -> tuple[bool | None, str]:
    """Re-download an Internet Archive copy: (matches, "") when a copy came back, (None, reason) when archive.org did not
    serve one (refused, rate-limited, error status). An error page is "could not check", never a content mismatch."""
    try:
        r = get(url, timeout=120, headers=A.UA)
    except requests.RequestException as e:
        return None, type(e).__name__
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}"
    return hashlib.sha256(r.content).hexdigest() == hashlib.sha256(local).hexdigest(), ""


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


def picks_checks() -> list[tuple[str, bool, str]]:
    """Picks and weekly results, recomputed from the release files and the publication evidence (never from the exported
    labels): stored labels match the rule; the projected winner (`pick`) is the final-pregame version's labels; the
    model pick (`locked_pick`) is the version chosen by the rule in force for the game ("original-pick" from
    picks.RULE_START: earliest valid pregame version with a line; "final-pregame" before), with that version's labels,
    line and publication label; versions without stored labels are re-derived and flagged retrospective; every grade is
    recomputed from the release labels; each week's results table equals the summary recomputed from its games."""
    from nflcast.predict import picks as PK
    from nflcast.predict.export_web import stats_only_for
    from nflcast.predict.validation import entry_is_valid
    evidence = PUB.load_evidence()
    rel_by_run, by_game = {}, {}
    for f in release_paths():
        r = json.loads(f.read_text(encoding="utf-8"))
        rel_by_run[r["run_id"]] = r
        for g in r.get("games", []):
            by_game.setdefault(g["game_id"], []).append((datetime.fromisoformat(r["generated_at_utc"]), r["run_id"], g))
    stored_bad, n_stored = [], 0
    for r in rel_by_run.values():
        for g in r.get("games", []):
            if g.get("picks"):
                n_stored += 1
                again = PK.derive(g.get("forecast"), g.get("market"), g["home_team"], g["away_team"])
                if {k: g["picks"][k] for k in again} != again:
                    stored_bad.append(f"{r['run_id']}:{g['game_id']}")

    def release_pick(entry: dict, home: str, away: str) -> dict:
        """Labels as published in the release, or derived now by the same rule when that release stored none."""
        return entry["picks"] if entry.get("picks") else PK.derive(entry.get("forecast"), entry.get("market"), home, away)

    def matches(exported: dict | None, rp: dict) -> bool:
        return exported is not None and {k: exported.get(k) for k in rp} == rp

    bad, lock_bad, label_bad, retro_bad, count_bad, n, n_lock = [], [], [], [], [], 0, 0
    for wf in sorted((ROOT / "web" / "public" / "data" / "weeks").glob("*.json")):
        doc = json.loads(wf.read_text(encoding="utf-8"))
        for it in doc["games"]:
            gid, H, A = it["game_id"], it["home"], it["away"]
            ko = datetime.fromisoformat(it["kickoff_utc"])
            pre = sorted((c for c in by_game.get(gid, []) if c[0] < ko and entry_is_valid(c[2])), key=lambda c: (c[0], c[1]))
            final = pre[-1] if pre else None
            fp = lp_rel = None
            if (final[1] if final else None) != it.get("forecast_run_id"):
                bad.append(gid)
            if final:
                fp = release_pick(final[2], H, A)
                if not matches(it.get("pick"), fp) or it["pick"]["retrospectively_derived"] != (not final[2].get("picks")):
                    bad.append(gid)
                if it.get("forecast_verification") != PUB.verification_label(final[0], ko, PUB.public_time(final[1], evidence)):
                    label_bad.append(gid)
            rule = "original-pick" if ko >= PK.RULE_START else "final-pregame"
            lock = (next((c for c in pre if (c[2].get("market") or {}).get("home_spread") is not None), None)
                    if rule == "original-pick" else final)
            lp = it.get("locked_pick")
            if lock is None:
                if lp is not None:
                    lock_bad.append(gid)
            else:
                n_lock += 1
                t, run, entry = lock
                lp_rel = release_pick(entry, H, A)
                if (lp is None or lp["run_id"] != run or datetime.fromisoformat(lp["generated_at"]) != t
                        or lp.get("rule") != rule or not matches(lp, lp_rel)
                        or lp.get("stats_only") != stats_only_for(entry)):
                    lock_bad.append(gid)
                else:
                    if lp.get("verification") != PUB.verification_label(t, ko, PUB.public_time(run, evidence)):
                        label_bad.append(gid)
                    if lp["retrospectively_derived"] != (not entry.get("picks")):
                        retro_bad.append(gid)
            if it.get("result_grade"):
                n += 1
                h, a = it["score"]["home"], it["score"]["away"]
                want = PK.grade(fp, h, a, H, A) if fp else None
                if want is not None:
                    want["lean"] = PK.grade(lp_rel, h, a, H, A)["lean"] if lp_rel else "no_line"
                if it["forecast_state"] != "scored" or want != it["result_grade"]:
                    bad.append(gid)
                if it.get("stats_only_grade") != PK.grade_stats_only(lp, h, a):
                    bad.append(gid)
        res = doc.get("results")
        again = PK.weekly_summary(doc["games"]) if any(it.get("pick") for it in doc["games"]) else None
        if again != res:
            count_bad.append(wf.name)
        elif res and any(sum(g["winner"].values()) != g["graded"] or sum(g["lean"].values()) != g["pick_graded"]
                         for g in res["groups"].values()):
            count_bad.append(wf.name)
    return [("stored pick labels match the published rule", not stored_bad, "; ".join(stored_bad[:5]) or f"{n_stored} stored picks"),
            ("model pick = version chosen by the rule in force (original-pick from 1 Oct 2026, final-pregame before), "
             "with that version's own labels, line and stats-only numbers", not lock_bad, "; ".join(lock_bad[:5]) or f"{n_lock} locked picks"),
            ("publication labels of the projected-winner and model-pick versions match the evidence", not label_bad,
             "; ".join(label_bad[:5])),
            ("graded: winner and margin error from the final pregame version, model pick from the locked version (both "
             "recomputed from the release files)", not bad, "; ".join(bad[:5]) or f"{n} graded"),
            ("picks without a stored label are flagged retrospectively derived", not retro_bad, "; ".join(retro_bad[:5])),
            ("weekly results tables equal the summary recomputed from their games, and records add up", not count_bad,
             "; ".join(count_bad))]


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
    for name, ok, detail in picks_checks():
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
    blocked = ""   # once archive.org stops serving, stop asking (repeated requests prolong its rate-limit block)
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
        if wa and download_web_archive:   # a copy that could not be checked is recorded as a failure, never skipped silently
            name = f"Web Archive copy matches {p.name}"
            if blocked:
                _check(R, name, False, f"not re-downloaded: archive.org stopped serving earlier in this run ({blocked}); retry later")
            else:
                ok, why = _redownload(wa[0]["archived_copy"], p.read_bytes())
                if ok is None:
                    if why == "HTTP 404":   # about this one capture, not a sign that archive.org stopped serving
                        _check(R, name, False, "archive.org returned no copy at the recorded address (HTTP 404); retry later")
                        continue
                    blocked = why
                    _check(R, name, False, f"could not re-download now ({why}); retry later")
                else:
                    _check(R, name, ok, wa[0]["capture_time_utc"])
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
