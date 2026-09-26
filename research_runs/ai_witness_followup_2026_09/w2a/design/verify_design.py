"""Read-only W2A design verifier; no experiment or network access. Also checks that W1's proposal
and W1's frozen design manifests W2A depends on are untouched."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

EXPECTED = {
    "README.md", "PROTOCOL.md", "METHOD_CONTRACT.md", "PROMPTS.md", "ANALYSIS_PLAN.md", "ARTIFACT_CONTRACT.md",
    "EXECUTION_PLAN.md", "DESIGN_CHANGES.md", "MEASURED_RUN_PROMPT.md", "DESIGN_FREEZE.md", "study_config.json",
    "w1_inputs.json", "verify_design.py", ".gitattributes",
}


def verify(root: Path) -> list[str]:
    errors: list[str] = []
    manifest = root / "DESIGN_FREEZE.sha256"
    if not manifest.is_file():
        return ["Missing DESIGN_FREEZE.sha256"]
    seen: set[str] = set()
    for n, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        m = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_.-]+)", line)
        if not m:
            errors.append(f"Malformed manifest line {n}")
            continue
        digest, name = m.groups()
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
        c = json.loads((root / "study_config.json").read_text(encoding="utf-8"))
        s = c["search"]
        checks = {
            "identity": c["study_id"] == "W2A" and c["design_version"] == "1.0",
            "roster": c["cases"] == ["pool162", "grpc1859", "k8s26980", "istio17860"],
            "arms": c["arms"] == ["F2", "F3"] and c["sessions_per_case_arm"] == 1,
            "generator": c["generator"]["requested_model"] == "claude-sonnet-5" and c["generator"]["effort"] == "medium",
            "no jev": s["max_jev_evaluations"] == 0 and c["study_caps"]["jev_atomic_evaluations"] == 0,
            "session caps": (s["wall_seconds"], s["max_generator_calls"], s["max_output_tokens"], s["max_usd"],
                             s["max_patch_proposals"], s["max_paired_runs"]) == (600, 12, 24000, 1.0, 4, 6),
            "input cap": s["max_input_tokens"] == 640000,
            "per-request output": c["generator"]["max_output_tokens_per_request"] == 4000,
            "f3 stages": s["f3_stage_max_calls"] == {"planner": 2, "judge": 2},
            "validation": c["validation"]["triplets_per_variant"] * c["validation"]["attempts_per_triplet"] == 15,
            "batch usd": abs(c["study_caps"]["provider_usd"] - 8.1) < 1e-9,
            "unlaunched": c["status"] == "DESIGN_FROZEN_NOT_LAUNCH_READY",
        }
        errors.extend(f"Configuration invariant failed: {k}" for k, ok in checks.items() if not ok)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"Cannot validate configuration: {exc}")
    study = root.parent
    w1 = study.parent.parent / "ai_witness_2026_09"
    try:
        pins = json.loads((root / "w1_inputs.json").read_text(encoding="utf-8"))
        for key, rel in (("w1_executable_freeze_manifest_sha256", "FREEZE.sha256"), ("w1_design_v1_2_manifest_sha256", "v1_2/DESIGN_FREEZE.sha256"),
                         ("w1_raw_seal_manifest_sha256", "raw_seal.sha256")):
            got = hashlib.sha256((w1 / rel).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            if got != pins[key]:
                errors.append(f"W1 {rel} differs from the W2A pin")
    except (OSError, ValueError, KeyError) as exc:
        errors.append(f"Cannot verify W1 pins: {exc}")
    return errors


def main() -> int:
    errors = verify(Path(__file__).resolve().parent)
    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1
    print(f"PASS: {len(EXPECTED)}/{len(EXPECTED)} W2A design hashes and invariants; W1 pins intact.")
    print("Design consistency only; launch readiness is evaluated by w2a.py preflight.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
