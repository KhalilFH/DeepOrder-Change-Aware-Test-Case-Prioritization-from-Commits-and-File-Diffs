"""The two frozen CPU profiles, and the checks that they are actually in force.

Protocol section 3: R has no container CPU quota, L has 200000 us of CPU per
100000 us period. Both set `GOMAXPROCS=16` explicitly and leave affinity,
memory, network, test and timeouts identical. A profile label alone changes
nothing, so every attempt's container configuration is inspected *before* it is
started (`verify_inspect`), and the runtime mapping from configuration to cgroup
limits is checked on helper containers (`evaluate_cgroup_probe`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

GOMAXPROCS = "16"
REQUIRED_HOST_CPUS = 16
PERIOD_US = 100000
QUOTA_US = 200000


@dataclass(frozen=True)
class Profile:
    pid: str
    cpu_args: tuple[str, ...]
    cpu_period: int
    cpu_quota: int
    allocated_vcpus: int
    expected_cpu_max: str

    @property
    def docker_args(self) -> tuple[str, ...]:
        """Everything a profile adds to `docker create`. Identical except CPU."""
        return (*self.cpu_args, "-e", f"GOMAXPROCS={GOMAXPROCS}")

    def as_manifest(self) -> dict[str, Any]:
        return {
            "profile": self.pid,
            "docker_args": list(self.docker_args),
            "cpu_period_us": self.cpu_period,
            "cpu_quota_us": self.cpu_quota,
            "gomaxprocs": GOMAXPROCS,
            "allocated_vcpus": self.allocated_vcpus,
            "expected_cgroup_cpu_max": self.expected_cpu_max,
        }


R = Profile("R", (), 0, 0, 16, f"max {PERIOD_US}")
L = Profile(
    "L",
    (f"--cpu-period={PERIOD_US}", f"--cpu-quota={QUOTA_US}"),
    PERIOD_US,
    QUOTA_US,
    2,
    f"{QUOTA_US} {PERIOD_US}",
)
PROFILES: dict[str, Profile] = {"R": R, "L": L}
UNVERIFIED_CHARGE_VCPUS = 16
"""Protocol 6: limited runs are charged at 2 only after enforcement is verified."""


def verify_inspect(
    profile: Profile,
    inspect: Mapping[str, Any],
    *,
    image_id: str,
    argv: list[str],
    workdir: str,
    entrypoint: str | None = None,
) -> list[str]:
    """Problems with a created (not yet started) container. Empty means it matches.

    Checks the configuration the daemon will actually apply, not the argv we
    sent: quota/period, no NanoCpus/cpuset/shares override, GOMAXPROCS exactly
    once, and the frozen image, command and working directory.
    """
    problems: list[str] = []
    host = inspect.get("HostConfig") or {}
    cfg = inspect.get("Config") or {}

    def want(label: str, got: Any, expected: Any) -> None:
        if got != expected:
            problems.append(f"{label}: got {got!r}, want {expected!r}")

    want("HostConfig.CpuQuota", host.get("CpuQuota") or 0, profile.cpu_quota)
    want("HostConfig.CpuPeriod", host.get("CpuPeriod") or 0, profile.cpu_period)
    want("HostConfig.NanoCpus", host.get("NanoCpus") or 0, 0)
    want("HostConfig.CpusetCpus", host.get("CpusetCpus") or "", "")
    want("HostConfig.CpuShares", host.get("CpuShares") or 0, 0)
    want("HostConfig.Memory", host.get("Memory") or 0, 0)
    env = [e for e in (cfg.get("Env") or []) if e.startswith("GOMAXPROCS=")]
    want("Config.Env GOMAXPROCS", env, [f"GOMAXPROCS={GOMAXPROCS}"])
    want("Image", inspect.get("Image"), image_id)
    want("Config.Cmd", cfg.get("Cmd"), list(argv))
    want("Config.WorkingDir", cfg.get("WorkingDir"), workdir)
    want("Config.Entrypoint", cfg.get("Entrypoint") or None, [entrypoint] if entrypoint else None)
    want("Config.Tty", bool(cfg.get("Tty")), False)
    return problems


def inspect_evidence(inspect: Mapping[str, Any]) -> dict[str, Any]:
    """The small subset of `docker inspect` stored on every attempt."""
    host = inspect.get("HostConfig") or {}
    cfg = inspect.get("Config") or {}
    return {
        "container_id": inspect.get("Id"),
        "image": inspect.get("Image"),
        "cpu_quota": host.get("CpuQuota"),
        "cpu_period": host.get("CpuPeriod"),
        "nano_cpus": host.get("NanoCpus"),
        "cpuset_cpus": host.get("CpusetCpus"),
        "cpu_shares": host.get("CpuShares"),
        "memory": host.get("Memory"),
        "network_mode": host.get("NetworkMode"),
        "gomaxprocs_env": [e for e in (cfg.get("Env") or []) if e.startswith("GOMAXPROCS=")],
        "cmd": cfg.get("Cmd"),
        "working_dir": cfg.get("WorkingDir"),
    }


# --- helper probe -----------------------------------------------------------

PROBE_BUSY_LOOPS = 4
PROBE_SECONDS = 3

PROBE_SCRIPT = (
    "echo CPU_MAX=$(cat /sys/fs/cgroup/cpu.max); "
    "echo CPUSET=$(cat /sys/fs/cgroup/cpuset.cpus.effective); "
    "echo NPROC=$(nproc); echo GOMAXPROCS_ENV=$GOMAXPROCS; "
    "grep -E '^(usage_usec|nr_periods|nr_throttled|throttled_usec) ' /sys/fs/cgroup/cpu.stat | sed 's/^/BEFORE_/;s/ /=/'; "
    "T0=$(cut -d' ' -f1 /proc/uptime); "
    f"P=; for i in $(seq {PROBE_BUSY_LOOPS}); do (while :; do :; done) & P=\"$P $!\"; done; "
    f"sleep {PROBE_SECONDS}; kill $P 2>/dev/null; wait 2>/dev/null; "
    "T1=$(cut -d' ' -f1 /proc/uptime); echo WALL_T0=$T0; echo WALL_T1=$T1; "
    "grep -E '^(usage_usec|nr_periods|nr_throttled|throttled_usec) ' /sys/fs/cgroup/cpu.stat | sed 's/^/AFTER_/;s/ /=/'"
)
"""A non-subject helper: reads the container's own cgroup limits, then runs
four busy loops for three seconds and reads how much CPU the cgroup got."""


def parse_probe(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            k, _, v = line.strip().partition("=")
            out[k] = v
    return out


def evaluate_cgroup_probe(profile: Profile, text: str) -> dict[str, Any]:
    """Decide whether the probe shows the profile actually enforced.

    R must show no quota and more than 2.5 CPUs of throughput from four busy
    loops; L must show `200000 100000`, throttled periods, and at most 2.2 CPUs.
    Both must see all 16 CPUs (quota is bandwidth, not affinity) and the
    explicit GOMAXPROCS.
    """
    v = parse_probe(text)
    problems: list[str] = []
    try:
        usage = (int(v["AFTER_usage_usec"]) - int(v["BEFORE_usage_usec"])) / 1e6
        # /proc/uptime has centisecond resolution; busybox `date` has no %N.
        wall = float(v["WALL_T1"]) - float(v["WALL_T0"])
        throttled = int(v["AFTER_nr_throttled"]) - int(v["BEFORE_nr_throttled"])
        cpus = usage / wall if wall > 0 else None
    except (KeyError, ValueError) as exc:
        return {"passed": False, "problems": [f"unparseable probe output: {exc}"], "values": v}
    if v.get("CPU_MAX") != profile.expected_cpu_max:
        problems.append(f"cpu.max {v.get('CPU_MAX')!r} != {profile.expected_cpu_max!r}")
    if v.get("NPROC") != str(REQUIRED_HOST_CPUS):
        problems.append(f"nproc {v.get('NPROC')!r} != {REQUIRED_HOST_CPUS}")
    if v.get("GOMAXPROCS_ENV") != GOMAXPROCS:
        problems.append(f"GOMAXPROCS env {v.get('GOMAXPROCS_ENV')!r} != {GOMAXPROCS}")
    if profile.cpu_quota:
        if cpus is None or cpus > 2.2:
            problems.append(f"limited profile used {cpus} CPUs, above 2.2")
        if throttled <= 0:
            problems.append("limited profile shows no throttled periods")
    else:
        if cpus is None or cpus < 2.5:
            problems.append(f"reference profile used {cpus} CPUs, below 2.5 for {PROBE_BUSY_LOOPS} busy loops")
    return {
        "passed": not problems,
        "problems": problems,
        "cpu_max": v.get("CPU_MAX"),
        "cpuset_effective": v.get("CPUSET"),
        "nproc": v.get("NPROC"),
        "gomaxprocs_env": v.get("GOMAXPROCS_ENV"),
        "busy_loops": PROBE_BUSY_LOOPS,
        "cpu_seconds": round(usage, 4),
        "wall_seconds": round(wall, 4),
        "observed_cpus": None if cpus is None else round(cpus, 3),
        "throttled_periods": throttled,
    }


GO_PROBE_SOURCE = (
    "package main\n"
    'import ("fmt"; "os"; "runtime")\n'
    "func main() {\n"
    '\tfmt.Printf("GO_VERSION=%s\\nGO_GOMAXPROCS=%d\\nGO_NUMCPU=%d\\nGO_ENV=%s\\n", '
    'runtime.Version(), runtime.GOMAXPROCS(0), runtime.NumCPU(), os.Getenv("GOMAXPROCS"))\n'
    "}\n"
)

GO_PROBE_SCRIPT = (
    "mkdir -p /tmp/c1probe && cd /tmp/c1probe && "
    "printf '%s' \"$C1_GO_PROBE\" > main.go && "
    "GO111MODULE=off go run main.go && "
    "echo CPU_MAX=$(cat /sys/fs/cgroup/cpu.max)"
)
"""Runs a four-line Go program with each subject image's own toolchain to show
the explicit GOMAXPROCS reaches the runtime the test binary was built with."""


def evaluate_go_probe(profile: Profile, text: str) -> dict[str, Any]:
    v = parse_probe(text)
    problems = []
    if v.get("GO_GOMAXPROCS") != GOMAXPROCS:
        problems.append(f"runtime.GOMAXPROCS {v.get('GO_GOMAXPROCS')!r} != {GOMAXPROCS}")
    if v.get("GO_NUMCPU") != str(REQUIRED_HOST_CPUS):
        problems.append(f"runtime.NumCPU {v.get('GO_NUMCPU')!r} != {REQUIRED_HOST_CPUS}")
    if v.get("CPU_MAX") != profile.expected_cpu_max:
        problems.append(f"cpu.max {v.get('CPU_MAX')!r} != {profile.expected_cpu_max!r}")
    return {
        "passed": not problems,
        "problems": problems,
        "go_version": v.get("GO_VERSION"),
        "gomaxprocs": v.get("GO_GOMAXPROCS"),
        "numcpu": v.get("GO_NUMCPU"),
        "cpu_max": v.get("CPU_MAX"),
    }
