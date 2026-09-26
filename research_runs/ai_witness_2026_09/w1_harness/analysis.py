"""Frozen descriptive analysis (analysis_plan.md). Reads sealed event records; writes a separate directory.

Primary endpoint: VALIDATED_WITNESS count out of the 3 scheduled replicates per enrolled
case x arm, with the missingness bound [s/3, (s + unresolved)/3] (identification bound,
not a confidence interval). Excluded cases are shown as EXCLUDED, never as zero.
Contrasts: B1..B4 minus B0, B3 minus B2 (structure), B4 minus B3 (Jev), per case.
Retry-policy visibility (P1 / P3 / P3-retain), capped time to validated submission,
and costs are reported separately; nothing is pooled across attempts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import ARMS, CASES, CONTROL_CASES
from .common import write_json, write_text_lf
from .ledger import ChainLedger

CAP_SECONDS = 600.0


def collect(events_path: Path) -> dict[str, Any]:
    led = ChainLedger(events_path)
    led.verify()
    sessions: dict[str, dict[str, Any]] = {}
    outcomes: dict[str, dict[str, Any]] = {}
    requests: list[dict[str, Any]] = []
    for row in led.iter_rows():
        et, p = row["event_type"], row["payload"]
        if et == "session_ended":
            sessions[p["id"]] = p
        elif et == "validation_outcome":
            outcomes[p["session_id"]] = p
        elif et == "request_completed":
            requests.append(p)
    return {"sessions": sessions, "outcomes": outcomes, "requests": requests}


def analyze(schedule: dict[str, Any], events_path: Path, out_dir: Path) -> dict[str, Any]:
    data = collect(events_path)
    excluded = schedule.get("exclusions") or {}
    table: dict[str, dict[str, Any]] = {}
    for case in CASES:
        table[case] = {}
        for arm in ARMS:
            rows = [s for s in schedule["sessions"] if s["case"] == case and s["arm"] == arm]
            if case in excluded:
                table[case][arm] = {"status": "EXCLUDED", "reason": excluded[case]}
                continue
            labels = []
            capped = []
            policy = []
            for r in rows:
                o = data["outcomes"].get(r["session_id"])
                sess = data["sessions"].get(r["session_id"])
                label = o["outcome"] if o else ("NOT_RUN" if not sess else "UNRESOLVED")
                labels.append(label)
                if label == "VALIDATED_WITNESS" and sess and sess["details"].get("final"):
                    capped.append(min(CAP_SECONDS, float(sess["details"]["final"].get("elapsed_seconds", CAP_SECONDS))))
                else:
                    capped.append(CAP_SECONDS)
                if o and o.get("policy"):
                    policy.append(o["policy"])
            succ = labels.count("VALIDATED_WITNESS")
            unres = sum(1 for l in labels if l in ("UNRESOLVED", "NOT_RUN"))
            table[case][arm] = {
                "validated": succ, "scheduled": len(rows), "labels": labels,
                "missingness_bound": [succ / len(rows), (succ + unres) / len(rows)] if rows else None,
                "mean_capped_time_to_validated_submission_s": sum(capped) / len(capped) if capped else None,
                "policy": policy,
            }
    contrasts: dict[str, Any] = {}
    for case in CASES:
        if case in excluded:
            contrasts[case] = "EXCLUDED"
            continue
        v = {a: table[case][a]["validated"] for a in ARMS}
        contrasts[case] = {"B1-B0": v["B1"] - v["B0"], "B2-B0": v["B2"] - v["B0"], "B3-B0": v["B3"] - v["B0"],
                           "B4-B0": v["B4"] - v["B0"], "B3-B2": v["B3"] - v["B2"], "B4-B3": v["B4"] - v["B3"],
                           "B4-B2": v["B4"] - v["B2"], "control": case in CONTROL_CASES}
    coverage = {a: sum(1 for c in CASES if c not in excluded and table[c][a]["validated"] > 0) for a in ARMS}
    costs = {}
    for r in data["requests"]:
        sid = r.get("session_id")
        if not sid:
            continue
        arm = sid.split(".")[-1]
        c = costs.setdefault(arm, {"requests": 0, "input_tokens": 0, "output_tokens": 0, "usd": 0.0})
        c["requests"] += 1
        c["input_tokens"] += r.get("input_tokens") or 0
        c["output_tokens"] += r.get("output_tokens") or 0
        c["usd"] += r.get("usd") or 0.0
    complete = all(l not in ("UNRESOLVED", "NOT_RUN") for c in CASES if c not in excluded
                   for a in ARMS for l in table[c][a]["labels"])
    result = {"artifact": "w1_analysis_v1", "table": table, "contrasts": contrasts, "case_coverage": coverage,
              "provider_costs_by_arm": costs, "complete": complete,
              "gates_note": "engineering gates apply only to a complete study without unresolved integrity problems",
              "claims_not_supported": ["population superiority", "prospective bug discovery", "diagnostic calibration",
                                       "TCP benefit"]}
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "analysis.json", result)
    lines = ["# W1 analysis (frozen descriptive procedure)", "",
             "| case | " + " | ".join(ARMS) + " |", "|---|" + "---|" * len(ARMS)]
    for case in CASES:
        cells = [("EXCLUDED" if table[case][a].get("status") == "EXCLUDED" else
                  f"{table[case][a]['validated']}/{table[case][a]['scheduled']}") for a in ARMS]
        lines.append(f"| {case} | " + " | ".join(cells) + " |")
    lines += ["", f"Complete: {complete}. Coverage per arm: {json.dumps(coverage)}.",
              "Counts are validated final candidates out of three scheduled replicates; missingness bounds and"
              " all labels are in analysis.json. No effectiveness claim follows from preparation or dry runs."]
    write_text_lf(out_dir / "report.md", "\n".join(lines) + "\n")
    return result
