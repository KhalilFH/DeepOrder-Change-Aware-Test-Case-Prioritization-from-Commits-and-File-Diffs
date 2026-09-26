"""Frozen W2A feasibility analysis (ANALYSIS_PLAN.md). Descriptive only: no tests, no intervals.

Reads the event ledger (session and validation records) and writes ``results.json`` and
``report.md`` to a separate output directory. Every scheduled session stays in the denominator.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import ARMS, CASES, NONCONTROL_CASES
from .common import write_json
from .config import design_config
from .ledger import ChainLedger

STEPS = ("plan_accepted", "judgments_accepted", "legal_modified_proposed", "modified_built_both", "modified_paired_run",
         "final_sealed", "final_modified", "modified_workflow_complete", "validated_witness")


def session_row(rec: dict[str, Any], outcome: dict[str, Any] | None) -> dict[str, Any]:
    d = rec.get("details") or {}
    props = d.get("proposals") or {}
    modified = {k: v for k, v in props.items() if k != "unchanged" and v.get("legal") and not v.get("unchanged")}
    final = d.get("final") or {}
    sealed = rec.get("status") == "SEALED"
    final_modified = sealed and not final.get("unchanged", True)
    stages = d.get("stage_records") or {}
    row = {
        "session_id": rec["id"], "case": rec.get("case"), "arm": rec.get("arm"), "status": rec.get("status"),
        "terminal": rec.get("terminal"),
        "plan_accepted": (stages.get("planner") or {}).get("accepted") if rec.get("arm") == "F3" else None,
        "judgments_accepted": (stages.get("judge") or {}).get("accepted") if rec.get("arm") == "F3" else None,
        "legal_modified_proposed": bool(modified),
        "modified_built_both": any(v.get("built_ok") for v in modified.values()),
        "modified_paired_run": any(v.get("paired_runs", 0) > 0 for v in modified.values()),
        "final_sealed": sealed, "final_modified": final_modified,
        "modified_workflow_complete": bool(final_modified and final.get("built_in_search") and final.get("paired_runs_in_search", 0) >= 1),
        "sealed_via": final.get("sealed_via"),
        "validation_outcome": (outcome or {}).get("outcome"),
        "validated_witness": (outcome or {}).get("outcome") == "VALIDATED_WITNESS",
        "calls": d.get("generator_calls"), "calls_by_stage": d.get("calls_by_stage"),
        "input_tokens": d.get("input_tokens"), "output_tokens": d.get("output_tokens"), "usd": d.get("usd"),
        "seconds": rec.get("elapsed_search_seconds"), "patch_proposals": d.get("patch_proposals"),
        "paired_runs": d.get("paired_runs"), "counters": d.get("counters"),
        "admission_denials": [x.get("reason") for x in d.get("admission_denials") or []],
        "final_call_used": d.get("final_call_used"),
        "carried_evidence_lines": {k: (v.get("carried_evidence") or {}).get("lines") for k, v in stages.items() if v.get("carried_evidence")},
    }
    return row


def analyze(schedule: dict[str, Any], events_path: Path, out_dir: Path) -> dict[str, Any]:
    led = ChainLedger(events_path)
    n_events = led.verify()
    sessions: dict[str, Any] = {}
    outcomes: dict[str, Any] = {}
    for r in led.iter_rows():
        if r["event_type"] == "session_ended":
            sessions[r["entity_id"]] = r["payload"]
        elif r["event_type"] == "validation_outcome":
            outcomes[r["payload"]["session_id"]] = r["payload"]
    rows = []
    for s in schedule["sessions"]:
        sid = s["session_id"]
        rec = sessions.get(sid) or {"id": sid, "case": s["case"], "arm": s["arm"], "status": "NOT_RUN", "terminal": "NOT_RUN"}
        rows.append(session_row(rec, outcomes.get(sid)))
    gcfg = design_config()["gates"]["live_feasibility"]
    gate: dict[str, Any] = {}
    for arm in ARMS:
        ar = [r for r in rows if r["arm"] == arm]
        sealed = sum(r["final_sealed"] for r in ar)
        mw = sorted(r["case"] for r in ar if r["case"] in NONCONTROL_CASES and r["modified_workflow_complete"])
        accounted = all(r["terminal"] not in (None, "NOT_RUN", "INTERRUPTED_INDETERMINATE") for r in ar)
        gate[arm] = {"sealed_cases": sealed, "modified_workflow_noncontrol_cases": mw, "terminal_accounting_complete": accounted,
                     "meets": sealed >= gcfg["sealed_cases_per_arm_min"] and len(mw) >= gcfg["modified_workflow_noncontrol_cases_per_arm_min"] and accounted}
    complete = all(r["status"] != "NOT_RUN" for r in rows) and all(r["session_id"] in outcomes for r in rows)
    attrition = {arm: {step: sum(1 for r in rows if r["arm"] == arm and r.get(step)) for step in STEPS} for arm in ARMS}
    totals = {arm: {k: round(sum((r.get(k) or 0) for r in rows if r["arm"] == arm), 6)
                    for k in ("calls", "input_tokens", "output_tokens", "usd", "seconds")} for arm in ARMS}
    result = {"artifact": "w2a_analysis_v1", "events_verified": n_events, "complete": complete, "rows": rows,
              "attrition": attrition, "totals": totals, "gate_live_feasibility": gate,
              "gate_met_both_arms": complete and all(g["meets"] for g in gate.values()),
              "note": "descriptive feasibility pilot on four exposed development cases; one session per case and arm; no inference"}
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "results.json", result)
    (out_dir / "report.md").write_text(render(result), encoding="utf-8", newline="\n")
    return result


def _yn(v: Any) -> str:
    return "—" if v is None else ("yes" if v else "no")


def render(res: dict[str, Any]) -> str:
    out = ["# W2A feasibility analysis (frozen script output)", "",
           f"Events verified: {res['events_verified']}. Complete: {res['complete']}. Descriptive only; development cases.", "",
           "| Session | Terminal | Plan | Judg. | Legal mod. | Built | Paired | Sealed | Modified final | Workflow complete | Validation | Calls | In tok | Out tok | USD | s |",
           "|---|---|---|---|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|"]
    for r in res["rows"]:
        out.append(f"| {r['session_id']} | {r['terminal']} | {_yn(r['plan_accepted'])} | {_yn(r['judgments_accepted'])} | "
                   f"{_yn(r['legal_modified_proposed'])} | {_yn(r['modified_built_both'])} | {_yn(r['modified_paired_run'])} | "
                   f"{_yn(r['final_sealed'])} | {_yn(r['final_modified'])} | {_yn(r['modified_workflow_complete'])} | "
                   f"{r['validation_outcome']} | {r['calls']} | {r['input_tokens']} | {r['output_tokens']} | {r['usd']} | {r['seconds']} |")
    out += ["", "## Stage attrition (sessions reaching each step, out of 4 per arm)", "",
            "| Step | " + " | ".join(ARMS) + " |", "|---|" + "---:|" * len(ARMS)]
    for step in STEPS:
        out.append(f"| {step} | " + " | ".join(str(res["attrition"][a][step]) for a in ARMS) + " |")
    out += ["", "## Live feasibility gate (ANALYSIS_PLAN.md)", ""]
    for arm, g in res["gate_live_feasibility"].items():
        out.append(f"- {arm}: sealed {g['sealed_cases']}/4; modified workflow on noncontrol cases {g['modified_workflow_noncontrol_cases']}; "
                   f"terminal accounting complete {g['terminal_accounting_complete']}; meets {g['meets']}")
    out.append(f"- Both arms meet the gate: {res['gate_met_both_arms']}")
    out += ["", "## Totals by arm", "", "| Arm | Calls | Input tokens | Output tokens | USD | Search seconds |", "|---|---:|---:|---:|---:|---:|"]
    for arm, t in res["totals"].items():
        out.append(f"| {arm} | {t['calls']} | {t['input_tokens']} | {t['output_tokens']} | {t['usd']} | {t['seconds']} |")
    out += ["", res["note"], ""]
    return "\n".join(out)
