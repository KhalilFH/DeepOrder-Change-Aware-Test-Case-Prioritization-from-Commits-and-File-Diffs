"""Run the E1 step-4 controls, exactly as frozen in AMENDMENTS.md section 7.

    python research_runs/ci_sensitivity_2026_09/e1/run_controls.py

Refuses to start unless `controls/plan.json`, `controls/manifests.json` and the
E1 manifests hash to their frozen values, each identity manifest is its E1
manifest with both version roles on the frozen `V_ok` image, every image ID is
present locally, `docker info` succeeds and `docker ps -a` lists no containers.

Blocks run one at a time, in plan order, through the frozen `Runner.run_block`
(three attempts on each version role), into `controls/<control>/attempts.jsonl`.
The E1 episode ledgers are read for cost only and never written.

Before each block, the cost guard refuses to start it if its hard-bound cost
would take E1 past 20.0 allocated vCPU-hours; a guard stop is final. After each
block, the run stops at the first structural mismatch: a version role without
exactly three recorded attempts, a ledger that disagrees with the executed
statuses or fails `verify_chain`, or a container from the block still present.
Nothing is retried.

A stopped run may resume only from the next unrecorded block, and only when
every recorded block is complete. Exit codes: 0 done, 1 refused, 2 `docker info`
failed, 3 guard stop, 4 structural mismatch.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "e1_harness"))

import run_direct as rd  # noqa: E402
from ledger import MAX_ATTEMPTS_PER_BLOCK, VERSIONS, V_OK, Ledger, LedgerError, read_records, verify_chain  # noqa: E402
from run_blocks import block_seed  # noqa: E402
from runner import CLEANUP_TIMEOUT_S, RUNNER_VERSION, Manifest, Runner  # noqa: E402

DriverError = rd.DriverError

FROZEN_PLAN_SHA256 = "c67830841a540cf68f509115d0a4627f3890b7ae31f2de8a2b217c7f8f9f6cd7"
FROZEN_CONTROL_MANIFEST_SHA256 = {
    "identity_etcd5509": "973488c9d0d7a89b4259a5ff8f3e0f4371f7814652d28be84687a7fab4d681c1",
    "identity_etcd7492": "362fa13a502e3eb1eb93ed18d3cacc57eeb550909562ca32df5f4d189e598358",
    "detfail_grpc1859": "87d94b32c105903e2f59c7badba44d0716452f44a1c4fc36d4cd06ea3169d2f6",
}
IDENTITY_OF = {"identity_etcd5509": "etcd5509", "identity_etcd7492": "etcd7492"}
PLAN_ORDER = (
    *(("identity_etcd5509", b) for b in range(201, 206)),
    *(("identity_etcd7492", b) for b in range(201, 206)),
    *(("detfail_grpc1859", b) for b in range(211, 214)),
)
CONTROL_FROM = 201

# AMENDMENTS.md section 7: the section 2.2 accounting, with the line at the E1 cap.
GUARD_LINE_VCPU_H = 20.0

EXIT_DONE, EXIT_REFUSED, EXIT_DOCKER, EXIT_GUARD, EXIT_MISMATCH = 0, 1, 2, 3, 4


@dataclass(frozen=True)
class ControlBlock:
    control: str
    block: int
    seed: int


def load_plan(
    path: str | Path,
    manifests: dict[str, Manifest],
    expected_sha256: str = FROZEN_PLAN_SHA256,
) -> list[ControlBlock]:
    """The frozen plan, in execution order. Refuses a plan that is not exactly it."""
    raw = Path(path).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected_sha256:
        raise DriverError(f"plan sha256 {digest} is not the frozen value")
    plan = [ControlBlock(**row) for row in json.loads(raw)["blocks"]]
    if tuple((b.control, b.block) for b in plan) != PLAN_ORDER:
        raise DriverError("plan blocks are not the frozen control order")
    for b in plan:
        if b.seed != block_seed(manifests[b.control].episode, b.block):
            raise DriverError(f"{b.control} block {b.block}: seed {b.seed} does not follow the frozen seed rule")
    return plan


def load_manifests(path: str | Path, e1_manifests: dict[str, Manifest]) -> dict[str, Manifest]:
    """Control manifests, hash-checked; identity manifests re-derived from E1's."""
    manifests = {
        name: Manifest(**spec)
        for name, spec in json.loads(Path(path).read_text(encoding="utf-8")).items()
    }
    if set(manifests) != set(FROZEN_CONTROL_MANIFEST_SHA256):
        raise DriverError(f"control manifests must be exactly {sorted(FROZEN_CONTROL_MANIFEST_SHA256)}")
    for name, frozen in FROZEN_CONTROL_MANIFEST_SHA256.items():
        if manifests[name].sha256 != frozen:
            raise DriverError(f"{name}: manifest sha256 {manifests[name].sha256} is not the frozen value")
    for name, episode in IDENTITY_OF.items():
        m, base = manifests[name], e1_manifests[episode]
        same = (m.episode, m.workdir, m.argv, m.timeout_s, m.condition) == (
            base.episode, base.workdir, base.argv, base.timeout_s, base.condition
        )
        if not same or m.images != {v: base.images[V_OK] for v in VERSIONS}:
            raise DriverError(f"{name} is not {episode}'s frozen manifest with both roles on its V_ok image")
    return manifests


# --- cost ---------------------------------------------------------------------


def block_hard_bound_vcpu_h(timeout_s: int) -> float:
    """A block's cost if all six attempts run to the runner timeout and full cleanup."""
    return rd.VCPUS * len(VERSIONS) * MAX_ATTEMPTS_PER_BLOCK * (timeout_s + CLEANUP_TIMEOUT_S + rd.GAP_S) / 3600


def cost_so_far(e1_records: Sequence[dict[str, Any]], control_records: Sequence[dict[str, Any]]) -> float:
    """E1's cost before the controls (section 2.2 basis) plus every control attempt."""
    return rd.cost_so_far(e1_records) + sum(rd.attempt_cost_vcpu_h(r["elapsed_s"]) for r in control_records)


# --- structure ----------------------------------------------------------------


def _block_rows(records: Sequence[dict[str, Any]], block: int) -> list[dict[str, Any]]:
    return [r for r in records if r["block"] == block]


def block_problems(rows: Sequence[dict[str, Any]], manifest: Manifest) -> list[str]:
    """Where a recorded block departs from a complete `run_block` on `manifest`."""
    problems = []
    for version in VERSIONS:
        attempts = sorted(r["attempt"] for r in rows if r["version"] == version)
        if attempts != list(range(1, MAX_ATTEMPTS_PER_BLOCK + 1)):
            problems.append(f"{version} has attempts {attempts}")
    if any(r["manifest_sha256"] != manifest.sha256 or r["episode"] != manifest.episode for r in rows):
        problems.append("a record carries another manifest or episode")
    return problems


def resume_index(plan: Sequence[ControlBlock], records: dict[str, list[dict[str, Any]]], manifests: dict[str, Manifest]) -> int:
    """How many plan blocks are already recorded. Refuses anything but complete prefix blocks."""
    planned = {(b.control, b.block) for b in plan}
    for control, rows in records.items():
        stray = sorted({r["block"] for r in rows if (control, r["block"]) not in planned})
        if stray:
            raise DriverError(f"{control}: blocks {stray} are not in the plan")
    done = [bool(_block_rows(records.get(b.control, []), b.block)) for b in plan]
    n = done.index(False) if False in done else len(done)
    if any(done[n:]):
        raise DriverError("recorded blocks are not a prefix of the plan order")
    for b in plan[:n]:
        problems = block_problems(_block_rows(records[b.control], b.block), manifests[b.control])
        if problems:
            raise DriverError(
                f"{b.control} block {b.block} is recorded but incomplete ({'; '.join(problems)}); "
                "resuming needs a recorded decision in AMENDMENTS.md"
            )
    return n


# --- run ----------------------------------------------------------------------


def run_controls(
    plan: Sequence[ControlBlock],
    manifests: dict[str, Manifest],
    ledger_paths: dict[str, Path],
    e1_records: Sequence[dict[str, Any]],
    docker: rd.Docker,
    out: Callable[[str], None],
    runner_factory: Callable[[Manifest], Runner] = Runner,
    line: float = GUARD_LINE_VCPU_H,
) -> int:
    records = {c: read_records(p) for c, p in ledger_paths.items()}
    start = resume_index(plan, records, manifests)
    if start:
        nxt = f"{plan[start].control} block {plan[start].block}" if start < len(plan) else "end"
        out(f"RESUME at {nxt} ({start} blocks recorded)")

    for b in plan[start:]:
        if not docker.info_ok():
            out(f"STOP before {b.control} block {b.block}: docker info failed")
            return EXIT_DOCKER
        manifest = manifests[b.control]
        spent = cost_so_far(e1_records, [r for rows in records.values() for r in rows])
        bound = block_hard_bound_vcpu_h(manifest.timeout_s)
        if spent + bound > line:
            out(
                f"GUARD STOP before {b.control} block {b.block}: {spent:.3f} + {bound:.3f} "
                f"> {line:.1f} vCPU-h; remaining blocks are not run"
            )
            return EXIT_GUARD

        path = ledger_paths[b.control]
        with Ledger(path) as led:
            outcome = runner_factory(manifest).run_block(led, b.block, b.seed)

        try:
            verify_chain(path)
            problems = []
        except LedgerError as exc:
            problems = [f"verify_chain: {exc}"]
        records[b.control] = read_records(path)
        rows = _block_rows(records[b.control], b.block)
        problems += block_problems(rows, manifest)
        for version in VERSIONS:
            recorded = [r["exit_status"] for r in sorted(rows, key=lambda r: r["attempt"]) if r["version"] == version]
            if recorded != list(outcome.statuses.get(version, [])):
                problems.append(f"ledger disagrees with the executed {version} statuses")
        names = docker.container_names()
        if names is None:
            problems.append("docker ps -a failed after the block")
        else:
            left = sorted({r["extra"].get("container") for r in rows} & set(names))
            if left:
                problems.append(f"containers still present: {left}")

        spent = cost_so_far(e1_records, [r for recs in records.values() for r in recs])
        out(
            f"block {b.block} {b.control} seed={b.seed} first={outcome.first_version} "
            f"statuses={json.dumps(outcome.statuses, sort_keys=True)} cost_so_far={spent:.3f}"
        )
        if problems:
            out(f"STOP structural mismatch at {b.control} block {b.block}: {'; '.join(problems)}")
            return EXIT_MISMATCH

    out("DONE")
    return EXIT_DONE


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    logs = HERE / "run_logs"
    try:
        e1_manifests = rd.load_manifests(HERE / "manifests.json")
        manifests = load_manifests(HERE / "controls" / "manifests.json", e1_manifests)
        plan = load_plan(HERE / "controls" / "plan.json", manifests)
    except DriverError as exc:
        sys.exit(str(exc))
    docker = rd.RealDocker()
    problems = rd.preflight(docker, manifests)
    if problems:
        sys.exit("refusing to start: " + "; ".join(problems))

    e1_records = [r for ep in e1_manifests for r in read_records(HERE / ep / "attempts.jsonl")]
    with open(logs / "controls_start_utc.txt", "a", encoding="utf-8", newline="\n") as f:
        f.write(f"{_utc()} docker_info=ok containers=0\n")
    code = "python-error"  # a Python-level failure stops the run; nothing is retried
    try:
        with open(logs / "controls_201-213.log", "a", encoding="utf-8", newline="\n") as log:
            def out(line: str) -> None:
                print(line, flush=True)
                log.write(line + "\n")
                log.flush()

            out(
                f"controls plan={FROZEN_PLAN_SHA256} runner={RUNNER_VERSION} line={GUARD_LINE_VCPU_H} "
                + " ".join(f"{c}={m.sha256}" for c, m in manifests.items())
            )
            try:
                code = run_controls(
                    plan, manifests,
                    {c: HERE / "controls" / c / "attempts.jsonl" for c in manifests},
                    e1_records, docker, out,
                )
            except DriverError as exc:
                out(f"REFUSED: {exc}")
                code = EXIT_REFUSED
    finally:
        with open(logs / "controls_end_utc.txt", "a", encoding="utf-8", newline="\n") as f:
            f.write(f"{_utc()} exit={code}\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
