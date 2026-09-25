"""Phase 1 artifact checks inside the existing images, and helper profile probes.

Authorized preparation work (HANDOFF step 2): source/blob checks for the six
fixed subjects only. Each image is checked once, in a fresh helper container
that runs `sh -c` with a read-only script: it never runs the subject test.
Expected values are the counterpart blobs recorded in the restoration records
and `task5_artifacts/verify.sh`; they are compared, not copied into the result.

Every container is charged to the preparation stage at 16 vCPUs (unrestricted
basis), including failed ones.
"""

from __future__ import annotations

import json
import secrets
from pathlib import Path
from typing import Any

from c1_harness import SUBJECT_ORDER
from c1_harness.budget import ResourceLedger
from c1_harness.dockerexec import ContainerSpec, DockerExecutor
from c1_harness.profiles import (
    GO_PROBE_SCRIPT,
    GO_PROBE_SOURCE,
    PROBE_SCRIPT,
    PROFILES,
    evaluate_cgroup_probe,
    evaluate_go_probe,
)

E = "/go/src/github.com/coreos/etcd"
G = "/go/src/google.golang.org/grpc"
I = "/go/src/istio.io/istio"
K = "/go/src/k8s.io/kubernetes"

EXPECTED: dict[str, dict[str, Any]] = {
    "etcd5509": {
        "repo": E, "commit": "9ed3b446cadd9f43734d9eed9dcb03f3b12567a5",
        "pkg": "clientv3/integration",
        "focal": {"clientv3/remote_client.go": ("b8209b8a5e2ebefcac268b64e0a62482266b9a3d", "b511163058cb31ebab14f42869e6e99d1b9dff68")},
        "same": ["clientv3/integration/kv_test.go", "test"],
        "source": "task5_etcd5509_restoration.md Step 1; task5_artifacts/verify.sh",
    },
    "etcd7492": {
        "repo": E, "commit": "148c923c72c4aa9207173c03b775e2c0b8754067",
        "pkg": "auth",
        "focal": {"auth/simple_token.go": ("7aa8079477132dec7447507a310394b49fa8ef33", "ff48c5140cbe103af6297990fd406a641d529631")},
        "same": ["auth/store_test.go", "test"],
        "source": "task5_etcd7492_restoration.md Step 1; task5_artifacts/verify.sh",
    },
    "grpc1859": {
        "repo": G, "commit": "484b3ebb4ab56d3decc8240d599718bdbefcf7eb",
        "pkg": "test",
        "focal": {
            "transport/http2_client.go": ("717e4192ea13547ffe323613d3d4945c9c5a9b00", "56b434ef37fed92f87811d9d08e3c9c834cf9971"),
            "transport/http2_server.go": ("5233d6f3db6bd29622f694a59befd50d9e6d7365", "24c2c7e18c48b007dd8a060cb4e09bfab1a55ebd"),
        },
        "same": ["test/end2end_test.go"],
        "source": "task5_grpc1859_restoration.md Step 1; task5_artifacts/verify.sh",
    },
    "grpc2391": {
        "repo": G, "commit": "ff2aa05958775030998dbe2f9bccbe2af324adf4",
        "pkg": "test",
        "focal": {"clientconn.go": ("e74f8e40ea3c697b5479cf020a97a82c5cabb897", "d04043137a7ed5bfa5fe9df401e064e693573569")},
        "same": ["test/end2end_test.go", "go.mod", "go.sum"],
        "source": "task5_grpc2391_restoration.md Step 1; task5_artifacts/grpc2391/blob_check_*.txt",
    },
    "istio17860": {
        "repo": I, "commit": "c6e9130227497ab064dd571a1409236d17aa2ef3",
        "pkg": "pkg/envoy",
        "focal": {"pkg/envoy/agent.go": ("f6644419ad8c6bf453fd120cadb75714842b4420", "638578e3341536ebdf3b93e1699ce2568d05d83b")},
        "same": ["pkg/envoy/agent_test.go", "go.mod", "go.sum"],
        "source": "task5_istio17860_restoration.md Step 1; task5_artifacts/istio17860/blob_check_*.txt",
    },
    "k8s26980": {
        "repo": K, "commit": "628af356b8c83f98ee3b50dfcf8b0250816a5581",
        "pkg": "pkg/controller/framework",
        "focal": {"pkg/controller/framework/shared_informer.go": ("ce9ddf2c7140ff2d9d9752ac8626cef1bb01a236", "c557bf97548a4e7054b05e0b158ba194b7dd59f2")},
        "same": ["pkg/controller/framework/processor_listener_test.go", "Godeps/Godeps.json"],
        "source": "task5_k8s26980_restoration.md Step 1; task5_artifacts/k8s26980/blob_check_*.txt",
    },
}


def check_script(exp: dict[str, Any]) -> str:
    """Read-only in-image facts as KEY=VALUE lines. Runs no test."""
    files = sorted(set(exp["focal"]) | set(exp["same"]))
    repo = exp["repo"]
    return " ; ".join(
        [
            f"cd {repo}",
            "echo COMMIT=$(git rev-parse HEAD)",
            *[f"echo BLOB:{f}=$(git hash-object {f} 2>/dev/null)" for f in files],
            # every tracked change and untracked file in the whole tree
            "git status --porcelain --untracked-files=all | sed 's/^/PORCELAIN=/'",
            # every test file of the target package, so equal treatment is not
            # inferred from one file
            f"for f in $(ls {exp['pkg']}/*_test.go | sort); do echo TESTFILE:$f=$(git hash-object $f); done",
            "echo BINARY_SHA256=$(sha256sum /go/gobench.test | cut -d' ' -f1)",
            "echo BINARY_BYTES=$(stat -c %s /go/gobench.test)",
            "echo GO_VERSION=$(go version)",
            # dependency identity outside the repository: GOPATH sources, module list
            f"echo GOPATH_DEPS_DIGEST=$(find /go/src -type f -not -path '{repo}/*' | LC_ALL=C sort | xargs -r sha256sum | sha256sum | cut -d' ' -f1)",
            f"echo GOPATH_DEPS_FILES=$(find /go/src -type f -not -path '{repo}/*' | wc -l)",
            f"find /go/src -name .git -type d -not -path '{repo}/*' | LC_ALL=C sort | while read d; do echo DEPREPO:$(dirname $d)=$(git -C $(dirname $d) rev-parse HEAD); done",
            "[ -f /go/dep_versions.txt ] && echo DEP_VERSIONS_SHA256=$(sha256sum /go/dep_versions.txt | cut -d' ' -f1)",
            "[ -d /go/pkg/mod ] && echo MODULE_DIRS_DIGEST=$(find /go/pkg/mod -mindepth 1 -maxdepth 5 -type d -name '*@*' | LC_ALL=C sort | sha256sum | cut -d' ' -f1)",
            "[ -d /go/pkg/mod ] && echo MODULE_DIRS=$(find /go/pkg/mod -mindepth 1 -maxdepth 5 -type d -name '*@*' | wc -l)",
            "[ -f go.sum ] && (GOPROXY=off go list -m all 2>/dev/null | sha256sum | cut -d' ' -f1 | sed 's/^/GO_LIST_M_ALL_SHA256=/')",
            "[ -d vendor ] && echo VENDOR_DIR=present",
            "[ -d cmd/vendor ] && echo CMD_VENDOR_DIR=present",
            "echo END=1",
        ]
    )


def parse_facts(text: str) -> dict[str, Any]:
    facts: dict[str, Any] = {"porcelain": [], "blob": {}, "testfile": {}, "deprepo": {}}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key == "PORCELAIN":
            facts["porcelain"].append(value)
        elif key.startswith("BLOB:"):
            facts["blob"][key[5:]] = value
        elif key.startswith("TESTFILE:"):
            facts["testfile"][key[9:]] = value
        elif key.startswith("DEPREPO:"):
            facts["deprepo"][key[8:]] = value
        else:
            facts[key.lower()] = value
    return facts


def evaluate_pair(subject: str, bug: dict[str, Any], fix: dict[str, Any]) -> dict[str, Any]:
    exp = EXPECTED[subject]
    checks: list[dict[str, Any]] = []

    def check(name: str, ok: bool, detail: Any) -> None:
        checks.append({"check": name, "passed": bool(ok), "detail": detail})

    check("both containers completed", bug.get("end") == "1" and fix.get("end") == "1", None)
    check("commit (bug, fix)", bug.get("commit") == exp["commit"] == fix.get("commit"),
          [bug.get("commit"), fix.get("commit"), exp["commit"]])
    for f, (want_bug, want_fix) in exp["focal"].items():
        check(f"focal blob {f}", bug["blob"].get(f) == want_bug and fix["blob"].get(f) == want_fix,
              {"bug": bug["blob"].get(f), "fix": fix["blob"].get(f), "want": [want_bug, want_fix]})
    for f in exp["same"]:
        b, x = bug["blob"].get(f), fix["blob"].get(f)
        check(f"identical {f}", bool(b) and b == x, {"bug": b, "fix": x})
    check("all target-package test files identical", bug["testfile"] == fix["testfile"] and bool(bug["testfile"]),
          {"count": len(bug["testfile"]), "differ": sorted(k for k in set(bug["testfile"]) | set(fix["testfile"])
                                                        if bug["testfile"].get(k) != fix["testfile"].get(k))})
    b_tree, f_tree = set(bug["porcelain"]), set(fix["porcelain"])
    delta = sorted(b_tree ^ f_tree)
    allowed = {f" M {f}" for f in exp["focal"]}
    inert = {e for e in delta if e.startswith("??") and e.endswith("bug_patch.diff")}
    check("tree delta is the focal production change only", set(delta) - inert == allowed,
          {"bug_minus_fix": sorted(b_tree - f_tree), "fix_minus_bug": sorted(f_tree - b_tree),
           "inert_untracked": sorted(inert), "common_changes": sorted(b_tree & f_tree)})
    for key in ("gopath_deps_digest", "dep_versions_sha256", "module_dirs_digest", "go_list_m_all_sha256", "go_version"):
        if bug.get(key) is not None or fix.get(key) is not None:
            check(f"identical {key}", bug.get(key) == fix.get(key), [bug.get(key), fix.get(key)])
    check("identical dependency repositories", bug["deprepo"] == fix["deprepo"], {"count": len(bug["deprepo"])})
    check("test binaries differ (different product code)", bug.get("binary_sha256") != fix.get("binary_sha256"),
          [bug.get("binary_sha256"), fix.get("binary_sha256")])
    return {"subject": subject, "passed": all(c["passed"] for c in checks), "checks": checks,
            "expected_source": exp["source"]}


def _helper(executor: DockerExecutor, ledger: ResourceLedger, *, stage: str, job_id: str, image_id: str,
            workdir: str, script: str, profile_id: str, basis_vcpus: float, basis_reason: str,
            extra_env: tuple[tuple[str, str], ...] = (), timeout_s: float = 300) -> tuple[Any, dict[str, Any]]:
    spec = ContainerSpec(
        name=f"c1-{stage}-{job_id}-{secrets.token_hex(4)}",
        image=image_id, workdir=workdir, argv=("-c", script), profile=PROFILES[profile_id],
        attempt_id=job_id, stage=stage, entrypoint="sh", extra_env=extra_env,
    )
    res = executor.run(spec, timeout_s)
    charge = ledger.charge(
        stage=stage, job_id=job_id, kind_of_job="helper", basis_vcpus=basis_vcpus, basis_reason=basis_reason,
        job_elapsed_s=res.job_elapsed_s, gap_s=0.0, started_utc=res.job_started_utc, ended_utc=res.job_ended_utc,
        attempt_elapsed_s=res.elapsed_s,
    )
    return res, charge


def run_image_checks(executor: DockerExecutor, ledger: ResourceLedger, out_dir: Path) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for subject in SUBJECT_ORDER:
        exp = EXPECTED[subject]
        facts = {}
        for variant in ("bug", "fix"):
            image = executor.image_id(f"{subject}-{variant}")
            if image is None:
                facts[variant] = {"error": "image not present", "porcelain": [], "blob": {}, "testfile": {}, "deprepo": {}}
                continue
            res, charge = _helper(
                executor, ledger, stage="preparation", job_id=f"prep-imagecheck-{subject}-{variant}",
                image_id=image, workdir=exp["repo"], script=check_script(exp), profile_id="R",
                basis_vcpus=16, basis_reason="unrestricted helper (protocol 6)",
            )
            (out_dir / f"imagecheck_{subject}_{variant}.log").write_text(
                res.stdout + ("\n--- stderr ---\n" + res.stderr if res.stderr else ""), encoding="utf-8", newline="\n"
            )
            f = parse_facts(res.stdout)
            f.update(image_id=image, exit_status=res.exit_status, cleanup_ok=res.cleanup_ok,
                     charge_seq=charge["seq"], error=res.error)
            facts[variant] = f
        results[subject] = {"facts": facts, "evaluation": evaluate_pair(subject, facts["bug"], facts["fix"])}
    return results


def run_profile_probes(executor: DockerExecutor, ledger: ResourceLedger, stage: str, tag: str) -> dict[str, Any]:
    """Alpine cgroup/throttle probe per profile, plus a Go-runtime probe in each
    subject toolchain (1.10, 1.12, 1.13) per profile."""
    out: dict[str, Any] = {"cgroup": {}, "go": {}}
    alpine = executor.image_id("alpine:latest")
    for pid, profile in PROFILES.items():
        if alpine is None:
            out["cgroup"][pid] = {"passed": False, "problems": ["alpine:latest not present"]}
            continue
        res, charge = _helper(
            executor, ledger, stage=stage, job_id=f"{tag}-cgroup-{pid}", image_id=alpine, workdir="/",
            script=PROBE_SCRIPT, profile_id=pid, basis_vcpus=16,
            basis_reason="profile probe charged at 16: enforcement is what it verifies",
            timeout_s=60,
        )
        ev = evaluate_cgroup_probe(profile, res.stdout)
        ev.update(raw=res.stdout, exit_status=res.exit_status, cleanup_ok=res.cleanup_ok,
                  inspect=res.inspect, profile_problems=res.profile_problems, charge_seq=charge["seq"])
        out["cgroup"][pid] = ev
    for image_tag, go in (("etcd5509-fix", "1.10"), ("k8s26980-fix", "1.12"), ("etcd7492-fix", "1.13")):
        image = executor.image_id(image_tag)
        for pid, profile in PROFILES.items():
            key = f"go{go}-{pid}"
            if image is None:
                out["go"][key] = {"passed": False, "problems": [f"{image_tag} not present"]}
                continue
            res, charge = _helper(
                executor, ledger, stage=stage, job_id=f"{tag}-go{go}-{pid}", image_id=image, workdir="/",
                script=GO_PROBE_SCRIPT, profile_id=pid, basis_vcpus=16,
                basis_reason="profile probe charged at 16: enforcement is what it verifies",
                extra_env=(("C1_GO_PROBE", GO_PROBE_SOURCE),), timeout_s=120,
            )
            ev = evaluate_go_probe(profile, res.stdout)
            ev.update(image=image_tag, image_id=image, raw=res.stdout, stderr=res.stderr[-2000:],
                      exit_status=res.exit_status, cleanup_ok=res.cleanup_ok, charge_seq=charge["seq"])
            out["go"][key] = ev
    out["passed"] = all(v["passed"] for v in out["cgroup"].values()) and all(v["passed"] for v in out["go"].values())
    return out


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


CLOCK_SLEEP_S = 20
CLOCK_SCRIPT = (
    "U0=$(cut -d' ' -f1 /proc/uptime); W0=$(date +%s); "
    f"sleep {CLOCK_SLEEP_S}; "
    "U1=$(cut -d' ' -f1 /proc/uptime); W1=$(date +%s); "
    "echo VM_UPTIME_DELTA=$(awk \"BEGIN{print $U1-$U0}\"); echo VM_WALL_DELTA=$((W1-W0))"
)
"""Environment check, not a design parameter: how fast the VM's clocks run
relative to the host's monotonic clock over a fixed in-VM sleep."""


def run_clock_probe(executor: DockerExecutor, ledger: ResourceLedger, stage: str, tag: str) -> dict[str, Any]:
    from c1_harness.profiles import parse_probe

    alpine = executor.image_id("alpine:latest")
    out: dict[str, Any] = {}
    for pid in ("R", "L"):
        res, charge = _helper(
            executor, ledger, stage=stage, job_id=f"{tag}-clock-{pid}", image_id=alpine, workdir="/",
            script=CLOCK_SCRIPT, profile_id=pid, basis_vcpus=16,
            basis_reason="helper clock probe charged at 16", timeout_s=CLOCK_SLEEP_S + 40,
        )
        v = parse_probe(res.stdout)
        vm = float(v.get("VM_UPTIME_DELTA", "nan"))
        out[pid] = {
            "vm_uptime_delta_s": vm, "vm_wall_delta_s": v.get("VM_WALL_DELTA"),
            "host_elapsed_s": res.elapsed_s, "in_vm_sleep_s": CLOCK_SLEEP_S,
            "host_over_vm_uptime": (res.elapsed_s / vm) if vm == vm and vm else None,
            "exit_status": res.exit_status, "cleanup_ok": res.cleanup_ok, "charge_seq": charge["seq"],
        }
    return out
