"""Complete, outcome-independent W2A schedule from the frozen seed.

Uses W1's SHA-256 counter stream and Fisher-Yates shuffle (w1_harness/schedule.py ``Stream``,
reproduced unchanged) with W2A labels:

* one block per case, in a shuffled case order;
* per block, a shuffled F2/F3 session order and an independently shuffled validation order; both
  finals of a block are sealed before either is validated;
* per session, seeded first-variant draws for up to six search pairs;
* per final candidate, five matched triplets per variant with a per-triplet seed and a seeded
  first variant.
"""

from __future__ import annotations

import hashlib
from typing import Any

from . import ARMS, CASES
from .common import sha256_json

GENERATOR_ID = "w2a-schedule/1 sha256-counter fisher-yates (W1 Stream)"


class Stream:
    def __init__(self, seed: int, label: str):
        self.seed = seed
        self.label = label
        self.counter = 0

    def u64(self) -> int:
        h = hashlib.sha256(f"{self.seed}:{self.label}:{self.counter}".encode()).digest()
        self.counter += 1
        return int.from_bytes(h[:8], "big")

    def below(self, n: int) -> int:
        if n <= 0:
            raise ValueError("n must be positive")
        limit = (1 << 64) - ((1 << 64) % n)
        while True:
            x = self.u64()
            if x < limit:
                return x % n

    def shuffle(self, items: list[Any]) -> list[Any]:
        a = list(items)
        for i in range(len(a) - 1, 0, -1):
            j = self.below(i + 1)
            a[i], a[j] = a[j], a[i]
        return a

    def seed32(self) -> int:
        return self.u64() & 0x7FFFFFFF


def session_id(case: str, arm: str) -> str:
    return f"w2a.{case}.{arm}"


def build(seed: int, triplets: int = 5, attempts_per_triplet: int = 3, max_pairs: int = 6) -> dict[str, Any]:
    blocks, sessions = [], []
    for case in Stream(seed, "w2a.cases").shuffle(list(CASES)):
        arms = Stream(seed, f"w2a.{case}.arms").shuffle(list(ARMS))
        val = Stream(seed, f"w2a.{case}.validation").shuffle(list(ARMS))
        block_id = f"w2a.{case}"
        blocks.append({"block_id": block_id, "case": case, "session_order": arms,
                       "validation_order": [session_id(case, a) for a in val], "status": "SCHEDULED"})
        for pos, arm in enumerate(arms, 1):
            sid = session_id(case, arm)
            fs = Stream(seed, f"{sid}.search.first")
            vs = Stream(seed, f"{sid}.validation")
            vtrip = [{"triplet": t, "seed": vs.seed32(), "first_variant": ("V_bad", "V_ok")[vs.below(2)]}
                     for t in range(1, triplets + 1)]
            sessions.append({"session_id": sid, "block_id": block_id, "case": case, "arm": arm, "position_in_block": pos,
                             "search_pair_first_variant": [("V_bad", "V_ok")[fs.below(2)] for _ in range(max_pairs)],
                             "validation_triplets": vtrip, "status": "SCHEDULED"})
    body = {
        "artifact": "w2a_schedule_v1", "generator": GENERATOR_ID, "seed": seed, "cases": list(CASES), "arms": list(ARMS),
        "blocks": blocks, "sessions": sessions,
        "validation_design": {"triplets_per_variant": triplets, "attempts_per_triplet": attempts_per_triplet,
                              "order": "per triplet k: first_variant triplet (3 consecutive attempts), then the other"},
        "counts": {"sessions": len(sessions), "blocks": len(blocks),
                   "max_validation_attempts": len(sessions) * triplets * attempts_per_triplet * 2},
    }
    body["schedule_sha256"] = sha256_json(body)
    return body


def verify(schedule: dict[str, Any]) -> list[str]:
    problems = []
    regen = build(schedule["seed"])
    if regen["schedule_sha256"] != schedule.get("schedule_sha256") or regen != schedule:
        problems.append("schedule does not regenerate byte-identically from its seed")
    ids = [s["session_id"] for s in schedule["sessions"]]
    if len(ids) != len(set(ids)):
        problems.append("duplicate session ids")
    if set(ids) != {session_id(c, a) for c in CASES for a in ARMS}:
        problems.append("schedule is not the complete cases x arms design")
    return problems
