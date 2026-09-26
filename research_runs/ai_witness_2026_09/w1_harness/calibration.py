"""Fixed unchanged-test calibration (execution_plan.md Phase 3).

Exactly the sealed schedule's calibration rows: two unchanged-test attempts per variant per
qualified case (at most 16), in the sealed order, using the qualification build artifacts
(hash-checked, no extra build). Records go to ``calibration/`` with their own hash-chained
ledger, separate from measured data. A repaired-variant non-pass blocks that case pending a
documented structural correction or exclusion; it never licenses extra attempts. Nothing is
tuned from these outcomes. A second invocation refuses to run.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .backends import BuildResult, DockerBackend
from .casespec import spec
from .charging import vcpu_h
from .common import W1Error, read_json, sha256_bytes, sha256_json, utc_now, write_json, write_text_lf
from .config import CALIBRATION_DIR, SCHEDULE, WORK_DIR, account
from .ledger import ChainLedger
from .oracles import PASS, classify, make_oracle
from .overlay import unchanged
from .packet import load_packet, originals
from .qualify import image_ids
from .restore import dossier_path

CAL_EVENTS = CALIBRATION_DIR / "events.jsonl"


def _qual_build(case: str, variant: str) -> BuildResult:
    d = read_json(dossier_path(case))
    qb = d["qualification_builds"][-1]
    r = qb["results"][variant]
    root = WORK_DIR / "runs" / "builds" / f"qual-{case}-build{qb['invocation']}" / variant / "out"
    s = spec(case)
    if s.language == "go":
        path = root / "w1.test"
        got = sha256_bytes(path.read_bytes())
    else:
        path = root / "classes"
        got = sha256_json(sorted((p.relative_to(path).as_posix(), sha256_bytes(p.read_bytes())) for p in path.rglob("*.class")))
    if got != r["artifact_sha256"]:
        raise W1Error(f"{case} {variant}: qualification artifact hash changed")
    return BuildResult(f"qual-{case}-build{qb['invocation']}", case, variant, qb["overlay_sha256"], True, got, str(path),
                       "", 0.0, r["started_utc"], 0)


def run(exclusions: dict[str, str] | None = None) -> dict[str, Any]:
    exclusions = exclusions or {}
    led = ChainLedger(CAL_EVENTS)
    if led.verify() > 0:
        raise W1Error("calibration already recorded; the fixed calibration is not repeated")
    sched = read_json(SCHEDULE)
    rows = [r for r in sched["calibration"] if r["case"] not in exclusions]
    if len(rows) > 16:
        raise W1Error("more than 16 calibration attempts scheduled")
    acct = account()
    backend = DockerBackend(image_ids())
    led.append("calibration", "calibration_started", "calibration", {"schedule_sha256": sched["schedule_sha256"],
                                                                      "rows": [r["id"] for r in rows], "exclusions": exclusions})
    results = []
    for row in rows:
        case, variant = row["case"], row["variant"]
        s = spec(case)
        pkt = load_packet(case)
        orig = originals(pkt)
        oracle = make_oracle(s, pkt["files"], orig)
        mat = unchanged(orig, s)
        b = _qual_build(case, variant)
        rid = acct.reserve("calibration", row["id"], {"vcpu_h": vcpu_h(s.outer + s.cleanup)})
        tr = backend.run(s, variant, b, mat.run_selection, row["id"], None)
        acct.settle(rid, {"vcpu_h": vcpu_h(tr.elapsed_s)}, {"exit_code": tr.exit_code, "elapsed_s": round(tr.elapsed_s, 3)})
        cls = classify(oracle, variant, exit_code=tr.exit_code, text=tr.text, outer_timeout=tr.outer_timeout,
                       cleanup_ok=tr.cleanup_ok, harness_error=tr.harness_error, selection=mat.run_selection,
                       final_sources=dict(orig))
        th = write_text_lf(CALIBRATION_DIR / "traces" / f"{row['id']}.log", tr.text)
        payload = {"kind": "attempt", "id": row["id"], "session_id": None, "phase": "calibration", "variant": variant,
                   "patch_sha256": mat.overlay_sha256, "triplet": None, "position": row["position"], "seed": None,
                   "status": cls.status, "elapsed_seconds": round(tr.elapsed_s, 3), "trace_sha256": th,
                   "premise_evidence": cls.premise_evidence, "consequence_evidence": cls.consequence_evidence,
                   "details": {"case": case, "argv": tr.argv, "exit_code": tr.exit_code, "outer_timeout": tr.outer_timeout,
                               "cleanup_ok": tr.cleanup_ok, "artifact_sha256": tr.artifact_sha256, "rule_id": cls.rule_id,
                               "reason": cls.reason, "test_results": cls.test_results,
                               "started_utc": tr.started_utc, "ended_utc": tr.ended_utc}}
        led.append("calibration", "attempt", row["id"], payload)
        results.append(payload)
        if not tr.cleanup_ok or tr.harness_error:
            led.append("calibration", "calibration_stopped", row["id"], {"reason": tr.harness_error or "cleanup failure"})
            break
    per_case: dict[str, Any] = {}
    for r in results:
        c = per_case.setdefault(r["details"]["case"], {"V_bad": [], "V_ok": [], "elapsed_s": []})
        c[r["variant"]].append(r["status"])
        c["elapsed_s"].append(r["elapsed_seconds"])
    for case, c in per_case.items():
        c["repaired_nonpass_blocks_case"] = any(x != PASS for x in c["V_ok"])
    report = {"artifact": "w1_calibration_report_v1", "utc": utc_now(), "attempts": len(results), "per_case": per_case,
              "note": "fixed unchanged-test calibration; separate from measured data; no tuning from these outcomes"}
    write_json(CALIBRATION_DIR / "report.json", report)
    led.append("calibration", "calibration_completed", "calibration", {"attempts": len(results)})
    return report
