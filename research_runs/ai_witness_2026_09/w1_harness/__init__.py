"""W1 harness: isolated runner for the AI-assisted behavioral witness study.

Governing design: ``research_runs/ai_witness_2026_09/v1_2/`` (design v1.2, amendment A2:
generator Claude Sonnet 5). v1.1 (``v1_1/``) and v1 (one level up) are superseded and must stay
byte-identical; the v1.2 verifier checks both.

This package imports nothing from the historical C1/E1 harnesses; the small
utilities it needs (canonical JSON, hash chains) are reimplemented here so the
historical harness behaviour cannot change and the launch hash set stays local.
Standard library only.
"""

from __future__ import annotations

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
STUDY_DIR = PACKAGE_DIR.parent
DESIGN_DIR = STUDY_DIR / "v1_2"
REPO_ROOT = STUDY_DIR.parent.parent

CASES = ("pool162", "grpc1859", "k8s26980", "istio17860")
ARMS = ("B0", "B1", "B2", "B3", "B4")
GO_CASES = ("grpc1859", "k8s26980", "istio17860")
NONCONTROL_CASES = ("pool162", "grpc1859", "k8s26980")
CONTROL_CASES = ("istio17860",)
PROJECT_OF = {
    "pool162": "commons-pool",
    "grpc1859": "grpc-go",
    "k8s26980": "kubernetes",
    "istio17860": "istio",
}

HARNESS_VERSION = "w1-harness/1.0"
