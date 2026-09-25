"""The batch-A integrity, validity and cost gate (protocol 6).

It checks provenance chains, identity joins against the schedule, profile and
cleanup evidence, harness-invalid fractions and the budget projection. It does
not compute any R/L or P1/P3 comparison: comparative effects never decide
whether batch B runs.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Sequence

from ledger import read_records, verify_chain
from policy import HARNESS_INVALID

from c1_harness.budget import block_reservation_vcpu_h
from c1_harness.cards import classify_text
from c1_harness.driver import Context, EventLog, stage_dir
from c1_harness.profiles import PROFILES
from c1_harness.subjects import VARIANT_OF, Subject

INVALID_LIMIT = 0.10


def gate_a(ctx: Context, subjects: dict[str, Subject], schedule_rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    problems: list[str] = []
    ctx.events.verify()
    ctx.budget.verify()
    ended_a = [e for e in ctx.events.rows() if e["kind"] == "session_end" and str(e.get("session", "")).startswith("measured-A-")]
    if not ended_a:
        problems.append("no batch-A session has ended: the gate follows batch A, it cannot precede it")
    sched = {r["attempt_id"]: r for r in schedule_rows}
    records = []
    for path in sorted(stage_dir(ctx, "measured").glob("*__*.jsonl")):
        try:
            verify_chain(path)
        except Exception as exc:  # noqa: BLE001 - any chain failure is an integrity failure
            problems.append(f"{path.name}: {exc}")
        records += read_records(path)

    ids = Counter((r.get("extra") or {}).get("attempt_id") for r in records)
    problems += [f"duplicate attempt id {i}" for i, n in ids.items() if n > 1]
    per_subject: dict[str, dict[str, Any]] = {}
    for r in records:
        x = r.get("extra") or {}
        s = sched.get(x.get("attempt_id"))
        if s is None:
            problems.append(f"record {r['seq']} ({x.get('attempt_id')}) is not in the frozen schedule")
            continue
        if (r["episode"], r["condition"], r["block"], r["version"], r["attempt"]) != (
            s["subject"], s["profile"], int(s["block"]), VARIANT_OF[s["variant"]], int(s["attempt"])
        ):
            problems.append(f"{x.get('attempt_id')}: record identity does not match the schedule row")
        prof = PROFILES[r["condition"]]
        insp = x.get("inspect") or {}
        if not x.get("profile_verified") or (insp.get("cpu_quota") or 0) != prof.cpu_quota:
            problems.append(f"{x.get('attempt_id')}: profile evidence missing or wrong")
        if not (x.get("cleanup") or {}).get("verified_absent"):
            problems.append(f"{x.get('attempt_id')}: cleanup not verified")
        d = per_subject.setdefault(r["episode"], {"recorded": 0, "harness_invalid": 0, "measured_vcpu_h_est": 0.0})
        d["recorded"] += 1
        if HARNESS_INVALID in classify_text(r["episode"], r["exit_status"], r["stdout"], r["stderr"]):
            d["harness_invalid"] += 1

    decisions = []
    for sid, s in subjects.items():
        if not s.enrolled:
            continue
        scheduled_a = sum(1 for r in schedule_rows if r["subject"] == sid and r["batch"] == "A")
        d = per_subject.get(sid, {"recorded": 0, "harness_invalid": 0})
        frac = d["harness_invalid"] / scheduled_a if scheduled_a else None
        stop = frac is not None and frac > INVALID_LIMIT
        decisions.append({"subject": sid, "scheduled_A": scheduled_a, "recorded": d["recorded"],
                          "missing": scheduled_a - d["recorded"], "harness_invalid": d["harness_invalid"],
                          "invalid_fraction_of_scheduled": frac, "stop_subject": stop})

    spent = ctx.budget.spent("measured")
    remaining = ctx.budget.remaining("measured")
    continuing = [d["subject"] for d in decisions if not d["stop_subject"]]
    projected_b = spent  # five blocks again, at the observed batch-A cost
    worst_block = max((block_reservation_vcpu_h(subjects[s].outer_timeout_s) for s in continuing), default=0.0)
    result = {
        "integrity_problems": problems,
        "integrity_passed": not problems,
        "subjects": decisions,
        "cost": {
            "measured_spent_vcpu_h": spent,
            "measured_remaining_vcpu_h": remaining,
            "projected_batch_b_vcpu_h_at_batch_a_rate": projected_b,
            "largest_block_reservation_vcpu_h": worst_block,
            "projection_within_remaining": projected_b <= remaining,
            "note": "the live block-admission guard still stops batch B if a reservation cannot be covered",
        },
        "effects_computed": False,
    }
    return result


def record_gate_a(events: EventLog, result: dict[str, Any]) -> None:
    for d in result["subjects"]:
        if d["stop_subject"]:
            events.append("subject_stopped", subject=d["subject"],
                          reason=f"harness-invalid fraction {d['invalid_fraction_of_scheduled']:.3f} > {INVALID_LIMIT}")
    events.append("gate_a", integrity_passed=result["integrity_passed"],
                  integrity_problems=result["integrity_problems"][:50], subjects=result["subjects"], cost=result["cost"])
