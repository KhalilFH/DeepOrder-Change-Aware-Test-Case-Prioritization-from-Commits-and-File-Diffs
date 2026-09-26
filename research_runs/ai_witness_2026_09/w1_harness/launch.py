"""Launch fields, cost projection, readiness gates, preflight and the executable freeze.

* ``launch_config()`` resolves runtime fields into launch_config.json without editing the frozen
  design (null design placeholders stay null there). Unresolved fields stay null with a reason.
* ``projection()`` gives an expected and a timeout-bound allocated-CPU projection plus provider
  ceilings; the expected cost plus 20 % headroom must fit the remaining study cap.
* ``gates()`` evaluates every readiness gate (PASS / FAIL / UNKNOWN with evidence).
* ``preflight()`` is non-executing: it starts no container and sends no provider request.
* ``write_freeze()`` refuses unless every gate passes; ``verify_freeze()`` recomputes it.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Any

from . import CASES, DESIGN_DIR, NONCONTROL_CASES, PROJECT_OF, REPO_ROOT, STUDY_DIR
from .common import normalized_sha256, read_json, sha256_json, utc_now, write_json
from .config import (CALIBRATION_DIR, EVENTS, INPUTS_DIR, LAUNCH_CONFIG, LAUNCH_FREEZE, LAUNCH_RECORD, ORACLES_DIR,
                     PREP_DIR, RESOURCE_LEDGER, SCHEDULE, account, design_config)
from .proc import run as prun
from .providers import ANTHROPIC_URL, ANTHROPIC_VERSION, JEV_URL

GENERATOR_KEY_ENV = "W1_GENERATOR_API_KEY"  # holds the OpenCode Zen key
GENERATOR_ENDPOINT = "https://opencode.ai/zen/v1/messages"
JEV_KEY_ENV = "TYPESAFE_API_KEY"
PRICING_SNAPSHOT = {
    "generator": {"model": "claude-sonnet-5", "input_per_mtok_usd": 2.0, "output_per_mtok_usd": 10.0,
                  "cache_read_per_mtok_usd": 0.20, "cache_write_per_mtok_usd": 2.50,
                  "source": "https://opencode.ai/docs/zen/ (OpenCode Zen price list, fetched 2026-09-26); equals "
                            "Anthropic list prices for Claude Sonnet 5 (platform.claude.com pricing, fetched 2026-09-26)",
                  "notes": "thinking tokens are billed as output tokens; explicit 5-minute prompt caching; no batch or fast mode"},
    "jev": {"model": "jev (alias jev-latest)", "input_per_mtok_usd": 0.042, "output_per_mtok_usd": 0.0,
            "source": "docs.typesafe.ai consistency cookbook: 'Historical TypeSafe rate, as of 2026-08' (via Context7, 2026-09-26)",
            "status": "ACCEPTED BY RESEARCHER 2026-09-26 ('jev is okay no issue on that'); documentation rate, "
                      "not an official price list; negligible against the caps even if 100x higher"},
}
GENERATOR_SETTINGS = {
    "thinking": {"type": "adaptive"},
    "output_config": {"effort": "medium"},
    "prompt_caching": "explicit ephemeral (5-minute) breakpoint on the first, packet-bearing user message of each stage conversation",
    "input_admission": "local estimate: ceil(UTF-8 bytes of the JSON request / 2) + 512 tokens (OpenCode Zen documents no token-count endpoint); reported usage is charged",
    "tool_choice": {"type": "auto"},
    "tools_strict": True,
    "max_tokens_per_request": 4000,
    "request_timeout_s": 240,
    "temperature": "unsupported on claude-sonnet-5 (non-default sampling parameters rejected); not sent",
    "seed": "unsupported; not simulated",
    "fallbacks": "not requested (would substitute another model)",
    "speed": "standard (fast mode not used)",
    "effort_rationale": "medium, one level below the Sonnet 5 default (high), fixed before any provider call because "
                        "thinking is billed as output and the frozen 8k output-token session ceiling covers every request; "
                        "not tuned on any W1 outcome",
}


def _run_verifier(path: Path) -> list[str]:
    spec = importlib.util.spec_from_file_location(f"w1v_{abs(hash(path))}", path)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod.verify(path.parent)


def verify_design() -> dict[str, Any]:
    errs_v11 = _run_verifier(DESIGN_DIR / "verify_design.py")
    independent = []
    for line in (DESIGN_DIR / "DESIGN_FREEZE.sha256").read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        got = __import__("hashlib").sha256((DESIGN_DIR / name).read_bytes()).hexdigest()
        if got != digest:
            independent.append(name)
    return {"design_errors": errs_v11, "independent_mismatches": independent,
            "manifest_sha256": normalized_sha256(DESIGN_DIR / "DESIGN_FREEZE.sha256"),
            "ok": not errs_v11 and not independent, "design_dir": DESIGN_DIR.name}


def qualification() -> dict[str, Any]:
    out = {}
    for case in CASES:
        p = PREP_DIR / "subjects" / case / "restoration.json"
        d = read_json(p) if p.exists() else {}
        builds = d.get("qualification_builds") or []
        built = bool(builds) and all(r["ok"] for r in builds[-1]["results"].values())
        identity = (d.get("image_check") or {}).get("passed") if case != "pool162" else bool(d.get("images")) and \
            d.get("production_delta") == ["src/java/org/apache/commons/pool/impl/GenericKeyedObjectPool.java",
                                          "src/java/org/apache/commons/pool/impl/GenericObjectPool.java"]
        packet_ok = (INPUTS_DIR / case / "packet_manifest.json").exists()
        oracle_ok = (ORACLES_DIR / case / "ORACLE.md").exists() and (ORACLES_DIR / case / "fixtures" / "expected.json").exists()
        cal = read_json(CALIBRATION_DIR / "report.json") if (CALIBRATION_DIR / "report.json").exists() else None
        blocked = bool(cal and cal["per_case"].get(case, {}).get("repaired_nonpass_blocks_case"))
        qualified = bool(identity and built and packet_ok and oracle_ok and not blocked)
        out[case] = {"project": PROJECT_OF[case], "source_identity": bool(identity), "unchanged_build": built,
                     "packet": packet_ok, "oracle": oracle_ok, "calibration_blocks": blocked,
                     "build_invocations": d.get("build_invocations"), "qualified": qualified}
    return out


def images() -> dict[str, dict[str, str]]:
    from .qualify import image_ids
    return image_ids()


def launch_config(status: str = "NOT_READY") -> dict[str, Any]:
    cfg = design_config()
    dv = verify_design()
    q = qualification()
    return {
        "artifact": "w1_launch_config_v1",
        "written_utc": utc_now(),
        "status": status,
        "design": {"version": cfg["design_version"], "manifest_sha256": dv["manifest_sha256"],
                   "note": "null provider placeholders in v1_2/study_config.json stay null; resolved values live here"},
        "roster": q,
        "images": images(),
        "environment": {"visible_logical_cpus": 16, "go_gomaxprocs": 16, "cpu_bandwidth_limit": None,
                        "concurrent_subject_processes": 1, "network": "none (container --network none)",
                        "scheduler_backend": None,
                        "scheduler_reason": "no controlled scheduler qualified: Fray targets modern JDKs and was not "
                                            "structurally prequalified for the historical POOL build, and no Go scheduler "
                                            "was prescribed; B1 has no controlled-scheduling component (narrower comparator)"},
        "timeouts_seconds": cfg["timeouts_seconds"],
        "build_timeout_seconds": 60,
        "generator": {
            "requested_family": cfg["provider_launch_fields"]["requested_generator_family"],
            "transport": f"OpenCode Zen, Anthropic-Messages-compatible endpoint, raw HTTPS via Python urllib, "
                         f"Authorization: Bearer (anthropic-version {ANTHROPIC_VERSION}); no SDK retries",
            "endpoint": GENERATOR_ENDPOINT,
            "auth": "both",
            "auth_note": "x-api-key and Authorization: Bearer both carry the Zen key: the documented Bearer header alone "
                         "returned 401 'Missing API key' on the Anthropic-format endpoint (smoke, 2026-09-26)",
            "count_tokens_url": None,
            "requested_model": "claude-sonnet-5",
            "requested_model_source": "OpenCode Zen model list (opencode.ai/docs/zen, fetched 2026-09-26): claude-sonnet-5 at "
                                      "https://opencode.ai/zen/v1/messages; Zen documents no routing or substitution policy, so "
                                      "the returned identity must be confirmed by the authorized smoke",
            "returned_identity": None,
            "returned_identity_status": "UNRESOLVED: requires the OpenCode Zen key and the authorized synthetic smoke request",
            "credential_env": GENERATOR_KEY_ENV,
            "credential_present": bool(os.environ.get(GENERATOR_KEY_ENV)),
            "settings": GENERATOR_SETTINGS,
        },
        "jev": {
            "transport": "TypeSafe System One API, raw HTTPS via Python urllib (Bearer auth)",
            "endpoint": JEV_URL,
            "requested_model": "jev-latest",
            "returned_identity": None,
            "returned_identity_status": "UNRESOLVED: alias; the returned version (docs example: jev-1.13.0) must be "
                                        "recorded by the authorized smoke and then frozen; a different return pauses sessions",
            "credential_env": JEV_KEY_ENV,
            "credential_present": bool(os.environ.get(JEV_KEY_ENV)),
            "question": "typed choice supported/contradicted/unknown (prompts.md B4 stage 2), one request per atomic claim",
        },
        "pricing_snapshot": PRICING_SNAPSHOT,
        "budgets": {"study_caps": cfg["study_caps"], "session": cfg["search"]},
        "live_smoke_authorized": cfg["provider_launch_fields"]["live_smoke_authorized"],
        "live_smoke_authorization_record": None,
        "measured_run_authorization": None,
        "commands": commands(),
    }


def commands() -> dict[str, str]:
    base = "python research_runs/ai_witness_2026_09/w1.py"
    return {k: f"{base} {v}" for k, v in {
        "verify_design": "verify-design", "inventory": "inventory", "offline_tests": "test", "dry_run": "dry-run",
        "calibrate": "calibrate", "preflight": "preflight", "launch_config": "launch-config",
        "projection": "projection", "freeze": "freeze", "verify_launch": "verify-launch",
        "measured_run": 'run --authorize "<researcher launch instruction>"', "analyze": "analyze"}.items()}


def projection() -> dict[str, Any]:
    cfg = design_config()
    cal = read_json(CALIBRATION_DIR / "report.json") if (CALIBRATION_DIR / "report.json").exists() else None
    t = cfg["timeouts_seconds"]
    per_case_attempt_s = {}
    for case in CASES:
        el = (cal or {}).get("per_case", {}).get(case, {}).get("elapsed_s") or []
        per_case_attempt_s[case] = max(el) if el else float(t[case]["outer"])
    sessions_per_case = 15
    # expected search elapsed: B0/B1 = builds + six pairs at calibrated attempt time; AI arms = full 600 s (conservative)
    exp_search_s = 0.0
    for case in CASES:
        a = per_case_attempt_s[case]
        b0 = 2 * 10 + 6 * 2 * a
        b1 = 4 * 2 * 10 + 6 * 2 * a
        exp_search_s += 3 * (b0 + b1 + 3 * 600)
    exp_valid_s = sum(sessions_per_case * 30 * per_case_attempt_s[c] + sessions_per_case * 2 * 10 for c in CASES)
    exp_vcpu = 16 * (exp_search_s + exp_valid_s) / 3600
    tb_search = 16 * 60 * 600 / 3600
    tb_valid = 16 * sum(sessions_per_case * 30 * (t[c]["outer"] + t[c]["cleanup"]) + sessions_per_case * 2 * 90 for c in CASES) / 3600
    acct = account()
    rem = acct.remaining()
    prep_spent = acct.committed("vcpu_h", ("preparation", "calibration", "smoke"))
    headroom = cfg["study_caps"]["expected_cost_headroom_fraction"]
    s = cfg["search"]
    ai_sessions = 36
    g = PRICING_SNAPSHOT["generator"]
    per_session_usd_max = (s["max_input_tokens"] * max(g["input_per_mtok_usd"], g["cache_write_per_mtok_usd"])
                           + s["max_output_tokens"] * g["output_per_mtok_usd"]) / 1e6
    return {
        "artifact": "w1_cost_projection_v1", "utc": utc_now(),
        "basis": {"attempt_seconds_per_case": per_case_attempt_s,
                  "source": "max observed fixed-calibration attempt (unchanged test) per case; outer timeout if absent",
                  "ai_session_seconds": "600 (full allowance, conservative)", "build_seconds": 10},
        "allocated_vcpu_h": {
            "preparation_spent_so_far": round(prep_spent, 4),
            "expected_measured": round(exp_vcpu, 2),
            "expected_measured_with_headroom": round(exp_vcpu * (1 + headroom), 2),
            "timeout_bound_measured": round(tb_search + tb_valid, 2),
            "timeout_bound_components": {"search": round(tb_search, 2), "validation": round(tb_valid, 2)},
            "remaining_study_cap": round(rem["vcpu_h_total"], 4),
            "expected_fits": exp_vcpu * (1 + headroom) <= rem["vcpu_h_total"],
            "timeout_bound_fits": tb_search + tb_valid <= rem["vcpu_h_total"],
            "note": "timeout-bound exceeds the cap: a slow or failing study may stop incomplete (reported, not reserved)",
        },
        "provider": {
            "ai_sessions": ai_sessions,
            "max_generator_requests": 12 * 4 + 12 * 4 + 12 * 3, "cap_generator_requests": cfg["study_caps"]["generator_requests"],
            "max_jev_evaluations": 12 * 8, "cap_jev_evaluations": cfg["study_caps"]["jev_atomic_evaluations"],
            "max_input_tokens": ai_sessions * s["max_input_tokens"], "cap_input_tokens": cfg["study_caps"]["input_tokens"],
            "max_usd_per_session_at_token_ceilings": round(per_session_usd_max, 4), "cap_usd_per_session": s["max_usd"],
            "timeout_bound_usd": round(ai_sessions * per_session_usd_max, 2), "cap_usd": cfg["study_caps"]["provider_usd"],
            "expected_usd": round(ai_sessions * per_session_usd_max * 0.75, 2),
            "expected_basis": "75% of token ceilings (no live observation exists; conservative placeholder)",
            "pricing": PRICING_SNAPSHOT,
            "fits": ai_sessions * per_session_usd_max <= cfg["study_caps"]["provider_usd"]
                    and ai_sessions * s["max_input_tokens"] <= cfg["study_caps"]["input_tokens"],
        },
    }


# --------------------------------------------------------------------------- gates

def _gate(name: str, status: str, evidence: str, detail: str = "") -> dict[str, str]:
    return {"gate": name, "status": status, "evidence": evidence, "detail": detail}


def docker_state() -> dict[str, Any]:
    r = prun(["docker", "info", "--format", "{{.NCPU}}"], timeout_s=30)
    ps = prun(["docker", "ps", "-q"], timeout_s=30)
    return {"reachable": r.exit_code == 0, "ncpu": r.stdout.strip(), "running": ps.stdout.split() if ps.exit_code == 0 else None}


def gates(check_docker: bool = True) -> list[dict[str, str]]:
    cfg = design_config()
    out = []
    dv = verify_design()
    out.append(_gate("design freeze v1.2 (+ chained v1.1, v1) intact", "PASS" if dv["ok"] else "FAIL", "v1_2/DESIGN_FREEZE.sha256",
                     "; ".join(dv["design_errors"] + dv["independent_mismatches"])))
    q = qualification()
    qual = [c for c, v in q.items() if v["qualified"]]
    projects = {PROJECT_OF[c] for c in qual}
    nonctrl = [c for c in qual if c in NONCONTROL_CASES]
    ok_roster = len(qual) >= cfg["minimum_subjects"] and len(projects) >= 3 and len(nonctrl) >= cfg["minimum_noncontrol_subjects"]
    out.append(_gate("minimum structurally qualified roster", "PASS" if ok_roster else "FAIL",
                     "prep/subjects/*/restoration.json, calibration/report.json", f"qualified={qual}"))
    if check_docker:
        ds = docker_state()
        env_ok = ds["reachable"] and ds["ncpu"] == "16"
        out.append(_gate("16-CPU execution environment reachable", "PASS" if env_ok else "FAIL",
                         "prep/subjects/*/restoration.json environment_probe", f"docker={ds}"))
        from .qualify import image_ids
        ids = image_ids()
        present = []
        for case, v in ids.items():
            for variant, iid in v.items():
                r = prun(["docker", "image", "inspect", "--format", "{{.Id}}", iid], timeout_s=30)
                present.append(r.exit_code == 0 and r.stdout.strip() == iid)
        out.append(_gate("pinned subject images present", "PASS" if all(present) else "FAIL", "launch_config.json images"))
    from .packet import leak_scan, load_packet
    from . import prompts, templates
    try:
        leaks = {c: leak_scan(prompts.packet_context(load_packet(c), templates.bindings(c))) for c in CASES}
        pk = "PASS" if not any(leaks.values()) else "FAIL"
    except Exception as exc:  # noqa: BLE001
        pk, leaks = "FAIL", {"error": str(exc)}
    out.append(_gate("packets verified and leak-free", pk, "inputs/<case>/packet_manifest.json", str(leaks)))
    from . import schedule as sch
    sp = sch.verify(read_json(SCHEDULE)) if SCHEDULE.exists() else ["missing"]
    out.append(_gate("complete schedule regenerates", "PASS" if not sp else "FAIL", "schedule.json", "; ".join(sp)))
    tr = PREP_DIR / "offline_tests.json"
    t_ok = tr.exists() and read_json(tr).get("ok") and read_json(tr).get("code_sha256") == code_sha256()
    out.append(_gate("offline tests pass on current code", "PASS" if t_ok else "FAIL", "prep/offline_tests.json"))
    dr = PREP_DIR / "dry_run.json"
    d_ok = dr.exists() and read_json(dr).get("ok") and read_json(dr).get("code_sha256") == code_sha256()
    out.append(_gate("dry run (fake providers/subjects) passes on current code", "PASS" if d_ok else "FAIL", "prep/dry_run.json"))
    cal = CALIBRATION_DIR / "report.json"
    c_ok = cal.exists() and read_json(cal)["attempts"] >= 1
    out.append(_gate("fixed calibration completed", "PASS" if c_ok else "FAIL", "calibration/report.json"))
    lc = read_json(LAUNCH_CONFIG) if LAUNCH_CONFIG.exists() else {}
    g = lc.get("generator") or {}
    gen_ok = bool(g.get("returned_identity")) and bool(os.environ.get(GENERATOR_KEY_ENV))
    out.append(_gate(f"generator transport, access and returned identity ({cfg['provider_launch_fields']['requested_generator_family']})", "PASS" if gen_ok else "FAIL",
                     "launch_config.json generator", "no W1 generator credential in the environment and no authorized smoke; "
                     "identity unresolved" if not gen_ok else ""))
    j = lc.get("jev") or {}
    jev_ok = bool(j.get("returned_identity")) and bool(os.environ.get(JEV_KEY_ENV))
    out.append(_gate("Jev transport, access and returned identity", "PASS" if jev_ok else "FAIL", "launch_config.json jev",
                     "credential present but no authorized smoke; returned version unresolved" if not jev_ok else ""))
    out.append(_gate("all five arms usable", "PASS" if gen_ok and jev_ok else "FAIL", "B2-B4 need the generator; B4 needs Jev"))
    jp = PRICING_SNAPSHOT["jev"].get("status", "")
    pr = projection()
    price_ok = pr["provider"]["fits"] and pr["allocated_vcpu_h"]["expected_fits"] and not jp.startswith("UNCONFIRMED")
    out.append(_gate("pricing snapshot and cost/resource projection within caps", "PASS" if price_ok else "FAIL",
                     "cost_projection.json", "Jev price unconfirmed" if jp.startswith("UNCONFIRMED") else
                     ("projection exceeds caps" if not price_ok else "")))
    auth = lc.get("live_smoke_authorization_record")
    out.append(_gate("recorded live-smoke authorization", "PASS" if auth else "FAIL", "launch_config.json",
                     "researcher has not recorded authorization for the synthetic smoke requests" if not auth else ""))
    fz = verify_freeze()
    out.append(_gate("executable launch freeze valid", "PASS" if not fz else "FAIL", "FREEZE.sha256", "; ".join(fz)))
    return out


def ready(gs: list[dict[str, str]], ignore: tuple[str, ...] = ()) -> bool:
    return all(g["status"] == "PASS" for g in gs if g["gate"] not in ignore)


# --------------------------------------------------------------------------- freeze

FREEZE_GLOBS = ("w1.py", "w1_harness/*.py", "w1_harness/tests/*.py", "inputs/**/*", "private_oracles/**/*",
                "prep/subjects/**/*", "prep/inventory.json", "schedule.json", "launch_config.json", "launch_record.md",
                "cost_projection.json", "calibration/report.json", "calibration/events.jsonl", "calibration/traces/*",
                "v1_2/*", "v1_2/.gitattributes", "v1_1/DESIGN_FREEZE.sha256", "DESIGN_FREEZE.sha256")


def freeze_files() -> list[Path]:
    files = set()
    for g in FREEZE_GLOBS:
        for p in STUDY_DIR.glob(g):
            if p.is_file() and "__pycache__" not in p.parts and p.name != "FREEZE.sha256":
                files.add(p.resolve())
    return sorted(files)


def code_sha256() -> str:
    return sha256_json([(p.relative_to(STUDY_DIR).as_posix(), normalized_sha256(p))
                        for p in sorted((STUDY_DIR / "w1_harness").rglob("*.py")) if "__pycache__" not in p.parts]
                       + [("w1.py", normalized_sha256(STUDY_DIR / "w1.py"))])


def write_freeze() -> Path:
    gs = gates()
    if not ready(gs, ignore=("executable launch freeze valid",)):
        raise RuntimeError("not all readiness gates pass; the executable freeze is not created")
    if not LAUNCH_RECORD.exists():
        raise RuntimeError("launch_record.md must exist before the freeze")
    lines = [f"# W1 executable launch freeze; frozen_utc {utc_now()}"]
    for p in freeze_files():
        lines.append(f"{normalized_sha256(p)}  {p.relative_to(REPO_ROOT).as_posix()}")
    LAUNCH_FREEZE.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return LAUNCH_FREEZE


def verify_freeze() -> list[str]:
    if not LAUNCH_FREEZE.exists():
        return ["FREEZE.sha256 absent: no executable launch freeze exists"]
    problems = []
    listed = set()
    for line in LAUNCH_FREEZE.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        digest, rel = line.split("  ", 1)
        listed.add(rel)
        p = REPO_ROOT / rel
        if not p.exists():
            problems.append(f"{rel}: missing")
        elif normalized_sha256(p) != digest:
            problems.append(f"{rel}: digest mismatch")
    now = {p.relative_to(REPO_ROOT).as_posix() for p in freeze_files()}
    extra = sorted(now - listed)
    if extra:
        problems.append(f"unfrozen files in frozen locations: {extra[:5]}")
    return problems
