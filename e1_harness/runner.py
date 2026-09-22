"""E1 command runner: execute attempts and hand the observations to the ledger.

Thin by design (plan, Experiment 1: "a thin isolated command runner"). It knows
how to start one attempt in a fresh container, how to fill a paired block, and
how to execute a policy with real early stopping. It does not classify, does not
analyse, and does not decide anything the reducer decides.

Three contracts it holds:

**Reset is a fresh container per attempt.** Every attempt is its own
`docker run --rm`; nothing carries over. This is the plan's "job retries using
fresh test processes and the same predeclared reset recipe", and it is why the
attempts within a block may be treated as independently reset. A container must
also not outlive its attempt: killing the `docker` CLI on timeout does not stop
the container, so each one is named and `DockerExecutor` removes it by name.

**A measured block always collects the full suffix.** `run_block` runs three
attempts per version whatever the outcomes, so P1 and P3 can both be replayed
from one shared prefix-generating procedure (plan 4.4). Conditioning collection
on the first outcome would distort unconditional blocking rates.

**Direct execution and replay must agree.** `run_policy_direct` executes a
policy with real early stopping, for the plan's 12 direct-policy checks. Its
decision is produced by the same reducer that scores replayed blocks, so a
disagreement is a structural mismatch rather than a difference of opinion.

The subprocess call is injected, so the orchestration is testable without
Docker. `DockerExecutor` is the real one; `FakeExecutor` is for tests.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import secrets
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol, Sequence

from ledger import AttemptRecord, Ledger, MAX_ATTEMPTS_PER_BLOCK, V_BAD, V_OK, VERSIONS
from policy import P1, P3, P3_RETAIN, POLICIES, Decision, reduce_block

RUNNER_VERSION = "e1-runner/1"

ATTEMPT_CEILING_S = 120
"""The plan's per-attempt ceiling. A manifest may not exceed it."""

CLEANUP_TIMEOUT_S = 30
"""How long `docker rm -f` may take to remove a timed-out attempt's container."""


class RunnerError(RuntimeError):
    """The runner's contract was violated."""


@dataclass(frozen=True)
class Attempt:
    """The raw result of one execution. `exit_status` is None if it never ran."""

    exit_status: int | None
    stdout: str
    stderr: str
    timed_out: bool = False
    extra: dict = field(default_factory=dict)
    """Executor bookkeeping, merged into the ledger record's `extra`."""


class Executor(Protocol):
    def run(self, argv: Sequence[str], timeout_s: int) -> Attempt: ...


@dataclass
class Manifest:
    """The frozen subject definition. Its hash is recorded on every attempt."""

    episode: str
    images: dict[str, str]
    workdir: str
    argv: list[str]
    timeout_s: int
    condition: str

    def __post_init__(self) -> None:
        missing = [v for v in VERSIONS if v not in self.images]
        if missing:
            raise RunnerError(f"manifest has no image for {missing}")
        if not 0 < self.timeout_s <= ATTEMPT_CEILING_S:
            raise RunnerError(
                f"timeout {self.timeout_s}s is outside the plan's "
                f"1..{ATTEMPT_CEILING_S}s attempt ceiling"
            )

    @property
    def sha256(self) -> str:
        payload = json.dumps(
            {
                "episode": self.episode,
                "images": self.images,
                "workdir": self.workdir,
                "argv": self.argv,
                "timeout_s": self.timeout_s,
                "condition": self.condition,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def docker_argv(self, version: str, name: str | None = None) -> list[str]:
        """The attempt's `docker run`. `name` is not part of the manifest hash."""
        return [
            "docker", "run", "--rm",
            *(["--name", name] if name is not None else []),
            "-w", self.workdir,
            self.images[version],
            *self.argv,
        ]


_UNSAFE_NAME_CHARS = re.compile(r"[^a-zA-Z0-9_.-]")


def container_name(episode: str, block: int, version: str, attempt: int) -> str:
    """A name unique to one attempt, valid as a Docker container name."""
    stem = f"e1-{episode}-b{block}-{version}-a{attempt}"
    return f"{_UNSAFE_NAME_CHARS.sub('-', stem)}-{secrets.token_hex(4)}"


def _container_name_in(argv: Sequence[str]) -> str | None:
    argv = list(argv)
    if "--name" in argv:
        i = argv.index("--name")
        if i + 1 < len(argv):
            return argv[i + 1]
    return None


def _text(value: str | bytes | None) -> str:
    return value.decode(errors="replace") if isinstance(value, bytes) else (value or "")


class DockerExecutor:
    """Runs the attempt as a real container.

    On timeout `subprocess.run` kills only the local `docker` CLI; the container
    keeps running. So a timed-out attempt's container is removed by the name in
    its argv, and the removal's outcome is returned in `Attempt.extra["cleanup"]`.
    An attempt without `--name` cannot be cleaned up and says so.

    `run` is the process launcher (`subprocess.run` by default), injectable so
    the cleanup path is testable without Docker.
    """

    def __init__(self, run=subprocess.run):
        self._run = run

    def run(self, argv: Sequence[str], timeout_s: int) -> Attempt:
        try:
            done = self._run(
                list(argv), capture_output=True, text=True, timeout=timeout_s
            )
        except subprocess.TimeoutExpired as exc:
            return Attempt(
                exit_status=None,
                stdout=_text(exc.stdout),
                stderr=_text(exc.stderr),
                timed_out=True,
                extra={"cleanup": self._remove(_container_name_in(argv))},
            )
        except OSError as exc:  # docker missing, daemon down, ...
            return Attempt(exit_status=None, stdout="", stderr=f"{type(exc).__name__}: {exc}")
        return Attempt(done.returncode, done.stdout, done.stderr)

    def _remove(self, name: str | None) -> dict:
        if name is None:
            return {"argv": None, "error": "attempt has no --name; container not removed"}
        argv = ["docker", "rm", "-f", name]
        try:
            done = self._run(
                argv, capture_output=True, text=True, timeout=CLEANUP_TIMEOUT_S
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            return {"argv": argv, "error": f"{type(exc).__name__}: {exc}"}
        return {
            "argv": argv,
            "exit_status": done.returncode,
            "stdout": done.stdout,
            "stderr": done.stderr,
        }


class FakeExecutor:
    """Replays a scripted list of attempts and records the argv it was given."""

    def __init__(self, scripted: Sequence[Attempt]):
        self._scripted = list(scripted)
        self.calls: list[list[str]] = []

    def run(self, argv: Sequence[str], timeout_s: int) -> Attempt:
        self.calls.append(list(argv))
        if not self._scripted:
            raise RunnerError("FakeExecutor ran out of scripted attempts")
        return self._scripted.pop(0)


@dataclass(frozen=True)
class BlockOutcome:
    block: int
    first_version: str
    seed: int
    statuses: dict[str, list[int | None]] = field(default_factory=dict)


@dataclass(frozen=True)
class DirectOutcome:
    block: int
    version: str
    policy: str
    decision: Decision
    executed: list[int | None]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


class Runner:
    def __init__(self, manifest: Manifest, executor: Executor | None = None):
        self.manifest = manifest
        self.executor = executor if executor is not None else DockerExecutor()

    def run_attempt(
        self,
        ledger: Ledger,
        block: int,
        version: str,
        attempt: int,
        seed: int | None = None,
    ) -> AttemptRecord:
        """Execute one attempt in a fresh container and append it to the ledger."""
        if version not in VERSIONS:
            raise RunnerError(f"unknown version {version!r}")
        name = container_name(self.manifest.episode, block, version, attempt)
        argv = self.manifest.docker_argv(version, name=name)
        started = _utc()
        clock = time.monotonic()
        result = self.executor.run(argv, self.manifest.timeout_s)
        elapsed = time.monotonic() - clock
        record = AttemptRecord(
            episode=self.manifest.episode,
            block=block,
            version=version,
            attempt=attempt,
            exit_status=result.exit_status,
            started_utc=started,
            ended_utc=_utc(),
            elapsed_s=round(elapsed, 6),
            timed_out=result.timed_out,
            condition=self.manifest.condition,
            seed=seed,
            manifest_sha256=self.manifest.sha256,
            runner_version=RUNNER_VERSION,
            stdout=result.stdout,
            stderr=result.stderr,
            extra={"argv": argv, "container": name, **result.extra},
        )
        ledger.append(record)
        return record

    def run_block(self, ledger: Ledger, block: int, seed: int) -> BlockOutcome:
        """One paired block: three attempts on each version, order randomised.

        The full three attempts are collected on both versions whatever the
        outcomes. The attempts after a policy's stopping point are the
        research-only suffix; they are recorded and never consulted by a policy.
        """
        rng = random.Random(seed)
        order = list(VERSIONS)
        rng.shuffle(order)

        statuses: dict[str, list[int | None]] = {}
        for version in order:
            collected: list[int | None] = []
            for attempt in range(1, MAX_ATTEMPTS_PER_BLOCK + 1):
                record = self.run_attempt(ledger, block, version, attempt, seed=seed)
                collected.append(record.exit_status)
            statuses[version] = collected

        return BlockOutcome(
            block=block, first_version=order[0], seed=seed, statuses=statuses
        )

    def run_policy_direct(
        self,
        ledger: Ledger,
        block: int,
        version: str,
        policy: str,
        seed: int | None = None,
        reserved_from: int | None = None,
    ) -> DirectOutcome:
        """Execute `policy` for real, stopping early exactly as it would in CI.

        For the plan's direct-policy checks. `reserved_from` guards the measured
        block range: direct checks are separately budgeted and must not be
        confused with the experiment's blocks.
        """
        if policy not in POLICIES:
            raise RunnerError(f"unknown policy {policy!r}")
        if reserved_from is not None and block < reserved_from:
            raise RunnerError(
                f"block {block} is inside the measured range; direct-policy "
                f"checks must use blocks >= {reserved_from}"
            )

        budget = 1 if policy == P1 else MAX_ATTEMPTS_PER_BLOCK
        executed: list[int | None] = []
        for attempt in range(1, budget + 1):
            record = self.run_attempt(ledger, block, version, attempt, seed=seed)
            executed.append(record.exit_status)
            if record.exit_status == 0:
                break  # accept-on-pass: the remaining attempts are never run

        return DirectOutcome(
            block=block,
            version=version,
            policy=policy,
            decision=reduce_block(policy, executed),
            executed=executed,
        )
