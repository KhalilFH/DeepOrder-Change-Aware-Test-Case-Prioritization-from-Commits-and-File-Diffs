"""Test doubles: a scripted Docker CLI and a scripted executor. No Docker needed."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from c1_harness.dockerexec import ContainerSpec, ExecResult
from c1_harness.subjects import V_BAD, V_OK, Subject


def go_pass(test: str) -> str:
    return f"=== RUN   {test}\n--- PASS: {test} (0.00s)\nPASS\n"


def go_fail(test: str, line: str) -> str:
    return f"=== RUN   {test}\n    x_test.go:1: {line}\n--- FAIL: {test} (30.00s)\nFAIL\n"


K8S_FOCAL = go_fail("TestPopReleaseLock", "Timeout after 30s")
K8S_OTHER = go_fail("TestPopReleaseLock", "something else")
K8S_PASS = go_pass("TestPopReleaseLock")


def subject(sid: str = "k8s26980", outer: int = 90) -> Subject:
    return Subject(
        sid=sid, project={"k8s26980": "kubernetes", "istio17860": "istio"}.get(sid, "etcd"),
        images={V_BAD: f"sha256:{'b' * 63}{sid[-1]}", V_OK: f"sha256:{'f' * 63}{sid[-1]}"},
        argv=("/go/gobench.test", "-test.v"), workdir="/w", inner_timeout_s=60, outer_timeout_s=outer,
        disposition="READY_HISTORICAL", enrolled=True,
    )


@dataclass
class FakeExecutor:
    """Stands in for DockerExecutor. `script(spec)` -> (exit, stdout, timed_out)."""

    script: Callable[[ContainerSpec], tuple[int | None, str, bool]]
    verified: bool = True
    cleanup_ok: bool = True
    runs: list[ContainerSpec] = field(default_factory=list)
    running: list[dict[str, str]] = field(default_factory=list)
    leftovers: list[str] = field(default_factory=list)

    def run(self, spec: ContainerSpec, outer_timeout_s: float, *, verify_profile: bool = True) -> ExecResult:
        self.runs.append(spec)
        exit_status, stdout, timed_out = self.script(spec)
        return ExecResult(
            exit_status=exit_status, stdout=stdout, stderr="", timed_out=timed_out,
            started_utc="2026-01-01T00:00:00.000000Z", ended_utc="2026-01-01T00:00:01.000000Z", elapsed_s=1.0,
            job_started_utc="2026-01-01T00:00:00.000000Z", job_ended_utc="2026-01-01T00:00:01.500000Z",
            job_elapsed_s=1.5, create_argv=spec.create_argv(), container_id=f"cid-{len(self.runs)}",
            profile_verified=self.verified, profile_problems=[] if self.verified else ["HostConfig.CpuQuota: wrong"],
            inspect={"cpu_quota": spec.profile.cpu_quota, "cpu_period": spec.profile.cpu_period},
            cleanup={"verified_absent": self.cleanup_ok},
        )

    def image_id(self, ref: str) -> str | None:
        return "sha256:" + "a" * 64

    def daemon_info(self) -> dict[str, Any]:
        return {"ncpu": 16}

    def study_containers(self) -> list[str]:
        return list(self.leftovers)

    def running_containers(self) -> list[dict[str, str]]:
        return list(self.running)


PROBE_OK = {
    "R": "CPU_MAX=max 100000\nCPUSET=0-15\nNPROC=16\nGOMAXPROCS_ENV=16\nBEFORE_usage_usec=0\nBEFORE_nr_throttled=0\n"
         "WALL_T0=100.00\nWALL_T1=103.00\nAFTER_usage_usec=11200000\nAFTER_nr_throttled=0\n",
    "L": "CPU_MAX=200000 100000\nCPUSET=0-15\nNPROC=16\nGOMAXPROCS_ENV=16\nBEFORE_usage_usec=0\nBEFORE_nr_throttled=0\n"
         "WALL_T0=100.00\nWALL_T1=103.00\nAFTER_usage_usec=6050000\nAFTER_nr_throttled=30\n",
}


def probe_aware(script: Callable[[ContainerSpec], tuple[int | None, str, bool]]):
    """Wrap a subject script so session-probe helpers get plausible cgroup output."""
    def inner(spec: ContainerSpec):
        if spec.entrypoint == "sh" and "cpu.max" in " ".join(spec.argv):
            return 0, PROBE_OK[spec.profile.pid], False
        return script(spec)
    return inner


class FakeCLI:
    """Scripted `subprocess.run` for DockerExecutor: records every argv."""

    def __init__(self, *, inspect: dict[str, Any], start: Any = 0, stdout: bytes = b"out", create_rc: int = 0,
                 absent_after_rm: bool = True):
        self.calls: list[list[str]] = []
        self.inspect_doc = inspect
        self.start = start
        self.stdout = stdout
        self.create_rc = create_rc
        self.absent_after_rm = absent_after_rm
        self.removed: set[str] = set()

    def __call__(self, argv, capture_output=True, timeout=None):
        self.calls.append(list(argv))
        cmd = argv[1]
        if cmd == "create":
            return subprocess.CompletedProcess(argv, self.create_rc, b"cid123\n" if self.create_rc == 0 else b"", b"err")
        if cmd == "inspect":
            doc = dict(self.inspect_doc)
            if any(c[1] == "start" for c in self.calls):
                doc["State"] = {"Status": "exited", "ExitCode": self.start if isinstance(self.start, int) else 0}
            return subprocess.CompletedProcess(argv, 0, json.dumps([doc]).encode(), b"")
        if cmd == "start":
            if self.start == "timeout":
                raise subprocess.TimeoutExpired(argv, timeout, output=b"partial", stderr=b"")
            return subprocess.CompletedProcess(argv, self.start, self.stdout, b"")
        if cmd == "rm":
            self.removed.add(argv[-1])
            return subprocess.CompletedProcess(argv, 0, argv[-1].encode(), b"")
        if cmd == "ps":
            gone = self.absent_after_rm
            return subprocess.CompletedProcess(argv, 0, b"" if gone else b"cid123\n", b"")
        raise AssertionError(f"unexpected docker call {argv}")


def inspect_doc(profile, image: str, argv: list[str], workdir: str, **overrides) -> dict[str, Any]:
    host = {"CpuQuota": profile.cpu_quota, "CpuPeriod": profile.cpu_period, "NanoCpus": 0, "CpusetCpus": "",
            "CpuShares": 0, "Memory": 0, "NetworkMode": "bridge"}
    cfg = {"Env": ["PATH=/usr/bin", "GOMAXPROCS=16"], "Cmd": list(argv), "WorkingDir": workdir, "Entrypoint": None, "Tty": False}
    doc = {"Id": "cid123", "Image": image, "HostConfig": host, "Config": cfg}
    for k, v in overrides.items():
        section, _, key = k.partition("__")
        doc[section][key] = v
    return doc


def tmp_study(tmp: Path) -> Path:
    (tmp / "measured").mkdir(parents=True, exist_ok=True)
    return tmp
