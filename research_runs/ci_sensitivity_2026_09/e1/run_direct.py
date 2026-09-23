"""Run the E1 direct-policy checks, exactly as frozen in AMENDMENTS.md section 2.

    python research_runs/ci_sensitivity_2026_09/e1/run_direct.py

Refuses to start unless `direct_checks_plan.json` and both manifests hash to
their frozen values, every image ID is present locally, `docker info` succeeds
and `docker ps -a` lists no containers. Checks run one at a time, in plan order,
through `Runner.run_policy_direct`, into the episode's existing ledger.

Before each check, the cost guard refuses to start it if its hard-bound cost
would take E1 past the 17.0 allocated vCPU-hour line (section 2.2); a guard stop
is final. After each check, the run stops at the first structural mismatch
(section 2.4): a prefix inconsistent with the planned policy's stopping rule, a
ledger that disagrees with the executed trace or fails `verify_chain`, or a
container from the check still present. Nothing is retried.

A stopped run may resume only from the next unrecorded check, and only when
every recorded check is structurally sound. Exit codes: 0 done, 1 refused,
2 `docker info` failed, 3 guard stop, 4 structural mismatch.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Protocol, Sequence

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "e1_harness"))

from ledger import VERSIONS, Ledger, LedgerError, read_records, verify_chain  # noqa: E402
from policy import P1, P3, RETRY_BUDGET  # noqa: E402
from run_blocks import FROZEN_MANIFEST_SHA256, block_seed  # noqa: E402
from runner import CLEANUP_TIMEOUT_S, RUNNER_VERSION, Manifest, Runner  # noqa: E402

FROZEN_PLAN_SHA256 = "5e74dc813f665fb8fa4c6a27e7570d3c55c993a6eb25adbda0fe610db4768883"
RESERVED_FROM = 101
PLAN_BLOCKS = tuple(range(101, 113))

# AMENDMENTS.md section 2.2: conservative accounting.
VCPUS = 16
GAP_S = 2.04
MEASURED_COST_VCPU_H = 10.61
GUARD_LINE_VCPU_H = 17.0

EXIT_DONE, EXIT_REFUSED, EXIT_DOCKER, EXIT_GUARD, EXIT_MISMATCH = 0, 1, 2, 3, 4


class DriverError(RuntimeError):
    """The driver refuses to start."""


@dataclass(frozen=True)
class Check:
    block: int
    episode: str
    version: str
    policy: str
    seed: int


def load_plan(path: str | Path, expected_sha256: str = FROZEN_PLAN_SHA256) -> list[Check]:
    """The frozen plan, in execution order. Refuses a plan that is not exactly it."""
    raw = Path(path).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected_sha256:
        raise DriverError(f"plan sha256 {digest} is not the frozen value")
    checks = [Check(**row) for row in json.loads(raw)["checks"]]
    if tuple(c.block for c in checks) != PLAN_BLOCKS:
        raise DriverError(f"plan blocks must be {PLAN_BLOCKS[0]}-{PLAN_BLOCKS[-1]} in order")
    for c in checks:
        if c.episode not in FROZEN_MANIFEST_SHA256:
            raise DriverError(f"block {c.block}: unknown episode {c.episode!r}")
        if c.version not in VERSIONS or c.policy not in (P1, P3):
            raise DriverError(f"block {c.block}: bad version/policy {c.version}/{c.policy}")
        if c.seed != block_seed(c.episode, c.block):
            raise DriverError(f"block {c.block}: seed {c.seed} does not follow the frozen seed rule")
    return checks


def load_manifests(path: str | Path) -> dict[str, Manifest]:
    manifests = {
        ep: Manifest(**spec)
        for ep, spec in json.loads(Path(path).read_text(encoding="utf-8")).items()
    }
    for ep, frozen in FROZEN_MANIFEST_SHA256.items():
        if manifests[ep].sha256 != frozen:
            raise DriverError(f"{ep}: manifest sha256 {manifests[ep].sha256} is not the frozen value")
    return manifests


# --- cost ---------------------------------------------------------------------


def attempt_cost_vcpu_h(elapsed_s: float) -> float:
    return VCPUS * (elapsed_s + GAP_S) / 3600


def hard_bound_vcpu_h(policy: str, timeout_s: int) -> float:
    """A check's cost if every attempt runs to the runner timeout and full cleanup."""
    attempts = 1 if policy == P1 else RETRY_BUDGET
    return VCPUS * attempts * (timeout_s + CLEANUP_TIMEOUT_S + GAP_S) / 3600


def cost_so_far(records: Sequence[dict[str, Any]], measured: float = MEASURED_COST_VCPU_H) -> float:
    """Fixed measured-block cost plus every direct-check attempt already recorded."""
    return measured + sum(
        attempt_cost_vcpu_h(r["elapsed_s"]) for r in records if r["block"] >= RESERVED_FROM
    )


# --- structure ----------------------------------------------------------------


def stopping_problems(policy: str, executed: Sequence[int | None]) -> list[str]:
    """Section 2.4: where a trace breaks its policy's stopping rule.

    A `None` (no exit status) is not a pass, so P3 continuing after one is
    consistent with the runner's rule; the reducer rates such a check
    INDETERMINATE, which is a decision, not a structural mismatch.
    """
    executed = list(executed)
    if not executed:
        return ["no attempt was executed"]
    if policy == P1:
        return [] if len(executed) == 1 else [f"P1 ran {len(executed)} attempts"]
    problems = []
    if len(executed) > RETRY_BUDGET:
        problems.append(f"P3 ran {len(executed)} attempts")
    if 0 in executed[:-1]:
        problems.append("P3 continued after exit 0")
    if len(executed) < RETRY_BUDGET and executed[-1] != 0:
        problems.append(f"P3 stopped after {len(executed)} attempts without exit 0")
    return problems


def _trace(records: Sequence[dict[str, Any]], check: Check) -> list[dict[str, Any]]:
    rows = [r for r in records if r["episode"] == check.episode and r["block"] == check.block]
    return sorted(rows, key=lambda r: r["attempt"])


def resume_index(plan: Sequence[Check], records: dict[str, list[dict[str, Any]]]) -> int:
    """How many plan checks are already recorded. Refuses anything but a sound prefix."""
    planned = {(c.episode, c.block) for c in plan}
    for ep, rows in records.items():
        stray = sorted({r["block"] for r in rows if r["block"] >= RESERVED_FROM and (ep, r["block"]) not in planned})
        if stray:
            raise DriverError(f"{ep}: direct-range blocks {stray} are not in the plan")
    done = [bool(_trace(records.get(c.episode, []), c)) for c in plan]
    n = done.index(False) if False in done else len(done)
    if any(done[n:]):
        raise DriverError("recorded checks are not a prefix of the plan order")
    for c in plan[:n]:
        rows = _trace(records[c.episode], c)
        problems = stopping_problems(c.policy, [r["exit_status"] for r in rows])
        if any(r["version"] != c.version for r in rows):
            problems.append(f"recorded version is not {c.version}")
        if problems:
            raise DriverError(
                f"block {c.block} is recorded but unsound ({'; '.join(problems)}); "
                "resuming needs a recorded decision in AMENDMENTS.md"
            )
    return n


# --- docker -------------------------------------------------------------------


class Docker(Protocol):
    def info_ok(self) -> bool: ...
    def image_present(self, image: str) -> bool: ...
    def container_names(self) -> list[str] | None: ...


class RealDocker:
    def _run(self, argv: list[str]) -> subprocess.CompletedProcess | None:
        try:
            return subprocess.run(argv, capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired):
            return None

    def info_ok(self) -> bool:
        done = self._run(["docker", "info"])
        return done is not None and done.returncode == 0

    def image_present(self, image: str) -> bool:
        done = self._run(["docker", "image", "inspect", image])
        return done is not None and done.returncode == 0

    def container_names(self) -> list[str] | None:
        done = self._run(["docker", "ps", "-a", "--format", "{{.Names}}"])
        if done is None or done.returncode != 0:
            return None
        return done.stdout.split()


def preflight(docker: Docker, manifests: dict[str, Manifest]) -> list[str]:
    """Section 2.4's start conditions that the driver can check itself."""
    if not docker.info_ok():
        return ["docker info failed"]
    problems = [
        f"image {image} is not present locally"
        for m in manifests.values()
        for image in m.images.values()
        if not docker.image_present(image)
    ]
    names = docker.container_names()
    if names is None:
        problems.append("docker ps -a failed")
    elif names:
        problems.append(f"docker ps -a lists {len(names)} container(s): {names}")
    return problems


# --- run ----------------------------------------------------------------------


def run_checks(
    plan: Sequence[Check],
    manifests: dict[str, Manifest],
    ledger_paths: dict[str, Path],
    docker: Docker,
    out: Callable[[str], None],
    runner_factory: Callable[[Manifest], Runner] = Runner,
    measured: float = MEASURED_COST_VCPU_H,
    line: float = GUARD_LINE_VCPU_H,
) -> int:
    records = {ep: read_records(p) for ep, p in ledger_paths.items()}
    start = resume_index(plan, records)
    if start:
        out(f"RESUME at block {plan[start].block if start < len(plan) else 'end'} ({start} checks recorded)")

    for check in plan[start:]:
        if not docker.info_ok():
            out(f"STOP before block {check.block}: docker info failed")
            return EXIT_DOCKER
        manifest = manifests[check.episode]
        spent = cost_so_far([r for rows in records.values() for r in rows], measured)
        bound = hard_bound_vcpu_h(check.policy, manifest.timeout_s)
        if spent + bound > line:
            out(
                f"GUARD STOP before block {check.block}: {spent:.3f} + {bound:.3f} "
                f"> {line:.1f} vCPU-h; remaining checks are not run"
            )
            return EXIT_GUARD

        path = ledger_paths[check.episode]
        with Ledger(path) as led:
            outcome = runner_factory(manifest).run_policy_direct(
                led, check.block, check.version, check.policy,
                seed=check.seed, reserved_from=RESERVED_FROM,
            )

        problems = stopping_problems(check.policy, outcome.executed)
        try:
            verify_chain(path)
        except LedgerError as exc:
            problems.append(f"verify_chain: {exc}")
        records[check.episode] = read_records(path)
        rows = _trace(records[check.episode], check)
        if [r["exit_status"] for r in rows] != list(outcome.executed):
            problems.append("ledger disagrees with the executed trace")
        if any(r["version"] != check.version for r in rows):
            problems.append(f"recorded version is not {check.version}")
        names = docker.container_names()
        if names is None:
            problems.append("docker ps -a failed after the check")
        else:
            left = sorted({r["extra"].get("container") for r in rows} & set(names))
            if left:
                problems.append(f"containers still present: {left}")

        spent = cost_so_far([r for rows in records.values() for r in rows], measured)
        out(
            f"block {check.block} {check.episode} {check.version} {check.policy} "
            f"seed={check.seed} executed={json.dumps(list(outcome.executed))} "
            f"decision={outcome.decision.final_status} cost_so_far={spent:.3f}"
        )
        if problems:
            out(f"STOP structural mismatch at block {check.block}: {'; '.join(problems)}")
            return EXIT_MISMATCH

    out("DONE")
    return EXIT_DONE


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    logs = HERE / "run_logs"
    try:
        plan = load_plan(HERE / "direct_checks_plan.json")
        manifests = load_manifests(HERE / "manifests.json")
    except DriverError as exc:
        sys.exit(str(exc))
    docker = RealDocker()
    problems = preflight(docker, manifests)
    if problems:
        sys.exit("refusing to start: " + "; ".join(problems))

    with open(logs / "direct_start_utc.txt", "a", encoding="utf-8", newline="\n") as f:
        f.write(f"{_utc()} docker_info=ok containers=0\n")
    code = "python-error"  # a Python-level failure stops the run; nothing is retried
    try:
        with open(logs / "direct_101-112.log", "a", encoding="utf-8", newline="\n") as log:
            def out(line: str) -> None:
                print(line, flush=True)
                log.write(line + "\n")
                log.flush()

            out(
                f"direct checks plan={FROZEN_PLAN_SHA256} runner={RUNNER_VERSION} "
                f"line={GUARD_LINE_VCPU_H} "
                + " ".join(f"{ep}={m.sha256}" for ep, m in manifests.items())
            )
            try:
                code = run_checks(
                    plan, manifests, {ep: HERE / ep / "attempts.jsonl" for ep in manifests}, docker, out
                )
            except DriverError as exc:
                out(f"REFUSED: {exc}")
                code = EXIT_REFUSED
    finally:
        with open(logs / "direct_end_utc.txt", "a", encoding="utf-8", newline="\n") as f:
            f.write(f"{_utc()} exit={code}\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
