"""Independent validation of sealed final candidates (protocol.md "Independent validation").

Every legal, buildable final overlay receives exactly five matched triplets per variant
(15 primitive attempts on V_bad and 15 on V_ok), each attempt a fresh container with the
same overlay, argv, masks, per-triplet seed and resource configuration. Triplet k of V_bad
and of V_ok share a seed; the first variant of each triplet pair follows the scheduled draw;
the three attempts of a triplet are consecutive and ordered. Illegal or unbuildable
overlays are INVALID_CANDIDATE with all 30 slots NOT_RUN (reason recorded). No extension
after a promising result; no efficacy stopping.
"""

from __future__ import annotations

from typing import Any

from .backends import BUILD_CLEANUP_S, SubjectBackend
from .casespec import CaseSpec
from .charging import vcpu_h
from .common import EMPTY_OVERLAY_SHA256
from .oracles import FOCAL, HARNESS_INVALID, NONFOCAL, NOT_RUN, PASS, UNRESOLVED, CaseOracle, classify
from .overlay import materialize
from .session import SEARCH_BUILD_TIMEOUT_S, SessionRecorder

VALIDATION_BUILD_TIMEOUT_S = SEARCH_BUILD_TIMEOUT_S

OUTCOMES = ("UNRESOLVED", "NO_SUBMISSION", "INVALID_CANDIDATE", "COUNTERPART_FAILURE", "VALIDATED_WITNESS",
            "NO_WITNESS_WITHIN_BUDGET")


def not_run_slots(sid: str, triplets: list[dict[str, Any]], reason: str) -> list[dict[str, Any]]:
    out = []
    for t in triplets:
        for variant in ("V_bad", "V_ok"):
            for j in range(1, 4):
                out.append({"id": f"{sid}.val.{variant}.t{t['triplet']}.a{j}", "variant": variant, "triplet": t["triplet"],
                            "position": j, "status": NOT_RUN, "reason": reason, "seed": t["seed"]})
    return out


def validate(sid: str, final: dict[str, Any] | None, spec: CaseSpec, originals: dict[str, str], oracle: CaseOracle,
             backend: SubjectBackend, account: Any, recorder: SessionRecorder, triplets: list[dict[str, Any]],
             stop_check: Any = None) -> dict[str, Any]:
    """Run (or mark NOT_RUN) the fixed validation cells and return the classified outcome record."""
    if final is None:
        slots = not_run_slots(sid, triplets, "no submission")
        return outcome_record(sid, None, slots, "NO_SUBMISSION", ["NO_SUBMISSION"])
    if final.get("malformed") or final.get("files") is None:
        slots = not_run_slots(sid, triplets, "malformed final submission")
        return outcome_record(sid, final.get("overlay_sha256"), slots, "NO_SUBMISSION", ["MALFORMED_FINAL"])
    # Re-materialize from sealed files and verify identity (the final hash was sealed before validation).
    try:
        mat = _materialize_files(final["files"], originals, spec)
    except ValueError as exc:
        slots = not_run_slots(sid, triplets, f"sealed overlay cannot be re-applied: {exc}")
        return outcome_record(sid, final.get("overlay_sha256"), slots, "UNRESOLVED", ["SEAL_REAPPLY_FAILED"])
    if mat.overlay_sha256 != final["overlay_sha256"]:
        slots = not_run_slots(sid, triplets, "sealed overlay hash mismatch")
        return outcome_record(sid, final["overlay_sha256"], slots, "UNRESOLVED", ["SEAL_HASH_MISMATCH"])
    if not mat.legal:
        slots = not_run_slots(sid, triplets, "illegal final overlay: " + "; ".join(mat.violations))
        return outcome_record(sid, mat.overlay_sha256, slots, "INVALID_CANDIDATE", ["ILLEGAL_PATCH"])
    builds = {}
    for variant in ("V_bad", "V_ok"):
        rid = account.reserve("validation", f"{sid}.val.build.{variant}", {"vcpu_h": vcpu_h(VALIDATION_BUILD_TIMEOUT_S + BUILD_CLEANUP_S)})
        b = backend.build(spec, variant, mat, f"{sid}.val")
        account.settle(rid, {"vcpu_h": vcpu_h(b.elapsed_s)}, {"exit_code": b.exit_code})
        recorder.write_blob(f"validation/build.{variant}.log", b.log.encode("utf-8"))
        recorder.event("validation_build", f"{sid}.val.{variant}", {"ok": b.ok, "artifact_sha256": b.artifact_sha256,
                                                                     "overlay_sha256": mat.overlay_sha256})
        builds[variant] = b
    if not all(b.ok for b in builds.values()):
        slots = not_run_slots(sid, triplets, "final overlay does not build on both variants")
        return outcome_record(sid, mat.overlay_sha256, slots, "INVALID_CANDIDATE", ["COMPILE_FAILURE"])
    final_sources = dict(originals)
    final_sources.update(mat.files)
    slots: list[dict[str, Any]] = []
    stopped: str | None = None
    for t in triplets:
        order = [t["first_variant"], "V_ok" if t["first_variant"] == "V_bad" else "V_bad"]
        for variant in order:
            for j in range(1, 4):
                aid = f"{sid}.val.{variant}.t{t['triplet']}.a{j}"
                if stopped is None and stop_check is not None:
                    stopped = stop_check()
                if stopped:
                    slots.append({"id": aid, "variant": variant, "triplet": t["triplet"], "position": j, "status": NOT_RUN,
                                  "reason": stopped, "seed": t["seed"]})
                    continue
                rid = account.reserve("validation", aid, {"vcpu_h": vcpu_h(spec.outer + spec.cleanup)})
                tr = backend.run(spec, variant, builds[variant], mat.run_selection, aid, t["seed"])
                account.settle(rid, {"vcpu_h": vcpu_h(tr.elapsed_s)}, {"exit_code": tr.exit_code})
                cls = classify(oracle, variant, exit_code=tr.exit_code, text=tr.text, outer_timeout=tr.outer_timeout,
                               cleanup_ok=tr.cleanup_ok, harness_error=tr.harness_error, selection=mat.run_selection,
                               final_sources=final_sources)
                th = recorder.write_blob(f"validation/traces/{aid}.log", tr.text.encode("utf-8"))
                payload = {"kind": "attempt", "id": aid, "session_id": sid, "phase": "validation", "variant": variant,
                           "patch_sha256": mat.overlay_sha256, "triplet": t["triplet"], "position": j, "seed": t["seed"],
                           "status": cls.status, "elapsed_seconds": round(tr.elapsed_s, 3), "trace_sha256": th,
                           "premise_evidence": cls.premise_evidence, "consequence_evidence": cls.consequence_evidence,
                           "details": {"argv": tr.argv, "exit_code": tr.exit_code, "outer_timeout": tr.outer_timeout,
                                       "cleanup_ok": tr.cleanup_ok, "artifact_sha256": tr.artifact_sha256,
                                       "rule_id": cls.rule_id, "reason": cls.reason, "test_results": cls.test_results}}
                recorder.event("attempt", aid, payload)
                slots.append({"id": aid, "variant": variant, "triplet": t["triplet"], "position": j, "status": cls.status,
                              "rule_id": cls.rule_id, "seed": t["seed"], "trace_sha256": th})
                if cls.status == HARNESS_INVALID and not tr.cleanup_ok:
                    stopped = "integrity stop: container cleanup failure"
    label, reasons = classify_outcome(slots)
    if stopped:
        reasons.append("STOPPED:" + stopped)
    return outcome_record(sid, mat.overlay_sha256, slots, label, reasons)


def _materialize_files(files: dict[str, str], originals: dict[str, str], spec: CaseSpec):
    """Rebuild a Materialized from sealed full-file contents (edits to supplied files, new files)."""
    from .overlay import materialize as _m
    edits = []
    new_files = []
    for path, content in sorted(files.items()):
        if path in originals:
            edits.append({"path": path, "old": originals[path].replace("\r\n", "\n"), "new": content})
        else:
            new_files.append({"path": path, "content": content})
    return _m({"edits": edits, "new_files": new_files}, originals, spec)


def classify_outcome(slots: list[dict[str, Any]]) -> tuple[str, list[str]]:
    """analysis_plan.md ordered rules (after NO_SUBMISSION / INVALID_CANDIDATE, handled by the caller)."""
    bad = [s for s in slots if s["variant"] == "V_bad"]
    ok = [s for s in slots if s["variant"] == "V_ok"]
    reasons: list[str] = []
    if any(s["status"] == HARNESS_INVALID for s in slots):
        return "UNRESOLVED", ["HARNESS_INVALID_ATTEMPT"]
    if any(s["status"] in (FOCAL, NONFOCAL) for s in ok):
        return "COUNTERPART_FAILURE", ["V_OK_NONPASS"]
    if any(s["status"] in (UNRESOLVED, NOT_RUN) for s in slots) or len(bad) != 15 or len(ok) != 15:
        return "UNRESOLVED", ["INCOMPLETE_OR_UNINTERPRETABLE"]
    focal = [s for s in bad if s["status"] == FOCAL]
    focal_triplets = {s["triplet"] for s in focal}
    others_ok = all(s["status"] in (PASS, FOCAL) for s in bad)
    if all(s["status"] == PASS for s in ok) and len(focal) >= 2 and len(focal_triplets) >= 2 and others_ok:
        return "VALIDATED_WITNESS", []
    if len(focal) < 2:
        reasons.append("FEWER_THAN_TWO_FOCAL")
    elif len(focal_triplets) < 2:
        reasons.append("FOCAL_IN_ONE_TRIPLET")
    if not others_ok:
        reasons.append("NONFOCAL_V_BAD_ATTEMPT")
    return "NO_WITNESS_WITHIN_BUDGET", reasons


def policy_visibility(slots: list[dict[str, Any]]) -> dict[str, Any]:
    """P1 / P3 accept-on-pass / P3-retain per defective triplet, with bounds for incomplete triplets."""
    per = {}
    for s in slots:
        if s["variant"] != "V_bad":
            continue
        per.setdefault(s["triplet"], {})[s["position"]] = s["status"]
    res = {"P1": [0, 0], "P3": [0, 0], "P3_retain": [0, 0], "focal_attempts": [0, 0], "triplets": len(per)}
    for t, pos in per.items():
        seq = [pos.get(j, NOT_RUN) for j in (1, 2, 3)]
        known = [x for x in seq if x != NOT_RUN and x != UNRESOLVED and x != HARNESS_INVALID]
        f = [x == FOCAL for x in seq]
        unk = [x in (NOT_RUN, UNRESOLVED, HARNESS_INVALID) for x in seq]
        lo_p1 = f[0]
        hi_p1 = f[0] or unk[0]
        lo_p3 = all(f)
        hi_p3 = all(a or b for a, b in zip(f, unk))
        lo_r = any(f)
        hi_r = any(a or b for a, b in zip(f, unk))
        for key, lo, hi in (("P1", lo_p1, hi_p1), ("P3", lo_p3, hi_p3), ("P3_retain", lo_r, hi_r)):
            res[key][0] += int(lo)
            res[key][1] += int(hi)
        res["focal_attempts"][0] += sum(f)
        res["focal_attempts"][1] += sum(a or b for a, b in zip(f, unk))
        _ = known
    return res


def outcome_record(sid: str, overlay_sha: str | None, slots: list[dict[str, Any]], label: str, reasons: list[str]) -> dict[str, Any]:
    counts = {}
    for v in ("V_bad", "V_ok"):
        counts[v] = {st: sum(1 for s in slots if s["variant"] == v and s["status"] == st)
                     for st in (PASS, FOCAL, NONFOCAL, UNRESOLVED, HARNESS_INVALID, NOT_RUN)}
    return {"session_id": sid, "overlay_sha256": overlay_sha, "outcome": label, "reason_codes": reasons,
            "counts": counts, "policy": policy_visibility(slots), "slots": slots}
