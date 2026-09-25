"""The six frozen subject commands, and the execution manifest built from them.

`FROZEN_COMMANDS` transcribes the subject register's table literally: argument
arrays (no shell), working directory and inner/outer timeouts, with the
original regexp spelling. The subject manifest supplies the image IDs and the
enrollment disposition; `load_subjects` refuses a manifest whose commands
disagree with this table, so a command cannot drift by editing a JSON file.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from c1_harness import HARNESS_VERSION, STUDY_DIR, STUDY_ID, SUBJECT_ORDER
from c1_harness.dockerexec import CLEANUP_TIMEOUT_S
from c1_harness.profiles import Profile

SUBJECT_MANIFEST = STUDY_DIR / "subject_manifest.json"

BASE = ("/go/gobench.test", "-test.v", "-test.count", "1")

FROZEN_COMMANDS: dict[str, dict[str, Any]] = {
    "etcd5509": {
        "project": "etcd",
        "argv": [*BASE, "-test.run", "TestKVGetErrConnClosed", "-test.timeout", "45s"],
        "workdir": "/go/src/github.com/coreos/etcd/clientv3/integration",
        "inner_timeout_s": 45, "outer_timeout_s": 60,
    },
    "etcd7492": {
        "project": "etcd",
        "argv": [*BASE, "-test.run", "TestHammerSimpleAuthenticate", "-test.timeout", "50s"],
        "workdir": "/go/src/github.com/coreos/etcd/auth",
        "inner_timeout_s": 50, "outer_timeout_s": 65,
    },
    "grpc1859": {
        "project": "grpc-go",
        "argv": [*BASE, "-test.run", "^TestClientDoesntDeadlockWhileWritingErrornousLargeMessages$",
                 "-test.timeout", "110s", "-only_env", "tcp-clear-v1-balancer"],
        "workdir": "/go/src/google.golang.org/grpc/test",
        "inner_timeout_s": 110, "outer_timeout_s": 120,
    },
    "grpc2391": {
        "project": "grpc-go",
        "argv": [*BASE, "-test.run", "^TestGoAwayThenClose$", "-test.timeout", "60s"],
        "workdir": "/go/src/google.golang.org/grpc/test",
        "inner_timeout_s": 60, "outer_timeout_s": 90,
    },
    "istio17860": {
        "project": "istio",
        "argv": [*BASE, "-test.run", "^TestExitDuringWaitForLive$", "-test.timeout", "30s"],
        "workdir": "/go/src/istio.io/istio/pkg/envoy",
        "inner_timeout_s": 30, "outer_timeout_s": 60,
    },
    "k8s26980": {
        "project": "kubernetes",
        "argv": [*BASE, "-test.run", "^TestPopReleaseLock$", "-test.timeout", "60s"],
        "workdir": "/go/src/k8s.io/kubernetes/pkg/controller/framework",
        "inner_timeout_s": 60, "outer_timeout_s": 90,
    },
}

V_BAD, V_OK = "V_bad", "V_ok"
VARIANT_OF = {"bad": V_BAD, "ok": V_OK}
"""Schedule cell labels (`bad`/`ok`) to E1 ledger version names."""

READY = ("READY_HISTORICAL", "READY_RECONSTRUCTED")


class SubjectError(ValueError):
    pass


@dataclass(frozen=True)
class Subject:
    sid: str
    project: str
    images: dict[str, str]
    argv: tuple[str, ...]
    workdir: str
    inner_timeout_s: int
    outer_timeout_s: int
    disposition: str
    enrolled: bool

    def execution_manifest(self, profile: Profile, stage: str) -> dict[str, Any]:
        """What every attempt of this subject/profile/stage is bound to."""
        return {
            "study_id": STUDY_ID,
            "harness_version": HARNESS_VERSION,
            "stage": stage,
            "subject": self.sid,
            "images": dict(self.images),
            "workdir": self.workdir,
            "argv": list(self.argv),
            "inner_timeout_s": self.inner_timeout_s,
            "outer_timeout_s": self.outer_timeout_s,
            "cleanup_timeout_s": CLEANUP_TIMEOUT_S,
            **profile.as_manifest(),
        }


def manifest_sha256(manifest: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load_subjects(path: Path = SUBJECT_MANIFEST) -> dict[str, Subject]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, Subject] = {}
    for sid in SUBJECT_ORDER:
        entry = data["subjects"][sid]
        frozen = FROZEN_COMMANDS[sid]
        ex = entry["execution"]
        for key in ("argv", "workdir", "inner_timeout_s", "outer_timeout_s"):
            if ex[key] != frozen[key]:
                raise SubjectError(f"{sid}: manifest {key} {ex[key]!r} differs from the frozen register {frozen[key]!r}")
        disposition = entry["readiness"]["disposition"]
        out[sid] = Subject(
            sid=sid,
            project=frozen["project"],
            images={V_BAD: entry["variants"][V_BAD]["image_id"], V_OK: entry["variants"][V_OK]["image_id"]},
            argv=tuple(frozen["argv"]),
            workdir=frozen["workdir"],
            inner_timeout_s=frozen["inner_timeout_s"],
            outer_timeout_s=frozen["outer_timeout_s"],
            disposition=disposition,
            enrolled=bool(entry["readiness"]["enrolled"]) and disposition in READY,
        )
    if list(data["subjects"]) != list(SUBJECT_ORDER) and set(data["subjects"]) != set(SUBJECT_ORDER):
        raise SubjectError("subject manifest roster differs from the fixed six")
    return out
