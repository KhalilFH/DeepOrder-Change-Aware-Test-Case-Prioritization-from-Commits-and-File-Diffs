"""The complete, outcome-independent measured schedule (protocol section 5).

- Batch A: blocks 1-5; batch B: blocks 6-10.
- Within a block, enrolled subjects are sorted by SHA-256 of
  `c1-v1:subject-order:<block>:<subject>`.
- Within subject/block, the four cells are sorted by SHA-256 of
  `c1-v1:cell-order:<subject>:<block>:<profile>:<variant>`.
- Ties break lexicographically on the literal string. Attempts are 1, 2, 3.

Each subject's sort key depends only on its own name, so the relative order of
enrolled subjects is the same whether it is computed over six or fewer; an
exclusion removes rows and moves nothing else. The literal hashed strings are
saved beside the order they produced.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from collections import Counter
from typing import Any, Sequence

BLOCKS = tuple(range(1, 11))
BATCHES = {"A": (1, 2, 3, 4, 5), "B": (6, 7, 8, 9, 10)}
PROFILES = ("R", "L")
VARIANTS = ("bad", "ok")
ATTEMPTS = (1, 2, 3)
PREFIX = "c1-v1"


def _key(text: str) -> tuple[str, str]:
    return (hashlib.sha256(text.encode("utf-8")).hexdigest(), text)


def subject_order(block: int, subjects: Sequence[str]) -> list[dict[str, str]]:
    keyed = [(_key(f"{PREFIX}:subject-order:{block}:{s}"), s) for s in subjects]
    return [{"subject": s, "string": k[1], "sha256": k[0]} for k, s in sorted(keyed)]


def cell_order(subject: str, block: int) -> list[dict[str, str]]:
    keyed = [
        (_key(f"{PREFIX}:cell-order:{subject}:{block}:{p}:{v}"), p, v)
        for p in PROFILES
        for v in VARIANTS
    ]
    return [{"profile": p, "variant": v, "string": k[1], "sha256": k[0]} for k, p, v in sorted(keyed)]


def batch_of(block: int) -> str:
    return "A" if block in BATCHES["A"] else "B"


def attempt_id(subject: str, block: int, profile: str, variant: str, attempt: int) -> str:
    return f"c1v1-measured-{subject}-b{block:02d}-{profile}-{variant}-a{attempt}"


def matched_block_id(subject: str, block: int) -> str:
    return f"c1v1-{subject}-b{block:02d}"


def generate(subjects: Sequence[str]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    orders: list[dict[str, Any]] = []
    seq = 0
    for block in BLOCKS:
        sorder = subject_order(block, subjects)
        for spos, s in enumerate(sorder, 1):
            corder = cell_order(s["subject"], block)
            orders.append({"block": block, "subject_position": spos, **s, "cells": corder})
            for cpos, c in enumerate(corder, 1):
                for a in ATTEMPTS:
                    seq += 1
                    rows.append({
                        "seq": seq,
                        "batch": batch_of(block),
                        "block": block,
                        "subject_position": spos,
                        "subject": s["subject"],
                        "cell_position": cpos,
                        "profile": c["profile"],
                        "variant": c["variant"],
                        "attempt": a,
                        "attempt_id": attempt_id(s["subject"], block, c["profile"], c["variant"], a),
                        "matched_block_id": matched_block_id(s["subject"], block),
                    })
    return {"subjects": list(subjects), "rows": rows, "orders": orders, "balance": balance(orders)}


def balance(orders: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Actual order balance, reported rather than engineered (protocol 5)."""
    first_cell = Counter(f"{o['cells'][0]['profile']}/{o['cells'][0]['variant']}" for o in orders)
    r_before_l = Counter()
    for o in orders:
        pos = {(c["profile"], c["variant"]): i for i, c in enumerate(o["cells"])}
        for v in VARIANTS:
            r_before_l[f"{v}: R before L"] += int(pos[("R", v)] < pos[("L", v)])
    position = Counter((o["subject"], o["subject_position"]) for o in orders)
    return {
        "first_cell_counts": dict(sorted(first_cell.items())),
        "r_before_l_counts": dict(sorted(r_before_l.items())),
        "subject_positions": {f"{s}@{p}": n for (s, p), n in sorted(position.items())},
        "subject_blocks": len(orders),
    }


CSV_FIELDS = ["seq", "batch", "block", "subject_position", "subject", "cell_position",
              "profile", "variant", "attempt", "attempt_id", "matched_block_id"]


def to_csv(rows: Sequence[dict[str, Any]]) -> str:
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=CSV_FIELDS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def to_json(schedule: dict[str, Any]) -> str:
    return json.dumps(
        {"rule": {
            "subject_order": f"sort by SHA-256 of '{PREFIX}:subject-order:<block>:<subject>', ties by string",
            "cell_order": f"sort by SHA-256 of '{PREFIX}:cell-order:<subject>:<block>:<profile>:<variant>', ties by string",
            "batches": {k: list(v) for k, v in BATCHES.items()},
            "attempts_per_cell": len(ATTEMPTS),
         },
         "subjects": schedule["subjects"], "orders": schedule["orders"], "balance": schedule["balance"]},
        indent=2,
    ) + "\n"
