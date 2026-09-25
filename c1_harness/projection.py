"""Measured-cost projection (protocol 6): old durations plus fixed calibration.

Three scenarios per subject-block, all at the frozen charging basis (R at 16,
verified L at 2), each attempt costing its job time plus the 2 s gap:

- **expected**: historical Q0 mean attempt duration per variant, with the
  larger of the Q0 mean and the smoke observation for L (calibration is one
  attempt, so it can only raise, never lower, the L estimate), plus the
  create/inspect/remove overhead measured in smoke.
- **conservative**: every defective-variant attempt on both profiles runs to the
  outer timeout plus full cleanup; acceptable variants as expected.
- **reservation**: the protocol's admission amount, everything at the timeout.

`simulate_admission` walks the frozen schedule in order with the live guard
(reserve the block's worst case, charge the scenario cost, release) and
reports the first matched block that would be refused.
"""

from __future__ import annotations

import csv
import statistics
from pathlib import Path
from typing import Any, Sequence

from c1_harness import REPO_ROOT
from c1_harness.budget import GAP_S, STAGE_CAPS, block_reservation_vcpu_h
from c1_harness.dockerexec import CLEANUP_TIMEOUT_S
from c1_harness.subjects import Subject

T5 = REPO_ROOT / "research_runs" / "ci_sensitivity_2026_09" / "task5_artifacts"
Q0_FILES = {
    "etcd5509": (T5 / "etcd5509/attempts/results_final.csv", "exit_code", {"vbad": "V_bad", "vok": "V_ok"}),
    "etcd7492": (T5 / "etcd7492/build/results.csv", "exit_code", {"vbad": "V_bad", "vok": "V_ok"}),
    "grpc1859": (T5 / "grpc1859/run/results.csv", "exit", None),
    "grpc2391": (T5 / "grpc2391/run/results.csv", "exit", None),
    "istio17860": (T5 / "istio17860/run/results.csv", "exit", None),
    "k8s26980": (T5 / "k8s26980/run/results.csv", "exit", None),
}


def q0_durations(sid: str) -> dict[str, dict[str, float]]:
    path, exit_col, rename = Q0_FILES[sid]
    by: dict[str, list[float]] = {}
    fails: dict[str, int] = {}
    for r in csv.DictReader(open(path, encoding="utf-8")):
        v = rename[r["version"]] if rename else r["version"]
        by.setdefault(v, []).append(float(r["elapsed_s"]))
        fails[v] = fails.get(v, 0) + int(int(r[exit_col]) != 0)
    return {v: {"mean_s": statistics.mean(x), "max_s": max(x), "n": len(x), "fail_rate": fails[v] / len(x)}
            for v, x in by.items()}


def smoke_observations(smoke_records: Sequence[dict[str, Any]]) -> dict[tuple[str, str, str], dict[str, float]]:
    out = {}
    for r in smoke_records:
        x = r.get("extra") or {}
        out[(r["episode"], r["condition"], r["version"])] = {
            "elapsed_s": r["elapsed_s"], "job_elapsed_s": x.get("job_elapsed_s", r["elapsed_s"]),
            "overhead_s": (x.get("job_elapsed_s") or r["elapsed_s"]) - r["elapsed_s"], "timed_out": r["timed_out"],
        }
    return out


def block_costs(s: Subject, q0: dict[str, dict[str, float]], smoke: dict[tuple[str, str, str], dict[str, float]]) -> dict[str, float]:
    overheads = [v["overhead_s"] for k, v in smoke.items() if k[0] == s.sid] or [1.0]
    overhead = max(overheads)
    exp, cons = 0.0, 0.0
    for profile, vcpus in (("R", 16), ("L", 2)):
        for version in ("V_bad", "V_ok"):
            hist = q0[version]["mean_s"]
            obs = smoke.get((s.sid, profile, version), {}).get("elapsed_s")
            e = hist if profile == "R" or obs is None else max(hist, obs)
            per = e + overhead + GAP_S
            exp += 3 * vcpus * per / 3600
            worst = s.outer_timeout_s + CLEANUP_TIMEOUT_S + GAP_S
            cons += 3 * vcpus * (worst if version == "V_bad" else per) / 3600
    return {"expected": exp, "conservative": cons, "reservation": block_reservation_vcpu_h(s.outer_timeout_s)}


def simulate_admission(schedule_rows: Sequence[dict[str, Any]], costs: dict[str, dict[str, float]], scenario: str,
                       cap: float = STAGE_CAPS["measured"]) -> dict[str, Any]:
    spent = 0.0
    order = []
    for r in schedule_rows:
        key = (int(r["block"]), r["subject"])
        if not order or order[-1] != key:
            order.append(key)
    for i, (block, sid) in enumerate(order, 1):
        need = costs[sid]["reservation"]
        if cap - spent < need - 1e-12:
            return {"scenario": scenario, "admitted_blocks": i - 1, "total_blocks": len(order),
                    "first_refused": {"block": block, "subject": sid, "remaining": cap - spent, "reservation": need},
                    "spent_at_refusal": spent}
        spent += costs[sid][scenario]
    return {"scenario": scenario, "admitted_blocks": len(order), "total_blocks": len(order),
            "first_refused": None, "projected_total": spent, "remaining_after": cap - spent}
