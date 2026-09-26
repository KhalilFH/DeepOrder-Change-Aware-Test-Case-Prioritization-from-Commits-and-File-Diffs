"""W2A harness: execution-feasibility pilot for AI-assisted behavioral witness strengthening.

Governing design: ``research_runs/ai_witness_followup_2026_09/w2a/design/`` (W2A design v1.0).
W2A is a separate study from W1. It reads immutable W1 subject artifacts (case packets, pinned
images, W1 oracle code copied byte-identically) but never writes into the W1 study directory.

Several modules are copies of W1 ``w1_harness`` modules, byte-identical or with small declared
changes; ``prep/provenance.json`` (``w2a.py provenance``) records every source hash and change.
Standard library only.
"""

from __future__ import annotations

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
STUDY_DIR = PACKAGE_DIR.parent
DESIGN_DIR = STUDY_DIR / "design"
REPO_ROOT = STUDY_DIR.parent.parent.parent
W1_STUDY_DIR = REPO_ROOT / "research_runs" / "ai_witness_2026_09"

CASES = ("pool162", "grpc1859", "k8s26980", "istio17860")
ARMS = ("F2", "F3")
NONCONTROL_CASES = ("pool162", "grpc1859", "k8s26980")
CONTROL_CASES = ("istio17860",)
PROJECT_OF = {
    "pool162": "commons-pool",
    "grpc1859": "grpc-go",
    "k8s26980": "kubernetes",
    "istio17860": "istio",
}

HARNESS_VERSION = "w2a-harness/1.0"
