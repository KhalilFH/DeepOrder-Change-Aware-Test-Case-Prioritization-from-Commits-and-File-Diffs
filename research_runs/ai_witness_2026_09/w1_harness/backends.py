"""Subject backends: real Docker execution and a scripted fake for offline tests.

A *build* compiles one materialized overlay against one production variant in a
fresh container; its artifact (Go test binary / Java test classes) is hashed.
An *attempt* starts a fresh container from the pinned image, mounts the build
artifact read-only, runs the selected tests and is removed. Both variants of a
pair or triplet use the identical overlay, argv, environment, masks and limits.

Runtime isolation: no network, variant-identifying files masked with an empty
file on BOTH variants, GOMAXPROCS=16 (Go), no CPU-bandwidth limit, one subject
process at a time (the runner is strictly serial).
"""

from __future__ import annotations

import hashlib
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol

from .casespec import GO_INSTRUMENT_FILE, CaseSpec
from .common import W1Error, sha256_bytes, sha256_json, utc_now
from .config import WORK_DIR
from .overlay import Materialized
from .proc import run

BUILD_TIMEOUT_S = 300
BUILD_CLEANUP_S = 30

GO_INSTRUMENT_TEMPLATE = """package {package}

// W1 harness-owned instrumentation, identical on both variants for every arm.
// On a non-zero test exit it prints a full goroutine dump taken after the
// selected tests return. It does not change production code or test logic.

import (
	w1fmt "fmt"
	w1os "os"
	w1runtime "runtime"
	w1testing "testing"
)

func TestMain(m *w1testing.M) {
	code := m.Run()
	if code != 0 {
		buf := make([]byte, 64<<20)
		n := w1runtime.Stack(buf, true)
		w1fmt.Fprintf(w1os.Stderr, "\\nW1-GOROUTINE-DUMP-BEGIN after-nonzero-exit\\n%s\\nW1-GOROUTINE-DUMP-END\\n", buf[:n])
	}
	w1os.Exit(code)
}
"""


def go_instrument_source(package: str) -> str:
    return GO_INSTRUMENT_TEMPLATE.replace("{package}", package)


@dataclass
class BuildResult:
    build_id: str
    case: str
    variant: str
    overlay_sha256: str
    ok: bool
    artifact_sha256: str | None
    artifact_path: str | None
    log: str
    elapsed_s: float
    started_utc: str
    exit_code: int | None
    timed_out: bool = False


@dataclass
class Trace:
    attempt_id: str
    case: str
    variant: str
    overlay_sha256: str
    artifact_sha256: str | None
    argv: list[str]
    exit_code: int | None
    stdout: str
    stderr: str
    elapsed_s: float
    outer_timeout: bool
    cleanup_ok: bool
    started_utc: str
    ended_utc: str
    harness_error: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def text(self) -> str:
        return self.stdout + ("\n" if self.stdout and not self.stdout.endswith("\n") else "") + self.stderr

    def trace_sha256(self) -> str:
        return sha256_bytes(self.text.encode("utf-8"))


class SubjectBackend(Protocol):
    name: str

    def build(self, spec: CaseSpec, variant: str, mat: Materialized, build_id: str) -> BuildResult: ...

    def run(self, spec: CaseSpec, variant: str, build: BuildResult, selection: list[str], attempt_id: str,
            seed: int | None) -> Trace: ...


def _bind(src: Path, dst: str, readonly: bool = False) -> list[str]:
    spec = f"type=bind,src={src},dst={dst}" + (",readonly" if readonly else "")
    return ["--mount", spec]


class DockerBackend:
    """Real execution against the pinned subject images (image IDs from launch config)."""

    name = "docker"

    def __init__(self, image_ids: dict[str, dict[str, str]], work_dir: Path | None = None):
        self.image_ids = image_ids
        self.work = Path(work_dir or (WORK_DIR / "runs"))
        self.work.mkdir(parents=True, exist_ok=True)
        self.empty = self.work / "empty_mask"
        self.empty.write_bytes(b"")

    def _image(self, spec: CaseSpec, variant: str) -> str:
        return self.image_ids[spec.case][variant]

    def build(self, spec: CaseSpec, variant: str, mat: Materialized, build_id: str) -> BuildResult:
        root = self.work / "builds" / build_id / variant
        if root.exists():
            shutil.rmtree(root)
        overlay = root / "overlay"
        out = root / "out"
        overlay.mkdir(parents=True)
        out.mkdir(parents=True)
        for path, content in mat.files.items():
            p = overlay / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(content.encode("utf-8"))
        name = f"w1b-{hashlib.sha256(f'{build_id}/{variant}'.encode()).hexdigest()[:16]}"
        if spec.language == "go":
            instr = overlay / spec.test_dir / GO_INSTRUMENT_FILE
            instr.parent.mkdir(parents=True, exist_ok=True)
            instr.write_bytes(go_instrument_source(spec.package_name or "").encode("utf-8"))
            script = (f"cp -R /w1/overlay/. {spec.repo_root}/ && cd {spec.repo_root} && "
                      f"go test -c -vet=off -o /w1/out/w1.test ./{spec.test_dir}")
            env = ["-e", "GOPROXY=off", "-e", "GOFLAGS="]
        else:
            script = ("cp -R /w1/overlay/. /w1/pool/ && cd /w1/pool && find src/test -name '*.java' | sort > /tmp/t.txt && "
                      "mkdir -p /w1/out/classes && javac --release 8 -nowarn -encoding ISO-8859-1 "
                      "-cp /w1/classes/main:/w1/lib/junit-3.8.2.jar -d /w1/out/classes @/tmp/t.txt")
            env = []
        argv = ["docker", "run", "--rm", "--name", name, "--network", "none", *env,
                *_bind(overlay, "/w1/overlay", True), *_bind(out, "/w1/out"),
                self._image(spec, variant), "sh", "-c", script]
        r = run(argv, timeout_s=BUILD_TIMEOUT_S)
        if r.timed_out:
            self._force_remove(name)
        ok = r.exit_code == 0 and not r.timed_out
        art_sha = None
        art_path = None
        if ok:
            if spec.language == "go":
                binary = out / "w1.test"
                ok = binary.exists()
                if ok:
                    art_sha = sha256_bytes(binary.read_bytes())
                    art_path = str(binary)
            else:
                classes = out / "classes"
                entries = sorted((p.relative_to(classes).as_posix(), sha256_bytes(p.read_bytes()))
                                 for p in classes.rglob("*.class"))
                ok = bool(entries)
                art_sha = sha256_json(entries) if ok else None
                art_path = str(classes)
        return BuildResult(build_id, spec.case, variant, mat.overlay_sha256, ok, art_sha, art_path,
                           (r.stdout + r.stderr)[-20000:], r.elapsed_s, r.started_utc, r.exit_code, r.timed_out)

    def run(self, spec: CaseSpec, variant: str, build: BuildResult, selection: list[str], attempt_id: str,
            seed: int | None) -> Trace:
        if not build.ok or not build.artifact_path:
            raise W1Error("cannot run an unbuilt candidate")
        name = f"w1r-{hashlib.sha256(attempt_id.encode()).hexdigest()[:20]}"
        masks = [a for m in spec.mask_paths for a in _bind(self.empty, m, True)]
        if spec.language == "go":
            regex = "^(" + "|".join(selection) + ")$"
            inner = ["/w1/bin/w1.test", "-test.v", "-test.count", "1", "-test.run", regex,
                     "-test.timeout", f"{spec.inner}s", *spec.extra_run_args]
            argv = ["docker", "run", "--rm", "--name", name, "--network", "none",
                    "-e", "GOMAXPROCS=16", "-e", "GOTRACEBACK=all",
                    *_bind(Path(build.artifact_path), "/w1/bin/w1.test", True), *masks,
                    "-w", f"{spec.repo_root}/{spec.test_dir}", self._image(spec, variant), *inner]
        else:
            inner = ["java", "-Xlog:exceptions=info", "-cp",
                     "/w1/classes/main:/w1/test-classes:/w1/classes/runner:/w1/lib/junit-3.8.2.jar",
                     "w1harness.W1Runner", str(spec.inner), *selection]
            argv = ["docker", "run", "--rm", "--name", name, "--network", "none",
                    *_bind(Path(build.artifact_path), "/w1/test-classes", True), *masks,
                    "-w", spec.repo_root, self._image(spec, variant), *inner]
        r = run(argv, timeout_s=spec.outer)
        cleanup_ok = True
        if r.timed_out:
            cleanup_ok = self._force_remove(name, spec.cleanup)
        else:
            cleanup_ok = self._gone(name, spec.cleanup)
        harness_error = r.error
        if r.exit_code == 125 and not r.timed_out:
            harness_error = "docker run failed (exit 125): " + r.stderr[-500:]
        return Trace(attempt_id, spec.case, variant, build.overlay_sha256, build.artifact_sha256, argv,
                     None if r.timed_out else r.exit_code, r.stdout, r.stderr, r.elapsed_s, r.timed_out,
                     cleanup_ok, r.started_utc, r.ended_utc, harness_error, {"container": name, "seed": seed})

    def _gone(self, name: str, within_s: float = 30) -> bool:
        deadline = time.monotonic() + within_s
        while time.monotonic() < deadline:
            r = run(["docker", "ps", "-a", "-q", "--filter", f"name=^{name}$"], timeout_s=20)
            if r.exit_code == 0 and not r.stdout.strip():
                return True
            time.sleep(0.5)
        return False

    def _force_remove(self, name: str, within_s: float = 30) -> bool:
        run(["docker", "kill", name], timeout_s=20)
        run(["docker", "rm", "-f", name], timeout_s=20)
        return self._gone(name, within_s)

    def probe_environment(self, spec: CaseSpec, variant: str) -> dict[str, Any]:
        """Structural environment probe (not a subject run): CPUs, cgroup quota, affinity, memory."""
        script = ("echo nproc=$(nproc); echo cpu_max=$(cat /sys/fs/cgroup/cpu.max 2>/dev/null); "
                  "grep -E 'Cpus_allowed_list' /proc/self/status; echo mem_max=$(cat /sys/fs/cgroup/memory.max 2>/dev/null); "
                  "echo loadavg=$(cat /proc/loadavg)")
        if spec.language == "java":
            script += "; java -XX:+PrintFlagsFinal -version 2>/dev/null | grep -E ' ActiveProcessorCount ' ; java -version 2>&1 | head -1"
        else:
            script += "; go version; echo GOMAXPROCS_env=$GOMAXPROCS"
        argv = ["docker", "run", "--rm", "--network", "none", "-e", "GOMAXPROCS=16", self._image(spec, variant), "sh", "-c", script]
        r = run(argv, timeout_s=120)
        return {"argv": argv, "exit_code": r.exit_code, "stdout": r.stdout, "stderr": r.stderr[-2000:],
                "elapsed_s": round(r.elapsed_s, 3), "utc": utc_now()}


# ---------------------------------------------------------------------------
# Fake backend for offline tests and dry runs: no containers, deterministic.

FakeOutcome = Callable[[CaseSpec, str, str, list[str], int | None, str], tuple[int | None, str, bool]]
"""(spec, variant, overlay_sha256, selection, seed, attempt_id) -> (exit_code, text, outer_timeout)."""


class FakeBackend:
    name = "fake"

    def __init__(self, outcome: FakeOutcome | None = None, build_fails: set[str] | None = None,
                 elapsed_s: float = 1.0):
        self.outcome = outcome or (lambda spec, v, h, sel, seed, aid: (0, "".join(f"--- PASS: {t}\n" for t in sel) + "PASS\n", False))
        self.build_fails = build_fails or set()
        self.elapsed_s = elapsed_s
        self.builds: list[tuple[str, str, str]] = []
        self.runs: list[tuple[str, str, str]] = []

    def build(self, spec: CaseSpec, variant: str, mat: Materialized, build_id: str) -> BuildResult:
        self.builds.append((spec.case, variant, mat.overlay_sha256))
        ok = mat.overlay_sha256 not in self.build_fails and not any("COMPILE_ERROR" in c for c in mat.files.values())
        art = sha256_json({"fake": mat.overlay_sha256, "variant": variant}) if ok else None
        return BuildResult(build_id, spec.case, variant, mat.overlay_sha256, ok, art, "fake://" + (art or ""),
                           "ok" if ok else "fake compile error", self.elapsed_s, utc_now(), 0 if ok else 2)

    def run(self, spec: CaseSpec, variant: str, build: BuildResult, selection: list[str], attempt_id: str,
            seed: int | None) -> Trace:
        if not build.ok:
            raise W1Error("cannot run an unbuilt candidate")
        self.runs.append((spec.case, variant, build.overlay_sha256))
        code, text, outer = self.outcome(spec, variant, build.overlay_sha256, selection, seed, attempt_id)
        now = utc_now()
        return Trace(attempt_id, spec.case, variant, build.overlay_sha256, build.artifact_sha256,
                     ["fake", spec.case, variant, *selection], code, text, "", self.elapsed_s, outer, True, now, now,
                     None, {"seed": seed})
