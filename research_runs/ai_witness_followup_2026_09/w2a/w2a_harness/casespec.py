"""Per-case execution facts shared by every arm (no oracle material here).

These are runtime launch fields selected from structural restoration facts
(subject_register.md, prep/subjects/<case>/restoration.json), not from outcomes.
Image identities are bound by digest at launch (launch_config.json); tags are
only convenience names.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .config import timeouts


@dataclass(frozen=True)
class CaseSpec:
    case: str
    language: str  # "go" | "java"
    image_tags: dict[str, str]
    repo_root: str  # inside the image
    test_dir: str  # repo-relative directory of the supplied test package
    package_name: str | None  # Go package clause of the test package
    editable_files: tuple[str, ...]  # repo-relative supplied test files that may be edited (insertion-only)
    entry_points: tuple[str, ...]  # supplied focal test entry points, always executed
    extra_run_args: tuple[str, ...] = ()
    production_files: tuple[str, ...] = ()  # repo-relative files changed by the repair
    context_files: tuple[str, ...] = ()  # additional allowed source/test helpers in the packet
    mask_paths: tuple[str, ...] = ()  # absolute in-image paths masked with an empty file on BOTH variants
    new_file_regex: str | None = None  # repo-relative pattern for method-created test files
    max_new_tests: int = 4
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def inner(self) -> int:
        return timeouts(self.case)["inner"]

    @property
    def outer(self) -> int:
        return timeouts(self.case)["outer"]

    @property
    def cleanup(self) -> int:
        return timeouts(self.case)["cleanup"]

    def is_new_file_allowed(self, path: str) -> bool:
        return bool(self.new_file_regex and re.fullmatch(self.new_file_regex, path))


GO_INSTRUMENT_FILE = "zz_w1_harness_instrument_test.go"
"""Harness-owned TestMain added to the test package on both variants for every arm."""

SPECS: dict[str, CaseSpec] = {
    "pool162": CaseSpec(
        case="pool162",
        language="java",
        image_tags={"V_bad": "w1-pool162-bad", "V_ok": "w1-pool162-ok"},
        repo_root="/w1/pool",
        test_dir="src/test/org/apache/commons/pool/impl",
        package_name=None,
        editable_files=(
            "src/test/org/apache/commons/pool/impl/TestGenericObjectPool.java",
            "src/test/org/apache/commons/pool/impl/TestGenericKeyedObjectPool.java",
            "src/test/org/apache/commons/pool/impl/TestStackObjectPool.java",
        ),
        entry_points=(
            "org.apache.commons.pool.impl.TestGenericObjectPool#testWhenExhaustedBlock",
            "org.apache.commons.pool.impl.TestGenericKeyedObjectPool#testWhenExhaustedGrow",
            "org.apache.commons.pool.impl.TestStackObjectPool#testBorrowFromEmptyPoolWithNullFactory",
        ),
        production_files=(
            "src/java/org/apache/commons/pool/impl/GenericObjectPool.java",
            "src/java/org/apache/commons/pool/impl/GenericKeyedObjectPool.java",
        ),
        context_files=(
            "src/java/org/apache/commons/pool/BaseObjectPool.java",
            "src/java/org/apache/commons/pool/ObjectPool.java",
            "src/java/org/apache/commons/pool/PoolableObjectFactory.java",
            "src/java/org/apache/commons/pool/impl/StackObjectPool.java",
            "src/test/org/apache/commons/pool/TestBaseObjectPool.java",
            "src/test/org/apache/commons/pool/TestObjectPool.java",
            "src/test/org/apache/commons/pool/TestKeyedObjectPool.java",
            "src/test/org/apache/commons/pool/TestBaseKeyedObjectPool.java",
        ),
        notes=("Supplied tests are the pre-fix candidates of 280c60ac on both variants; the repair-added test is withheld.",),
    ),
    "grpc1859": CaseSpec(
        case="grpc1859",
        language="go",
        image_tags={"V_bad": "grpc1859-bug", "V_ok": "grpc1859-fix"},
        repo_root="/go/src/google.golang.org/grpc",
        test_dir="test",
        package_name="test",
        editable_files=("test/end2end_test.go",),
        entry_points=("TestClientDoesntDeadlockWhileWritingErrornousLargeMessages",),
        extra_run_args=("-only_env", "tcp-clear-v1-balancer"),
        production_files=("transport/http2_client.go", "transport/http2_server.go"),
        context_files=("transport/control.go", "transport/transport.go"),
        mask_paths=("/go/src/google.golang.org/grpc/google.golang.org/grpc/bug_patch.diff", "/go/dep_versions.txt"),
        new_file_regex=r"test/w1_[a-z0-9_]{1,40}_test\.go",
        notes=("Repair-backported supplied test, identical on both variants.",
               "-only_env tcp-clear-v1-balancer as in C1: TLS test certificates expired."),
    ),
    "k8s26980": CaseSpec(
        case="k8s26980",
        language="go",
        image_tags={"V_bad": "k8s26980-bug", "V_ok": "k8s26980-fix"},
        repo_root="/go/src/k8s.io/kubernetes",
        test_dir="pkg/controller/framework",
        package_name="framework",
        editable_files=("pkg/controller/framework/processor_listener_test.go",),
        entry_points=("TestPopReleaseLock",),
        production_files=("pkg/controller/framework/shared_informer.go",),
        context_files=(),
        mask_paths=("/go/blob_check.txt",),
        new_file_regex=r"pkg/controller/framework/w1_[a-z0-9_]{1,40}_test\.go",
        notes=("Repair-backported supplied test, identical on both variants.",),
    ),
    "istio17860": CaseSpec(
        case="istio17860",
        language="go",
        image_tags={"V_bad": "istio17860-bug", "V_ok": "istio17860-fix"},
        repo_root="/go/src/istio.io/istio",
        test_dir="pkg/envoy",
        package_name="envoy",
        editable_files=("pkg/envoy/agent_test.go",),
        entry_points=("TestExitDuringWaitForLive",),
        production_files=("pkg/envoy/agent.go",),
        context_files=(),
        mask_paths=("/go/blob_check.txt", "/go/dep_versions.txt"),
        new_file_regex=r"pkg/envoy/w1_[a-z0-9_]{1,40}_test\.go",
        notes=("Repair-backported supplied test, identical on both variants.",
               "Same goautoneg go.mod replacement on both variants (restoration deviation)."),
    ),
}


def spec(case: str) -> CaseSpec:
    return SPECS[case]
