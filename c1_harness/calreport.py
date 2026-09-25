"""Summarize the fixed calibration stages from their ledgers, annotations and events.

Reports what each stage was for (execution/capture, identity, structure,
isolation/timeout) and the integrity facts behind it. It deliberately reports
single-attempt outcomes as counts only: calibration never estimates an effect,
and nothing here feeds a design parameter.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from ledger import read_records, verify_chain

from c1_harness.budget import ResourceLedger
from c1_harness.driver import EventLog


def stage_summary(stage_dir: Path) -> dict[str, Any]:
    records = []
    for p in sorted(stage_dir.glob("*__*.jsonl")):
        verify_chain(p)
        records += read_records(p)
    ann_path = stage_dir / "annotations.jsonl"
    ann = {a["record_sha256"]: a for a in read_records(ann_path)} if ann_path.exists() else {}
    cats = Counter()
    for r in records:
        a = ann.get(r["sha256"])
        cats[(r["episode"], r["condition"], r["version"], "+".join(a["categories"]) if a else "UNANNOTATED")] += 1
    x = [r.get("extra") or {} for r in records]
    return {
        "records": len(records),
        "unique_attempt_ids": len({e.get("attempt_id") for e in x}),
        "profile_verified": sum(bool(e.get("profile_verified")) for e in x),
        "quota_matches_profile": sum(
            (e.get("inspect") or {}).get("cpu_quota") == (200000 if r["condition"] == "L" else 0) for r, e in zip(records, x)
        ),
        "gomaxprocs_env_ok": sum((e.get("inspect") or {}).get("gomaxprocs_env") == ["GOMAXPROCS=16"] for e in x),
        "cleanup_verified": sum(bool((e.get("cleanup") or {}).get("verified_absent")) for e in x),
        "outer_timeouts": sum(bool(r["timed_out"]) for r in records),
        "harness_invalid": sum(1 for r in records if "HARNESS_INVALID" in (ann.get(r["sha256"]) or {}).get("categories", [])),
        "acceptable_variant_focal": [
            e.get("attempt_id") for r, e in zip(records, x)
            if r["version"] == "V_ok" and "FOCAL_DEFECT_WITNESS" in (ann.get(r["sha256"]) or {}).get("categories", [])
            and not e.get("identity_control")
        ],
        "identity_slot_focal": [
            e.get("attempt_id") for r, e in zip(records, x)
            if e.get("identity_control") and "FOCAL_DEFECT_WITNESS" in (ann.get(r["sha256"]) or {}).get("categories", [])
        ],
        "category_counts": [
            {"subject": s, "profile": p, "version": v, "categories": c, "n": n} for (s, p, v, c), n in sorted(cats.items())
        ],
        "attempt_elapsed_s": {"min": min((r["elapsed_s"] for r in records), default=None),
                              "max": max((r["elapsed_s"] for r in records), default=None)},
    }


def build(study_dir: Path) -> dict[str, Any]:
    events = EventLog(study_dir / "events.jsonl")
    events.verify()
    budget = ResourceLedger(study_dir / "resources" / "resource_ledger.jsonl")
    budget.verify()
    rows = events.rows()
    out: dict[str, Any] = {
        "stages": {s: stage_summary(study_dir / "calibration" / s) for s in ("smoke", "identity", "direct")
                   if (study_dir / "calibration" / s).exists()},
        "direct_traces": [{k: e[k] for k in ("trace_id", "policy", "profile", "variant", "executed", "ledger_prefix",
                                            "direct_decision", "replayed_decision", "decision_match",
                                            "stopping_rule_respected", "attempt_ids") if k in e}
                          for e in rows if e["kind"] == "direct_trace"],
        "helpers": [{k: e[k] for k in ("job", "profile", "step", "exit", "timed_out", "elapsed_s", "stdout", "cleanup_ok",
                                       "profile_verified", "passed") if k in e}
                    for e in rows if e["kind"] == "helper_check"],
        "session_probes": [{k: e[k] for k in ("tag", "stage", "passed", "summary")} for e in rows if e["kind"] == "session_probe"],
        "stops": [e for e in rows if e["kind"] == "stop_all"
                  or (e["kind"] == "calibration_end" and e.get("outcome") == "stopped")],
        "budget": budget.summary(),
    }
    clock = study_dir / "calibration" / "clock_probe.json"
    if clock.exists():
        out["clock_probe"] = json.loads(clock.read_text(encoding="utf-8"))
    return out
