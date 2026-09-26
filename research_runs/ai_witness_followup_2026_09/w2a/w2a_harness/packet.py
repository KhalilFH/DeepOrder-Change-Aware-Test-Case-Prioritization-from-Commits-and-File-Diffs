"""Read-only W1 case packets, the W2A helper-inclusion rule and the model-facing leak screen.

W2A reuses W1's immutable per-case packets (``research_runs/ai_witness_2026_09/inputs/<case>``)
without rebuilding them. ``load_packet`` verifies both W1's own manifest hash chain and the
packet hash pinned in ``design/w1_inputs.json``; any mismatch stops the harness.

Helper-inclusion rule (METHOD_CONTRACT.md "Deterministic context"), applied identically to F2
and F3, using only T0 static extraction and packet source (no oracle or outcome knowledge):

* H1 (direct test-side callees). For each supplied entry point in T0 ``entry_point_ranks``
  order, take its T0 ``direct_calls`` callees in source order. Keep each callee definition that
  lies in a shared *test* file (Go ``*_test.go``; Java ``src/test/``) of the entry point's own
  package directory (Go) or its own class file (Java). Skip Go callees qualified by an imported
  package name of the entry-point file (for example ``errors.New``).
* H2 (JUnit 3 fixture). For Java entry points, add ``setUp()`` and ``tearDown()`` declared in
  the entry point's class file; JUnit 3 runs them around every test method.
* Skip definitions already fully visible in the initial excerpts; clip each definition to 80
  lines; at most 8 definitions and 240 lines per case, in rule order; record every omission.
"""

from __future__ import annotations

import re
from typing import Any

from . import CASES, DESIGN_DIR
from .common import W1Error, read_json, sha256_bytes, sha256_json
from .config import W1_INPUTS_DIR, search_config
from .overlay import go_imports

W2AError = W1Error

HELD_OUT_MARKERS = (
    # W1 markers (w1_harness/packet.py), unchanged
    "testWhenExhaustedBlockInterupt", "POOL-162", "subject_register", "private_oracles", "VALIDATED_WITNESS",
    "FOCAL_FAILURE", "focal oracle", "C1 ", "ci_configuration_2026_09", "must not consume capacity",
    "strand send quota", "retain the listener lock", "epoch-exit processing", "premise_evidence",
    "consequence_evidence", "rule_id",
    # W2A additions: W1 outcomes, audit and trace material
    "NO_WITNESS_WITHIN_BUDGET", "NO_SUBMISSION", "INVALID_CANDIDATE", "postrun_audit", "results_report",
    "raw_seal", "ai_witness_2026_09", "ai_witness_followup", "measured/w1.", "w1.pool162.", "w1.grpc1859.",
    "w1.k8s26980.", "w1.istio17860.", "BUDGET_DENIED", "private_oracle",
)


def leak_scan(text: str) -> list[str]:
    return [m for m in HELD_OUT_MARKERS if m in text]


def pinned_inputs() -> dict[str, Any]:
    return read_json(DESIGN_DIR / "w1_inputs.json")


def load_packet(case: str) -> dict[str, Any]:
    """Load and verify one W1 packet (read-only)."""
    dest = W1_INPUTS_DIR / case
    manifest = read_json(dest / "packet_manifest.json")
    body = {k: v for k, v in manifest.items() if k != "packet_sha256"}
    if sha256_json(body) != manifest["packet_sha256"]:
        raise W2AError(f"{case}: W1 packet manifest hash mismatch")
    pinned = pinned_inputs()["packets"][case]["packet_sha256"]
    if manifest["packet_sha256"] != pinned:
        raise W2AError(f"{case}: W1 packet {manifest['packet_sha256']} differs from the W2A pin {pinned}")
    files = {}
    for fid, e in manifest["files"].items():
        text = (dest / "files" / fid).read_text(encoding="utf-8").replace("\r\n", "\n")
        if sha256_bytes(text.encode("utf-8")) != e["sha256"]:
            raise W2AError(f"{case}: packet file {fid} changed")
        files[fid] = text
    diff = (dest / "diff.patch").read_text(encoding="utf-8").replace("\r\n", "\n")
    if sha256_bytes(diff.encode("utf-8")) != manifest["diff_sha256"]:
        raise W2AError(f"{case}: diff changed")
    t0 = read_json(dest / "t0.json")
    if sha256_json(t0) != manifest["t0_sha256"]:
        raise W2AError(f"{case}: t0 changed")
    br = (dest / "build_run.md").read_text(encoding="utf-8").replace("\r\n", "\n")
    if sha256_bytes(br.encode("utf-8")) != manifest["build_run_sha256"]:
        raise W2AError(f"{case}: build_run changed")
    pkt = {"case": case, "manifest": manifest, "files": files, "diff": diff, "t0": t0, "build_run": br}
    pkt["excerpt_ranges"] = excerpt_ranges(pkt)
    pkt["helpers"] = helper_definitions(pkt)
    return pkt


def originals(packet: dict[str, Any]) -> dict[str, str]:
    return {p: packet["files"][f"shared/{p}"] for p in packet["manifest"]["editable_files"]}


def file_lines(packet: dict[str, Any], fid: str) -> int:
    return len(packet["files"][fid].split("\n"))


# --------------------------------------------------------------------------- initial excerpts (W1 rule)

INITIAL_EXCERPT_MAX_LINES = 400  # as W1 prompts.INITIAL_EXCERPT_MAX_LINES


def excerpt_ranges(packet: dict[str, Any]) -> list[tuple[str, int, int]]:
    """W1's deterministic initial excerpts: entry-point tests, then changed functions (defective)."""
    t0 = packet["t0"]
    out: list[tuple[str, int, int]] = []
    for r in t0.get("entry_point_ranks", []):
        path, rng = r["span"].rsplit(":", 1)
        a, b = (int(x) for x in rng.split("-"))
        fid = f"shared/{path}"
        out.append((fid, a, min(b, file_lines(packet, fid), a + INITIAL_EXCERPT_MAX_LINES - 1)))
    seen = set()
    for c in t0["changed_functions"]:
        if c["version"] != "defective" or c["span"] in seen:
            continue
        seen.add(c["span"])
        path, rng = c["span"].rsplit(":", 1)
        a, b = (int(x) for x in rng.split("-"))
        fid = f"defective/{path}"
        out.append((fid, a, min(b, file_lines(packet, fid), a + INITIAL_EXCERPT_MAX_LINES - 1)))
    return out


def covered(ranges: list[tuple[str, int, int]], fid: str, a: int, b: int) -> bool:
    return any(f == fid and x <= a and b <= y for f, x, y in ranges)


# --------------------------------------------------------------------------- helper rule

def _is_test_file(path: str) -> bool:
    return path.endswith("_test.go") or "/src/test/" in f"/{path}" or path.startswith("src/test/")


def _dirname(path: str) -> str:
    return path.rsplit("/", 1)[0] if "/" in path else ""


def _java_method_range(text: str, name: str) -> tuple[int, int] | None:
    """Line range of a no-argument method ``name`` declared in ``text`` (brace matching)."""
    lines = text.split("\n")
    pat = re.compile(rf"^\s*(public|protected|private)?\s*(static\s+)?void\s+{re.escape(name)}\s*\(\s*\)")
    for i, line in enumerate(lines):
        if pat.search(line):
            depth, opened = 0, False
            for j in range(i, len(lines)):
                depth += lines[j].count("{") - lines[j].count("}")
                opened = opened or "{" in lines[j]
                if opened and depth <= 0:
                    return i + 1, j + 1
            return None
    return None


def helper_definitions(packet: dict[str, Any]) -> dict[str, Any]:
    """Apply rules H1/H2; return included definitions and a record of every omission."""
    cfg = search_config()["helper_rule"]
    t0 = packet["t0"]
    lang = "java" if any(fid.endswith(".java") for fid in packet["files"]) else "go"
    calls_by_caller = {d["caller"]: d for d in t0["direct_calls"]}
    included: list[dict[str, Any]] = []
    omitted: list[dict[str, Any]] = []
    total = 0
    seen: set[tuple[str, int, int]] = set()
    excerpts = packet["excerpt_ranges"]

    def consider(rule: str, entry: str, callee: str, fid: str, a: int, b: int) -> None:
        nonlocal total
        key = (fid, a, b)
        if key in seen:
            return
        seen.add(key)
        if covered(excerpts, fid, a, b):
            omitted.append({"rule": rule, "entry_point": entry, "callee": callee, "span": f"{fid}:{a}-{b}",
                            "reason": "already in initial excerpts"})
            return
        if len(included) >= cfg["max_definitions_per_case"] or total >= cfg["max_lines_per_case"]:
            omitted.append({"rule": rule, "entry_point": entry, "callee": callee, "span": f"{fid}:{a}-{b}",
                            "reason": "per-case helper cap reached"})
            return
        end = min(b, a + cfg["max_lines_per_definition"] - 1, a + (cfg["max_lines_per_case"] - total) - 1)
        included.append({"rule": rule, "entry_point": entry, "callee": callee, "file_id": fid, "start": a, "end": end,
                         "definition_end": b, "clipped": end < b})
        total += end - a + 1

    for er in t0.get("entry_point_ranks", []):
        entry = er["entry_point"]
        epath = er["span"].rsplit(":", 1)[0]
        name = entry.split("#")[-1]
        d = calls_by_caller.get(name)
        imported = {i.rsplit("/", 1)[-1] for i in go_imports(packet["files"][f"shared/{epath}"])} if lang == "go" else set()
        for c in (d or {}).get("calls", []):
            callee = c["callee"]
            qualifier = callee.split(".", 1)[0] if "." in callee else None
            if lang == "go" and qualifier in imported:
                continue
            for definition in c.get("definitions") or []:
                path, rng = definition.rsplit(":", 1)
                a, b = (int(x) for x in rng.split("-"))
                fid = f"shared/{path}"
                if fid not in packet["files"] or not _is_test_file(path):
                    continue
                if lang == "go" and _dirname(path) != _dirname(epath):
                    continue
                if lang == "java" and path != epath:
                    continue
                if name == callee:
                    continue
                consider("H1", entry, callee, fid, a, b)
        if lang == "java":
            fid = f"shared/{epath}"
            for fixture in ("setUp", "tearDown"):
                rng = _java_method_range(packet["files"][fid], fixture)
                if rng:
                    consider("H2", entry, fixture, fid, *rng)
    return {"included": included, "omitted": omitted, "total_lines": total,
            "rule": "H1 direct test-side callees + H2 JUnit3 fixtures (packet.py docstring)"}
