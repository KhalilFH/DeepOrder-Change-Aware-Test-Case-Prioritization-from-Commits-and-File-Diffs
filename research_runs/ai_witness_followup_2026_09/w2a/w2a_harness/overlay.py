"""Test overlays: representation, deterministic application and the edit contract.

An overlay is proposed as exact-snippet edits to supplied editable test files
plus (Go only) new test files matching the case pattern. It is *materialized*
into full file contents; its identity is the SHA-256 of the canonical JSON list
of materialized (path, content-sha256) pairs, so the unchanged overlay has the
explicit hash ``EMPTY_OVERLAY_SHA256``.

Edit contract (method_contract.md), enforced statically before any execution:

* only supplied editable test files or permitted new test files; no production
  file, no path escape;
* **insertion-only** on supplied files: every original line survives, in order.
  Existing assertions, timeouts and test bodies cannot be removed or weakened;
* inserted/new code may not read files, environment, process or variant
  identity, exec processes, exit/skip, touch the network beyond loopback test
  servers, define the harness-owned TestMain, or print harness/oracle markers;
* size limits keep interventions small.

The deny rules are a conservative static screen, not a proof of good faith; the
runtime additionally runs without network and masks variant-identifying files.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .casespec import GO_INSTRUMENT_FILE, CaseSpec
from .common import EMPTY_OVERLAY_SHA256, sha256_json, sha256_text

MAX_INSERTED_LINES = 400
MAX_NEW_FILES = 2
MAX_OVERLAY_BYTES = 64_000  # inserted/new bytes, not the size of edited supplied files

COMMON_DENY = [
    (r"W1[-_]", "harness marker text"),
    (r"w1harness", "harness package"),
    (r"V_bad|V_ok|bug_patch|blob_check|gobench|dep_versions", "variant identity"),
    (r"Exception <a|thrown in (interpreter|compiled) method", "VM exception-log imitation"),
    (r"goroutine \d+ \[", "goroutine-dump imitation"),
]
GO_DENY = [
    (r"\bos\.(Open|OpenFile|ReadFile|Create|Getenv|LookupEnv|Environ|Exit|Stat|Lstat|ReadDir|Readlink|Hostname|Executable|Getwd|Chdir|Remove|RemoveAll|Rename|WriteFile|Mkdir|MkdirAll|Args|StartProcess|Getpid|Getppid)\b", "file/env/process access"),
    (r"\bioutil\.", "file access"),
    (r"\bexec\.", "process execution"),
    (r"\bsyscall\.", "syscall"),
    (r"\bunsafe\.", "unsafe"),
    (r"\bfilepath\.", "file path access"),
    (r"\bplugin\.", "plugin"),
    (r"\.Skip(Now|f)?\(", "skip"),
    (r"\bruntime\.Goexit\b", "goexit"),
    (r"\bfunc\s+TestMain\s*\(", "harness-owned TestMain"),
    (r"//\s*\+build|//go:", "build/compiler directive"),
    (r"\bhttp\.(Get|Post|Head|Do)\b", "network client"),
]
GO_FORBIDDEN_IMPORTS = {"os/exec", "syscall", "unsafe", "plugin", "io/ioutil", "path/filepath", "net/http", "os", "os/signal"}
JAVA_DENY = [
    (r"System\s*\.\s*(exit|getenv|getProperty|setProperty|getProperties|setOut|setErr|load|loadLibrary)\b", "process/env access"),
    (r"Runtime\s*\.\s*getRuntime|\.halt\s*\(|ProcessBuilder", "process control"),
    (r"java\.io\.File\b|\bnew\s+File(InputStream|OutputStream|Reader|Writer)?\s*\(|\bFiles\s*\.|\bPaths\s*\.|RandomAccessFile", "file access"),
    (r"Class\s*\.\s*forName|setAccessible|getDeclared(Field|Method|Constructor)|ClassLoader|sun\.misc|java\.lang\.reflect", "reflection/class loading"),
    (r"java\.net\.|\bSocket\b|URLConnection", "network"),
]


class OverlayError(ValueError):
    """The proposal cannot be applied deterministically (malformed or ambiguous)."""


@dataclass
class Materialized:
    files: dict[str, str]  # repo-relative path -> full new content (changed or new files only)
    overlay_sha256: str
    legal: bool
    violations: list[str] = field(default_factory=list)
    inserted_lines: int = 0
    new_tests: list[str] = field(default_factory=list)
    run_selection: list[str] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        return {"overlay_sha256": self.overlay_sha256, "legal": self.legal, "violations": self.violations,
                "files": {p: sha256_text(c) for p, c in sorted(self.files.items())},
                "inserted_lines": self.inserted_lines, "new_tests": self.new_tests,
                "run_selection": self.run_selection}


def overlay_hash(files: dict[str, str]) -> str:
    return sha256_json({"files": [{"path": p, "sha256": sha256_text(files[p])} for p in sorted(files)]})


assert overlay_hash({}) == EMPTY_OVERLAY_SHA256


def _normalize(text: str) -> str:
    return text.replace("\r\n", "\n")


def apply_proposal(proposal: dict[str, Any], originals: dict[str, str], spec: CaseSpec) -> dict[str, str]:
    """Apply {"edits":[{path,old,new}], "new_files":[{path,content}]} to originals.

    Each ``old`` must occur exactly once in the current content of its file.
    Raises OverlayError for malformed or ambiguous proposals (a method failure).
    """
    if not isinstance(proposal, dict):
        raise OverlayError("proposal must be an object")
    unknown = set(proposal) - {"edits", "new_files"}
    if unknown:
        raise OverlayError(f"unknown proposal fields {sorted(unknown)}")
    edits = proposal.get("edits") or []
    new_files = proposal.get("new_files") or []
    if not isinstance(edits, list) or not isinstance(new_files, list):
        raise OverlayError("edits/new_files must be lists")
    current: dict[str, str] = {}
    for i, e in enumerate(edits):
        if not isinstance(e, dict) or set(e) != {"path", "old", "new"} or not all(isinstance(e[k], str) for k in e):
            raise OverlayError(f"edit {i}: must have string path/old/new only")
        path = e["path"].strip().lstrip("./")
        if path not in spec.editable_files:
            raise OverlayError(f"edit {i}: {path!r} is not an editable supplied test file")
        content = current.get(path, _normalize(originals[path]))
        old = _normalize(e["old"])
        if not old:
            raise OverlayError(f"edit {i}: empty anchor")
        count = content.count(old)
        if count != 1:
            raise OverlayError(f"edit {i}: anchor occurs {count} times in {path} (must be exactly once)")
        current[path] = content.replace(old, _normalize(e["new"]), 1)
    for i, nf in enumerate(new_files):
        if not isinstance(nf, dict) or set(nf) != {"path", "content"} or not all(isinstance(nf[k], str) for k in nf):
            raise OverlayError(f"new file {i}: must have string path/content only")
        path = nf["path"].strip().lstrip("./")
        if path in originals or path in current:
            raise OverlayError(f"new file {i}: {path!r} already exists")
        if not spec.is_new_file_allowed(path):
            raise OverlayError(f"new file {i}: {path!r} does not match the permitted new-test-file pattern")
        current[path] = _normalize(nf["content"])
    return {p: c for p, c in current.items() if originals.get(p) is None or c != _normalize(originals[p])}


def _is_subsequence(original: list[str], new: list[str]) -> bool:
    it = iter(new)
    return all(any(line == candidate for candidate in it) for line in original)


def _inserted_lines(original: list[str], new: list[str]) -> list[str]:
    """Lines of ``new`` not consumed by a greedy in-order match of ``original``."""
    out = []
    j = 0
    for line in new:
        if j < len(original) and line == original[j]:
            j += 1
        else:
            out.append(line)
    return out


GO_TEST_FUNC = re.compile(r"^func\s+(Test[A-Z0-9_][A-Za-z0-9_]*)\s*\(\s*\w+\s+\*testing\.T\s*\)", re.M)
JAVA_TEST_METHOD = re.compile(r"^\s*public\s+void\s+(test[A-Za-z0-9_]*)\s*\(\s*\)", re.M)
GO_IMPORT_BLOCK = re.compile(r"^import\s*\((.*?)^\)", re.M | re.S)
GO_IMPORT_LINE = re.compile(r'^import\s+(?:\w+\s+)?"([^"]+)"', re.M)


def go_imports(src: str) -> set[str]:
    found = set(GO_IMPORT_LINE.findall(src))
    for block in GO_IMPORT_BLOCK.findall(src):
        found.update(re.findall(r'"([^"]+)"', block))
    return found


def _java_class_of(path: str) -> str:
    rel = path.split("src/test/", 1)[1]
    return rel[:-5].replace("/", ".")


def test_names(spec: CaseSpec, path: str, content: str) -> list[str]:
    if spec.language == "go":
        return GO_TEST_FUNC.findall(content)
    return [f"{_java_class_of(path)}#{m}" for m in JAVA_TEST_METHOD.findall(content)]


def materialize(proposal: dict[str, Any] | None, originals: dict[str, str], spec: CaseSpec) -> Materialized:
    """Apply and check a proposal. ``None`` means the unchanged overlay."""
    files = {} if proposal is None else apply_proposal(proposal, originals, spec)
    violations: list[str] = []
    inserted_total = 0
    new_tests: list[str] = []
    new_file_count = 0
    total_bytes = 0
    deny = COMMON_DENY + (GO_DENY if spec.language == "go" else JAVA_DENY)
    for path, content in sorted(files.items()):
        base = spec.test_dir + "/"
        if not path.startswith(base) or ".." in path.split("/"):
            violations.append(f"{path}: outside the test package")
        if path.endswith(GO_INSTRUMENT_FILE):
            violations.append(f"{path}: harness-owned file name")
        if path in originals:
            orig_lines = _normalize(originals[path]).split("\n")
            new_lines = content.split("\n")
            if not _is_subsequence(orig_lines, new_lines):
                violations.append(f"{path}: an original line was removed or modified (edits must be insertion-only)")
            inserted = _inserted_lines(orig_lines, new_lines)
            before = set(test_names(spec, path, originals[path]))
        else:
            new_file_count += 1
            inserted = content.split("\n")
            before = set()
            if spec.language == "go":
                m = re.search(r"^package\s+(\w+)", content, re.M)
                if not m or m.group(1) != spec.package_name:
                    violations.append(f"{path}: new file must declare package {spec.package_name}")
        inserted_total += len(inserted)
        text = "\n".join(inserted)
        total_bytes += len(text.encode("utf-8"))
        for pattern, why in deny:
            m = re.search(pattern, text)
            if m:
                violations.append(f"{path}: forbidden construct ({why}): {m.group(0)!r}")
        if spec.language == "go":
            added_imports = go_imports(content) - (go_imports(originals[path]) if path in originals else set())
            bad = sorted(i for i in added_imports if i in GO_FORBIDDEN_IMPORTS or "." in i.split("/")[0] and not _import_in_package_deps(i, originals))
            for imp in bad:
                violations.append(f"{path}: forbidden or new external import {imp!r}")
        for name in test_names(spec, path, content):
            if name not in before and name not in new_tests:
                new_tests.append(name)
    if new_file_count > MAX_NEW_FILES:
        violations.append(f"too many new files ({new_file_count} > {MAX_NEW_FILES})")
    if inserted_total > MAX_INSERTED_LINES:
        violations.append(f"too many inserted lines ({inserted_total} > {MAX_INSERTED_LINES})")
    if total_bytes > MAX_OVERLAY_BYTES:
        violations.append(f"overlay too large ({total_bytes} bytes > {MAX_OVERLAY_BYTES})")
    if len(new_tests) > spec.max_new_tests:
        violations.append(f"too many new test entry points ({len(new_tests)} > {spec.max_new_tests})")
    for name in new_tests:
        if name in spec.entry_points:
            violations.append(f"duplicate entry point {name}")
    selection = list(spec.entry_points) + [n for n in new_tests if n not in spec.entry_points]
    return Materialized(files=files, overlay_sha256=overlay_hash(files), legal=not violations,
                        violations=violations, inserted_lines=inserted_total, new_tests=new_tests,
                        run_selection=selection)


def _import_in_package_deps(imp: str, originals: dict[str, str]) -> bool:
    """A non-stdlib import is allowed only if some supplied file already imports it."""
    return any(imp in go_imports(src) for src in originals.values())


def unchanged(originals: dict[str, str], spec: CaseSpec) -> Materialized:
    return materialize(None, originals, spec)
