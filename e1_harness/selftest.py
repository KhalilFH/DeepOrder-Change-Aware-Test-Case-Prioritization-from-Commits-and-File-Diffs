"""Docker-dependent self-checks for the E1 runner.

The unit suite injects a fake executor, so it proves the orchestration is right
but nothing about the real one. This script exercises `DockerExecutor` against a
built subject image and checks the three properties that cannot be faked:

  1. **Reset isolation.** State written by one attempt must not be visible to
     the next. Each attempt is its own `docker run --rm`; this verifies the
     claim instead of assuming it.
  2. **Direct execution agrees with replay.** A policy run with real early
     stopping must reach the same decision as the reducer replaying that same
     recorded trace. This is the structural half of the plan's direct-policy
     checks (Experiment 1, step 3).
  3. **No container outlives its attempt.** A timeout kills only the local
     `docker` CLI; the container would keep running into later attempts. This
     times an attempt out for real and checks `docker ps` finds nothing by its
     name afterwards. It also reports whether the container was still running
     before cleanup, i.e. whether the cleanup was needed on this host.

Nothing written here is experimental data: it uses its own episode names and a
scratch ledger, and it is not part of any measured block range.

Usage:
    python e1_harness/selftest.py [image] [workdir]
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ledger import Ledger, V_BAD, V_OK, exit_statuses_for, read_records, verify_chain
from policy import P1, P3, reduce_block
from runner import DockerExecutor, Manifest, Runner

DEFAULT_IMAGE = "grpc1859-bug"
DEFAULT_WORKDIR = "/go"


def check_reset_isolation(image: str, workdir: str) -> bool:
    print("=== reset isolation")
    with tempfile.TemporaryDirectory() as tmp:
        manifest = Manifest(
            episode="SELFTEST-reset",
            images={V_BAD: image, V_OK: image},
            workdir=workdir,
            argv=[
                "sh", "-c",
                "if [ -e /tmp/e1_marker ]; then echo LEAKED; else echo ABSENT; fi; "
                "touch /tmp/e1_marker; echo $(hostname)",
            ],
            timeout_s=60,
            condition="selftest",
        )
        ledger_path = Path(tmp) / "reset.jsonl"
        with Ledger(ledger_path) as led:
            Runner(manifest).run_block(led, block=1, seed=1)

        rows = read_records(ledger_path)
        verdicts = [r["stdout"].split()[0] for r in rows]
        hosts = {r["stdout"].split()[1] for r in rows}

    leaked = [i for i, v in enumerate(verdicts, 1) if v != "ABSENT"]
    ok = not leaked and len(hosts) == len(verdicts)
    print(f"    marker absent on {verdicts.count('ABSENT')}/{len(verdicts)} attempts")
    print(f"    distinct containers: {len(hosts)}/{len(verdicts)}")
    print("    OK" if ok else f"    FAILED: state leaked into attempts {leaked}")
    return ok


def check_direct_matches_replay(image: str, workdir: str) -> bool:
    """Run both policies for real against deterministic commands and compare."""
    print("=== direct execution vs replay")
    cases = [
        ("always-pass", "exit 0"),
        ("always-fail", "exit 1"),
    ]
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        for name, script in cases:
            for policy in (P1, P3):
                manifest = Manifest(
                    episode=f"SELFTEST-{name}-{policy}",
                    images={V_BAD: image, V_OK: image},
                    workdir=workdir,
                    argv=["sh", "-c", script],
                    timeout_s=60,
                    condition="selftest",
                )
                path = Path(tmp) / f"{name}-{policy}.jsonl"
                runner = Runner(manifest)
                with Ledger(path) as led:
                    direct = runner.run_policy_direct(
                        led, block=90, version=V_BAD, policy=policy, reserved_from=90
                    )
                rows = read_records(path)
                replayed = reduce_block(
                    policy,
                    exit_statuses_for(rows, manifest.episode, 90, V_BAD),
                )
                agree = (
                    direct.decision.final_status == replayed.final_status
                    and direct.decision.attempts_consumed == replayed.attempts_consumed
                )
                ok = ok and agree
                print(
                    f"    {name:12s} {policy:10s} "
                    f"direct={direct.decision.final_status}/{direct.decision.attempts_consumed} "
                    f"replay={replayed.final_status}/{replayed.attempts_consumed} "
                    f"{'OK' if agree else 'MISMATCH'}"
                )
                verify_chain(path)
    return ok


def _containers_named(name: str) -> list[str]:
    done = subprocess.run(
        ["docker", "ps", "-a", "--filter", f"name=^{name}$", "--format", "{{.Names}} {{.State}}"],
        capture_output=True, text=True, timeout=30, check=True,
    )
    return done.stdout.splitlines()


def check_timeout_leaves_no_container(image: str, workdir: str) -> bool:
    print("=== timed-out attempt leaves no container")
    before_cleanup: list[str] = []

    def observing_run(argv, **kw):
        # Look just before `docker rm -f`: is the container still there?
        if argv[:2] == ["docker", "rm"]:
            before_cleanup.extend(_containers_named(argv[-1]))
        return subprocess.run(argv, **kw)

    with tempfile.TemporaryDirectory() as tmp:
        manifest = Manifest(
            episode="SELFTEST-timeout",
            images={V_BAD: image, V_OK: image},
            workdir=workdir,
            argv=["sh", "-c", "sleep 300"],
            timeout_s=5,
            condition="selftest",
        )
        with Ledger(Path(tmp) / "timeout.jsonl") as led:
            record = Runner(manifest, DockerExecutor(run=observing_run)).run_attempt(
                led, block=1, version=V_BAD, attempt=1
            )

    name = record.extra["container"]
    cleanup = record.extra.get("cleanup", {})
    after = _containers_named(name)
    ok = record.timed_out and cleanup.get("exit_status") == 0 and not after
    print(f"    container {name}")
    print(f"    timed out: {record.timed_out}; docker rm -f exit: {cleanup.get('exit_status')}")
    print(f"    before cleanup: {before_cleanup or 'gone'}; after: {after or 'gone'}")
    print("    OK" if ok else "    FAILED: the container outlived its attempt")
    return ok


def main() -> int:
    image = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_IMAGE
    workdir = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_WORKDIR
    print(f"image={image} workdir={workdir}\n")
    results = [
        check_reset_isolation(image, workdir),
        check_direct_matches_replay(image, workdir),
        check_timeout_leaves_no_container(image, workdir),
    ]
    print("\nALL SELF-CHECKS PASSED" if all(results) else "\nSELF-CHECKS FAILED")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
