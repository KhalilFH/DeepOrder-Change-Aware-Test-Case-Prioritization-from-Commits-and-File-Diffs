"""Read-only W1 design consistency verifier; no experiment or network access."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys


EXPECTED = {
    "README.md", "proposal.md", "protocol.md", "subject_register.md",
    "method_contract.md", "prompts.md", "study_config.json",
    "execution_plan.md", "analysis_plan.md", "artifact_contract.md",
    "artifact_schema.json", "HANDOFF_PROMPT.md", "MEASURED_RUN_PROMPT.md",
    "DESIGN_FREEZE.md", "verify_design.py", ".gitattributes",
}


def verify(root: Path) -> list[str]:
    errors: list[str] = []
    manifest = root / "DESIGN_FREEZE.sha256"
    if not manifest.is_file():
        return ["Missing DESIGN_FREEZE.sha256"]
    seen: set[str] = set()
    for line_number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_.-]+)", line)
        if not match:
            errors.append(f"Malformed manifest line {line_number}")
            continue
        digest, name = match.groups()
        if name in seen:
            errors.append(f"Duplicate manifest entry: {name}")
        seen.add(name)
        if name not in EXPECTED:
            errors.append(f"Unexpected manifest entry: {name}")
            continue
        path = root / name
        if not path.is_file():
            errors.append(f"Missing file: {name}")
            continue
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            errors.append(f"SHA-256 mismatch: {name}")
        if b"\r" in data:
            errors.append(f"Non-LF content: {name}")
    for name in sorted(EXPECTED - seen):
        errors.append(f"Absent from manifest: {name}")
    try:
        config = json.loads((root / "study_config.json").read_text(encoding="utf-8"))
        schema = json.loads((root / "artifact_schema.json").read_text(encoding="utf-8"))
        checks = {
            "study identity": config["study_id"] == "W1" and config["design_version"] == "1.0",
            "roster": config["subjects"] == ["pool162", "grpc1859", "k8s26980", "istio17860"],
            "arms": config["arms"] == ["B0", "B1", "B2", "B3", "B4"],
            "replicates": config["search_replicates"] == 3,
            "search allowance": config["search"]["wall_seconds"] == 600,
            "validation counts": config["validation"]["triplets_per_variant"] * config["validation"]["attempts_per_triplet"] == config["validation"]["required_ok_passes"] == 15,
            "model family": config["provider_launch_fields"]["requested_generator_family"] == "GPT-5.6 Sol",
            "unresolved runtime": config["status"] == "DESIGN_FROZEN_NOT_LAUNCH_READY" and config["provider_launch_fields"]["generator_transport"] is None,
            "payload definitions": {"session", "request", "attempt"}.issubset(schema["$defs"]),
        }
        errors.extend(f"Configuration invariant failed: {name}" for name, passed in checks.items() if not passed)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"Cannot validate configuration: {exc}")
    return errors


def main() -> int:
    errors = verify(Path(__file__).resolve().parent)
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(f"PASS: {len(EXPECTED)}/{len(EXPECTED)} design hashes and configuration invariants.")
    print("Design consistency only; executable launch readiness is NOT established.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
