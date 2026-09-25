"""Budget reconciliation for the post-C1 signal-validity audit.

Appends the audit's timed computation charges (signal_audit/cost_log.jsonl) to
the chained resources/resource_ledger.jsonl as analysis-stage charges, using
c1_harness's own ResourceLedger so the chain format is unchanged. The charges
are recorded retrospectively: no reservation rows are fabricated, and each
row's note says so. Finally the ledger is charged for this reconciliation job
itself. Refuses to run twice.

Run from the repository root: python -B research_runs/ci_configuration_2026_09/signal_audit/s07_reconcile_budget.py
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
from pathlib import Path

T0 = time.perf_counter()
STARTED = dt.datetime.now(dt.timezone.utc)
REPO = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO), str(REPO / "e1_harness")]

from c1_harness.budget import ResourceLedger  # noqa: E402

HERE = Path(__file__).resolve().parent
LEDGER = HERE.parent / "resources" / "resource_ledger.jsonl"
COST_LOG = HERE / "cost_log.jsonl"
PREFIX = "signal-audit-v1-"
BASIS = "Conservative 16-vCPU host capacity (same basis as the post-collection pass); stdlib Python, no container or subject execution."


def iso_plus(start: str, seconds: float) -> str:
    return (dt.datetime.fromisoformat(start) + dt.timedelta(seconds=seconds)).isoformat()


def main() -> int:
    led = ResourceLedger(LEDGER)
    led.verify()
    if any(r.get("job_id", "").startswith(PREFIX) for r in led.rows()):
        print("refusing: signal-audit charges already recorded")
        return 2
    before = led.summary()["analysis"]
    rows = [json.loads(l) for l in COST_LOG.read_text(encoding="utf-8").splitlines() if l.strip()]
    for i, c in enumerate(rows, 1):
        led.charge(
            stage="analysis",
            job_id=f"{PREFIX}{i:02d}-{c['script'].removesuffix('.py')}",
            kind_of_job="post_hoc_signal_audit",
            basis_vcpus=c["basis_vcpus"],
            basis_reason=BASIS,
            job_elapsed_s=c["elapsed_s"],
            gap_s=0,
            started_utc=c["started_utc"],
            ended_utc=iso_plus(c["started_utc"], c["elapsed_s"]),
            note=(f"Recorded retrospectively on reconciliation from signal_audit/cost_log.jsonl row {i} "
                  f"(script_sha256 {c['script_sha256']}, rc {c['returncode']}); no reservation was opened at run time."),
        )
    elapsed = time.perf_counter() - T0
    led.charge(
        stage="analysis",
        job_id=f"{PREFIX}{len(rows) + 1:02d}-s07_reconcile_budget",
        kind_of_job="budget_reconciliation",
        basis_vcpus=16,
        basis_reason=BASIS,
        job_elapsed_s=elapsed,
        gap_s=0,
        started_utc=STARTED.isoformat(),
        ended_utc=iso_plus(STARTED.isoformat(), elapsed),
        note="This reconciliation job itself, timed up to this append; not a run_timed.py run.",
    )
    with open(COST_LOG, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps({
            "label": "exploratory post-hoc signal audit", "script": "s07_reconcile_budget.py",
            "script_sha256": None, "python": sys.version.split()[0], "started_utc": STARTED.isoformat(),
            "elapsed_s": round(elapsed, 6), "basis_vcpus": 16, "charged_vcpu_h": 16 * elapsed / 3600,
            "returncode": 0, "note": "self-timed reconciliation job; also charged in resources/resource_ledger.jsonl",
        }, sort_keys=True) + "\n")
    n = led.verify()
    after = led.summary()["analysis"]
    audit_total = sum(r["charged_vcpu_h"] for r in led.rows() if r.get("job_id", "").startswith(PREFIX))
    print(json.dumps({"ledger_rows": n, "analysis_before": before, "analysis_after": after,
                      "signal_audit_charged_vcpu_h": round(audit_total, 6), "charges_added": len(rows) + 1}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
