"""Stage budgets, charges and block reservations (protocol section 6).

One append-only, hash-chained JSONL file records every charge, reservation and
release, across all stages, including failed and interrupted work. Nothing is
transferred between stages. Allocated-capacity hours, host-reservation hours and
measured CPU are separate fields: a 2-vCPU quota on a 16-vCPU VM that is
reserved anyway does not make the bill smaller, and CPU time that was not
measured is `null`, never zero.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from ledger import GENESIS, _canonical, _digest  # E1's chain format, reused as-is

from c1_harness.dockerexec import CLEANUP_TIMEOUT_S, utc_now

STAGE_CAPS = {"preparation": 8.0, "validation": 6.0, "measured": 24.0, "analysis": 2.0}
TOTAL_CAP = 40.0
HOST_VCPUS = 16
GAP_S = 2.0
"""Fixed pause after each attempt's cleanup (protocol 5); charged with the attempt."""

CPU_UNMEASURED = (
    "not instrumented: the container's cgroup is removed when it exits, and reading "
    "it concurrently would need a second container that could perturb one profile"
)


class BudgetError(RuntimeError):
    """A stage cap cannot cover the requested work, or the ledger is corrupt."""


def block_reservation_vcpu_h(outer_timeout_s: float) -> float:
    """Protocol 6: `3 * (16 + 2) * 2 * (outer + 30 + 2) / 3600` capacity-hours."""
    return 3 * (16 + 2) * 2 * (outer_timeout_s + CLEANUP_TIMEOUT_S + GAP_S) / 3600


def attempt_reservation_vcpu_h(basis_vcpus: float, outer_timeout_s: float) -> float:
    """Worst case for one attempt: runs to the outer timeout, full cleanup, gap."""
    return basis_vcpus * (outer_timeout_s + CLEANUP_TIMEOUT_S + GAP_S) / 3600


class ResourceLedger:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    # --- reading ------------------------------------------------------------

    def rows(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        out = []
        for n, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip():
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise BudgetError(f"{self.path}:{n}: malformed row: {exc}") from exc
        return out

    def verify(self) -> int:
        previous = GENESIS
        rows = self.rows()
        for i, row in enumerate(rows, 1):
            row = dict(row)
            recorded = row.pop("sha256", None)
            if row.get("prev_sha256") != previous or _digest(previous, row) != recorded:
                raise BudgetError(f"resource ledger row {i} was edited, reordered or deleted")
            previous = recorded
        return len(rows)

    def spent(self, stage: str | None = None) -> float:
        return sum(
            r["charged_vcpu_h"]
            for r in self.rows()
            if r["kind"] == "charge" and (stage is None or r["stage"] == stage)
        )

    def host_reservation(self, stage: str | None = None) -> float:
        return sum(
            r["host_reservation_h"]
            for r in self.rows()
            if r["kind"] == "charge" and (stage is None or r["stage"] == stage)
        )

    def open_reservations(self, stage: str | None = None) -> dict[str, dict[str, Any]]:
        opened: dict[str, dict[str, Any]] = {}
        for r in self.rows():
            if r["kind"] == "reserve":
                opened[r["reservation_id"]] = r
            elif r["kind"] == "release":
                opened.pop(r["reservation_id"], None)
        return {k: v for k, v in opened.items() if stage is None or v["stage"] == stage}

    def reserved(self, stage: str) -> float:
        return sum(r["amount_vcpu_h"] for r in self.open_reservations(stage).values())

    def remaining(self, stage: str) -> float:
        return STAGE_CAPS[stage] - self.spent(stage) - self.reserved(stage)

    def summary(self) -> dict[str, Any]:
        return {
            stage: {
                "cap_vcpu_h": cap,
                "spent_vcpu_h": round(self.spent(stage), 6),
                "reserved_vcpu_h": round(self.reserved(stage), 6),
                "remaining_vcpu_h": round(self.remaining(stage), 6),
                "host_reservation_h": round(self.host_reservation(stage), 6),
            }
            for stage, cap in STAGE_CAPS.items()
        }

    # --- writing ------------------------------------------------------------

    def _append(self, payload: dict[str, Any]) -> dict[str, Any]:
        rows = self.rows()
        previous = rows[-1]["sha256"] if rows else GENESIS
        payload = {"seq": len(rows) + 1, "recorded_utc": utc_now(), **payload, "prev_sha256": previous}
        payload["sha256"] = _digest(previous, payload)
        with open(self.path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(_canonical(payload) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        return payload

    def charge(
        self,
        *,
        stage: str,
        job_id: str,
        kind_of_job: str,
        basis_vcpus: float,
        basis_reason: str,
        job_elapsed_s: float,
        gap_s: float,
        started_utc: str,
        ended_utc: str,
        attempt_elapsed_s: float | None = None,
        measured_cpu_s: float | None = None,
        note: str = "",
    ) -> dict[str, Any]:
        if stage not in STAGE_CAPS:
            raise BudgetError(f"unknown stage {stage!r}")
        full = job_elapsed_s + gap_s
        return self._append(
            {
                "kind": "charge",
                "stage": stage,
                "job_id": job_id,
                "job_kind": kind_of_job,
                "basis_vcpus": basis_vcpus,
                "basis_reason": basis_reason,
                "started_utc": started_utc,
                "ended_utc": ended_utc,
                "attempt_elapsed_s": attempt_elapsed_s,
                "job_elapsed_s": round(job_elapsed_s, 6),
                "gap_s": gap_s,
                "charged_vcpu_h": basis_vcpus * full / 3600,
                "host_reservation_h": HOST_VCPUS * full / 3600,
                "measured_cpu_s": measured_cpu_s,
                "measured_cpu_note": None if measured_cpu_s is not None else CPU_UNMEASURED,
                "note": note,
            }
        )

    def admit(self, stage: str, reservation_id: str, amount_vcpu_h: float, note: str = "") -> dict[str, Any]:
        """Reserve worst-case capacity before work starts, or refuse."""
        if reservation_id in self.open_reservations():
            raise BudgetError(f"reservation {reservation_id} is already open")
        left = self.remaining(stage)
        if amount_vcpu_h > left + 1e-12:
            raise BudgetError(
                f"{stage}: reservation {amount_vcpu_h:.4f} vCPU-h exceeds the remaining "
                f"{left:.4f} of the {STAGE_CAPS[stage]} cap"
            )
        return self._append(
            {
                "kind": "reserve",
                "stage": stage,
                "reservation_id": reservation_id,
                "amount_vcpu_h": amount_vcpu_h,
                "remaining_before_vcpu_h": left,
                "note": note,
            }
        )

    def release(self, reservation_id: str, note: str = "") -> dict[str, Any]:
        opened = self.open_reservations()
        if reservation_id not in opened:
            raise BudgetError(f"no open reservation {reservation_id}")
        return self._append(
            {
                "kind": "release",
                "stage": opened[reservation_id]["stage"],
                "reservation_id": reservation_id,
                "note": note,
            }
        )

    def agent_time(self, *, stage: str, started_utc: str, ended_utc: str, note: str) -> dict[str, Any]:
        """Agent wall-clock for a stretch of work. Not a human-hour measurement."""
        return self._append(
            {
                "kind": "agent_time",
                "stage": stage,
                "started_utc": started_utc,
                "ended_utc": ended_utc,
                "human_minutes": None,
                "note": note,
            }
        )
