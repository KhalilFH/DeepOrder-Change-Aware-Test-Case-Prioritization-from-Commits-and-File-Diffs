"""Append-only, hash-chained JSONL ledgers (artifact_contract.md, "Stable IDs and chronology").

Every envelope has schema_version, a monotonically increasing sequence, a UTC
timestamp, stage, event_type, entity_id, previous_event_sha256 and payload.
event_sha256 is the SHA-256 of the canonical JSON of the envelope without
event_sha256. The genesis previous hash is 64 zeros. Each append is flushed and
fsynced before returning, so a caller can claim completion only after the event
is persisted. This is an integrity chain, not a trusted external timestamp.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterator

from .common import ZERO_HASH, W1Error, canonical_bytes, sha256_bytes, utc_now

SCHEMA_VERSION = "w2a-event/1"  # W2A copy of W1 ledger.py; only the schema identifier differs
ENVELOPE_KEYS = (
    "schema_version", "sequence", "utc", "stage", "event_type", "entity_id",
    "previous_event_sha256", "payload",
)


class LedgerError(W1Error):
    """The chain is broken, reordered, edited or otherwise unusable."""


def envelope_digest(envelope: dict[str, Any]) -> str:
    body = {k: envelope[k] for k in ENVELOPE_KEYS}
    return sha256_bytes(canonical_bytes(body))


class ChainLedger:
    """One JSONL file; each line is an envelope plus its event_sha256."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._tail: tuple[int, str] | None = None

    # -- reading -----------------------------------------------------------
    def iter_rows(self) -> Iterator[dict[str, Any]]:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8", newline="\n") as fh:
            for n, line in enumerate(fh, 1):
                if not line.strip():
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as exc:
                    raise LedgerError(f"{self.path}:{n}: malformed JSON ({exc})") from exc

    def rows(self) -> list[dict[str, Any]]:
        return list(self.iter_rows())

    def verify(self) -> int:
        """Verify the whole chain; return the number of events."""
        previous = ZERO_HASH
        count = 0
        for i, row in enumerate(self.iter_rows(), 1):
            missing = [k for k in ENVELOPE_KEYS + ("event_sha256",) if k not in row]
            if missing:
                raise LedgerError(f"{self.path} event {i}: missing {missing}")
            if row["sequence"] != i:
                raise LedgerError(f"{self.path} event {i}: sequence {row['sequence']} is not {i}")
            if row["previous_event_sha256"] != previous:
                raise LedgerError(f"{self.path} event {i}: previous hash does not chain")
            if envelope_digest(row) != row["event_sha256"]:
                raise LedgerError(f"{self.path} event {i}: event_sha256 mismatch (edited)")
            previous = row["event_sha256"]
            count = i
        self._tail = (count, previous)
        return count

    def tail(self) -> tuple[int, str]:
        if self._tail is None:
            self.verify()
        assert self._tail is not None
        return self._tail

    # -- writing -----------------------------------------------------------
    def append(self, stage: str, event_type: str, entity_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        sequence, previous = self.tail()
        envelope = {
            "schema_version": SCHEMA_VERSION,
            "sequence": sequence + 1,
            "utc": utc_now(),
            "stage": stage,
            "event_type": event_type,
            "entity_id": entity_id,
            "previous_event_sha256": previous,
            "payload": payload,
        }
        envelope["event_sha256"] = envelope_digest(envelope)
        line = json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(line + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        self._tail = (sequence + 1, envelope["event_sha256"])
        return envelope

    def find(self, *, event_type: str | None = None, entity_id: str | None = None) -> list[dict[str, Any]]:
        return [
            r for r in self.iter_rows()
            if (event_type is None or r["event_type"] == event_type)
            and (entity_id is None or r["entity_id"] == entity_id)
        ]
