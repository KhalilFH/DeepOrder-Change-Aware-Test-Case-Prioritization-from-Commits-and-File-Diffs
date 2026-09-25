"""Design-freeze verification and the executable launch freeze.

Both use SHA-256 of LF-normalized bytes (CRLF -> LF), because this checkout
uses `core.autocrlf=true`: the digest must not depend on how Git wrote the
working tree. Paths in `DESIGN_FREEZE.sha256` are relative to the study
directory (as frozen); paths in `FREEZE.sha256` are relative to the repository
root, because the launch freeze also binds code outside the study directory.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable

from c1_harness import REPO_ROOT, STUDY_DIR

DESIGN_FREEZE = STUDY_DIR / "DESIGN_FREEZE.sha256"
LAUNCH_FREEZE = STUDY_DIR / "FREEZE.sha256"


def normalized_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _parse(path: Path) -> list[tuple[str, str]]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            digest, _, rel = line.partition("  ")
            out.append((digest.strip(), rel.strip().lstrip("*")))
    return out


def verify_design() -> list[str]:
    """Problems with the design freeze; empty means every listed digest matches."""
    if not DESIGN_FREEZE.exists():
        return ["DESIGN_FREEZE.sha256 missing"]
    problems = []
    entries = _parse(DESIGN_FREEZE)
    if len(entries) != 8:
        problems.append(f"expected 8 design entries, found {len(entries)}")
    for digest, rel in entries:
        p = STUDY_DIR / rel
        if not p.exists():
            problems.append(f"{rel}: missing")
        elif normalized_sha256(p) != digest:
            problems.append(f"{rel}: digest mismatch")
    return problems


def write_launch_freeze(paths: Iterable[Path], header: str) -> Path:
    lines = [f"# {h}" for h in header.splitlines()]
    for p in sorted({Path(p).resolve() for p in paths}):
        if p == LAUNCH_FREEZE.resolve():
            continue
        rel = p.relative_to(REPO_ROOT).as_posix()
        lines.append(f"{normalized_sha256(p)}  {rel}")
    LAUNCH_FREEZE.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return LAUNCH_FREEZE


def verify_launch() -> list[str]:
    if not LAUNCH_FREEZE.exists():
        return ["FREEZE.sha256 missing: no executable launch freeze exists"]
    problems = []
    entries = _parse(LAUNCH_FREEZE)
    if not entries:
        problems.append("FREEZE.sha256 lists no files")
    for digest, rel in entries:
        p = REPO_ROOT / rel
        if not p.exists():
            problems.append(f"{rel}: missing")
        elif normalized_sha256(p) != digest:
            problems.append(f"{rel}: digest mismatch")
    listed = {rel for _, rel in entries}
    required = {"research_runs/ci_configuration_2026_09/DESIGN_FREEZE.sha256",
                "research_runs/ci_configuration_2026_09/launch_record.md",
                "research_runs/ci_configuration_2026_09/schedule.csv",
                "research_runs/ci_configuration_2026_09/subject_manifest.json"}
    for r in sorted(required - listed):
        problems.append(f"{r}: required in the launch freeze but not listed")
    return problems + [f"design: {p}" for p in verify_design()]
