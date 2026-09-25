"""C1 command line. Run from the repository root: `python -m c1_harness.cli <command>`.

Commands that start containers say STARTS CONTAINERS in their help:
`prepare-checks`, `probe-profiles`, `calibrate`, `run-batch`. Every other
command (`verify-design`, `env-manifest`, `schedule`, `calibration-plan`,
`annotate`, `analyze`, `gate-a`, `dry-run`, `preflight`, `write-launch-freeze`,
`verify-launch`, `budget`, `agent-time`) never starts a container.
"""

from __future__ import annotations

import argparse
import csv
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

from c1_harness import HARNESS_VERSION, REPO_ROOT, STUDY_DIR, STUDY_ID
from c1_harness.budget import STAGE_CAPS, BudgetError, ResourceLedger, block_reservation_vcpu_h
from c1_harness.dockerexec import DockerExecutor, utc_now

RESOURCE_LEDGER = STUDY_DIR / "resources" / "resource_ledger.jsonl"
EVENTS = STUDY_DIR / "events.jsonl"
PREP_DIR = STUDY_DIR / "prep"
SCHEDULE_CSV = STUDY_DIR / "schedule.csv"
SCHEDULE_JSON = STUDY_DIR / "schedule.json"
CAL_PLAN = STUDY_DIR / "calibration" / "plan.json"


def _print(data: Any) -> None:
    print(json.dumps(data, indent=2, sort_keys=True, default=str))


def _ctx():
    from c1_harness.driver import Context, EventLog

    return Context(study_dir=STUDY_DIR, executor=DockerExecutor(), budget=ResourceLedger(RESOURCE_LEDGER),
                   events=EventLog(EVENTS))


def _subjects():
    from c1_harness.subjects import load_subjects

    return load_subjects()


def _schedule_rows() -> list[dict[str, Any]]:
    with open(SCHEDULE_CSV, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


# --- preparation ------------------------------------------------------------------------


def cmd_prepare_checks(args: argparse.Namespace) -> int:
    """STARTS CONTAINERS: one read-only `sh` helper per subject image."""
    from c1_harness.prepare import run_image_checks, write_json

    PREP_DIR.mkdir(parents=True, exist_ok=True)
    started = utc_now()
    results = run_image_checks(DockerExecutor(), ResourceLedger(RESOURCE_LEDGER), PREP_DIR)
    write_json(PREP_DIR / "image_checks.json", {"started_utc": started, "ended_utc": utc_now(), "results": results})
    for subject, r in results.items():
        ev = r["evaluation"]
        print(f"{subject:11} {'PASS' if ev['passed'] else 'FAIL'}")
        for c in ev["checks"]:
            if not c["passed"]:
                print(f"    FAILED {c['check']}: {json.dumps(c['detail'])[:300]}")
    return 0 if all(r["evaluation"]["passed"] for r in results.values()) else 1


def cmd_probe_profiles(args: argparse.Namespace) -> int:
    """STARTS CONTAINERS: alpine cgroup and Go-toolchain probes on both profiles."""
    from c1_harness.prepare import run_profile_probes, write_json

    started = utc_now()
    out = run_profile_probes(DockerExecutor(), ResourceLedger(RESOURCE_LEDGER), args.stage, args.tag)
    out.update(started_utc=started, ended_utc=utc_now(), stage=args.stage)
    path = STUDY_DIR / args.out
    write_json(path, out)
    for kind in ("cgroup", "go"):
        for key, ev in out[kind].items():
            shown = {k: ev.get(k) for k in ("cpu_max", "observed_cpus", "throttled_periods", "gomaxprocs", "numcpu", "go_version") if k in ev}
            print(f"{kind:6} {key:10} {'PASS' if ev['passed'] else 'FAIL'} {shown} {ev.get('problems') or ''}")
    print(f"profile probes {'PASSED' if out['passed'] else 'FAILED'} -> {path}")
    return 0 if out["passed"] else 1


def cmd_probe_clock(args: argparse.Namespace) -> int:
    """STARTS CONTAINERS: two helper clock-rate probes (VM clocks vs host monotonic)."""
    from c1_harness.prepare import run_clock_probe, write_json

    out = run_clock_probe(DockerExecutor(), ResourceLedger(RESOURCE_LEDGER), args.stage, args.tag)
    out["observed_utc"] = utc_now()
    write_json(STUDY_DIR / args.out, out)
    _print(out)
    return 0


def cmd_env_manifest(args: argparse.Namespace) -> int:
    """Read-only: daemon info, host facts, toolchain, probe references."""
    ex = DockerExecutor()
    host: dict[str, Any] = {}
    try:
        done = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "$c=Get-CimInstance Win32_Processor; $o=Get-CimInstance Win32_OperatingSystem; "
             "\"$($c.Name)|$($c.NumberOfLogicalProcessors)|$($c.NumberOfCores)|$($o.Caption)|$($o.Version)|$($o.TotalVisibleMemorySize)\""],
            capture_output=True, text=True, timeout=60)
        name, logical, cores, caption, version, mem_kb = done.stdout.strip().split("|")
        host = {"cpu": name.strip(), "logical_cpus": int(logical), "cores": int(cores), "os": caption, "os_version": version,
                "memory_kib": int(mem_kb)}
    except Exception as exc:  # noqa: BLE001 - facts are optional, recorded as unknown
        host = {"error": f"{type(exc).__name__}: {exc}"}
    ver = subprocess.run(["docker", "version", "--format", "{{json .}}"], capture_output=True, text=True, timeout=60)
    try:
        dv = json.loads(ver.stdout)
        docker_version = {"client": dv["Client"]["Version"], "server": dv["Server"]["Version"],
                          "platform": dv["Server"].get("Platform", {}).get("Name"), "api": dv["Server"]["ApiVersion"]}
    except Exception:  # noqa: BLE001
        docker_version = {"raw": ver.stdout.strip()[:500]}
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=REPO_ROOT).stdout.strip()
    probes = {p.name: json.loads(p.read_text(encoding="utf-8")).get("passed") for p in sorted(PREP_DIR.glob("profile_probe_*.json"))}
    manifest = {
        "study_id": STUDY_ID,
        "artifact": "c1_environment_manifest_v1",
        "observed_utc": utc_now(),
        "host": host,
        "docker": {**(ex.daemon_info() or {}), **docker_version, "context": "desktop-linux (Windows host client)"},
        "driver": {"python": platform.python_version(), "platform": platform.platform(), "harness_version": HARNESS_VERSION},
        "repository": {"head": head, "branch": "research/revival-2026",
                       "note": "C1 implementation files are uncommitted; FREEZE.sha256 binds their LF-normalized hashes"},
        "profiles": {pid: p.as_manifest() for pid, p in __import__("c1_harness.profiles", fromlist=["PROFILES"]).PROFILES.items()},
        "profile_probe_files": probes,
        "memory_limit": "none on either profile (identical)",
        "network": "default bridge on either profile (identical)",
        "cpu_affinity": "none on either profile; cpuset.cpus.effective 0-15 observed on both",
    }
    (STUDY_DIR / "environment_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    _print(manifest)
    return 0


# --- schedule and plans ------------------------------------------------------------------


def _generated_schedule() -> tuple[str, str]:
    from c1_harness.schedule import generate, to_csv, to_json

    enrolled = [s.sid for s in _subjects().values() if s.enrolled]
    sched = generate(enrolled)
    return to_csv(sched["rows"]), to_json(sched)


def cmd_schedule(args: argparse.Namespace) -> int:
    csv_text, json_text = _generated_schedule()
    if args.write:
        if SCHEDULE_CSV.exists() and not args.replace:
            print(f"{SCHEDULE_CSV} exists; refusing to overwrite (the schedule is never redrawn)", file=sys.stderr)
            return 2
        SCHEDULE_CSV.write_text(csv_text, encoding="utf-8", newline="\n")
        SCHEDULE_JSON.write_text(json_text, encoding="utf-8", newline="\n")
        print(f"wrote {SCHEDULE_CSV} ({csv_text.count(chr(10)) - 1} rows) and {SCHEDULE_JSON}")
        return 0
    ok = SCHEDULE_CSV.exists() and SCHEDULE_CSV.read_bytes().replace(b"\r\n", b"\n") == csv_text.encode("utf-8") \
        and SCHEDULE_JSON.read_bytes().replace(b"\r\n", b"\n") == json_text.encode("utf-8")
    print("schedule regenerates identically" if ok else "SCHEDULE MISMATCH: regenerated schedule differs from the saved one")
    return 0 if ok else 1


def cmd_calibration_plan(args: argparse.Namespace) -> int:
    from c1_harness.driver import calibration_plan

    text = json.dumps(calibration_plan(_subjects()), indent=2) + "\n"
    if args.write:
        if CAL_PLAN.exists():
            print(f"{CAL_PLAN} exists; refusing to overwrite", file=sys.stderr)
            return 2
        CAL_PLAN.parent.mkdir(parents=True, exist_ok=True)
        CAL_PLAN.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {CAL_PLAN}")
        return 0
    ok = CAL_PLAN.exists() and CAL_PLAN.read_bytes().replace(b"\r\n", b"\n") == text.encode("utf-8")
    print("calibration plan regenerates identically" if ok else "CALIBRATION PLAN MISMATCH")
    return 0 if ok else 1


# --- calibration ------------------------------------------------------------------------------


def cmd_calibrate(args: argparse.Namespace) -> int:
    """STARTS CONTAINERS: one fixed calibration stage, charged to the validation budget."""
    from c1_harness.driver import (StopAll, preblock_checks, probe_session, recorded_attempt_ids, run_direct,
                                   run_helpers, run_identity, run_smoke)

    if cmd_calibration_plan(argparse.Namespace(write=False)) != 0 or cmd_schedule(argparse.Namespace(write=False, replace=False)) != 0:
        print("refusing: schedule and calibration plan must be saved and regenerate identically first", file=sys.stderr)
        return 2
    plan = json.loads(CAL_PLAN.read_text(encoding="utf-8"))
    ctx = _ctx()
    subjects = _subjects()
    if args.stage != "helpers" and recorded_attempt_ids(ctx, args.stage):
        print(f"refusing: calibration stage {args.stage} already has recorded attempts; it is never repeated", file=sys.stderr)
        return 2
    if args.stage == "helpers" and any(e["kind"] == "helper_check" for e in ctx.events.rows()):
        print("refusing: helper checks already recorded", file=sys.stderr)
        return 2
    started = utc_now()
    ctx.events.append("calibration_start", stage=args.stage)
    try:
        pre = preblock_checks(ctx, f"calibration {args.stage}")
        probe_session(ctx, "validation", f"cal-{args.stage}-{started}")
        first = subjects[plan["first_structurally_ready_subject"]]
        if args.stage == "smoke":
            out = run_smoke(ctx, subjects, plan["smoke"])
        elif args.stage == "identity":
            out = run_identity(ctx, first, plan["identity"])
        elif args.stage == "direct":
            out = run_direct(ctx, first, plan["direct"])
        else:
            out = run_helpers(ctx)
    except (StopAll, BudgetError) as exc:
        ctx.events.append("calibration_end", stage=args.stage, outcome="stopped", reason=str(exc)[:1000])
        print(f"STOPPED: {exc}", file=sys.stderr)
        return 3
    ctx.events.append("calibration_end", stage=args.stage, outcome="completed", preblock=pre, started_utc=started)
    print(f"calibration {args.stage} completed: {len(out)} items; budget {json.dumps(ctx.budget.summary()['validation'])}")
    return 0


# --- annotation and analysis ------------------------------------------------------------------


def cmd_annotate(args: argparse.Namespace) -> int:
    from ledger import read_records, verify_chain
    from oracle import load_overrides, write_annotations

    from c1_harness.cards import annotate
    from c1_harness.driver import Context, stage_dir

    d = stage_dir(Context(STUDY_DIR, None, None, None), args.stage)  # type: ignore[arg-type]
    records = []
    for p in sorted(d.glob("*__*.jsonl")):
        verify_chain(p)
        records += read_records(p)
    anns = annotate(records, load_overrides(args.overrides))
    write_annotations(d / "annotations.jsonl", anns, replace=args.replace)
    counts: dict[str, int] = {}
    for r, a in zip(records, anns):
        key = f"{r['episode']:11} {r['condition']} {r['version']:5} {'+'.join(a['categories'])}"
        counts[key] = counts.get(key, 0) + 1
    for k, n in sorted(counts.items()):
        print(f"{k:60} {n}")
    print(f"{len(anns)} annotations -> {d / 'annotations.jsonl'}")
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    from c1_harness.matched import analyse, write_outputs

    subjects = _subjects()
    enrolled = [s.sid for s in subjects.values() if s.enrolled]
    measured = Path(args.measured_dir) if args.measured_dir else STUDY_DIR / "measured"
    if args.subject:
        enrolled = [s for s in enrolled if s in args.subject]
    result = analyse(measured, measured / "annotations.jsonl", enrolled,
                     {s.sid: s.project for s in subjects.values()}, questioned=args.questioned or [])
    out = Path(args.out) if Path(args.out).is_absolute() else STUDY_DIR / args.out
    write_outputs(result, out)
    print(f"analysis written to {out}")
    return 0


def cmd_calibration_report(args: argparse.Namespace) -> int:
    from c1_harness.calreport import build

    report = build(STUDY_DIR)
    (STUDY_DIR / args.out).write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8", newline="\n")
    _print({k: v for k, v in report.items() if k != "stages"})
    for stage, s in report["stages"].items():
        print(stage, {k: v for k, v in s.items() if k != "category_counts"})
    return 0


def cmd_gate_a(args: argparse.Namespace) -> int:
    from c1_harness.gates import gate_a, record_gate_a

    ctx = _ctx()
    result = gate_a(ctx, _subjects(), _schedule_rows())
    if args.record:
        record_gate_a(ctx.events, result)
    _print(result)
    return 0 if result["integrity_passed"] else 1


# --- launch -----------------------------------------------------------------------------------


def _launch_checks(batch: str, *, docker_checks: bool) -> list[str]:
    from c1_harness.freeze import verify_launch

    problems = [f"launch freeze: {p}" for p in verify_launch()]
    if cmd_schedule(argparse.Namespace(write=False, replace=False)) != 0:
        problems.append("schedule does not regenerate identically")
    try:
        ResourceLedger(RESOURCE_LEDGER).verify()
        from c1_harness.driver import EventLog

        EventLog(EVENTS).verify()
    except Exception as exc:  # noqa: BLE001
        problems.append(f"ledger chain: {exc}")
    subjects = _subjects()
    enrolled = [s for s in subjects.values() if s.enrolled]
    budget = ResourceLedger(RESOURCE_LEDGER)
    need = max((block_reservation_vcpu_h(s.outer_timeout_s) for s in enrolled), default=0.0)
    left = budget.remaining("measured")
    if left < min((block_reservation_vcpu_h(s.outer_timeout_s) for s in enrolled), default=0.0):
        problems.append(f"measured budget remaining {left:.3f} vCPU-h cannot admit any matched block")
    if budget.open_reservations():
        problems.append(f"open budget reservations: {sorted(budget.open_reservations())}")
    if docker_checks:
        ex = DockerExecutor()
        info = ex.daemon_info()
        if info is None or info.get("ncpu") != 16:
            problems.append(f"daemon unavailable or not 16 CPUs: {info}")
        for s in enrolled:
            for version, image in s.images.items():
                if ex.image_id(image) != image:
                    problems.append(f"{s.sid} {version}: image {image} not present")
        if ex.study_containers() != []:
            problems.append("study containers present")
        if ex.running_containers() != []:
            problems.append("other containers running")
    print(f"largest block reservation {need:.4f} vCPU-h; measured remaining {left:.4f} vCPU-h")
    return problems


def cmd_dry_run(args: argparse.Namespace) -> int:
    """Never starts containers and never calls Docker: prints the batch plan and reservations."""
    from c1_harness.driver import StopAll, run_measured_batch

    ctx = _ctx()
    try:
        plan = run_measured_batch(ctx, args.batch, _subjects(), _schedule_rows(), resume_review=args.resume_review, dry_run=True)
    except StopAll as exc:
        print(f"DRY RUN: batch {args.batch} would be refused: {exc}")
        return 2
    _print(plan)
    return 0


def cmd_preflight(args: argparse.Namespace) -> int:
    """Non-executing: verifies both freezes, schedule, chains, budget, images and daemon state."""
    problems = _launch_checks(args.batch, docker_checks=True)
    for p in problems:
        print(f"PREFLIGHT FAIL: {p}")
    print("PREFLIGHT PASSED" if not problems else f"PREFLIGHT FAILED ({len(problems)} problems)")
    return 0 if not problems else 1


def cmd_run_batch(args: argparse.Namespace) -> int:
    """STARTS CONTAINERS: a measured batch. Refuses without a valid launch freeze and budget."""
    from c1_harness.driver import StopAll, run_measured_batch

    problems = _launch_checks(args.batch, docker_checks=True)
    if problems:
        for p in problems:
            print(f"REFUSED: {p}", file=sys.stderr)
        return 2
    ctx = _ctx()
    try:
        summary = run_measured_batch(ctx, args.batch, _subjects(), _schedule_rows(), resume_review=args.resume_review)
    except (StopAll, BudgetError) as exc:
        print(f"STOPPED: {exc}", file=sys.stderr)
        return 3
    _print({"summary": summary, "budget": ctx.budget.summary()})
    return 0


def cmd_verify_design(args: argparse.Namespace) -> int:
    from c1_harness.freeze import verify_design

    problems = verify_design()
    for p in problems:
        print(f"DESIGN FREEZE: {p}")
    print("design freeze verified (8/8)" if not problems else "DESIGN FREEZE FAILED")
    return 0 if not problems else 1


def cmd_verify_launch(args: argparse.Namespace) -> int:
    from c1_harness.freeze import verify_launch

    problems = verify_launch()
    for p in problems:
        print(f"LAUNCH FREEZE: {p}")
    print("launch freeze and design freeze verified" if not problems else "LAUNCH FREEZE FAILED")
    return 0 if not problems else 1


def cmd_write_launch_freeze(args: argparse.Namespace) -> int:
    from c1_harness.freeze import write_launch_freeze

    files = [Path(REPO_ROOT / f) for f in json.loads(Path(args.file_list).read_text(encoding="utf-8"))]
    missing = [str(f) for f in files if not f.exists()]
    if missing:
        print(f"missing: {missing}", file=sys.stderr)
        return 2
    path = write_launch_freeze(files, header=args.header)
    print(f"wrote {path} ({len(files)} files)")
    return 0


# --- accounting -----------------------------------------------------------------------------


def cmd_budget(args: argparse.Namespace) -> int:
    ledger = ResourceLedger(RESOURCE_LEDGER)
    _print({"rows": ledger.verify(), "stages": ledger.summary(), "caps": STAGE_CAPS})
    return 0


def cmd_agent_time(args: argparse.Namespace) -> int:
    row = ResourceLedger(RESOURCE_LEDGER).agent_time(stage=args.stage, started_utc=args.started,
                                                      ended_utc=args.ended or utc_now(), note=args.note)
    _print(row)
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="python -m c1_harness.cli", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)

    def add(name: str, func, help_: str | None = None) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help_ or (func.__doc__ or "").strip().splitlines()[0])
        p.set_defaults(func=func)
        return p

    add("prepare-checks", cmd_prepare_checks)
    p = add("probe-profiles", cmd_probe_profiles)
    p.add_argument("--stage", required=True, choices=["preparation", "validation", "measured"])
    p.add_argument("--tag", required=True)
    p.add_argument("--out", required=True, help="output JSON path relative to the study directory")
    p = add("probe-clock", cmd_probe_clock)
    p.add_argument("--stage", required=True, choices=["preparation", "validation"])
    p.add_argument("--tag", required=True)
    p.add_argument("--out", required=True)
    add("env-manifest", cmd_env_manifest)
    p = add("schedule", cmd_schedule, "write (once) or check the measured schedule; never redraws")
    p.add_argument("--write", action="store_true")
    p.add_argument("--replace", action="store_true", help=argparse.SUPPRESS)
    p = add("calibration-plan", cmd_calibration_plan, "write (once) or check the fixed calibration plan")
    p.add_argument("--write", action="store_true")
    p = add("calibrate", cmd_calibrate)
    p.add_argument("stage", choices=["smoke", "identity", "direct", "helpers"])
    p = add("annotate", cmd_annotate, "mechanical oracle annotations for one stage (reads ledgers only)")
    p.add_argument("--stage", required=True, choices=["smoke", "identity", "direct", "measured"])
    p.add_argument("--overrides")
    p.add_argument("--replace", action="store_true")
    p = add("analyze", cmd_analyze, "frozen matched-block analysis of the measured ledgers")
    p.add_argument("--out", default="analysis")
    p.add_argument("--questioned", action="append", help="subject whose oracle is questioned (pair-validity review)")
    p.add_argument("--measured-dir", help="validation only: analyse ledgers from another directory")
    p.add_argument("--subject", action="append", help="validation only: restrict to these enrolled subjects")
    p = add("calibration-report", cmd_calibration_report, "summarize calibration ledgers/events (reads only)")
    p.add_argument("--out", default="calibration/report.json")
    p = add("gate-a", cmd_gate_a, "batch-A integrity/validity/cost gate; computes no effects")
    p.add_argument("--record", action="store_true", help="append the gate outcome to events.jsonl")
    for name, func in (("dry-run", cmd_dry_run), ("preflight", cmd_preflight), ("run-batch", cmd_run_batch)):
        p = add(name, func)
        p.add_argument("--batch", required=True, choices=["A", "B"])
        if name != "preflight":
            p.add_argument("--resume-review", help="required to resume after an interruption: the review note")
    add("verify-design", cmd_verify_design, "recompute DESIGN_FREEZE.sha256")
    add("verify-launch", cmd_verify_launch, "recompute FREEZE.sha256 and DESIGN_FREEZE.sha256")
    p = add("write-launch-freeze", cmd_write_launch_freeze, "write FREEZE.sha256 from a JSON list of repo-relative paths")
    p.add_argument("--file-list", required=True)
    p.add_argument("--header", required=True)
    add("budget", cmd_budget, "verify the resource ledger and print stage balances")
    p = add("agent-time", cmd_agent_time, "record agent wall-clock for a stretch of work (not human hours)")
    p.add_argument("--stage", required=True)
    p.add_argument("--started", required=True)
    p.add_argument("--ended")
    p.add_argument("--note", required=True)
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
