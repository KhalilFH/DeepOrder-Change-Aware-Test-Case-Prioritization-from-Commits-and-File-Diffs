"""Bounded subprocess execution with monotonic timing (no shell)."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import Sequence

from .common import monotonic, utc_now


@dataclass
class ProcResult:
    argv: list[str]
    exit_code: int | None
    stdout: str
    stderr: str
    elapsed_s: float
    timed_out: bool
    started_utc: str
    ended_utc: str
    error: str | None = None
    extra: dict = field(default_factory=dict)


def run(argv: Sequence[str], *, timeout_s: float, input_bytes: bytes | None = None, cwd: str | None = None) -> ProcResult:
    started = utc_now()
    t0 = monotonic()
    try:
        cp = subprocess.run(
            list(argv), input=input_bytes, capture_output=True, timeout=timeout_s, cwd=cwd,
        )
        return ProcResult(list(argv), cp.returncode, cp.stdout.decode("utf-8", "replace"),
                          cp.stderr.decode("utf-8", "replace"), monotonic() - t0, False, started, utc_now())
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        err = exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return ProcResult(list(argv), None, out, err, monotonic() - t0, True, started, utc_now())
    except OSError as exc:
        return ProcResult(list(argv), None, "", "", monotonic() - t0, False, started, utc_now(), error=repr(exc))
