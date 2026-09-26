"""Phase 0 read-only inventory (execution_plan.md).

Starts no container, builds nothing and changes no host or Docker setting. It
records what exists now and marks everything it cannot establish as unknown.
Credential *presence* is recorded as a boolean by variable name; values are
never read into the record.
"""

from __future__ import annotations

import json
import os
import platform
import sys
from pathlib import Path
from typing import Any

from . import CASES, REPO_ROOT, STUDY_DIR
from .common import normalized_sha256, utc_now, write_json
from .proc import run

C1_MANIFEST = REPO_ROOT / "research_runs" / "ci_configuration_2026_09" / "subject_manifest.json"
GO_IMAGE_TAGS = {
    "grpc1859": ("grpc1859-bug", "grpc1859-fix"),
    "k8s26980": ("k8s26980-bug", "k8s26980-fix"),
    "istio17860": ("istio17860-bug", "istio17860-fix"),
}
CREDENTIAL_NAMES = ("ANTHROPIC_API_KEY", "TYPESAFE_API_KEY", "JEV_API_KEY")


def _cmd(argv: list[str], timeout: float = 60) -> dict[str, Any]:
    r = run(argv, timeout_s=timeout)
    return {"argv": argv, "exit_code": r.exit_code, "stdout": r.stdout.strip(), "stderr": r.stderr.strip()[:2000]}


def collect() -> dict[str, Any]:
    inv: dict[str, Any] = {"artifact": "w1_inventory_v1", "collected_utc": utc_now(), "unknowns": []}
    inv["repository"] = {
        "head": _cmd(["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"])["stdout"],
        "branch": _cmd(["git", "-C", str(REPO_ROOT), "rev-parse", "--abbrev-ref", "HEAD"])["stdout"],
        "status_short": _cmd(["git", "-C", str(REPO_ROOT), "status", "--short"])["stdout"].splitlines(),
    }
    inv["host"] = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "os_cpu_count": os.cpu_count(),
        "python": sys.version.split()[0],
    }
    info = _cmd(["docker", "info", "--format", "{{json .}}"])
    docker: dict[str, Any] = {"reachable": info["exit_code"] == 0}
    if info["exit_code"] == 0:
        d = json.loads(info["stdout"])
        docker.update({k: d.get(k) for k in ("NCPU", "MemTotal", "KernelVersion", "OperatingSystem", "ServerVersion",
                                              "CgroupVersion", "CgroupDriver", "Architecture", "Name", "ContainersRunning",
                                              "Containers", "Images")})
        docker["runtimes"] = sorted((d.get("Runtimes") or {}).keys())
        docker["context"] = _cmd(["docker", "context", "show"])["stdout"]
    else:
        inv["unknowns"].append("docker daemon unreachable")
    inv["docker"] = docker
    manifest = json.loads(C1_MANIFEST.read_text(encoding="utf-8")) if C1_MANIFEST.exists() else {"subjects": {}}
    images: dict[str, Any] = {}
    for case, tags in GO_IMAGE_TAGS.items():
        rows = {}
        for tag, variant in zip(tags, ("V_bad", "V_ok")):
            got = _cmd(["docker", "image", "inspect", "--format", "{{.Id}} {{.Created}} {{.Size}}", tag])
            recorded = (manifest["subjects"].get(case, {}).get("variants", {}).get(variant) or {}).get("image_id")
            parts = got["stdout"].split() if got["exit_code"] == 0 else []
            rows[variant] = {
                "tag": tag,
                "present": got["exit_code"] == 0,
                "image_id": parts[0] if parts else None,
                "created": parts[1] if len(parts) > 1 else None,
                "size_bytes": int(parts[2]) if len(parts) > 2 else None,
                "c1_recorded_image_id": recorded,
                "matches_c1_record": bool(parts) and parts[0] == recorded,
            }
            if not rows[variant]["present"]:
                inv["unknowns"].append(f"{case} {variant} image {tag} absent")
        images[case] = rows
    images["pool162"] = {"note": "no existing W1/C1 restoration; source and JDK image must be retrieved (Phase 1)"}
    inv["subject_images"] = images
    inv["running_containers"] = _cmd(["docker", "ps", "--format", "{{.ID}} {{.Image}} {{.Names}}"])["stdout"].splitlines()
    inv["local_toolchains"] = {
        "java": _cmd(["java", "-version"])["stderr"].splitlines()[:1],
        "go_on_host": _cmd(["where", "go"]) ["exit_code"] == 0 if os.name == "nt" else None,
    }
    inv["historical_harnesses"] = {
        name: sorted(p.name for p in (REPO_ROOT / name).glob("*.py"))
        for name in ("c1_harness", "e1_harness")
    }
    inv["source_records"] = {
        "c1_subject_manifest": {"path": "research_runs/ci_configuration_2026_09/subject_manifest.json",
                                "sha256_lf": normalized_sha256(C1_MANIFEST) if C1_MANIFEST.exists() else None},
        "task5_artifacts": "research_runs/ci_sensitivity_2026_09/task5_artifacts/",
    }
    inv["provider_credentials_present"] = {n: bool(os.environ.get(n)) for n in CREDENTIAL_NAMES}
    inv["provider_note"] = (
        "Credential presence only. ANTHROPIC_BASE_URL/Claude Code session variables belong to the coding-agent "
        "session and are not a W1 provider transport (method_contract.md: no coding-agent conversation as a "
        "measured session)."
    )
    inv["roster"] = list(CASES)
    inv["unknowns"] += [
        "container CPU affinity/quota/GOMAXPROCS not probed in inventory (probe runs in Phase 1 environment check)",
        "base-image registry digests of Go subject images unknown (locally built)",
        "host background load not gated; recorded per probe",
    ]
    return inv


def write(path: Path | None = None) -> Path:
    path = path or (STUDY_DIR / "prep" / "inventory.json")
    write_json(path, collect())
    return path
