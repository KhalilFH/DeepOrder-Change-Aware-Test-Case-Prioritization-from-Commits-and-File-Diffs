"""Append-only, hash-chained ledger of E1 attempt observations.

Per the plan (section 4.2), every attempt retains its raw exit code, full
stdout/stderr, duration, timing, and environment/seed/condition identity. Two
properties are enforced here rather than left to discipline:

**Append-only.** The class exposes no update, delete or truncate verb. Opening
an existing ledger appends to it; re-recording an attempt identity that is
already present is refused, because that means a bookkeeping error rather than
a new observation. Section 4.3 requires that earlier failures stay in the
research ledger even when a policy accepts, so nothing may remove them.

**Tamper-evident.** Each record carries the SHA-256 of the previous record's
serialised form, so `verify_chain` detects any later edit, reordering or
deletion. The point is not security against an adversary; it is that a
qualification result which turns on a handful of attempts should not rest on a
file that could have been quietly corrected.

Deliberately *not* recorded here: the oracle categories. Classification is a
separate evaluator step, and a runner that wrote categories at capture time
would be adjudicating on the same pass that observes.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

V_BAD = "V_bad"
V_OK = "V_ok"
VERSIONS = (V_BAD, V_OK)

MAX_ATTEMPTS_PER_BLOCK = 3

GENESIS = "0" * 64


class LedgerError(RuntimeError):
    """The ledger's contract was violated."""


@dataclass(frozen=True)
class AttemptRecord:
    """One executed attempt. `exit_status` is the only field a policy may read."""

    episode: str
    block: int
    version: str
    attempt: int

    exit_status: int | None
    started_utc: str
    ended_utc: str
    elapsed_s: float
    timed_out: bool

    condition: str
    seed: int | None
    manifest_sha256: str
    runner_version: str

    stdout: str
    stderr: str

    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def identity(self) -> tuple[str, int, str, int]:
        return (self.episode, self.block, self.version, self.attempt)

    def validate(self) -> "AttemptRecord":
        if self.version not in VERSIONS:
            raise LedgerError(
                f"unknown version {self.version!r}; expected one of {VERSIONS}"
            )
        if not 1 <= self.attempt <= MAX_ATTEMPTS_PER_BLOCK:
            raise LedgerError(
                f"attempt {self.attempt} is outside a block's "
                f"1..{MAX_ATTEMPTS_PER_BLOCK} range"
            )
        if self.block < 1:
            raise LedgerError(f"block {self.block} is not a positive block number")
        if self.exit_status is not None and not isinstance(self.exit_status, int):
            raise LedgerError(f"exit_status must be an int or None, got {self.exit_status!r}")
        return self


def _canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(previous: str, payload: dict[str, Any]) -> str:
    return hashlib.sha256((previous + _canonical(payload)).encode("utf-8")).hexdigest()


def read_records(path: str | Path) -> list[dict[str, Any]]:
    """Every record in the ledger, in written order. Returns [] if absent."""
    p = Path(path)
    if not p.exists():
        return []
    out = []
    for lineno, line in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise LedgerError(f"{p}:{lineno}: malformed ledger line: {exc}") from exc
    return out


def verify_chain(path: str | Path) -> int:
    """Re-walk the hash chain. Raises `LedgerError` on any break; returns the count."""
    previous = GENESIS
    records = read_records(path)
    for position, row in enumerate(records, start=1):
        row = dict(row)
        recorded = row.pop("sha256", None)
        # `prev_sha256` stays in the payload: it was part of the digested form.
        prev_recorded = row.get("prev_sha256")
        if recorded is None or prev_recorded is None:
            raise LedgerError(f"record {position} is missing its chain fields")
        if prev_recorded != previous:
            raise LedgerError(
                f"record {position} (seq {row.get('seq')}) does not follow the "
                f"previous record: a record was edited, reordered or deleted"
            )
        if _digest(previous, row) != recorded:
            raise LedgerError(
                f"record {position} (seq {row.get('seq')}) has been modified "
                f"since it was written"
            )
        previous = recorded
    return len(records)


def exit_statuses_for(
    records: Iterable[dict[str, Any]], episode: str, block: int, version: str
) -> list[int | None]:
    """The block's attempts in attempt order, ready for `policy.reduce_block`.

    A gap in the attempt numbers becomes `None` so the reducer treats the block
    as undetermined rather than silently reading a short prefix as complete.
    """
    found: dict[int, int | None] = {}
    for row in records:
        if (row["episode"], row["block"], row["version"]) == (episode, block, version):
            found[row["attempt"]] = row["exit_status"]
    if not found:
        return []
    return [found.get(i) for i in range(1, max(found) + 1)]


class Ledger:
    """Append-only writer. Use as a context manager."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        existing = read_records(self.path)
        self._seq = len(existing)
        self._previous = existing[-1]["sha256"] if existing else GENESIS
        self._seen = {
            (r["episode"], r["block"], r["version"], r["attempt"]) for r in existing
        }
        self._handle = None

    def __enter__(self) -> "Ledger":
        self._handle = open(self.path, "a", encoding="utf-8", newline="\n")
        return self

    def __exit__(self, *exc) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None

    def append(self, record: AttemptRecord) -> dict[str, Any]:
        """Write one attempt. Raises if its identity is already in the ledger."""
        record.validate()
        if record.identity in self._seen:
            raise LedgerError(
                f"attempt {record.identity} is already in the ledger; a ledger "
                "is append-only, so an observation is never re-recorded"
            )
        if self._handle is None:
            raise LedgerError("ledger is not open; use it as a context manager")

        self._seq += 1
        payload = asdict(record)
        payload["seq"] = self._seq
        payload["prev_sha256"] = self._previous
        payload["sha256"] = _digest(self._previous, payload)

        self._handle.write(_canonical(payload) + "\n")
        self._handle.flush()
        os.fsync(self._handle.fileno())

        self._previous = payload["sha256"]
        self._seen.add(record.identity)
        return payload

    def __len__(self) -> int:
        return self._seq
