"""W2A paths and frozen design configuration (``design/study_config.json``).

W2A writes only below its own study directory. W1 paths are read-only inputs.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from . import DESIGN_DIR, STUDY_DIR, W1_STUDY_DIR
from .common import read_json
from .resources import Caps, ResourceAccount

DESIGN_CONFIG = DESIGN_DIR / "study_config.json"
EVENTS = STUDY_DIR / "events.jsonl"
RESOURCE_LEDGER = STUDY_DIR / "resources" / "resource_ledger.jsonl"
PREP_DIR = STUDY_DIR / "prep"
MEASURED_DIR = STUDY_DIR / "measured"
ANALYSIS_DIR = STUDY_DIR / "analysis"
SCHEDULE = STUDY_DIR / "schedule.json"
LAUNCH_CONFIG = STUDY_DIR / "launch_config.json"
LAUNCH_RECORD = STUDY_DIR / "launch_record.md"
PACKAGE_FREEZE = STUDY_DIR / "PACKAGE_FREEZE.sha256"
LAUNCH_FREEZE = STUDY_DIR / "LAUNCH_FREEZE.sha256"
RAW_SEAL = STUDY_DIR / "raw_seal.sha256"
READINESS = STUDY_DIR / "readiness.md"
WORK_DIR = STUDY_DIR / "work"  # local, git-ignored scratch for builds (not evidence)

# Read-only W1 inputs (never written by W2A).
W1_INPUTS_DIR = W1_STUDY_DIR / "inputs"
ORACLES_DIR = W1_STUDY_DIR / "private_oracles"  # referenced by the copied oracle_fixtures module; never written
W1_LAUNCH_CONFIG = W1_STUDY_DIR / "launch_config.json"


@lru_cache(maxsize=1)
def design_config() -> dict[str, Any]:
    return read_json(DESIGN_CONFIG)


def search_config() -> dict[str, Any]:
    return design_config()["search"]


def account(path: Path | None = None) -> ResourceAccount:
    return ResourceAccount(path or RESOURCE_LEDGER, Caps.from_study_config(design_config()))


def timeouts(case: str) -> dict[str, int]:
    return dict(design_config()["timeouts_seconds"][case])
