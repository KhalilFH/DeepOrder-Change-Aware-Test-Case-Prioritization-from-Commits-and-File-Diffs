"""Repository-root launcher: ``python research_runs/ai_witness_2026_09/w1.py <command>``."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from w1_harness.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
