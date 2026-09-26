"""Repository-root launcher: ``python research_runs/ai_witness_followup_2026_09/w2a/w2a.py <command>``."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from w2a_harness.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
