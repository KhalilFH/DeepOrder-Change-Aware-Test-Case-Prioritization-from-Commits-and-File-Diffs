"""EXPLORATORY / POST HOC signal-validity audit: shared read-only loaders.

Independent of c1_harness / e1_harness scoring code. Policy prefixes are
re-derived here from exit statuses only (protocol section 4):
  P1: attempt 1 only; nonzero exit blocks.
  P3: attempts up to and including the first zero exit (max 3); block iff all three nonzero.
Everything after a policy's stop point is a research-only suffix.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
OUT = STUDY / "signal_audit" / "out"
SUBJECTS = ["etcd5509", "etcd7492", "grpc1859", "grpc2391", "istio17860", "k8s26980"]


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_bytes().decode("utf-8").splitlines() if l.strip()]


def load_schedule() -> list[dict]:
    with open(STUDY / "schedule.csv", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_attempts(subjects=SUBJECTS) -> dict[str, dict]:
    """attempt_id -> merged record (raw ledger + annotation + schedule row)."""
    ann = {a["attempt_id"]: a for a in load_jsonl(STUDY / "measured" / "annotations.jsonl")}
    sched = {r["attempt_id"]: r for r in load_schedule()}
    out = {}
    for s in subjects:
        for prof in ("R", "L"):
            for r in load_jsonl(STUDY / "measured" / f"{s}__{prof}.jsonl"):
                aid = r["extra"]["attempt_id"]
                a = ann[aid]
                assert a["record_sha256"] == r["sha256"], aid
                sc = sched[aid]
                out[aid] = {
                    "attempt_id": aid,
                    "subject": s,
                    "profile": prof,
                    "variant": "bad" if r["version"] == "V_bad" else "ok",
                    "block": int(r["block"]),
                    "attempt": int(r["attempt"]),
                    "batch": r["extra"]["batch"],
                    "exit": r["exit_status"],
                    "timed_out_outer": r["timed_out"],
                    "elapsed_s": r["elapsed_s"],
                    "job_elapsed_s": r["extra"]["job_elapsed_s"],
                    "started_utc": r["started_utc"],
                    "ended_utc": r["ended_utc"],
                    "vm_started": r["extra"]["state"]["StartedAt"],
                    "vm_finished": r["extra"]["state"]["FinishedAt"],
                    "category": "+".join(a["categories"]),
                    "signatures": ",".join(a["signatures"]),
                    "seq": int(sc["seq"]),
                    "subject_position": int(sc["subject_position"]),
                    "cell_position": int(sc["cell_position"]),
                    "stdout": r["stdout"],
                    "stderr": r["stderr"],
                    "profile_verified": r["extra"]["profile_verified"],
                }
    return out


def cells(att: dict[str, dict]) -> dict[tuple, list[dict]]:
    """(subject, block, profile, variant) -> attempts sorted 1..3."""
    c: dict[tuple, list[dict]] = {}
    for a in att.values():
        c.setdefault((a["subject"], a["block"], a["profile"], a["variant"]), []).append(a)
    for v in c.values():
        v.sort(key=lambda x: x["attempt"])
    return c


def p1_prefix(trip):
    return trip[:1]


def p3_prefix(trip):
    pre = []
    for a in trip:
        pre.append(a)
        if a["exit"] == 0:
            break
    return pre


def blocks(prefix) -> bool:
    return all(a["exit"] != 0 for a in prefix)


def focal(a) -> bool:
    return "FOCAL_DEFECT_WITNESS" in a["category"]


def supported_block(prefix) -> int:
    """S for a defective variant: blocks and prefix contains a focal witness.
    (No UNRESOLVED/HARNESS_INVALID/nuisance labels exist in C1; asserted by callers.)"""
    return int(blocks(prefix) and any(focal(a) for a in prefix))


def write_json(name: str, obj) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / name
    p.write_text(json.dumps(obj, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8", newline="\n")
    return p


def write_csv(name: str, rows: list[dict]) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / name
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return p
