"""EXPLORATORY / POST HOC: run one audit script and record its timed cost.

Usage (repository root): python -B research_runs/ci_configuration_2026_09/signal_audit/run_timed.py sNN_name.py

Appends one line to signal_audit/cost_log.jsonl. Cost basis follows the prior
post-collection pass: conservative 16 allocated vCPUs x wall-clock elapsed time
(Windows host process, no container). This log is kept separate from the
chained resources/resource_ledger.jsonl, which this audit does not modify.
"""
from __future__ import annotations

import datetime as dt
import os
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASIS_VCPUS = 16


def main() -> int:
    script = HERE / sys.argv[1]
    started = dt.datetime.now(dt.timezone.utc)
    t0 = time.perf_counter()
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    proc = subprocess.run([sys.executable, "-B", str(script)], capture_output=True, text=True,
                          encoding="utf-8", env=env, cwd=str(HERE))
    elapsed = time.perf_counter() - t0
    stem = script.stem
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / f"{stem}.stdout.txt").write_text(proc.stdout, encoding="utf-8", newline="\n")
    (HERE / "out" / f"{stem}.stderr.txt").write_text(proc.stderr, encoding="utf-8", newline="\n")
    row = {
        "label": "exploratory post-hoc signal audit",
        "script": script.name,
        "script_sha256": hashlib.sha256(script.read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        "python": sys.version.split()[0],
        "started_utc": started.isoformat(),
        "elapsed_s": round(elapsed, 6),
        "basis_vcpus": BASIS_VCPUS,
        "charged_vcpu_h": BASIS_VCPUS * elapsed / 3600,
        "returncode": proc.returncode,
    }
    with open(HERE / "cost_log.jsonl", "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")
    sys.stdout.buffer.write(proc.stdout.encode("utf-8"))
    sys.stdout.flush()
    sys.stderr.write(proc.stderr)
    print(f"[timed] {script.name}: {elapsed:.3f}s -> {row['charged_vcpu_h']:.6f} vCPU-h (rc={proc.returncode})")
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
