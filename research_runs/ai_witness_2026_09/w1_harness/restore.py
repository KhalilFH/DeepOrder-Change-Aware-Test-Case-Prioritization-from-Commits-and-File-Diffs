"""Phase 1 restoration of the four registered cases (no other cases).

* pool162: fresh source retrieval from the upstream repository, then ONE build
  invocation (a declared script building both variant images from one recipe).
* Go cases: the C1-verified local images are reused unchanged; restoration is an
  in-image identity check (blob hashes, toolchain, tree delta). The per-candidate
  test build happens later inside those images.

Every command, including failed attempts, is appended to
``prep/subjects/<case>/restoration.json`` and charged to the preparation stage.
At most three build invocations per case (study_config.json calibration).
"""

from __future__ import annotations

import io
import json
import shutil
import tarfile
from pathlib import Path
from typing import Any

from . import STUDY_DIR
from .charging import charged_run
from .common import W1Error, read_json, sha256_bytes, utc_now, write_json
from .config import PREP_DIR, WORK_DIR, account, design_config
from .proc import run

POOL_REPO = "https://github.com/apache/commons-pool.git"
POOL_BAD = "280c60ac3e918eb7fe8fb542847913bb5317cbc6"
POOL_OK = "674a6ba9877d2de7224306c83e7871e1eddeab93"
POOL_TEST_BLOB = "4008f1ee2b1cca71040feb1c14ee506701e70af9"
POOL_TEST_PATH = "src/test/org/apache/commons/pool/impl/TestGenericObjectPool.java"
JUNIT_URL = "https://repo1.maven.org/maven2/junit/junit/3.8.2/junit-3.8.2.jar"
JUNIT_SHA1 = "07e4cde26b53a9a0e3fe5b00d1dbbc7cc1d46060"
JUNIT_SHA256 = "ecdcc08183708ea3f7b0ddc96f19678a0db8af1fb397791d484aed63200558b0"
POOL_IMAGES = {"V_bad": "w1-pool162-bad", "V_ok": "w1-pool162-ok"}
RECIPE_DIR = PREP_DIR / "subjects" / "pool162" / "recipe"

GO_IMAGES = {
    "grpc1859": {"V_bad": "grpc1859-bug", "V_ok": "grpc1859-fix"},
    "k8s26980": {"V_bad": "k8s26980-bug", "V_ok": "k8s26980-fix"},
    "istio17860": {"V_bad": "istio17860-bug", "V_ok": "istio17860-fix"},
}
GO_ROOTS = {
    "grpc1859": "/go/src/google.golang.org/grpc",
    "k8s26980": "/go/src/k8s.io/kubernetes",
    "istio17860": "/go/src/istio.io/istio",
}
GO_TEST_PKG = {"grpc1859": "test", "k8s26980": "pkg/controller/framework", "istio17860": "pkg/envoy"}
GO_PROD_FILES = {
    "grpc1859": ["transport/http2_client.go", "transport/http2_server.go"],
    "k8s26980": ["pkg/controller/framework/shared_informer.go"],
    "istio17860": ["pkg/envoy/agent.go"],
}
GO_EXPECTED_BLOBS = {  # subject_register.md / C1 subject_manifest.json
    "grpc1859": {
        "V_bad": {"transport/http2_client.go": "717e4192ea13547ffe323613d3d4945c9c5a9b00",
                  "transport/http2_server.go": "5233d6f3db6bd29622f694a59befd50d9e6d7365",
                  "test/end2end_test.go": "6a583182170323ec5b23d760d926c92d3816be18"},
        "V_ok": {"transport/http2_client.go": "56b434ef37fed92f87811d9d08e3c9c834cf9971",
                 "transport/http2_server.go": "24c2c7e18c48b007dd8a060cb4e09bfab1a55ebd",
                 "test/end2end_test.go": "6a583182170323ec5b23d760d926c92d3816be18"},
    },
    "k8s26980": {
        "V_bad": {"pkg/controller/framework/shared_informer.go": "ce9ddf2c7140ff2d9d9752ac8626cef1bb01a236",
                  "pkg/controller/framework/processor_listener_test.go": "ffd72d8fae243a1e221a574781a87ed2107aaf1a"},
        "V_ok": {"pkg/controller/framework/shared_informer.go": "c557bf97548a4e7054b05e0b158ba194b7dd59f2",
                 "pkg/controller/framework/processor_listener_test.go": "ffd72d8fae243a1e221a574781a87ed2107aaf1a"},
    },
    "istio17860": {
        "V_bad": {"pkg/envoy/agent.go": "f6644419ad8c6bf453fd120cadb75714842b4420",
                  "pkg/envoy/agent_test.go": "09ea287d1f94319c7284f281838a579fdc98d442"},
        "V_ok": {"pkg/envoy/agent.go": "638578e3341536ebdf3b93e1699ce2568d05d83b",
                 "pkg/envoy/agent_test.go": "09ea287d1f94319c7284f281838a579fdc98d442"},
    },
}
GO_COMMITS = {
    "grpc1859": "484b3ebb4ab56d3decc8240d599718bdbefcf7eb",
    "k8s26980": "628af356b8c83f98ee3b50dfcf8b0250816a5581",
    "istio17860": "c6e9130227497ab064dd571a1409236d17aa2ef3",
}


def dossier_path(case: str) -> Path:
    return PREP_DIR / "subjects" / case / "restoration.json"


def _load(case: str) -> dict[str, Any]:
    p = dossier_path(case)
    return read_json(p) if p.exists() else {"case": case, "commands": [], "build_invocations": 0}


def _record(dossier: dict[str, Any], label: str, r: Any, extra: dict[str, Any] | None = None) -> None:
    dossier["commands"].append({
        "label": label, "argv": r.argv, "started_utc": r.started_utc, "ended_utc": r.ended_utc,
        "elapsed_s": round(r.elapsed_s, 3), "exit_code": r.exit_code, "timed_out": r.timed_out,
        "stdout_tail": r.stdout[-3000:], "stderr_tail": r.stderr[-3000:], **(extra or {}),
    })


def _git(repo: Path, *args: str, timeout: float = 120) -> Any:
    return run(["git", "-C", str(repo), *args], timeout_s=timeout)


def _extract_tree(repo: Path, commit: str, subdir: str, dest: Path) -> dict[str, str]:
    """git archive (exact blob bytes, no autocrlf) -> dest; return {path: sha256}."""
    import subprocess
    cp = subprocess.run(["git", "-C", str(repo), "archive", "--format=tar", commit, subdir],
                        capture_output=True, timeout=120)
    if cp.returncode != 0:
        raise W1Error(f"git archive {commit} {subdir} failed: {cp.stderr.decode(errors='replace')}")
    data = cp.stdout
    hashes: dict[str, str] = {}
    with tarfile.open(fileobj=io.BytesIO(data)) as tf:
        for m in tf.getmembers():
            if m.isfile():
                content = tf.extractfile(m).read()  # type: ignore[union-attr]
                out = dest / m.name
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(content)
                hashes[m.name] = sha256_bytes(content)
    return hashes


def restore_pool162(*, build: bool = True) -> dict[str, Any]:
    acct = account()
    dossier = _load("pool162")
    if dossier["build_invocations"] >= design_config()["calibration"]["max_build_invocations_per_subject"]:
        raise W1Error("pool162: build invocation cap reached")
    repo = WORK_DIR / "pool-src"
    if not repo.exists():
        r = charged_run(acct, "preparation", "pool162.clone", ["git", "clone", "-q", POOL_REPO, str(repo)], timeout_s=600, cleanup_s=0)
        _record(dossier, "clone", r)
        if r.exit_code != 0:
            write_json(dossier_path("pool162"), dossier)
            raise W1Error("pool162 clone failed")
    ident = {}
    for name, commit in (("V_bad", POOL_BAD), ("V_ok", POOL_OK)):
        r = _git(repo, "rev-parse", "--verify", commit + "^{commit}")
        ident[name] = r.stdout.strip()
        if ident[name] != commit:
            raise W1Error(f"pool162 {name}: commit {commit} not resolvable ({r.stderr})")
    parent = _git(repo, "rev-parse", POOL_OK + "^").stdout.strip()
    blob = _git(repo, "rev-parse", f"{POOL_BAD}:{POOL_TEST_PATH}").stdout.strip()
    if blob != POOL_TEST_BLOB:
        raise W1Error(f"pool162 pre-fix test blob {blob} != register {POOL_TEST_BLOB}")
    ctx = WORK_DIR / "pool162_ctx"
    if ctx.exists():
        shutil.rmtree(ctx)
    prod = {v: _extract_tree(repo, c, "src/java", ctx / f"prod-{'bad' if v == 'V_bad' else 'ok'}")
            for v, c in (("V_bad", POOL_BAD), ("V_ok", POOL_OK))}
    tests = _extract_tree(repo, POOL_BAD, "src/test", ctx / "tests")
    repaired_tests = {}
    tmp = WORK_DIR / "pool162_repaired_tests_probe"
    if tmp.exists():
        shutil.rmtree(tmp)
    repaired_tests = _extract_tree(repo, POOL_OK, "src/test", tmp)
    shutil.rmtree(tmp)
    prod_diff = sorted(p for p in set(prod["V_bad"]) | set(prod["V_ok"]) if prod["V_bad"].get(p) != prod["V_ok"].get(p))
    test_diff_vs_repair = sorted(p for p in set(tests) | set(repaired_tests) if tests.get(p) != repaired_tests.get(p))
    expected_prod = ["src/java/org/apache/commons/pool/impl/GenericKeyedObjectPool.java",
                     "src/java/org/apache/commons/pool/impl/GenericObjectPool.java"]
    if prod_diff != expected_prod:
        raise W1Error(f"pool162 production delta {prod_diff} != {expected_prod}")
    jar = WORK_DIR / "junit-3.8.2.jar"
    if not jar.exists():
        r = run(["curl", "-sS", "-L", "-o", str(jar), JUNIT_URL], timeout_s=120)
        _record(dossier, "junit download", r)
    import hashlib
    jar_bytes = jar.read_bytes()
    if hashlib.sha1(jar_bytes).hexdigest() != JUNIT_SHA1 or sha256_bytes(jar_bytes) != JUNIT_SHA256:
        raise W1Error("junit-3.8.2.jar checksum mismatch")
    shutil.copy(jar, ctx / "junit-3.8.2.jar")
    shutil.copy(RECIPE_DIR / "W1Runner.java", ctx / "W1Runner.java")
    shutil.copy(RECIPE_DIR / "Dockerfile", ctx / "Dockerfile")
    dossier.update({
        "source": {"repository": POOL_REPO, "V_bad_commit": POOL_BAD, "V_ok_commit": POOL_OK,
                   "V_ok_parent": parent, "V_bad_is_parent_of_V_ok": parent == POOL_BAD,
                   "pre_fix_test_blob": blob},
        "production_file_sha256": prod,
        "production_delta": prod_diff,
        "supplied_test_tree": "src/test of V_bad commit on BOTH variants",
        "supplied_test_file_sha256": tests,
        "withheld_repair_test_delta": test_diff_vs_repair,
        "junit": {"url": JUNIT_URL, "sha1": JUNIT_SHA1, "sha256": JUNIT_SHA256},
        "recipe": {"Dockerfile_sha256": sha256_bytes((RECIPE_DIR / "Dockerfile").read_bytes()),
                   "W1Runner_java_sha256": sha256_bytes((RECIPE_DIR / "W1Runner.java").read_bytes())},
        "compatibility_deviations": [
            "Temurin JDK 17.0.20.1 (image pinned by digest) compiling at --release 8, instead of the historical JDK/Maven 2 build",
            "JUnit 3.8.2 jar (pom-declared version) run by the harness-owned W1Runner instead of maven-surefire",
            "identical on both variants; -Xlog:exceptions=info VM exception logging is harness instrumentation",
        ],
    })
    if build:
        dossier["build_invocations"] += 1
        inv = dossier["build_invocations"]
        results = {}
        for variant, tag in POOL_IMAGES.items():
            arg = "bad" if variant == "V_bad" else "ok"
            r = charged_run(acct, "preparation", f"pool162.build{inv}.{variant}",
                            ["docker", "build", "--network", "none", "--build-arg", f"VARIANT={arg}", "-t", tag, str(ctx)],
                            timeout_s=900)
            _record(dossier, f"build invocation {inv} {variant}", r)
            results[variant] = r.exit_code
        images = {}
        for variant, tag in POOL_IMAGES.items():
            r = run(["docker", "image", "inspect", "--format", "{{.Id}}", tag], timeout_s=30)
            images[variant] = {"tag": tag, "image_id": r.stdout.strip() if r.exit_code == 0 else None}
        dossier.setdefault("builds", []).append({"invocation": inv, "utc": utc_now(), "exit_codes": results, "images": images})
        dossier["images"] = images
    write_json(dossier_path("pool162"), dossier)
    return dossier


def check_go_images(case: str) -> dict[str, Any]:
    """In-image identity check (no build, no test execution)."""
    acct = account()
    dossier = _load(case)
    root = GO_ROOTS[case]
    pkg = GO_TEST_PKG[case]
    out: dict[str, Any] = {}
    for variant, tag in GO_IMAGES[case].items():
        files = sorted(set(GO_EXPECTED_BLOBS[case][variant]) | set(GO_PROD_FILES[case]))
        script = (
            f"cd {root} && echo COMMIT $(git rev-parse HEAD) && go version && "
            f"echo STATUS && git status --short --untracked-files=all && echo BLOBS && "
            f"for f in {' '.join(files)}; do echo \"$f $(git hash-object $f)\"; done && echo PKGTESTS && "
            f"for f in {pkg}/*_test.go; do echo \"$f $(git hash-object $f)\"; done && echo END"
        )
        r = charged_run(acct, "preparation", f"{case}.imagecheck.{variant}",
                        ["docker", "run", "--rm", "--network", "none", tag, "sh", "-c", script], timeout_s=120)
        _record(dossier, f"image check {variant}", r)
        text = r.stdout
        blobs = {}
        pkg_tests = {}
        section = None
        status = []
        for line in text.splitlines():
            if line in ("STATUS", "BLOBS", "PKGTESTS", "END"):
                section = line
                continue
            if section == "STATUS":
                status.append(line)
            elif section == "BLOBS" and " " in line:
                k, v = line.rsplit(" ", 1)
                blobs[k] = v
            elif section == "PKGTESTS" and " " in line:
                k, v = line.rsplit(" ", 1)
                pkg_tests[k] = v
        commit = next((l.split()[1] for l in text.splitlines() if l.startswith("COMMIT ")), None)
        img = run(["docker", "image", "inspect", "--format", "{{.Id}}", tag], timeout_s=30).stdout.strip()
        out[variant] = {"tag": tag, "image_id": img, "commit": commit, "go_version": next((l for l in text.splitlines() if l.startswith("go version")), None),
                        "status_short": status, "blobs": blobs, "package_test_blobs": pkg_tests,
                        "blob_match": all(blobs.get(k) == v for k, v in GO_EXPECTED_BLOBS[case][variant].items())}
    checks = {
        "same commit": out["V_bad"]["commit"] == out["V_ok"]["commit"] == GO_COMMITS[case],
        "expected blobs": out["V_bad"]["blob_match"] and out["V_ok"]["blob_match"],
        "identical package tests": out["V_bad"]["package_test_blobs"] == out["V_ok"]["package_test_blobs"],
        "same go version": out["V_bad"]["go_version"] == out["V_ok"]["go_version"],
        "production files differ": all(out["V_bad"]["blobs"][f] != out["V_ok"]["blobs"][f] for f in GO_PROD_FILES[case]),
    }
    dossier["image_check"] = {"utc": utc_now(), "variants": out, "checks": checks, "passed": all(checks.values())}
    write_json(dossier_path(case), dossier)
    return dossier["image_check"]
