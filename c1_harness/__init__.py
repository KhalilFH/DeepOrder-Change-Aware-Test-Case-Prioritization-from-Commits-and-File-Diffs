"""C1 adapter: CPU configuration and defect visibility (study `c1_ci_configuration_visibility_v1`).

A narrow layer over `e1_harness`. It reuses E1's policy reducer, append-only
ledger, oracle classifier and exact-interval primitives unchanged, and adds only
what C1 needs and E1 lacks: enforced and evidenced CPU profiles, matched R/L
blocks with unique identities, a budget guard, three more oracle cards, and the
matched-block analysis. `e1_harness/`, the pipeline and every historical result
file are read, never written.

The design is frozen in `research_runs/ci_configuration_2026_09/` (see
`DESIGN_FREEZE.md`); this package implements it and does not redefine it.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
E1_DIR = REPO_ROOT / "e1_harness"
STUDY_DIR = REPO_ROOT / "research_runs" / "ci_configuration_2026_09"

# E1 modules import each other by flat name (`from ledger import ...`), so the
# E1 directory has to be importable as a top-level path. C1 modules live in this
# package and never shadow those names.
if str(E1_DIR) not in sys.path:
    sys.path.insert(0, str(E1_DIR))

STUDY_ID = "c1_ci_configuration_visibility_v1"
HARNESS_VERSION = "c1-harness/1"

SUBJECT_ORDER = ("etcd5509", "etcd7492", "grpc1859", "grpc2391", "istio17860", "k8s26980")
"""The fixed roster and order (protocol section 2). Never extended."""
