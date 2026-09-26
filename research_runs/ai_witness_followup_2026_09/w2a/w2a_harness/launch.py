"""Design/W1 verification, provenance, readiness gates, package and launch freezes, smoke and run.

Two freezes, as in W1 but split by authority:

* ``PACKAGE_FREEZE.sha256`` (offline): code, tests, schedule, design manifest digest, W1 input pins
  and offline check reports. Written only when every offline gate passes.
* ``LAUNCH_FREEZE.sha256`` (after the authorized smoke): the package freeze digest plus
  ``launch_config.json`` and ``launch_record.md``. Written only when every gate passes.

``preflight`` starts no container and sends no provider request.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
from typing import Any

from . import CASES, DESIGN_DIR, REPO_ROOT, STUDY_DIR, W1_STUDY_DIR
from .common import canonical_bytes, normalized_sha256, read_json, sha256_bytes, utc_now, write_json
from .config import (EVENTS, LAUNCH_CONFIG, LAUNCH_FREEZE, LAUNCH_RECORD, PACKAGE_FREEZE, PREP_DIR, SCHEDULE,
                     account, design_config)
from .proc import run as prun

COPIED_FROM_W1 = ("common.py", "charging.py", "proc.py", "casespec.py", "overlay.py", "oracles.py", "static_extract.py",
                  "templates.py", "validation.py", "oracle_fixtures.py", "backends.py", "ledger.py", "resources.py")


# --------------------------------------------------------------------------- design and W1 integrity

def verify_design() -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("w2a_verify_design", DESIGN_DIR / "verify_design.py")
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    errors = mod.verify(DESIGN_DIR)
    return {"ok": not errors, "errors": errors, "manifest_sha256": normalized_sha256(DESIGN_DIR / "DESIGN_FREEZE.sha256")
            if (DESIGN_DIR / "DESIGN_FREEZE.sha256").exists() else None}


def verify_w1() -> dict[str, Any]:
    """Read-only: the W1 manifests W2A relies on still have their pinned digests, and every W1
    executable-freeze entry for the reused inputs, oracle code and pinned images still matches."""
    pins = read_json(DESIGN_DIR / "w1_inputs.json")
    problems = []
    for key, rel in (("w1_executable_freeze_manifest_sha256", "FREEZE.sha256"),
                     ("w1_design_v1_2_manifest_sha256", "v1_2/DESIGN_FREEZE.sha256"),
                     ("w1_raw_seal_manifest_sha256", "raw_seal.sha256")):
        if normalized_sha256(W1_STUDY_DIR / rel) != pins[key]:
            problems.append(f"W1 {rel} digest differs from the W2A pin")
    checked = 0
    for line in (W1_STUDY_DIR / "FREEZE.sha256").read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        digest, rel = line.split("  ", 1)
        if "/inputs/" in rel or rel.endswith("w1_harness/oracles.py") or rel.endswith("launch_config.json"):
            checked += 1
            if normalized_sha256(REPO_ROOT / rel) != digest:
                problems.append(f"W1 frozen file changed: {rel}")
    w1_lc = read_json(W1_STUDY_DIR / "launch_config.json")
    if w1_lc["images"] != pins["images"]:
        problems.append("W1 pinned images differ from the W2A pin")
    return {"ok": not problems, "problems": problems, "w1_frozen_files_checked": checked}


def reproduce_w1_audit(out_dir: Path) -> dict[str, Any]:
    """Re-run the W1 post-run audit script into a scratch directory (never into W1) and compare."""
    import contextlib
    import io
    import tempfile
    src = W1_STUDY_DIR / "postrun_audit" / "audit.py"
    spec = importlib.util.spec_from_file_location("w1_postrun_audit", src)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    with tempfile.TemporaryDirectory() as tmp:
        mod.HERE = Path(tmp)
        with contextlib.redirect_stdout(io.StringIO()):
            mod.main()
        fresh = (Path(tmp) / "audit.json").read_bytes()
    recorded = (W1_STUDY_DIR / "postrun_audit" / "audit.json").read_bytes()
    import json
    res = json.loads(fresh)
    out = {"artifact": "w2a_w1_audit_reproduction_v1", "utc": utc_now(), "script": "research_runs/ai_witness_2026_09/postrun_audit/audit.py",
           "script_sha256": sha256_bytes(src.read_bytes()), "recorded_audit_sha256": sha256_bytes(recorded),
           "reproduced_audit_sha256": sha256_bytes(fresh), "byte_identical": fresh == recorded,
           "integrity": {k: {kk: vv for kk, vv in v.items() if kk != "tail"} for k, v in res["integrity"].items()},
           "labels_checked": res["labels_checked"], "complete_policies_checked": res["complete_policies_checked"],
           "returned_models": res["returned_models"], "denials": len(res["denials"]), "table": res["table"],
           "note": "W1 audit re-executed with its output redirected to a temporary directory; W1 files were only read"}
    write_json(out_dir / "w1_audit_reproduction.json", out)
    return out


def provenance() -> dict[str, Any]:
    rows = []
    for name in COPIED_FROM_W1:
        w1 = W1_STUDY_DIR / "w1_harness" / name
        w2 = STUDY_DIR / "w2a_harness" / name
        rows.append({"module": name, "w1_source": w1.relative_to(REPO_ROOT).as_posix(), "w1_sha256": normalized_sha256(w1),
                     "w2a_sha256": normalized_sha256(w2), "byte_identical": normalized_sha256(w1) == normalized_sha256(w2)})
    changes = {"backends.py": "BUILD_TIMEOUT_S 300 -> 60 (matches the reserved build bound); container prefixes w2ab-/w2ar-; docstring",
               "ledger.py": "SCHEMA_VERSION w1-event/1 -> w2a-event/1",
               "resources.py": "study output-token ceiling added; docstring"}
    for r in rows:
        r["declared_change"] = changes.get(r["module"]) if not r["byte_identical"] else None
    undeclared = [r["module"] for r in rows if not r["byte_identical"] and not r["declared_change"]]
    return {"artifact": "w2a_provenance_v1", "utc": utc_now(), "copied_modules": rows, "undeclared_changes": undeclared,
            "new_modules": sorted(p.name for p in (STUDY_DIR / "w2a_harness").glob("*.py") if p.name not in COPIED_FROM_W1),
            "w1_read_only_inputs": ["inputs/<case>/ packets (pinned in design/w1_inputs.json)", "launch_config.json images",
                                    "measured/ responses used as offline replay fixtures and calibration",
                                    "events.jsonl (calibration)", "postrun_audit/audit.py (reproduction)"]}


# --------------------------------------------------------------------------- launch configuration

GENERATOR_KEY_ENV = "W2A_GENERATOR_API_KEY"


def launch_config_template() -> dict[str, Any]:
    d = design_config()
    g = d["generator"]
    return {"artifact": "w2a_launch_config_v1", "written_utc": utc_now(), "design_version": d["design_version"],
            "design_manifest_sha256": verify_design()["manifest_sha256"],
            "generator": {"endpoint": g["endpoint"], "auth": g["auth"], "requested_model": g["requested_model"],
                          "expected_returned_model": g["expected_returned_model"], "credential_env": GENERATOR_KEY_ENV,
                          "credential_present": bool(os.environ.get(GENERATOR_KEY_ENV)), "returned_identity": None,
                          "returned_identity_status": "UNRESOLVED: requires the authorized W2A smoke request",
                          "settings": {k: g[k] for k in ("thinking", "effort", "tool_choice", "tools_strict", "max_output_tokens_per_request",
                                                         "request_timeout_s", "prompt_caching", "input_admission")}},
            "pricing_snapshot": d["pricing_snapshot"], "pricing_confirmed": None,
            "images": read_json(DESIGN_DIR / "w1_inputs.json")["images"],
            "smoke_authorization_record": None, "smoke": None, "measured_run_authorization": None}


def load_launch_config() -> dict[str, Any]:
    return read_json(LAUNCH_CONFIG) if LAUNCH_CONFIG.exists() else launch_config_template()


# --------------------------------------------------------------------------- gates

def _gate(name: str, status: str, evidence: str, detail: str = "", group: str = "offline") -> dict[str, str]:
    return {"gate": name, "status": status, "evidence": evidence, "detail": detail, "group": group}


def code_sha256() -> str:
    files = sorted(p for p in (STUDY_DIR / "w2a_harness").rglob("*.py") if "__pycache__" not in p.parts)
    return hashlib.sha256(canonical_bytes([(p.relative_to(STUDY_DIR).as_posix(), normalized_sha256(p)) for p in files]
                                          + [("w2a.py", normalized_sha256(STUDY_DIR / "w2a.py")),
                                             ("design", normalized_sha256(DESIGN_DIR / "DESIGN_FREEZE.sha256") if (DESIGN_DIR / "DESIGN_FREEZE.sha256").exists() else None)])).hexdigest()


def _report_ok(name: str) -> tuple[bool, str]:
    p = PREP_DIR / name
    if not p.exists():
        return False, f"prep/{name} missing"
    r = read_json(p)
    if not r.get("ok"):
        return False, f"prep/{name} not ok"
    if r.get("code_sha256") != code_sha256():
        return False, f"prep/{name} was produced by different code"
    return True, ""


def docker_state() -> dict[str, Any]:
    r = prun(["docker", "info", "--format", "{{.NCPU}}"], timeout_s=30)
    return {"reachable": r.exit_code == 0, "ncpu": r.stdout.strip()}


def offline_gates(check_docker: bool = True) -> list[dict[str, str]]:
    out = []
    dv = verify_design()
    out.append(_gate("design freeze intact", "PASS" if dv["ok"] else "FAIL", "design/DESIGN_FREEZE.sha256", "; ".join(dv["errors"])))
    w1 = verify_w1()
    out.append(_gate("W1 read-only inputs match their pins", "PASS" if w1["ok"] else "FAIL", "design/w1_inputs.json", "; ".join(w1["problems"])))
    pv = provenance()
    out.append(_gate("copied W1 modules identical or declared", "PASS" if not pv["undeclared_changes"] else "FAIL", "prep/provenance.json",
                     str(pv["undeclared_changes"])))
    from . import schedule as sch
    probs = sch.verify(read_json(SCHEDULE)) if SCHEDULE.exists() else ["schedule.json missing"]
    if SCHEDULE.exists() and read_json(SCHEDULE)["seed"] != design_config()["schedule_seed"]:
        probs.append("schedule seed differs from the design seed")
    out.append(_gate("schedule regenerates from the frozen seed", "PASS" if not probs else "FAIL", "schedule.json", "; ".join(probs)))
    for name, what in (("offline_tests.json", "offline tests pass on current code"),
                       ("dry_run.json", "fake 8-session dry run passes on current code"),
                       ("w1_regressions.json", "W1 failure-case regressions pass on current code"),
                       ("render_check.json", "model-facing renderings are leak-free on current code"),
                       ("budget_check.json", "limit check passes on current code")):
        ok, why = _report_ok(name)
        out.append(_gate(what, "PASS" if ok else "FAIL", f"prep/{name}", why))
    ra = PREP_DIR / "w1_audit_reproduction.json"
    ok = ra.exists() and read_json(ra).get("byte_identical")
    out.append(_gate("W1 offline audit reproduced byte-identically", "PASS" if ok else "FAIL", "prep/w1_audit_reproduction.json"))
    if check_docker:
        ds = docker_state()
        out.append(_gate("16-CPU Docker environment reachable", "PASS" if ds["reachable"] and ds["ncpu"] == "16" else "FAIL",
                         "docker info", str(ds)))
        pins = read_json(DESIGN_DIR / "w1_inputs.json")["images"]
        missing = []
        for case, v in pins.items():
            for variant, iid in v.items():
                r = prun(["docker", "image", "inspect", "--format", "{{.Id}}", iid], timeout_s=30)
                if not (r.exit_code == 0 and r.stdout.strip() == iid):
                    missing.append(f"{case}.{variant}")
        out.append(_gate("pinned subject images present", "PASS" if not missing else "FAIL", "design/w1_inputs.json images", str(missing)))
    fz = verify_package_freeze()
    out.append(_gate("executable package freeze valid", "PASS" if not fz else "FAIL", "PACKAGE_FREEZE.sha256", "; ".join(fz)))
    return out


def provider_gates() -> list[dict[str, str]]:
    lc = load_launch_config()
    g = lc["generator"]
    out = [_gate("generator credential present in environment", "PASS" if os.environ.get(GENERATOR_KEY_ENV) else "FAIL",
                 f"${GENERATOR_KEY_ENV}", "not set in this environment", "provider")]
    ident = g.get("returned_identity")
    out.append(_gate("authorized smoke returned the frozen identity with the W2A request shape",
                     "PASS" if ident == design_config()["generator"]["expected_returned_model"] and (lc.get("smoke") or {}).get("tool_use_returned")
                     else "FAIL", "launch_config.json smoke", f"returned_identity={ident}", "provider"))
    out.append(_gate("pricing snapshot re-confirmed at launch", "PASS" if lc.get("pricing_confirmed") else "FAIL",
                     "launch_config.json pricing_confirmed", "record the source and date of the current price list", "provider"))
    acct = account()
    rem = acct.remaining()
    need = {"generator_requests": 96, "usd": 8.0, "input_tokens": 8 * design_config()["search"]["max_input_tokens"]}
    short = {k: rem[k] for k, v in need.items() if rem[k] + 1e-9 < v}
    out.append(_gate("study reservations cover the full batch", "PASS" if not short else "FAIL", "resources/resource_ledger.jsonl",
                     str(short), "provider"))
    return out


def launch_gates() -> list[dict[str, str]]:
    fz = verify_launch_freeze()
    return [_gate("launch freeze valid", "PASS" if not fz else "FAIL", "LAUNCH_FREEZE.sha256", "; ".join(fz), "launch")]


def ready(gs: list[dict[str, str]], ignore: tuple[str, ...] = ()) -> bool:
    return all(g["status"] == "PASS" for g in gs if g["gate"] not in ignore)


# --------------------------------------------------------------------------- freezes

PACKAGE_GLOBS = ("w2a.py", "w2a_harness/*.py", "w2a_harness/tests/*.py", "schedule.json", "design/DESIGN_FREEZE.sha256",
                 "design/w1_inputs.json", "prep/offline_tests.json", "prep/dry_run.json", "prep/w1_regressions.json",
                 "prep/render_check.json", "prep/rendered/*", "prep/budget_check.json", "prep/provenance.json",
                 "prep/w1_audit_reproduction.json", ".gitignore", ".gitattributes")


def package_files() -> list[Path]:
    files = set()
    for g in PACKAGE_GLOBS:
        for p in STUDY_DIR.glob(g):
            if p.is_file() and "__pycache__" not in p.parts:
                files.add(p.resolve())
    return sorted(files)


def _write_manifest(path: Path, title: str, files: list[Path]) -> None:
    lines = [f"# {title}; frozen_utc {utc_now()}"]
    lines += [f"{normalized_sha256(p)}  {p.relative_to(REPO_ROOT).as_posix()}" for p in files]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _verify_manifest(path: Path, expected_files: list[Path] | None) -> list[str]:
    if not path.exists():
        return [f"{path.name} absent"]
    problems, listed = [], set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        digest, rel = line.split("  ", 1)
        listed.add(rel)
        p = REPO_ROOT / rel
        if not p.exists():
            problems.append(f"{rel}: missing")
        elif normalized_sha256(p) != digest:
            problems.append(f"{rel}: digest mismatch")
    if expected_files is not None:
        extra = sorted({p.relative_to(REPO_ROOT).as_posix() for p in expected_files} - listed)
        if extra:
            problems.append(f"unfrozen files in frozen locations: {extra[:5]}")
    return problems


def write_package_freeze() -> Path:
    gs = offline_gates()
    if not ready(gs, ignore=("executable package freeze valid",)):
        raise RuntimeError("offline gates fail: " + "; ".join(f"{g['gate']}: {g['detail']}" for g in gs if g["status"] != "PASS"))
    _write_manifest(PACKAGE_FREEZE, "W2A executable package freeze (offline gates passed)", package_files())
    return PACKAGE_FREEZE


def verify_package_freeze() -> list[str]:
    return _verify_manifest(PACKAGE_FREEZE, package_files())


def launch_files() -> list[Path]:
    return [PACKAGE_FREEZE, LAUNCH_CONFIG, LAUNCH_RECORD]


def write_launch_freeze() -> Path:
    gs = offline_gates() + provider_gates()
    if not ready(gs):
        raise RuntimeError("gates fail: " + "; ".join(f"{g['gate']}" for g in gs if g["status"] != "PASS"))
    if not LAUNCH_RECORD.exists():
        raise RuntimeError("launch_record.md must exist before the launch freeze")
    _write_manifest(LAUNCH_FREEZE, "W2A launch freeze", launch_files())
    return LAUNCH_FREEZE


def verify_launch_freeze() -> list[str]:
    return _verify_manifest(LAUNCH_FREEZE, None) + (verify_package_freeze() if LAUNCH_FREEZE.exists() else [])


# --------------------------------------------------------------------------- smoke

def smoke_body(model: str) -> dict[str, Any]:
    """Synthetic non-case request with the measured request shape: system text, strict tools, adaptive
    thinking, medium effort, tool_choice auto and two cache breakpoints."""
    tool = {"name": "report_ready", "description": "Report readiness.", "strict": True,
            "input_schema": {"type": "object", "properties": {"status": {"type": "string", "enum": ["ready"]}},
                             "required": ["status"], "additionalProperties": False}}
    return {"model": model, "system": "You are a connectivity check for a research harness. Use the tool.",
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": "Synthetic smoke request; no research content.", "cache_control": {"type": "ephemeral"}},
                {"type": "text", "text": "Call report_ready with status ready.", "cache_control": {"type": "ephemeral"}}]}],
            "tools": [tool], "thinking": {"type": "adaptive"}, "output_config": {"effort": "medium"},
            "tool_choice": {"type": "auto"}, "max_tokens": 1024}
