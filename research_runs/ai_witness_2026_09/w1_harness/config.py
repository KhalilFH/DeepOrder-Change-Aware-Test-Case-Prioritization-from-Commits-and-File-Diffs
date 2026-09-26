"""Frozen design configuration and paths of study artifacts."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from . import DESIGN_DIR, STUDY_DIR
from .common import read_json
from .resources import Caps, ResourceAccount

DESIGN_CONFIG = DESIGN_DIR / "study_config.json"
EVENTS = STUDY_DIR / "events.jsonl"
RESOURCE_LEDGER = STUDY_DIR / "resources" / "resource_ledger.jsonl"
PREP_DIR = STUDY_DIR / "prep"
INPUTS_DIR = STUDY_DIR / "inputs"
ORACLES_DIR = STUDY_DIR / "private_oracles"
CALIBRATION_DIR = STUDY_DIR / "calibration"
MEASURED_DIR = STUDY_DIR / "measured"
ANALYSIS_DIR = STUDY_DIR / "analysis"
SCHEDULE = STUDY_DIR / "schedule.json"
LAUNCH_CONFIG = STUDY_DIR / "launch_config.json"
LAUNCH_RECORD = STUDY_DIR / "launch_record.md"
LAUNCH_FREEZE = STUDY_DIR / "FREEZE.sha256"
READINESS = STUDY_DIR / "readiness.md"
WORK_DIR = STUDY_DIR / "work"  # local, git-ignored scratch for builds (not evidence)


@lru_cache(maxsize=1)
def design_config() -> dict[str, Any]:
    return read_json(DESIGN_CONFIG)


def account(path: Path | None = None) -> ResourceAccount:
    return ResourceAccount(path or RESOURCE_LEDGER, Caps.from_study_config(design_config()))


def timeouts(case: str) -> dict[str, int]:
    return dict(design_config()["timeouts_seconds"][case])
