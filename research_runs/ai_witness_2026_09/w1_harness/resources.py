"""Study resource account: reservations before work, settlement after it.

All ceilings come from the governing ``v1_2/study_config.json`` ``study_caps`` (execution_plan.md
Phase 4). They are hard ceilings, not estimates or authority to buy anything.

* ``vcpu_h`` is allocated execution capacity: reserved CPUs x elapsed allocated
  time, including provider waiting while capacity remains reserved. It is not a
  CPU-utilisation measurement.
* Preparation (inventory, restoration builds, calibration, synthetic smoke) has
  its own 80 vCPU-h subcap inside the 400 vCPU-h study cap.
* Provider resources (USD, input tokens, generator requests, Jev atomic
  evaluations) are study-wide; the input-token ceiling includes smoke requests.

An open reservation (reserve without settle, e.g. after a crash) keeps counting
at its full reserved amount until an explicit reconciliation settles it; it is
never silently released.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .common import W1Error
from .ledger import ChainLedger

RESOURCE_KINDS = ("vcpu_h", "usd", "input_tokens", "output_tokens", "generator_requests", "jev_evaluations", "human_hours")
STAGES = ("preparation", "calibration", "smoke", "search", "validation", "analysis")
PREPARATION_STAGES = ("preparation", "calibration", "smoke")


class BudgetExceeded(W1Error):
    """A reservation cannot fit the remaining ceiling; the work must not start."""


@dataclass(frozen=True)
class Caps:
    vcpu_h_total: float
    vcpu_h_preparation: float
    human_hours: float
    generator_requests: int
    jev_evaluations: int
    input_tokens: int
    usd: float

    @classmethod
    def from_study_config(cls, config: dict[str, Any]) -> "Caps":
        c = config["study_caps"]
        return cls(
            vcpu_h_total=float(c["allocated_vcpu_hours"]),
            vcpu_h_preparation=float(c["preparation_allocated_vcpu_hours"]),
            human_hours=float(c["human_hours"]),
            generator_requests=int(c["generator_requests"]),
            jev_evaluations=int(c["jev_atomic_evaluations"]),
            input_tokens=int(c["input_tokens"]),
            usd=float(c["provider_usd"]),
        )


def _zero() -> dict[str, float]:
    return {k: 0.0 for k in RESOURCE_KINDS}


class ResourceAccount:
    def __init__(self, path: Path, caps: Caps):
        self.ledger = ChainLedger(path)
        self.caps = caps

    # -- state ------------------------------------------------------------
    def state(self) -> dict[str, Any]:
        charged = {s: _zero() for s in STAGES}
        open_res: dict[str, dict[str, Any]] = {}
        for row in self.ledger.iter_rows():
            p = row["payload"]
            et = row["event_type"]
            if et == "reserve":
                open_res[p["reservation_id"]] = {"stage": row["stage"], "amounts": p["amounts"], "entity_id": row["entity_id"]}
            elif et == "settle":
                open_res.pop(p["reservation_id"], None)
                for k, v in p["charged"].items():
                    charged[row["stage"]][k] += float(v or 0)
            elif et == "charge":
                for k, v in p["charged"].items():
                    charged[row["stage"]][k] += float(v or 0)
        reserved = {s: _zero() for s in STAGES}
        for r in open_res.values():
            for k, v in r["amounts"].items():
                reserved[r["stage"]][k] += float(v or 0)
        return {"charged": charged, "reserved": reserved, "open": open_res}

    def committed(self, kind: str, stages: tuple[str, ...] = STAGES) -> float:
        st = self.state()
        return sum(st["charged"][s][kind] + st["reserved"][s][kind] for s in stages)

    def remaining(self) -> dict[str, float]:
        st = self.state()

        def total(kind: str, stages: tuple[str, ...] = STAGES) -> float:
            return sum(st["charged"][s][kind] + st["reserved"][s][kind] for s in stages)

        return {
            "vcpu_h_total": self.caps.vcpu_h_total - total("vcpu_h"),
            "vcpu_h_preparation": self.caps.vcpu_h_preparation - total("vcpu_h", PREPARATION_STAGES),
            "usd": self.caps.usd - total("usd"),
            "input_tokens": self.caps.input_tokens - total("input_tokens"),
            "generator_requests": self.caps.generator_requests - total("generator_requests"),
            "jev_evaluations": self.caps.jev_evaluations - total("jev_evaluations"),
            "human_hours": self.caps.human_hours - total("human_hours"),
        }

    def summary(self) -> dict[str, Any]:
        st = self.state()
        return {
            "charged_by_stage": {s: {k: round(v, 6) for k, v in st["charged"][s].items() if v} for s in STAGES},
            "reserved_by_stage": {s: {k: round(v, 6) for k, v in st["reserved"][s].items() if v} for s in STAGES},
            "open_reservations": sorted(st["open"]),
            "remaining": {k: round(v, 6) for k, v in self.remaining().items()},
        }

    # -- writing ----------------------------------------------------------
    def _check(self, stage: str, amounts: dict[str, float]) -> None:
        if stage not in STAGES:
            raise W1Error(f"unknown stage {stage!r}")
        unknown = set(amounts) - set(RESOURCE_KINDS)
        if unknown:
            raise W1Error(f"unknown resource kinds {sorted(unknown)}")
        rem = self.remaining()
        need = {k: float(v or 0) for k, v in amounts.items()}
        checks = [
            ("vcpu_h_total", need.get("vcpu_h", 0.0)),
            ("usd", need.get("usd", 0.0)),
            ("input_tokens", need.get("input_tokens", 0.0)),
            ("generator_requests", need.get("generator_requests", 0.0)),
            ("jev_evaluations", need.get("jev_evaluations", 0.0)),
            ("human_hours", need.get("human_hours", 0.0)),
        ]
        if stage in PREPARATION_STAGES:
            checks.append(("vcpu_h_preparation", need.get("vcpu_h", 0.0)))
        for key, want in checks:
            if want > 0 and want > rem[key] + 1e-12:
                raise BudgetExceeded(f"{stage}: need {want:.6f} {key}, remaining {rem[key]:.6f}")

    def reserve(self, stage: str, entity_id: str, amounts: dict[str, float], details: dict[str, Any] | None = None) -> str:
        self._check(stage, amounts)
        seq, _ = self.ledger.tail()
        reservation_id = f"res-{seq + 1:06d}-{entity_id}"
        self.ledger.append(stage, "reserve", entity_id, {
            "reservation_id": reservation_id,
            "amounts": {k: float(v) for k, v in amounts.items()},
            "details": details or {},
        })
        return reservation_id

    def settle(self, reservation_id: str, charged: dict[str, float], details: dict[str, Any] | None = None) -> None:
        st = self.state()
        opened = st["open"].get(reservation_id)
        if opened is None:
            raise W1Error(f"reservation {reservation_id} is not open")
        overrun = {k: v for k, v in charged.items() if float(v or 0) > float(opened["amounts"].get(k, 0)) + 1e-9}
        self.ledger.append(opened["stage"], "settle", opened["entity_id"], {
            "reservation_id": reservation_id,
            "charged": {k: float(v or 0) for k, v in charged.items()},
            "overrun": overrun,
            "details": details or {},
        })

    def charge(self, stage: str, entity_id: str, charged: dict[str, float], details: dict[str, Any] | None = None, *, enforce: bool = True) -> None:
        """Direct charge (e.g. declared human hours or already-elapsed work)."""
        if enforce:
            self._check(stage, charged)
        self.ledger.append(stage, "charge", entity_id, {
            "charged": {k: float(v or 0) for k, v in charged.items()},
            "details": details or {},
        })

    def note(self, stage: str, entity_id: str, details: dict[str, Any]) -> None:
        self.ledger.append(stage, "note", entity_id, {"details": details})
