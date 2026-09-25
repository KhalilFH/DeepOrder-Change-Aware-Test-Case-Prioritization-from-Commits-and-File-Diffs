"""EXPLORATORY / POST HOC signal audit s06: input/output hash manifest and
cost total. Raw SHA-256 of bytes as they exist on disk (no normalization),
plus the LF-normalized digest for text files.
Outputs: out/MANIFEST.json
"""
from __future__ import annotations

import hashlib
import json

from audit_common import STUDY, write_json

REPO = STUDY.parents[1]
HERE = STUDY / "signal_audit"


def digests(p):
    b = p.read_bytes()
    return {"sha256_raw": hashlib.sha256(b).hexdigest(), "sha256_lf": hashlib.sha256(b.replace(b"\r\n", b"\n")).hexdigest(), "bytes": len(b)}


def main():
    inputs = [
        *sorted((STUDY / "measured").glob("*.jsonl")),
        STUDY / "schedule.csv", STUDY / "events.jsonl", STUDY / "resources" / "resource_ledger.jsonl",
        STUDY / "DESIGN_FREEZE.sha256", STUDY / "FREEZE.sha256",
        STUDY / "analysis_audit" / "pre_analysis_seal.json", STUDY / "analysis" / "summary.json",
        STUDY / "analysis" / "report.md", STUDY / "analysis_audit" / "independent_verification.json",
        REPO / "e1_harness" / "oracle.py",
        STUDY.parent / "ci_sensitivity_2026_09" / "e1" / "etcd5509" / "attempts.jsonl",
        STUDY.parent / "ci_sensitivity_2026_09" / "e1" / "etcd5509" / "annotations.jsonl",
        STUDY.parent / "ci_sensitivity_2026_09" / "task5_artifacts" / "etcd5509" / "attempts" / "results.csv",
        STUDY.parent / "ci_sensitivity_2026_09" / "task5_artifacts" / "etcd5509" / "recipe" / "as_built" / "bug_patch.diff",
        *sorted((STUDY.parent / "ci_sensitivity_2026_09" / "task5_artifacts" / "etcd5509" / "attempts").glob("vbad_attempt_*.log")),
    ]
    scripts = sorted(HERE.glob("*.py"))
    outputs = sorted(p for p in (HERE / "out").glob("*") if p.name != "MANIFEST.json")
    report = HERE / "SIGNAL_VALIDITY_AUDIT.md"
    rel = lambda p: p.relative_to(REPO).as_posix()
    costs = [json.loads(l) for l in (HERE / "cost_log.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    res = {
        "label": "EXPLORATORY/POST-HOC s06 manifest",
        "inputs": {rel(p): digests(p) for p in inputs},
        "scripts": {rel(p): digests(p) for p in scripts},
        "outputs": {rel(p): digests(p) for p in outputs},
        "report": {rel(report): digests(report)} if report.exists() else {},
        "cost_log_rows_before_this_run": len(costs),
        "cost_total_vcpu_h_before_this_run": sum(c["charged_vcpu_h"] for c in costs),
        "cost_elapsed_s_before_this_run": sum(c["elapsed_s"] for c in costs),
    }
    write_json("MANIFEST.json", res)
    print(json.dumps({k: v for k, v in res.items() if k not in ("inputs",)}, indent=1))
    print("inputs:", len(res["inputs"]))


if __name__ == "__main__":
    main()
