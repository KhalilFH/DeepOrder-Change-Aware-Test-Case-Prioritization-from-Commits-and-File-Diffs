"""Common per-case method packets (method_contract.md, "Shared source and execution facilities").

One immutable packet per case, identical for every arm:

* ``diff.patch``: production-only defective -> repaired unified diff;
* ``files/``: allowed source files. Changed production files appear twice
  (``defective/<path>`` and ``repaired/<path>``); supplied tests and helpers,
  identical on both variants, appear once under ``shared/<path>``;
* ``build_run.md``: build/run interface, harness instrumentation and edit rules;
* ``t0.json``: deterministic static extraction (static_extract.py);
* ``packet_manifest.json``: every file id, path, version, line count and SHA-256;
  ``packet_sha256`` is the hash of the canonical manifest.

Held out: the POOL repair-added test, issue text, human diagnoses, C1 results,
subject_register.md, oracle code and validation results. ``leak_scan`` checks
rendered packets for known held-out markers.
"""

from __future__ import annotations

import io
import subprocess
import tarfile
from pathlib import Path
from typing import Any

from . import CASES, STUDY_DIR
from .casespec import CaseSpec, spec
from .charging import vcpu_h
from .common import W1Error, canonical_json, read_json, sha256_bytes, sha256_json, utc_now, write_json, write_text_lf
from .config import INPUTS_DIR, WORK_DIR, account
from .proc import run
from . import static_extract

HELD_OUT_MARKERS = (
    "testWhenExhaustedBlockInterupt", "POOL-162", "subject_register", "private_oracles", "VALIDATED_WITNESS",
    "FOCAL_FAILURE", "focal oracle", "C1 ", "ci_configuration_2026_09", "must not consume capacity",
    "strand send quota", "retain the listener lock", "epoch-exit processing", "premise_evidence",
    "consequence_evidence", "rule_id",
)


def _docker_tar(image: str, root: str, paths: list[str]) -> dict[str, bytes]:
    cp = subprocess.run(["docker", "run", "--rm", "--network", "none", image, "tar", "cf", "-", "-C", root, *paths],
                        capture_output=True, timeout=300)
    if cp.returncode != 0:
        raise W1Error(f"tar from {image} failed: {cp.stderr.decode(errors='replace')[:500]}")
    out: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(cp.stdout)) as tf:
        for m in tf.getmembers():
            if m.isfile():
                out[m.name] = tf.extractfile(m).read()  # type: ignore[union-attr]
    return out


def _list_dir(image: str, root: str, d: str) -> list[str]:
    r = run(["docker", "run", "--rm", "--network", "none", image, "sh", "-c", f"cd {root}/{d} && ls -p | grep -v /"], timeout_s=120)
    if r.exit_code != 0:
        raise W1Error(f"listing {d} in {image} failed")
    return [f"{d}/{n}" for n in r.stdout.split() if n.endswith(".go")]


def acquire_sources(case: str) -> dict[str, dict[str, bytes]]:
    """Return {variant: {path: bytes}} for the packet file set (charged to preparation)."""
    s = spec(case)
    acct = account()
    rid = acct.reserve("preparation", f"{case}.packet_sources", {"vcpu_h": vcpu_h(4 * 300)})
    import time
    t0 = time.monotonic()
    try:
        if s.language == "java":
            ctx = WORK_DIR / "pool162_ctx"
            if not ctx.exists():
                raise W1Error("pool162 context missing: run restoration first")
            out: dict[str, dict[str, bytes]] = {}
            for variant, sub in (("V_bad", "prod-bad"), ("V_ok", "prod-ok")):
                files = {}
                for p in s.production_files + tuple(x for x in s.context_files if x.startswith("src/java/")):
                    files[p] = (ctx / sub / p).read_bytes()
                for p in s.editable_files + tuple(x for x in s.context_files if x.startswith("src/test/")):
                    files[p] = (ctx / "tests" / p).read_bytes()
                out[variant] = files
            return out
        out = {}
        for variant, tag in s.image_tags.items():
            listing = _list_dir(tag, s.repo_root, s.test_dir)
            paths = sorted(set(listing) | set(s.production_files) | set(s.context_files) | set(s.editable_files))
            out[variant] = _docker_tar(tag, s.repo_root, paths)
        return out
    finally:
        acct.settle(rid, {"vcpu_h": vcpu_h(time.monotonic() - t0)}, {"what": "source extraction for packet"})


def cached_sources(case: str) -> dict[str, dict[str, bytes]]:
    """Sources from the local scratch cache (work/sources), acquiring them once if absent."""
    root = WORK_DIR / "sources" / case
    if not root.exists():
        got = acquire_sources(case)
        for variant, files in got.items():
            for p, data in files.items():
                out = root / variant / p
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(data)
    return {v.name: {p.relative_to(v).as_posix(): p.read_bytes() for p in v.rglob("*") if p.is_file()}
            for v in sorted(root.iterdir())}


BUILD_RUN_GO = """# Build and run interface ({case})

Language: Go ({go_version}), package `{package}` in `{test_dir}` (repository-relative). Build and run
happen in the case's fixed container images without network access. Both production variants use
identical test sources, instrumentation, arguments and timeouts; you cannot see or choose which
variant is which beyond the paired result labels `defective` and `repaired`.

Build: the harness copies your overlay into the package, adds its own file `{instrument}`
(which defines `TestMain`), and runs `go test -c -vet=off ./{test_dir}` on each variant.

Run: `<binary> -test.v -test.count 1 -test.run '^(<selected tests>)$' -test.timeout {inner}s{extra}`
with GOMAXPROCS=16 and GOTRACEBACK=all, working directory `{test_dir}`. Selected tests are the supplied
entry point(s) {entry} plus any new `func TestXxx(t *testing.T)` your overlay adds (at most {max_new}).
Outer limit {outer}s per run (the process is killed and the run is unresolved), cleanup {cleanup}s.

Harness instrumentation (identical everywhere): if any selected test fails, `TestMain` prints a full
goroutine dump after the tests return; on the {inner}s test timeout the Go runtime dumps all
goroutines. You may add bounded test-side observation (for example printing `runtime.Stack(buf, true)`).

Editing rules: edit only {editable} (insertion-only: every original line must remain, in order) and/or
add at most 2 new files named like `{test_dir}/w1_<name>_test.go` in package `{package}`. Do not modify
production code, remove or weaken assertions, change timeouts or arguments, define `TestMain`, read
files/environment/process information, exec processes, skip tests, access the network (loopback
test servers are fine), branch on revision identity, or print text imitating runtime dumps.
New imports must be standard library (not os, os/exec, io/ioutil, path/filepath, syscall, unsafe,
net/http, plugin) or packages already imported by the supplied test files. At most 400 inserted lines.
"""

BUILD_RUN_JAVA = """# Build and run interface ({case})

Language: Java, compiled by Temurin JDK 17 at `--release 8` against JUnit 3.8.2 and the production classes
of each variant, in fixed container images without network access. Both production variants use
identical test sources, instrumentation, arguments and timeouts; you cannot see or choose which variant is
which beyond the paired result labels `defective` and `repaired`.

Build: the harness copies your overlay into `src/test` and compiles all of `src/test`.

Run: `java -Xlog:exceptions=info w1harness.W1Runner {inner} <selected tests>` with 16 visible CPUs. Selected
tests are the supplied entry points {entry} plus any new `public void testXxx()` methods your overlay adds
to the editable classes (at most {max_new}). Each selected test runs once, in order, via JUnit 3
(`setUp`/`tearDown` apply). Outer limit {outer}s per run (killed and unresolved), cleanup {cleanup}s.

Harness instrumentation (identical everywhere): the VM logs thrown exceptions (`-Xlog:exceptions=info`),
the runner prints each failure's stack trace and a full thread dump after any non-passing test, and at
{inner}s it dumps all threads and exits (inner timeout).

Editing rules: edit only {editable} (insertion-only: every original line must remain, in order). Do not
modify production code, remove or weaken assertions, change timeouts, read files/environment/system
properties, exit or halt the VM, use reflection or class loading, access the network, branch on revision
identity, or print text imitating VM exception logs. At most 400 inserted lines.
"""


def build_run_text(s: CaseSpec, go_version: str | None) -> str:
    common = dict(case=s.case, inner=s.inner, outer=s.outer, cleanup=s.cleanup, max_new=s.max_new_tests,
                  entry=", ".join(f"`{e}`" for e in s.entry_points),
                  editable=", ".join(f"`{e}`" for e in s.editable_files))
    if s.language == "go":
        from .casespec import GO_INSTRUMENT_FILE
        extra = (" " + " ".join(s.extra_run_args)) if s.extra_run_args else ""
        return BUILD_RUN_GO.format(go_version=go_version, package=s.package_name, test_dir=s.test_dir,
                                   instrument=GO_INSTRUMENT_FILE, extra=extra, **common)
    return BUILD_RUN_JAVA.format(**common)


def build_packet(case: str, sources: dict[str, dict[str, bytes]] | None = None) -> dict[str, Any]:
    s = spec(case)
    sources = sources or cached_sources(case)
    bad, ok = sources["V_bad"], sources["V_ok"]
    if set(bad) != set(ok):
        raise W1Error(f"{case}: variant file sets differ: {sorted(set(bad) ^ set(ok))}")
    differing = sorted(p for p in bad if bad[p] != ok[p])
    if differing != sorted(s.production_files):
        raise W1Error(f"{case}: differing files {differing} != production files {sorted(s.production_files)}")
    dest = INPUTS_DIR / case
    files_dir = dest / "files"
    entries: dict[str, Any] = {}

    def add(file_id: str, path: str, version: str, data: bytes) -> None:
        text = data.decode("utf-8").replace("\r\n", "\n")
        write_text_lf(files_dir / file_id, text)
        entries[file_id] = {"path": path, "version": version, "sha256": sha256_bytes(text.encode("utf-8")),
                            "lines": text.count("\n") + (0 if text.endswith("\n") else 1), "bytes": len(text.encode("utf-8"))}

    for p in sorted(bad):
        if p in s.production_files:
            add(f"defective/{p}", p, "defective", bad[p])
            add(f"repaired/{p}", p, "repaired", ok[p])
        else:
            add(f"shared/{p}", p, "shared", bad[p])
    norm = lambda b: b.decode("utf-8").replace("\r\n", "\n")  # noqa: E731
    diff = "".join(static_extract.unified_diff(p, norm(bad[p]), norm(ok[p])) for p in sorted(s.production_files))
    write_text_lf(dest / "diff.patch", diff)
    source_crlf = sorted(p for p in bad if b"\r\n" in bad[p])
    text_of = lambda fid: (files_dir / fid).read_text(encoding="utf-8")  # noqa: E731
    production = {p: (text_of(f"defective/{p}"), text_of(f"repaired/{p}")) for p in s.production_files}
    tests = {p: text_of(f"shared/{p}") for p in s.editable_files}
    helpers = {e["path"]: text_of(fid) for fid, e in entries.items() if e["version"] == "shared" and e["path"] not in tests}
    t0 = static_extract.extract(s.language, production, tests, helpers, list(s.entry_points))
    write_json(dest / "t0.json", t0)
    go_version = None
    if s.language == "go":
        dossier = read_json(STUDY_DIR / "prep" / "subjects" / case / "restoration.json")
        go_version = dossier["image_check"]["variants"]["V_bad"]["go_version"]
    br = build_run_text(s, go_version)
    write_text_lf(dest / "build_run.md", br)
    manifest = {
        "artifact": "w1_packet_manifest_v1",
        "case": case,
        "files": entries,
        "diff_sha256": sha256_bytes(diff.encode("utf-8")),
        "t0_sha256": sha256_json(t0),
        "build_run_sha256": sha256_bytes(br.encode("utf-8")),
        "editable_files": list(s.editable_files),
        "line_endings": {"normalized_to": "LF", "source_files_with_crlf": source_crlf},
        "entry_points": list(s.entry_points),
        "withheld": ["repair-added regression test (pool162)", "issue discussions", "human diagnoses",
                     "C1/Q0 results", "subject_register.md", "private_oracles/", "validation results"],
    }
    manifest["packet_sha256"] = sha256_json(manifest)
    write_json(dest / "packet_manifest.json", manifest)
    return manifest


def load_packet(case: str) -> dict[str, Any]:
    dest = INPUTS_DIR / case
    manifest = read_json(dest / "packet_manifest.json")
    body = {k: v for k, v in manifest.items() if k != "packet_sha256"}
    if sha256_json(body) != manifest["packet_sha256"]:
        raise W1Error(f"{case}: packet manifest hash mismatch")
    files = {}
    for fid, e in manifest["files"].items():
        text = (dest / "files" / fid).read_text(encoding="utf-8").replace("\r\n", "\n")
        if sha256_bytes(text.encode("utf-8")) != e["sha256"]:
            raise W1Error(f"{case}: packet file {fid} changed")
        files[fid] = text
    diff = (dest / "diff.patch").read_text(encoding="utf-8").replace("\r\n", "\n")
    if sha256_bytes(diff.encode("utf-8")) != manifest["diff_sha256"]:
        raise W1Error(f"{case}: diff changed")
    t0 = read_json(dest / "t0.json")
    if sha256_json(t0) != manifest["t0_sha256"]:
        raise W1Error(f"{case}: t0 changed")
    br = (dest / "build_run.md").read_text(encoding="utf-8").replace("\r\n", "\n")
    if sha256_bytes(br.encode("utf-8")) != manifest["build_run_sha256"]:
        raise W1Error(f"{case}: build_run changed")
    return {"manifest": manifest, "files": files, "diff": diff, "t0": t0, "build_run": br}


def originals(packet: dict[str, Any]) -> dict[str, str]:
    """Supplied editable test files (identical on both variants)."""
    return {p: packet["files"][f"shared/{p}"] for p in packet["manifest"]["editable_files"]}


def leak_scan(text: str) -> list[str]:
    return [m for m in HELD_OUT_MARKERS if m in text]
