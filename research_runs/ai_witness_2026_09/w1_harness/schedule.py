"""Complete, outcome-independent W1 schedule from the frozen seed (protocol.md "Fixed design").

Randomness: a SHA-256 counter stream keyed by (seed, label), consumed by rejection
sampling, drives an implementation-defined Fisher-Yates shuffle. It is independent of
Python's ``random`` module and of platform, so the schedule regenerates byte-identically.

Structure:
* calibration: shuffled case order; per case a shuffled sequence of two unchanged-test
  attempts per variant (at most 16 attempts);
* search: 3 replicate rounds; per round a shuffled case order; per case a shuffled arm order
  (one block = five sessions of a case/round, all sealed before any validation);
* per block, a shuffled validation order of the five sealed finals;
* per session, seeded first-variant draws for up to six search pairs;
* per final candidate, five matched triplets per variant with a per-triplet seed and a
  seeded first variant.

Rows are never removed: excluded cases keep their rows with status EXCLUDED.
"""

from __future__ import annotations

import hashlib
from typing import Any

from . import ARMS, CASES
from .common import sha256_json

GENERATOR_ID = "w1-schedule/1 sha256-counter fisher-yates"


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


def session_id(case: str, replicate: int, arm: str) -> str:
    return f"w1.{case}.r{replicate}.{arm}"


def build(seed: int, replicates: int = 3, exclusions: dict[str, str] | None = None,
          triplets: int = 5, attempts_per_triplet: int = 3, max_pairs: int = 6,
          calib_per_variant: int = 2) -> dict[str, Any]:
    exclusions = dict(exclusions or {})
    cal_cases = Stream(seed, "calibration.cases").shuffle(list(CASES))
    calibration = []
    for case in cal_cases:
        seq = Stream(seed, f"calibration.{case}").shuffle(["V_bad"] * calib_per_variant + ["V_ok"] * calib_per_variant)
        for k, variant in enumerate(seq, 1):
            calibration.append({"id": f"w1.cal.{case}.a{k}", "case": case, "variant": variant, "position": k,
                                "status": "EXCLUDED" if case in exclusions else "SCHEDULED"})
    blocks = []
    sessions = []
    for r in range(1, replicates + 1):
        for case in Stream(seed, f"round{r}.cases").shuffle(list(CASES)):
            arms = Stream(seed, f"round{r}.{case}.arms").shuffle(list(ARMS))
            val_order = Stream(seed, f"round{r}.{case}.validation").shuffle(list(arms))
            block_id = f"w1.{case}.r{r}"
            blocks.append({"block_id": block_id, "replicate": r, "case": case, "session_order": arms,
                           "validation_order": [session_id(case, r, a) for a in val_order],
                           "status": "EXCLUDED" if case in exclusions else "SCHEDULED"})
            for pos, arm in enumerate(arms, 1):
                sid = session_id(case, r, arm)
                fs = Stream(seed, f"{sid}.search.first")
                search_first = [("V_bad", "V_ok")[fs.below(2)] for _ in range(max_pairs)]
                vs = Stream(seed, f"{sid}.validation")
                vtrip = []
                for t in range(1, triplets + 1):
                    vtrip.append({"triplet": t, "seed": vs.seed32(), "first_variant": ("V_bad", "V_ok")[vs.below(2)]})
                sessions.append({"session_id": sid, "block_id": block_id, "case": case, "replicate": r, "arm": arm,
                                 "position_in_block": pos, "search_pair_first_variant": search_first,
                                 "validation_triplets": vtrip,
                                 "status": "EXCLUDED" if case in exclusions else "SCHEDULED"})
    body = {
        "artifact": "w1_schedule_v1",
        "generator": GENERATOR_ID,
        "seed": seed,
        "replicates": replicates,
        "cases": list(CASES),
        "arms": list(ARMS),
        "exclusions": exclusions,
        "calibration": calibration,
        "blocks": blocks,
        "sessions": sessions,
        "validation_design": {"triplets_per_variant": triplets, "attempts_per_triplet": attempts_per_triplet,
                              "order": "per triplet k: first_variant triplet (3 consecutive attempts), then the other"},
        "counts": {"sessions": len(sessions), "blocks": len(blocks), "calibration_attempts": len(calibration),
                   "max_validation_attempts": len(sessions) * triplets * attempts_per_triplet * 2},
    }
    body["schedule_sha256"] = sha256_json({k: v for k, v in body.items()})
    return body


def verify(schedule: dict[str, Any]) -> list[str]:
    problems = []
    regen = build(schedule["seed"], schedule["replicates"], schedule.get("exclusions"))
    if regen["schedule_sha256"] != schedule.get("schedule_sha256"):
        problems.append("schedule does not regenerate byte-identically from its seed and exclusions")
    ids = [s["session_id"] for s in schedule["sessions"]]
    if len(ids) != len(set(ids)):
        problems.append("duplicate session ids")
    want = {session_id(c, r, a) for c in CASES for r in range(1, schedule["replicates"] + 1) for a in ARMS}
    if set(ids) != want:
        problems.append("schedule is not the complete cases x arms x replicates design")
    return problems
