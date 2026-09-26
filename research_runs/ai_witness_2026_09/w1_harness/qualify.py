"""Structural qualification: unchanged-overlay build per case and environment probes.

A build invocation compiles the unchanged overlay (with harness instrumentation)
for both variants under one declared procedure and counts against the
three-build-per-case cap together with restoration builds. No test runs here.
"""

from __future__ import annotations

from typing import Any

from . import CASES
from .backends import BUILD_CLEANUP_S, BUILD_TIMEOUT_S, DockerBackend
from .casespec import spec
from .charging import vcpu_h
from .common import W1Error, read_json, utc_now, write_json
from .config import account, design_config
from .overlay import unchanged
from .packet import load_packet, originals
from .restore import _load, dossier_path


def image_ids() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for case in CASES:
        d = read_json(dossier_path(case))
        if case == "pool162":
            out[case] = {v: d["images"][v]["image_id"] for v in ("V_bad", "V_ok")}
        else:
            out[case] = {v: d["image_check"]["variants"][v]["image_id"] for v in ("V_bad", "V_ok")}
    return out


def build_unchanged(case: str) -> dict[str, Any]:
    acct = account()
    d = _load(case)
    cap = design_config()["calibration"]["max_build_invocations_per_subject"]
    if d.get("build_invocations", 0) >= cap:
        raise W1Error(f"{case}: build invocation cap {cap} reached")
    d["build_invocations"] = d.get("build_invocations", 0) + 1
    inv = d["build_invocations"]
    s = spec(case)
    pkt = load_packet(case)
    mat = unchanged(originals(pkt), s)
    backend = DockerBackend(image_ids())
    results = {}
    for variant in ("V_bad", "V_ok"):
        rid = acct.reserve("preparation", f"{case}.build{inv}.{variant}", {"vcpu_h": vcpu_h(BUILD_TIMEOUT_S + BUILD_CLEANUP_S)})
        b = backend.build(s, variant, mat, f"qual-{case}-build{inv}")
        acct.settle(rid, {"vcpu_h": vcpu_h(b.elapsed_s)}, {"exit_code": b.exit_code, "elapsed_s": round(b.elapsed_s, 3)})
        results[variant] = {"ok": b.ok, "exit_code": b.exit_code, "timed_out": b.timed_out, "elapsed_s": round(b.elapsed_s, 3),
                            "artifact_sha256": b.artifact_sha256, "log_tail": b.log[-3000:], "started_utc": b.started_utc}
    d.setdefault("qualification_builds", []).append({
        "invocation": inv, "utc": utc_now(), "overlay_sha256": mat.overlay_sha256, "run_selection": mat.run_selection,
        "results": results, "procedure": "DockerBackend.build (unchanged overlay + harness instrumentation), both variants",
    })
    write_json(dossier_path(case), d)
    return results


def probe_environment(case: str) -> dict[str, Any]:
    acct = account()
    s = spec(case)
    backend = DockerBackend(image_ids())
    d = _load(case)
    out = {}
    for variant in ("V_bad", "V_ok"):
        rid = acct.reserve("preparation", f"{case}.envprobe.{variant}", {"vcpu_h": vcpu_h(150)})
        p = backend.probe_environment(s, variant)
        acct.settle(rid, {"vcpu_h": vcpu_h(p["elapsed_s"])}, {"exit_code": p["exit_code"]})
        out[variant] = p
    d["environment_probe"] = out
    write_json(dossier_path(case), d)
    return out


def template_compile_check(case: str) -> dict[str, Any]:
    """One declared build invocation: a composite of all applicable B1 templates, both variants, no test run."""
    from . import templates
    from .overlay import materialize
    acct = account()
    d = _load(case)
    cap = design_config()["calibration"]["max_build_invocations_per_subject"]
    if d.get("build_invocations", 0) >= cap:
        raise W1Error(f"{case}: build invocation cap {cap} reached")
    s = spec(case)
    orig = originals(load_packet(case))
    current = dict(orig)
    new_files: dict[str, str] = {}
    applied = []
    for _ in range(3):  # compose sequentially so Java insertions anchor on the updated file
        for tid, prop, reason in templates.candidates(s, current):
            if prop is None or tid in applied:
                continue
            m = materialize(prop, current, s)
            if not m.legal:
                raise W1Error(f"{case} {tid} illegal: {m.violations}")
            for p, c in m.files.items():
                if p in current:
                    current[p] = c
                else:
                    new_files[p] = c
            applied.append(tid)
            break
    composite = {"edits": [{"path": p, "old": orig[p], "new": current[p]} for p in orig if current[p] != orig[p]],
                 "new_files": [{"path": p, "content": c} for p, c in sorted(new_files.items())]}
    mat = materialize(composite, orig, s)
    d["build_invocations"] = d.get("build_invocations", 0) + 1
    inv = d["build_invocations"]
    backend = DockerBackend(image_ids())
    results = {}
    for variant in ("V_bad", "V_ok"):
        rid = acct.reserve("preparation", f"{case}.build{inv}.{variant}", {"vcpu_h": vcpu_h(BUILD_TIMEOUT_S + BUILD_CLEANUP_S)})
        b = backend.build(s, variant, mat, f"qual-{case}-templates{inv}")
        acct.settle(rid, {"vcpu_h": vcpu_h(b.elapsed_s)}, {"exit_code": b.exit_code, "elapsed_s": round(b.elapsed_s, 3)})
        results[variant] = {"ok": b.ok, "exit_code": b.exit_code, "elapsed_s": round(b.elapsed_s, 3),
                            "artifact_sha256": b.artifact_sha256, "log_tail": b.log[-3000:]}
    d.setdefault("template_compile_checks", []).append({
        "invocation": inv, "utc": utc_now(), "templates": applied, "composite_overlay_sha256": mat.overlay_sha256,
        "legal": mat.legal, "violations": mat.violations, "results": results,
        "note": "compile-only structural check of the frozen B1 bank; no test executed"})
    write_json(dossier_path(case), d)
    return {"templates": applied, "legal": mat.legal, "results": {v: (r["ok"], r["exit_code"]) for v, r in results.items()},
            "log": {v: r["log_tail"][-800:] for v, r in results.items() if not r["ok"]}}
