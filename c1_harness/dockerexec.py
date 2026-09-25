"""One fresh container per attempt, with its profile verified before it starts.

E1's runner used `docker run --rm`, which leaves nothing to inspect: a
short-lived container is gone before its configuration can be read. C1 needs
evidence that each attempt ran under its profile, so an attempt is split into
the daemon's own steps:

1. `docker create` with the literal argv (never a shell string);
2. `docker inspect`, checked against the profile and frozen command *before*
   anything runs; a mismatch removes the container unstarted;
3. `docker start -a` under the outer wall-clock timeout;
4. `docker inspect` again for the authoritative exit code and timestamps;
5. `docker rm -f` of that container only, then a check that it is gone.

Nothing else is ever removed: cleanup targets the container ID this attempt
created. The process launcher is injected so every path is testable offline.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Sequence

from c1_harness import STUDY_ID
from c1_harness.profiles import Profile, inspect_evidence, verify_inspect

CLEANUP_TIMEOUT_S = 30
"""Protocol: per-container cleanup has a separate 30-second maximum."""

DOCKER_CALL_TIMEOUT_S = 60
"""Bound on create/inspect/ps calls, so a hung daemon cannot hang the driver."""

LABEL_STUDY = "c1.study"
LABEL_ATTEMPT = "c1.attempt"
LABEL_STAGE = "c1.stage"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _b(value: Any) -> bytes:
    if value is None:
        return b""
    return value if isinstance(value, bytes) else str(value).encode("utf-8")


def _t(value: Any) -> str:
    return _b(value).decode("utf-8", errors="replace")


@dataclass(frozen=True)
class ContainerSpec:
    name: str
    image: str
    workdir: str
    argv: tuple[str, ...]
    profile: Profile
    attempt_id: str
    stage: str
    entrypoint: str | None = None
    """Helpers only. Subject attempts use the image's (empty) entrypoint."""
    extra_env: tuple[tuple[str, str], ...] = ()
    """Helpers only (e.g. the Go probe source). Subject attempts add nothing."""

    def create_argv(self) -> list[str]:
        out = [
            "docker", "create",
            "--name", self.name,
            "--label", f"{LABEL_STUDY}={STUDY_ID}",
            "--label", f"{LABEL_ATTEMPT}={self.attempt_id}",
            "--label", f"{LABEL_STAGE}={self.stage}",
            "-w", self.workdir,
            *self.profile.docker_args,
        ]
        for key, value in self.extra_env:
            out += ["-e", f"{key}={value}"]
        if self.entrypoint is not None:
            out += ["--entrypoint", self.entrypoint]
        return [*out, self.image, *self.argv]


@dataclass
class ExecResult:
    exit_status: int | None
    stdout: str
    stderr: str
    timed_out: bool
    started_utc: str | None
    ended_utc: str | None
    elapsed_s: float | None
    job_started_utc: str
    job_ended_utc: str
    job_elapsed_s: float
    create_argv: list[str]
    container_id: str | None = None
    profile_verified: bool = False
    profile_problems: list[str] = field(default_factory=list)
    inspect: dict[str, Any] = field(default_factory=dict)
    state: dict[str, Any] = field(default_factory=dict)
    cli_returncode: int | None = None
    cleanup: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    stdout_sha256: str = ""
    stderr_sha256: str = ""

    @property
    def cleanup_ok(self) -> bool:
        return bool(self.cleanup.get("verified_absent"))

    def extra(self) -> dict[str, Any]:
        """Executor bookkeeping stored in the ledger record's `extra`."""
        return {
            "create_argv": self.create_argv,
            "container_id": self.container_id,
            "profile_verified": self.profile_verified,
            "profile_problems": self.profile_problems,
            "inspect": self.inspect,
            "state": self.state,
            "cli_returncode": self.cli_returncode,
            "cleanup": self.cleanup,
            "error": self.error,
            "stdout_sha256": self.stdout_sha256,
            "stderr_sha256": self.stderr_sha256,
            "job_started_utc": self.job_started_utc,
            "job_ended_utc": self.job_ended_utc,
            "job_elapsed_s": self.job_elapsed_s,
        }


Launcher = Callable[..., Any]
"""`subprocess.run`-compatible: (argv, capture_output=True, timeout=...) -> object
with `returncode`, `stdout`, `stderr` (bytes), raising `TimeoutExpired`."""


class DockerExecutor:
    def __init__(self, run: Launcher = subprocess.run, clock: Callable[[], float] = time.monotonic):
        self._run = run
        self._clock = clock

    def _call(self, argv: Sequence[str], timeout: float) -> tuple[int | None, bytes, bytes, str | None]:
        try:
            done = self._run(list(argv), capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            return None, _b(exc.stdout), _b(exc.stderr), f"timeout after {timeout}s"
        except OSError as exc:
            return None, b"", b"", f"{type(exc).__name__}: {exc}"
        return done.returncode, _b(done.stdout), _b(done.stderr), None

    def inspect(self, ref: str) -> dict[str, Any] | None:
        rc, out, _err, _ = self._call(["docker", "inspect", ref], DOCKER_CALL_TIMEOUT_S)
        if rc != 0:
            return None
        try:
            data = json.loads(_t(out))
        except json.JSONDecodeError:
            return None
        return data[0] if isinstance(data, list) and data else None

    def remove(self, ref: str) -> dict[str, Any]:
        """Remove exactly this container, then confirm the daemon no longer has it."""
        argv = ["docker", "rm", "-f", ref]
        rc, out, err, problem = self._call(argv, CLEANUP_TIMEOUT_S)
        q_rc, q_out, _q_err, q_problem = self._call(
            ["docker", "ps", "-a", "-q", "--no-trunc", "--filter", f"id={ref}"], DOCKER_CALL_TIMEOUT_S
        )
        absent = q_rc == 0 and not _t(q_out).strip()
        return {
            "argv": argv,
            "returncode": rc,
            "stdout": _t(out).strip(),
            "stderr": _t(err).strip(),
            "error": problem or q_problem,
            "verified_absent": absent,
        }

    def run(
        self,
        spec: ContainerSpec,
        outer_timeout_s: float,
        *,
        verify_profile: bool = True,
    ) -> ExecResult:
        job_t0 = self._clock()
        job_started = utc_now()
        create_argv = spec.create_argv()

        def finish(**kw: Any) -> ExecResult:
            res = ExecResult(
                job_started_utc=job_started,
                job_ended_utc=utc_now(),
                job_elapsed_s=round(self._clock() - job_t0, 6),
                create_argv=create_argv,
                **kw,
            )
            res.stdout_sha256 = sha256_bytes(res.stdout.encode("utf-8"))
            res.stderr_sha256 = sha256_bytes(res.stderr.encode("utf-8"))
            return res

        rc, out, err, problem = self._call(create_argv, DOCKER_CALL_TIMEOUT_S)
        if rc != 0:
            # A partly created container would carry our unique name; remove by name only.
            cleanup = self.remove(spec.name)
            return finish(
                exit_status=None, stdout="", stderr=_t(err), timed_out=False,
                started_utc=None, ended_utc=None, elapsed_s=None,
                cli_returncode=rc, cleanup=cleanup,
                error=f"docker create failed ({problem or rc}): {_t(err).strip()[:500]}",
            )
        cid = _t(out).strip().splitlines()[-1] if _t(out).strip() else spec.name

        pre = self.inspect(cid)
        evidence = inspect_evidence(pre) if pre else {}
        problems = (
            verify_inspect(
                spec.profile, pre, image_id=spec.image, argv=list(spec.argv),
                workdir=spec.workdir, entrypoint=spec.entrypoint,
            )
            if (pre and verify_profile)
            else ([] if pre else ["docker inspect of the created container failed"])
        )
        if problems:
            cleanup = self.remove(cid)
            return finish(
                exit_status=None, stdout="", stderr="", timed_out=False,
                started_utc=None, ended_utc=None, elapsed_s=None,
                container_id=cid, profile_verified=False, profile_problems=problems,
                inspect=evidence, cleanup=cleanup,
                error="profile/command verification failed; container removed unstarted",
            )

        started = utc_now()
        t0 = self._clock()
        rc, out, err, problem = self._call(["docker", "start", "-a", cid], outer_timeout_s)
        elapsed = round(self._clock() - t0, 6)
        ended = utc_now()
        timed_out = problem is not None and problem.startswith("timeout")

        post = self.inspect(cid)
        st = (post or {}).get("State") or {}
        state = {
            k: st.get(k)
            for k in ("Status", "ExitCode", "OOMKilled", "StartedAt", "FinishedAt", "Error")
        }
        exit_status = None
        error = problem
        if not timed_out and st.get("Status") == "exited" and isinstance(st.get("ExitCode"), int):
            exit_status = st["ExitCode"]
            if rc is not None and rc != exit_status:
                error = f"docker start -a returned {rc} but the container exit code is {exit_status}"
        elif not timed_out and error is None:
            error = f"container state after start: {state}"

        cleanup = self.remove(cid)
        return finish(
            exit_status=exit_status, stdout=_t(out), stderr=_t(err), timed_out=timed_out,
            started_utc=started, ended_utc=ended, elapsed_s=elapsed,
            container_id=cid, profile_verified=verify_profile, profile_problems=[],
            inspect=evidence, state=state, cli_returncode=rc, cleanup=cleanup, error=error,
        )

    # --- daemon-level checks ------------------------------------------------

    def study_containers(self) -> list[str] | None:
        """Any container, running or not, carrying this study's label. None if unknown."""
        rc, out, _err, _ = self._call(
            ["docker", "ps", "-a", "-q", "--no-trunc", "--filter", f"label={LABEL_STUDY}={STUDY_ID}"],
            DOCKER_CALL_TIMEOUT_S,
        )
        return None if rc != 0 else [x for x in _t(out).split() if x]

    def running_containers(self) -> list[dict[str, str]] | None:
        """Every running container on the daemon (IDs, names, images). None if unknown."""
        rc, out, _err, _ = self._call(
            ["docker", "ps", "--no-trunc", "--format", "{{.ID}}\t{{.Names}}\t{{.Image}}"],
            DOCKER_CALL_TIMEOUT_S,
        )
        if rc != 0:
            return None
        rows = []
        for line in _t(out).splitlines():
            parts = line.split("\t")
            if len(parts) == 3:
                rows.append({"id": parts[0], "name": parts[1], "image": parts[2]})
        return rows

    def daemon_info(self) -> dict[str, Any] | None:
        rc, out, _err, _ = self._call(["docker", "info", "--format", "{{json .}}"], DOCKER_CALL_TIMEOUT_S)
        if rc != 0:
            return None
        try:
            info = json.loads(_t(out))
        except json.JSONDecodeError:
            return None
        return {
            "ncpu": info.get("NCPU"),
            "mem_total": info.get("MemTotal"),
            "kernel": info.get("KernelVersion"),
            "server_version": info.get("ServerVersion"),
            "cgroup_version": info.get("CgroupVersion"),
            "cgroup_driver": info.get("CgroupDriver"),
            "operating_system": info.get("OperatingSystem"),
            "name": info.get("Name"),
            "id": info.get("ID"),
        }

    def image_id(self, ref: str) -> str | None:
        rc, out, _err, _ = self._call(
            ["docker", "image", "inspect", "--format", "{{.Id}}", ref], DOCKER_CALL_TIMEOUT_S
        )
        return _t(out).strip() if rc == 0 else None
