"""Pure utilities: canonical JSON, hashing, clocks and small file helpers."""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import math
import os
import time
from pathlib import Path
from typing import Any

ZERO_HASH = "0" * 64
EMPTY_OVERLAY_SHA256 = hashlib.sha256(b'{"files":[]}').hexdigest()
"""Explicit hash of the unchanged (empty) overlay: canonical JSON of its materialized file list."""


class W1Error(RuntimeError):
    """Base class for harness errors that must stop the current operation."""


def _reject_nan(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("NaN/Infinity is not allowed in canonical JSON")
    if isinstance(value, dict):
        for v in value.values():
            _reject_nan(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            _reject_nan(v)
    return value


def canonical_json(value: Any) -> str:
    """UTF-8 canonical JSON: sorted keys, compact separators, no NaN (artifact_contract.md)."""
    _reject_nan(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def canonical_bytes(value: Any) -> bytes:
    return canonical_json(value).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))


def normalized_sha256(path: Path) -> str:
    """SHA-256 of LF-normalized bytes, so digests do not depend on core.autocrlf."""
    return sha256_bytes(Path(path).read_bytes().replace(b"\r\n", b"\n"))


def raw_sha256(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def monotonic() -> float:
    return time.monotonic()


def write_json(path: Path, value: Any, *, pretty: bool = True) -> str:
    """Write JSON with LF endings; return the SHA-256 of the written bytes."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _reject_nan(value)
    text = json.dumps(value, indent=1 if pretty else None, sort_keys=True, ensure_ascii=False, allow_nan=False)
    data = (text + "\n").encode("utf-8")
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)
    return sha256_bytes(data)


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_text_lf(path: Path, text: str) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = text.replace("\r\n", "\n").encode("utf-8")
    path.write_bytes(data)
    return sha256_bytes(data)


def rel_to(path: Path, root: Path) -> str:
    return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
