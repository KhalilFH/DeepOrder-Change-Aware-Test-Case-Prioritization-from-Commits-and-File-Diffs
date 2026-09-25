"""Replay every surviving historical log through the C1 cards.

Old observations are oracle-validation inputs here, never C1 data. Three sources:

1. Q0 counted attempts (`task5_artifacts/<subject>`): raw log + recorded exit
   code + recorded classification. Agreement is checked category by category.
2. Exploratory/timing logs (no recorded exit code): only signature matches are
   reported, with the version they came from. Any focal match on an acceptable
   variant or on a known non-focal harness failure (grpc1859's expired
   certificates) is a disagreement.
3. E1 ledgers: every record's mechanical category is recomputed with the C1
   registry and compared with E1's stored mechanical annotation.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from oracle import classify, gather

from c1_harness import REPO_ROOT
from c1_harness.cards import card_for

OLD = REPO_ROOT / "research_runs" / "ci_sensitivity_2026_09"
T5 = OLD / "task5_artifacts"

RECORDED = {"FOCAL_DEFECT_WITNESS_A": "FOCAL_DEFECT_WITNESS", "FOCAL_DEFECT_WITNESS_B": "FOCAL_DEFECT_WITNESS"}

# etcd7492's Q0 results.csv has no classification column; the restoration
# record (Step 4) states V_bad attempts 2 and 11 were focal and every other of
# the 40 counted attempts PASS.
ETCD7492_FOCAL = {("vbad", 2), ("vbad", 11)}


def _read(path: Path) -> str:
    return path.read_bytes().decode("utf-8", errors="replace")


def _signatures(subject: str, text: str) -> list[str]:
    ev = gather(text, "", 1)
    return [s.sid for s in card_for(subject).signatures if s.matches(ev)]


def q0_counted() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def add(subject: str, version: str, attempt: int, exit_code: int, log: Path, recorded: str) -> None:
        text = _read(log)
        got = sorted(classify(card_for(subject), exit_code, text, "").categories)
        want = RECORDED.get(recorded, recorded)
        rows.append({
            "source": "q0_counted", "subject": subject, "version": version, "attempt": attempt,
            "log": str(log.relative_to(REPO_ROOT)).replace("\\", "/"), "exit": exit_code,
            "recorded": recorded, "c1": "+".join(got), "agree": got == [want],
        })

    for r in csv.DictReader(open(T5 / "etcd5509/attempts/results_final.csv", encoding="utf-8")):
        add("etcd5509", r["version"], int(r["attempt"]), int(r["exit_code"]),
            T5 / f"etcd5509/attempts/{r['version']}_attempt_{r['attempt']}.log", r["classification"])
    for r in csv.DictReader(open(T5 / "etcd7492/build/results.csv", encoding="utf-8")):
        rec = "FOCAL_DEFECT_WITNESS" if (r["version"], int(r["attempt"])) in ETCD7492_FOCAL else "PASS"
        add("etcd7492", r["version"], int(r["attempt"]), int(r["exit_code"]), T5 / "etcd7492/build" / r["logfile"], rec)
    for subject in ("grpc1859", "grpc2391", "istio17860", "k8s26980"):
        for r in csv.DictReader(open(T5 / subject / "run/results.csv", encoding="utf-8")):
            add(subject, r["version"], int(r["attempt"]), int(r["exit"]),
                T5 / subject / f"run/logs/{r['version']}_{int(r['attempt']):02d}.log", r["classification"])
    return rows


def uncounted() -> list[dict[str, Any]]:
    """Logs without a recorded exit code: signature matches only."""
    groups: list[tuple[str, str, str, str]] = []  # subject, glob, version, expectation
    groups += [("etcd5509", "etcd5509/attempts/smoke_bug.log", "bad", "exploratory")]
    groups += [("etcd7492", "etcd7492/build/attempts/exploratory_bug*.log", "bad", "exploratory")]
    groups += [("etcd7492", "etcd7492/build/attempts/exploratory_fix*.log", "ok", "must not match")]
    groups += [("grpc1859", "grpc1859/timing/bug_timing_*.log", "bad", "expired-certificate timeout: must not match")]
    groups += [("grpc1859", "grpc1859/timing/fix_timing_*.log", "ok", "expired-certificate timeout: must not match")]
    groups += [("grpc1859", "grpc1859/timing/*bug*clear*.log", "bad", "exploratory")]
    groups += [("grpc1859", "grpc1859/timing/*fix*clear*.log", "ok", "must not match")]
    for s in ("grpc2391", "istio17860", "k8s26980"):
        groups += [(s, f"{s}/timing/probe_bug_*.log", "bad", "exploratory"), (s, f"{s}/timing/probe_fix_*.log", "ok", "must not match")]
    rows = []
    seen: set[Path] = set()
    for subject, pattern, version, expectation in groups:
        for log in sorted(T5.glob(pattern)):
            if log in seen:
                continue
            seen.add(log)
            sigs = _signatures(subject, _read(log))
            must_not = expectation.startswith("must not") or "must not match" in expectation
            rows.append({
                "source": "uncounted", "subject": subject, "version": version,
                "log": str(log.relative_to(REPO_ROOT)).replace("\\", "/"),
                "expectation": expectation, "signatures": sigs,
                "agree": (not sigs) if must_not else True,
            })
    return rows


def e1_ledgers() -> list[dict[str, Any]]:
    rows = []
    for ann_path in sorted(OLD.glob("e1/**/annotations.jsonl")):
        led_path = ann_path.with_name("attempts.jsonl")
        if not led_path.exists():
            continue
        records = {json.loads(l)["sha256"]: json.loads(l) for l in led_path.read_text(encoding="utf-8").splitlines() if l.strip()}
        for line in ann_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            a = json.loads(line)
            rec = records[a["record_sha256"]]
            # E1 controls use their own episode names; the card is the real subject's.
            subject = rec["episode"]
            for known in ("etcd5509", "etcd7492", "grpc1859"):
                if known in subject:
                    subject = known
            got = sorted(classify(card_for(subject), rec["exit_status"], rec["stdout"], rec["stderr"]).categories)
            want = a.get("mechanical", a["categories"])
            rows.append({
                "source": "e1_ledger", "subject": subject, "episode": rec["episode"],
                "ledger": str(led_path.relative_to(REPO_ROOT)).replace("\\", "/"),
                "record_seq": rec["seq"], "version": rec["version"],
                "e1_mechanical": "+".join(want), "c1": "+".join(got), "agree": got == sorted(want),
            })
    return rows


def replay() -> dict[str, Any]:
    parts = {"q0_counted": q0_counted(), "uncounted": uncounted(), "e1_ledgers": e1_ledgers()}
    summary: dict[str, Any] = {}
    for name, rows in parts.items():
        by_subject: dict[str, dict[str, int]] = {}
        for r in rows:
            s = by_subject.setdefault(r["subject"], {"logs": 0, "agree": 0, "disagree": 0})
            s["logs"] += 1
            s["agree" if r["agree"] else "disagree"] += 1
        summary[name] = by_subject
    focal_positive = {}
    for r in parts["q0_counted"] + parts["e1_ledgers"]:
        if "FOCAL_DEFECT_WITNESS" in r["c1"]:
            focal_positive[r["subject"]] = focal_positive.get(r["subject"], 0) + 1
    for r in parts["uncounted"]:
        if r["signatures"]:
            focal_positive[r["subject"]] = focal_positive.get(r["subject"], 0) + 1
    return {
        "summary": summary,
        "focal_positive_logs_by_subject": focal_positive,
        "disagreements": [r for rows in parts.values() for r in rows if not r["agree"]],
        "rows": parts,
    }
