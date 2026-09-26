"""Run a bounded external command with a vCPU reservation before it starts.

Allocation convention (execution_plan.md Phase 4): 16 reserved CPUs x elapsed
allocated time. The reservation covers the full timeout plus cleanup; the
settlement charges what was actually elapsed (never less than zero, never
erased on overrun).
"""

from __future__ import annotations

from typing import Any, Sequence

from .proc import ProcResult, run
from .resources import ResourceAccount

RESERVED_VCPUS = 16


def vcpu_h(seconds: float, vcpus: int = RESERVED_VCPUS) -> float:
    return vcpus * max(0.0, seconds) / 3600.0


def charged_run(account: ResourceAccount, stage: str, entity_id: str, argv: Sequence[str], *, timeout_s: float,
                cleanup_s: float = 30.0, details: dict[str, Any] | None = None, cwd: str | None = None) -> ProcResult:
    rid = account.reserve(stage, entity_id, {"vcpu_h": vcpu_h(timeout_s + cleanup_s)},
                          {"argv": list(argv), "timeout_s": timeout_s, **(details or {})})
    result = run(argv, timeout_s=timeout_s, cwd=cwd)
    account.settle(rid, {"vcpu_h": vcpu_h(result.elapsed_s)}, {
        "elapsed_s": round(result.elapsed_s, 3), "exit_code": result.exit_code,
        "timed_out": result.timed_out, "error": result.error,
    })
    return result
