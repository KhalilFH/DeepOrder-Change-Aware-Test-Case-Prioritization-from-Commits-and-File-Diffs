"""Study-local driver: attempts, measured batches, calibration stages.

Contracts held here (execution plan, Phase 2):

- **One container at a time**, fresh per attempt, removed by its own ID, with a
  fixed 2 s pause after cleanup. No overlapping jobs.
- **Profiles are verified, not labelled.** Each session starts with a helper
  cgroup probe; each attempt's created container is inspected before start.
  Limited attempts are charged at 2 vCPUs only when both checks passed.
- **Unique identities.** One E1 ledger per stage/subject/profile; every attempt
  also carries a study-wide `attempt_id`, refused if already recorded anywhere
  in the stage. A `matched_block_id` joins R and L.
- **Measured cells always collect three attempts.** Direct policy checks stop
  early for real. Nothing is re-run automatically.
- **Budget admission before work.** A matched block reserves
  `3*(16+2)*2*(outer+32)/3600` vCPU-h; a calibration attempt reserves its own
  worst case. Refusal stops collection.
- **Stops.** Unenforced profile, cleanup failure, daemon failure, a leftover
  study container, or an unrelated running container stop everything. A
  mechanical focal match on an acceptable variant pauses that subject.
- **Resume** only after a reviewed interruption: already-recorded attempt IDs
  are never repeated, and a partly collected matched block stays incomplete.

Validity alarms read the mechanical oracle; policies never do.
"""

from __future__ import annotations

import json
import os
import secrets
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

from ledger import AttemptRecord, Ledger, read_records
from policy import FOCAL_DEFECT_WITNESS, P1, P3, reduce_block

from c1_harness import HARNESS_VERSION, STUDY_ID
from c1_harness.budget import (
    GAP_S,
    BudgetError,
    ResourceLedger,
    attempt_reservation_vcpu_h,
    block_reservation_vcpu_h,
)
from c1_harness.cards import classify_text
from c1_harness.dockerexec import ContainerSpec, DockerExecutor, ExecResult, utc_now
from c1_harness.profiles import (
    PROBE_SCRIPT,
    PROFILES,
    UNVERIFIED_CHARGE_VCPUS,
    Profile,
    evaluate_cgroup_probe,
)
from c1_harness.schedule import BATCHES, attempt_id as measured_attempt_id
from c1_harness.subjects import V_BAD, V_OK, VARIANT_OF, Subject, manifest_sha256

from ledger import GENESIS, _canonical, _digest


class StopAll(RuntimeError):
    """A condition under which the protocol stops all collection."""


# --- event log ------------------------------------------------------------------


class EventLog:
    """Append-only, hash-chained operational events (interruptions, stops, gates)."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def rows(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [json.loads(l) for l in self.path.read_text(encoding="utf-8").splitlines() if l.strip()]

    def verify(self) -> int:
        previous = GENESIS
        rows = self.rows()
        for i, row in enumerate(rows, 1):
            row = dict(row)
            recorded = row.pop("sha256")
            if row.get("prev_sha256") != previous or _digest(previous, row) != recorded:
                raise StopAll(f"event log row {i} was edited, reordered or deleted")
            previous = recorded
        return len(rows)

    def append(self, kind: str, **fields: Any) -> dict[str, Any]:
        rows = self.rows()
        previous = rows[-1]["sha256"] if rows else GENESIS
        payload = {"seq": len(rows) + 1, "utc": utc_now(), "kind": kind, **fields, "prev_sha256": previous}
        payload["sha256"] = _digest(previous, payload)
        with open(self.path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(_canonical(payload) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        return payload


# --- host checks ------------------------------------------------------------------


def windows_host_load() -> dict[str, Any]:
    """Host CPU load as Windows reports it; recorded, not gated (no frozen threshold)."""
    try:
        done = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor).LoadPercentage"],
            capture_output=True, text=True, timeout=30,
        )
        value = done.stdout.strip()
        return {"host_load_percent": int(value) if value.isdigit() else None, "source": "Win32_Processor.LoadPercentage"}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"host_load_percent": None, "source": f"unavailable: {type(exc).__name__}"}


# --- context ----------------------------------------------------------------------


@dataclass
class Context:
    study_dir: Path
    executor: DockerExecutor
    budget: ResourceLedger
    events: EventLog
    sleep: Callable[[float], None] = time.sleep
    clock: Callable[[], float] = time.monotonic
    host_load: Callable[[], dict[str, Any]] = windows_host_load
    enforcement_verified: bool = False
    session_probe: dict[str, Any] = field(default_factory=dict)


def stage_dir(ctx: Context, stage: str) -> Path:
    return ctx.study_dir / ("measured" if stage == "measured" else f"calibration/{stage}")


def ledger_path(ctx: Context, stage: str, subject: str, profile: str) -> Path:
    return stage_dir(ctx, stage) / f"{subject}__{profile}.jsonl"


def recorded_attempt_ids(ctx: Context, stage: str) -> set[str]:
    out: set[str] = set()
    for p in sorted(stage_dir(ctx, stage).glob("*.jsonl")):
        for r in read_records(p):
            aid = (r.get("extra") or {}).get("attempt_id")
            if aid:
                out.add(aid)
    return out


# --- session probe ------------------------------------------------------------------


def probe_session(ctx: Context, budget_stage: str, tag: str) -> dict[str, Any]:
    """Helper cgroup probe on both profiles at the start of every executing session."""
    alpine = ctx.executor.image_id("alpine:latest")
    results: dict[str, Any] = {}
    for pid, profile in PROFILES.items():
        if alpine is None:
            results[pid] = {"passed": False, "problems": ["alpine:latest not present"]}
            continue
        job = f"{tag}-probe-{pid}"
        ctx.budget.admit(budget_stage, job, attempt_reservation_vcpu_h(16, 60), note="session profile probe")
        try:
            spec = ContainerSpec(
                name=f"c1-probe-{pid}-{secrets.token_hex(4)}", image=alpine, workdir="/",
                argv=("-c", PROBE_SCRIPT), profile=profile, attempt_id=job, stage=budget_stage, entrypoint="sh",
            )
            res = ctx.executor.run(spec, 60)
            ctx.budget.charge(
                stage=budget_stage, job_id=job, kind_of_job="profile_probe", basis_vcpus=16,
                basis_reason="profile probe charged at 16", job_elapsed_s=res.job_elapsed_s, gap_s=0.0,
                started_utc=res.job_started_utc, ended_utc=res.job_ended_utc, attempt_elapsed_s=res.elapsed_s,
            )
        finally:
            ctx.budget.release(job, note="probe finished")
        ev = evaluate_cgroup_probe(profile, res.stdout)
        ev.update(cleanup_ok=res.cleanup_ok, profile_problems=res.profile_problems, raw=res.stdout)
        if not res.cleanup_ok:
            ev["passed"] = False
            ev.setdefault("problems", []).append("probe container cleanup not verified")
        results[pid] = ev
    passed = all(r["passed"] for r in results.values())
    ctx.enforcement_verified = passed
    ctx.session_probe = {"tag": tag, "passed": passed, "results": results}
    ctx.events.append("session_probe", tag=tag, stage=budget_stage, passed=passed,
                      summary={p: {k: r.get(k) for k in ("cpu_max", "observed_cpus", "throttled_periods", "problems")}
                               for p, r in results.items()})
    if not passed:
        raise StopAll(f"profile enforcement not verified at session start: {json.dumps(results)[:800]}")
    return ctx.session_probe


def preblock_checks(ctx: Context, label: str) -> dict[str, Any]:
    info = ctx.executor.daemon_info()
    if info is None:
        raise StopAll(f"{label}: docker daemon not reachable")
    if info.get("ncpu") != 16:
        raise StopAll(f"{label}: daemon reports {info.get('ncpu')} CPUs, not the required 16")
    leftover = ctx.executor.study_containers()
    if leftover is None or leftover:
        raise StopAll(f"{label}: study containers present or unknown: {leftover}")
    running = ctx.executor.running_containers()
    if running is None or running:
        raise StopAll(f"{label}: other containers are running on the daemon: {running}")
    load = ctx.host_load()
    return {"daemon": info, "host_load": load}


# --- one attempt ------------------------------------------------------------------


def charge_basis(ctx: Context, profile: Profile, res: ExecResult) -> tuple[int, str]:
    if profile.cpu_quota == 0:
        return profile.allocated_vcpus, "reference profile: 16 allocated vCPUs"
    if ctx.enforcement_verified and res.profile_verified:
        return profile.allocated_vcpus, "limited profile, enforcement verified (session probe + container inspect)"
    return UNVERIFIED_CHARGE_VCPUS, "limited profile NOT verified: charged at 16"


def run_attempt(
    ctx: Context,
    *,
    stage: str,
    budget_stage: str,
    subject: Subject,
    profile: Profile,
    version: str,
    image_id: str,
    block: int,
    attempt: int,
    attempt_id: str,
    matched_block_id: str | None,
    ledger: Ledger,
    extra: dict[str, Any] | None = None,
    reserve: bool = True,
) -> tuple[dict[str, Any], ExecResult]:
    """Execute one attempt, append it, pause, charge. Raises StopAll on a stop condition."""
    manifest = subject.execution_manifest(profile, stage)
    if image_id not in subject.images.values():
        raise StopAll(f"{attempt_id}: image {image_id} is not one of {subject.sid}'s frozen images")
    variant = "bad" if version == V_BAD else "ok"
    name = f"c1-{stage[:4]}-{subject.sid}-{profile.pid}-{variant}-b{block}-a{attempt}-{secrets.token_hex(3)}"
    spec = ContainerSpec(
        name=name, image=image_id, workdir=subject.workdir, argv=subject.argv,
        profile=profile, attempt_id=attempt_id, stage=stage,
    )
    worst = attempt_reservation_vcpu_h(16 if profile.cpu_quota == 0 else UNVERIFIED_CHARGE_VCPUS, subject.outer_timeout_s)
    if reserve:
        ctx.budget.admit(budget_stage, attempt_id, worst, note="attempt worst case")
    try:
        res = ctx.executor.run(spec, subject.outer_timeout_s)
        record = AttemptRecord(
            episode=subject.sid,
            block=block,
            version=version,
            attempt=attempt,
            exit_status=res.exit_status,
            started_utc=res.started_utc or res.job_started_utc,
            ended_utc=res.ended_utc or res.job_ended_utc,
            elapsed_s=res.elapsed_s if res.elapsed_s is not None else 0.0,
            timed_out=res.timed_out,
            condition=profile.pid,
            seed=None,
            manifest_sha256=manifest_sha256(manifest),
            runner_version=HARNESS_VERSION,
            stdout=res.stdout,
            stderr=res.stderr,
            extra={
                "study_id": STUDY_ID,
                "stage": stage,
                "attempt_id": attempt_id,
                "matched_block_id": matched_block_id,
                "profile": profile.pid,
                "image_id": image_id,
                "availability_utc": res.job_ended_utc,
                "session_probe_passed": ctx.enforcement_verified,
                **(extra or {}),
                **res.extra(),
            },
        )
        row = ledger.append(record)
        gap_t0 = ctx.clock()
        ctx.sleep(GAP_S)
        gap = max(round(ctx.clock() - gap_t0, 6), GAP_S)
        basis, reason = charge_basis(ctx, profile, res)
        ctx.budget.charge(
            stage=budget_stage, job_id=attempt_id, kind_of_job=f"attempt:{stage}", basis_vcpus=basis,
            basis_reason=reason, job_elapsed_s=res.job_elapsed_s, gap_s=gap,
            started_utc=res.job_started_utc, ended_utc=res.job_ended_utc, attempt_elapsed_s=res.elapsed_s,
        )
    finally:
        if reserve:
            ctx.budget.release(attempt_id, note="attempt finished")

    if res.profile_problems:
        ctx.events.append("stop_all", reason="profile verification failed", attempt_id=attempt_id, problems=res.profile_problems)
        raise StopAll(f"{attempt_id}: profile not enforced: {res.profile_problems}")
    if not res.cleanup_ok:
        ctx.events.append("stop_all", reason="cleanup failure", attempt_id=attempt_id, cleanup=res.cleanup)
        raise StopAll(f"{attempt_id}: container cleanup not verified: {res.cleanup}")
    if res.container_id is None or (res.error and res.error.startswith("docker create failed")):
        ctx.events.append("stop_all", reason="daemon/create failure", attempt_id=attempt_id, error=res.error)
        raise StopAll(f"{attempt_id}: {res.error}")
    return row, res


# --- measured batches ------------------------------------------------------------------


def _subject_state(ctx: Context) -> dict[str, str]:
    """Subjects paused or stopped by earlier events (validity alarm, gate A)."""
    state: dict[str, str] = {}
    for e in ctx.events.rows():
        if e["kind"] in ("subject_paused", "subject_stopped"):
            state[e["subject"]] = e["kind"]
    return state


def interrupted_sessions(ctx: Context) -> list[str]:
    open_: dict[str, dict[str, Any]] = {}
    for e in ctx.events.rows():
        if e["kind"] == "session_start":
            open_[e["session"]] = e
        elif e["kind"] == "session_end":
            open_.pop(e["session"], None)
    return sorted(open_)


def plan_batch(schedule_rows: Sequence[dict[str, Any]], batch: str) -> list[tuple[int, str, list[dict[str, Any]]]]:
    """[(block, subject, rows)] in scheduled order."""
    out: list[tuple[int, str, list[dict[str, Any]]]] = []
    for row in schedule_rows:
        if row["batch"] != batch:
            continue
        key = (int(row["block"]), row["subject"])
        if not out or (out[-1][0], out[-1][1]) != key:
            out.append((key[0], key[1], []))
        out[-1][2].append(row)
    return out


def run_measured_batch(
    ctx: Context,
    batch: str,
    subjects: dict[str, Subject],
    schedule_rows: Sequence[dict[str, Any]],
    *,
    resume_review: str | None = None,
    dry_run: bool = False,
    log: Callable[[str], None] = print,
) -> dict[str, Any]:
    if batch not in BATCHES:
        raise StopAll(f"unknown batch {batch!r}")
    stage = "measured"
    done = recorded_attempt_ids(ctx, stage)
    interrupted = interrupted_sessions(ctx)
    plan = plan_batch(schedule_rows, batch)
    partial = [(b, s) for b, s, rows in plan if 0 < sum(r["attempt_id"] in done for r in rows) < len(rows)]
    batch_started = any(r["attempt_id"] in done for _, _, rows in plan for r in rows)
    if (interrupted or partial or batch_started) and not resume_review:
        raise StopAll(
            f"batch {batch} has recorded work (interrupted sessions {interrupted}, partial blocks {partial}, "
            f"started={batch_started}); resuming requires --resume-review with the review note"
        )
    if batch == "B":
        gates = [e for e in ctx.events.rows() if e["kind"] == "gate_a"]
        if not gates or not gates[-1].get("integrity_passed"):
            raise StopAll("batch B requires a recorded passing batch-A integrity/cost gate (gate-a)")
    state = _subject_state(ctx)

    if dry_run:
        lines = []
        for block, sid, rows in plan:
            s = subjects[sid]
            status = ("excluded" if not s.enrolled else state.get(sid)
                      or ("done" if all(r["attempt_id"] in done for r in rows) else
                          "incomplete (kept missing)" if any(r["attempt_id"] in done for r in rows) else "to run"))
            res = block_reservation_vcpu_h(s.outer_timeout_s)
            lines.append({"block": block, "subject": sid, "status": status, "reservation_vcpu_h": round(res, 4),
                          "cells": [f"{r['profile']}/{r['variant']}" for r in rows[::3]],
                          "first_docker_create": ContainerSpec(
                              name="<unique>", image=s.images[VARIANT_OF[rows[0]['variant']]], workdir=s.workdir,
                              argv=s.argv, profile=PROFILES[rows[0]["profile"]], attempt_id=rows[0]["attempt_id"],
                              stage=stage).create_argv()})
        return {"dry_run": True, "batch": batch, "plan": lines, "budget": ctx.budget.summary(),
                "interrupted_sessions": interrupted, "partial_blocks": partial}

    session = f"measured-{batch}-{utc_now()}"
    ctx.events.append("session_start", session=session, batch=batch, resume_review=resume_review,
                      interrupted_before=interrupted, partial_before=partial)
    for b, s in partial:
        ctx.events.append("block_incomplete", session=session, block=b, subject=s,
                          note="partly collected matched block left incomplete; unrun cells stay missing")
    summary: dict[str, Any] = {"session": session, "blocks": []}
    try:
        # Daemon, leftover and foreign-container checks come before even the probe helpers start.
        preblock_checks(ctx, f"batch {batch} session start")
        probe_session(ctx, "measured", f"{session}")
        for block in BATCHES[batch]:
            pre = preblock_checks(ctx, f"batch {batch} block {block}")
            ctx.events.append("block_start", session=session, block=block, **pre)
            for b, sid, rows in plan:
                if b != block:
                    continue
                s = subjects[sid]
                recorded = [r["attempt_id"] in done for r in rows]
                if not s.enrolled or sid in state:
                    ctx.events.append("subject_block_skipped", session=session, block=block, subject=sid,
                                      reason="not enrolled" if not s.enrolled else state[sid])
                    continue
                if any(recorded):
                    continue  # complete, or partial and already marked incomplete
                rid = f"{session}:{rows[0]['matched_block_id']}"
                amount = block_reservation_vcpu_h(s.outer_timeout_s)
                try:
                    ctx.budget.admit("measured", rid, amount, note="matched block worst case")
                except BudgetError as exc:
                    ctx.events.append("stop_all", session=session, reason="budget", detail=str(exc))
                    raise StopAll(f"budget: {exc}") from exc
                paused = False
                try:
                    for r in rows:
                        profile = PROFILES[r["profile"]]
                        version = VARIANT_OF[r["variant"]]
                        path = ledger_path(ctx, stage, sid, r["profile"])
                        with Ledger(path) as led:
                            row, res = run_attempt(
                                ctx, stage=stage, budget_stage="measured", subject=s, profile=profile,
                                version=version, image_id=s.images[version], block=block, attempt=int(r["attempt"]),
                                attempt_id=r["attempt_id"], matched_block_id=r["matched_block_id"], ledger=led,
                                extra={"scheduled_seq": int(r["seq"]), "batch": batch, "cell": f"{r['profile']}/{r['variant']}",
                                       "session": session},
                                reserve=False,
                            )
                        log(f"{r['attempt_id']} exit={res.exit_status} {res.elapsed_s}s")
                        if version == V_OK and FOCAL_DEFECT_WITNESS in classify_text(sid, res.exit_status, res.stdout, res.stderr):
                            ctx.events.append("subject_paused", session=session, subject=sid, attempt_id=r["attempt_id"],
                                              reason="mechanical focal match on the acceptable variant: pair-validity review required")
                            paused = True
                            break
                finally:
                    ctx.budget.release(rid, note="matched block finished")
                ctx.events.append("subject_block_end", session=session, block=block, subject=sid,
                                  complete=not paused, paused=paused)
                summary["blocks"].append({"block": block, "subject": sid, "complete": not paused})
                if paused:
                    state[sid] = "subject_paused"
    except StopAll as exc:
        ctx.events.append("session_end", session=session, outcome="stopped", reason=str(exc)[:1000])
        raise
    ctx.events.append("session_end", session=session, outcome="completed")
    return summary


# --- calibration stages ------------------------------------------------------------------


def cell_ids(stage: str, subject: str, profile: str, variant: str, attempt: int, trace: str = "") -> str:
    return f"c1v1-{stage}-{subject}-{trace + '-' if trace else ''}{profile}-{variant}-a{attempt}"


def run_smoke(ctx: Context, subjects: dict[str, Subject], plan: Sequence[dict[str, Any]], log=print) -> list[dict[str, Any]]:
    """One attempt per enrolled subject/profile/variant, in the saved plan order."""
    done = recorded_attempt_ids(ctx, "smoke")
    out = []
    for step in plan:
        if step["attempt_id"] in done:
            raise StopAll(f"{step['attempt_id']} already recorded; smoke is never repeated")
        s = subjects[step["subject"]]
        profile = PROFILES[step["profile"]]
        version = VARIANT_OF[step["variant"]]
        with Ledger(ledger_path(ctx, "smoke", s.sid, profile.pid)) as led:
            row, res = run_attempt(
                ctx, stage="smoke", budget_stage="validation", subject=s, profile=profile, version=version,
                image_id=s.images[version], block=1, attempt=1, attempt_id=step["attempt_id"],
                matched_block_id=None, ledger=led, extra={"plan_position": step["position"]},
            )
        log(f"{step['attempt_id']} exit={res.exit_status} elapsed={res.elapsed_s}s timed_out={res.timed_out}")
        out.append({"attempt_id": step["attempt_id"], "seq": row["seq"], "exit": res.exit_status})
    return out


def run_identity(ctx: Context, subject: Subject, plan: Sequence[dict[str, Any]], log=print) -> list[dict[str, Any]]:
    """Same acceptable image in both nominal slots; never evidence of revision attribution."""
    done = recorded_attempt_ids(ctx, "identity")
    out = []
    for step in plan:
        if step["attempt_id"] in done:
            raise StopAll(f"{step['attempt_id']} already recorded")
        profile = PROFILES[step["profile"]]
        with Ledger(ledger_path(ctx, "identity", subject.sid, profile.pid)) as led:
            row, res = run_attempt(
                ctx, stage="identity", budget_stage="validation", subject=subject, profile=profile,
                version=VARIANT_OF[step["slot"]], image_id=subject.images[V_OK], block=1, attempt=step["attempt"],
                attempt_id=step["attempt_id"], matched_block_id=None, ledger=led,
                extra={"identity_control": True, "slot": step["slot"], "slot_image": "V_ok image in both slots",
                       "plan_position": step["position"]},
            )
        log(f"{step['attempt_id']} exit={res.exit_status} elapsed={res.elapsed_s}s")
        out.append({"attempt_id": step["attempt_id"], "exit": res.exit_status})
    return out


def run_direct(ctx: Context, subject: Subject, plan: Sequence[dict[str, Any]], log=print) -> list[dict[str, Any]]:
    """Each profile x variant x P1/P3 once, with real early stopping."""
    done = recorded_attempt_ids(ctx, "direct")
    out = []
    for step in plan:
        profile = PROFILES[step["profile"]]
        version = VARIANT_OF[step["variant"]]
        budget = 1 if step["policy"] == P1 else 3
        executed: list[int | None] = []
        ids = []
        for attempt in range(1, budget + 1):
            aid = f"{step['trace_id']}-a{attempt}"
            if aid in done:
                raise StopAll(f"{aid} already recorded")
            with Ledger(ledger_path(ctx, "direct", subject.sid, profile.pid)) as led:
                row, res = run_attempt(
                    ctx, stage="direct", budget_stage="validation", subject=subject, profile=profile,
                    version=version, image_id=subject.images[version], block=step["block"], attempt=attempt,
                    attempt_id=aid, matched_block_id=None, ledger=led,
                    extra={"direct_policy": step["policy"], "trace_id": step["trace_id"], "plan_position": step["position"]},
                )
            executed.append(res.exit_status)
            ids.append(aid)
            if res.exit_status == 0:
                break  # accept-on-pass: remaining attempts are never run
        decision = reduce_block(step["policy"], executed)
        # Replay: the reducer over the trace's own prefix as re-read from the ledger file.
        stored = sorted(
            (r for r in read_records(ledger_path(ctx, "direct", subject.sid, profile.pid))
             if (r.get("extra") or {}).get("trace_id") == step["trace_id"]),
            key=lambda r: r["attempt"],
        )
        replayed = reduce_block(step["policy"], [r["exit_status"] for r in stored])
        stop_ok = (
            (step["policy"] == P1 and len(executed) == 1)
            or (step["policy"] == P3 and (executed[-1] == 0 or len(executed) == 3)
                and all(x not in (0,) for x in executed[:-1]))
        )
        result = {
            "trace_id": step["trace_id"], "policy": step["policy"], "profile": profile.pid, "variant": step["variant"],
            "executed": executed, "attempt_ids": ids, "direct_decision": decision.final_status,
            "replayed_decision": replayed.final_status, "decision_match": decision == replayed,
            "ledger_prefix": [r["exit_status"] for r in stored],
            "stopping_rule_respected": stop_ok,
        }
        ctx.events.append("direct_trace", **result)
        log(json.dumps(result))
        out.append(result)
    return out


HELPER_TIMEOUT_S = 10


def run_helpers(ctx: Context, log=print) -> list[dict[str, Any]]:
    """Two fresh helper containers per profile: marker write, then marker-absence check + timeout."""
    alpine = ctx.executor.image_id("alpine:latest")
    if alpine is None:
        raise StopAll("alpine:latest not present for helper checks")
    out = []
    scripts = {
        "marker": "touch /tmp/c1_marker && echo WROTE $(hostname)",
        "check_timeout": "if [ -e /tmp/c1_marker ]; then echo LEAKED; else echo ABSENT; fi; echo HOST $(hostname); sleep 600",
    }
    for pid, profile in PROFILES.items():
        for step, script in scripts.items():
            job = f"c1v1-helpers-{pid}-{step}"
            ctx.budget.admit("validation", job, attempt_reservation_vcpu_h(16, HELPER_TIMEOUT_S), note="helper worst case")
            try:
                spec = ContainerSpec(
                    name=f"c1-help-{pid}-{step}-{secrets.token_hex(3)}", image=alpine, workdir="/",
                    argv=("-c", script), profile=profile, attempt_id=job, stage="helpers", entrypoint="sh",
                )
                res = ctx.executor.run(spec, HELPER_TIMEOUT_S)
                ctx.sleep(GAP_S)
                basis, reason = charge_basis(ctx, profile, res)
                ctx.budget.charge(
                    stage="validation", job_id=job, kind_of_job="helper:isolation_timeout", basis_vcpus=basis,
                    basis_reason=reason, job_elapsed_s=res.job_elapsed_s, gap_s=GAP_S,
                    started_utc=res.job_started_utc, ended_utc=res.job_ended_utc, attempt_elapsed_s=res.elapsed_s,
                )
            finally:
                ctx.budget.release(job, note="helper finished")
            result = {
                "job": job, "profile": pid, "step": step, "exit": res.exit_status, "timed_out": res.timed_out,
                "elapsed_s": res.elapsed_s, "stdout": res.stdout.strip(), "cleanup": res.cleanup,
                "cleanup_ok": res.cleanup_ok, "profile_verified": res.profile_verified,
                "profile_problems": res.profile_problems, "inspect": res.inspect,
            }
            if step == "marker":
                result["passed"] = res.exit_status == 0 and "WROTE" in res.stdout and res.cleanup_ok
            else:
                result["passed"] = (res.timed_out and "ABSENT" in res.stdout and "LEAKED" not in res.stdout
                                    and res.cleanup_ok)
            ctx.events.append("helper_check", **{k: v for k, v in result.items() if k != "inspect"})
            log(json.dumps({k: result[k] for k in ("job", "exit", "timed_out", "elapsed_s", "stdout", "cleanup_ok", "passed")}))
            out.append(result)
    return out


def calibration_plan(subjects: dict[str, Subject]) -> dict[str, Any]:
    """The fixed calibration plan, persisted before any calibration outcome exists."""
    import hashlib

    def order(stage: str, sid: str, cells: Iterable[tuple[str, str]]) -> list[tuple[str, str]]:
        return [c for _, c in sorted((hashlib.sha256(f"c1-v1:{stage}-order:{sid}:{p}:{v}".encode()).hexdigest(), (p, v))
                                     for p, v in cells)]

    enrolled = [s for s in subjects.values() if s.enrolled]
    smoke = []
    for s in enrolled:
        for p, v in order("smoke", s.sid, [(p, v) for p in ("R", "L") for v in ("bad", "ok")]):
            smoke.append({"position": len(smoke) + 1, "subject": s.sid, "profile": p, "variant": v,
                          "attempt_id": cell_ids("smoke", s.sid, p, v, 1)})
    first = enrolled[0]
    identity = []
    for p in ("R", "L"):
        for slot in ("bad", "ok"):
            for a in (1, 2, 3):
                identity.append({"position": len(identity) + 1, "subject": first.sid, "profile": p, "slot": slot,
                                 "attempt": a, "attempt_id": cell_ids("identity", first.sid, p, f"slot{slot}", a)})
    direct = []
    for p in ("R", "L"):
        for v in ("bad", "ok"):
            for pol in (P1, P3):
                n = len(direct) + 1
                direct.append({"position": n, "subject": first.sid, "profile": p, "variant": v, "policy": pol,
                               "block": 100 + n, "trace_id": f"c1v1-direct-{first.sid}-{p}-{v}-{pol}"})
    return {
        "study_id": STUDY_ID,
        "first_structurally_ready_subject": first.sid,
        "smoke": smoke,
        "identity": identity,
        "direct": direct,
        "helpers": [{"profile": p, "step": s} for p in ("R", "L") for s in ("marker", "check_timeout")],
        "helper_timeout_s": HELPER_TIMEOUT_S,
        "max_primitive_attempts": {"smoke": len(smoke), "identity": len(identity),
                                   "direct": sum(1 if d["policy"] == P1 else 3 for d in direct), "helpers": 4},
    }
