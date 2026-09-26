"""W2A command line. Run from the repository root:

    python research_runs/ai_witness_followup_2026_09/w2a/w2a.py <command> [options]

Read-only / offline (no provider request, no container):
  verify-design, verify-w1, reproduce-w1-audit, provenance, schedule, render, test, dry-run,
  regressions, budget-check, prepare (all of the above in order), preflight, package-freeze,
  verify-package, analyze
Provider (requires recorded researcher authorization; not run during preparation):
  smoke --authorization "<text>" [--deviation "<text>"]
Launch and measured run (after the smoke):
  confirm-pricing --source "<text>", launch-freeze, verify-launch,
  run --authorize "<researcher launch instruction>" [--resume-review "<note>"], seal
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

from . import CASES, STUDY_DIR
from .common import normalized_sha256, read_json, utc_now, write_json
from .config import (ANALYSIS_DIR, EVENTS, LAUNCH_CONFIG, LAUNCH_FREEZE, LAUNCH_RECORD, MEASURED_DIR, PACKAGE_FREEZE, PREP_DIR,
                     RAW_SEAL, RESOURCE_LEDGER, SCHEDULE, account, design_config)
from .ledger import ChainLedger

BASE = "python research_runs/ai_witness_followup_2026_09/w2a/w2a.py"


def _print(obj: Any) -> None:
    print(json.dumps(obj, indent=1, sort_keys=True, default=str))


def _stamp(report: dict[str, Any], command: str) -> dict[str, Any]:
    from .launch import code_sha256
    return {**report, "utc": utc_now(), "code_sha256": code_sha256(), "command": f"{BASE} {command}"}


def cmd_verify_design(a) -> int:
    from .launch import verify_design
    r = verify_design()
    print(("PASS" if r["ok"] else "FAIL") + ": W2A design manifest and invariants")
    _print(r)
    return 0 if r["ok"] else 1


def cmd_verify_w1(a) -> int:
    from .launch import verify_w1
    r = verify_w1()
    print(("PASS" if r["ok"] else "FAIL") + ": W1 read-only inputs match the W2A pins")
    _print(r)
    return 0 if r["ok"] else 1


def cmd_reproduce_w1_audit(a) -> int:
    from .launch import reproduce_w1_audit
    r = reproduce_w1_audit(PREP_DIR)
    print(("PASS" if r["byte_identical"] else "FAIL") + ": W1 offline audit reproduced into a temporary directory")
    _print({k: r[k] for k in ("byte_identical", "labels_checked", "complete_policies_checked", "returned_models", "denials")})
    return 0 if r["byte_identical"] else 1


def cmd_provenance(a) -> int:
    from .launch import provenance
    r = provenance()
    write_json(PREP_DIR / "provenance.json", r)
    _print({"undeclared_changes": r["undeclared_changes"], "identical": [x["module"] for x in r["copied_modules"] if x["byte_identical"]]})
    return 0 if not r["undeclared_changes"] else 1


def cmd_schedule(a) -> int:
    from . import schedule as sch
    body = sch.build(design_config()["schedule_seed"])
    if SCHEDULE.exists():
        probs = sch.verify(read_json(SCHEDULE))
        print("PASS: schedule.json regenerates from its seed" if not probs else "FAIL: " + "; ".join(probs))
        return 0 if not probs else 1
    write_json(SCHEDULE, body)
    print(f"wrote {SCHEDULE} ({body['schedule_sha256']})")
    return 0


def cmd_render(a) -> int:
    """Write the model-facing first-stage renderings for review and screen them for held-out markers."""
    from .budget import offline_session
    from .packet import leak_scan
    from . import prompts
    out_dir = PREP_DIR / "rendered"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = {}
    with tempfile.TemporaryDirectory() as tmp:
        for case in CASES:
            s = offline_session(case, "F2", Path(tmp))
            for stage, arm, calls in (("agent", "F2", 11), ("planner", "F3", 2)):
                text = "# SYSTEM\n" + prompts.render_system() + "\n\n# FIRST USER MESSAGE\n" + prompts.render_first(
                    stage, s.packet_ctx, s.state_text(f"{arm} {stage} stage", calls), [], 2 if stage == "planner" else None)
                path = out_dir / f"{case}.{arm}.{stage}.txt"
                path.write_text(text, encoding="utf-8", newline="\n")
                rows[path.name] = {"sha256": normalized_sha256(path), "chars": len(text), "leaks": leak_scan(text)}
    ok = not any(r["leaks"] for r in rows.values())
    report = _stamp({"artifact": "w2a_render_check_v1", "ok": ok, "files": rows, "prompts_sha256": prompts.prompts_sha256(),
                     "tools_sha256": prompts.tools_sha256(), "tool_leaks": leak_scan(json.dumps(prompts.TOOLS)),
                     "scope": "harness-authored text: system, task/notice texts, packet context, helper definitions, state block"}, "render")
    report["ok"] = ok and not report["tool_leaks"]
    write_json(PREP_DIR / "render_check.json", report)
    print(("PASS" if report["ok"] else "FAIL") + f": {len(rows)} renderings written to prep/rendered/")
    return 0 if report["ok"] else 1


def cmd_test(a) -> int:
    suite = unittest.defaultTestLoader.discover(str(STUDY_DIR / "w2a_harness" / "tests"), top_level_dir=str(STUDY_DIR))
    res = unittest.TextTestRunner(verbosity=1).run(suite)
    ok = res.wasSuccessful()
    write_json(PREP_DIR / "offline_tests.json", _stamp({"artifact": "w2a_offline_tests_v1", "ok": ok, "tests_run": res.testsRun,
                                                        "failures": len(res.failures), "errors": len(res.errors)}, "test"))
    return 0 if ok else 1


def dry_run(root: Path) -> dict[str, Any]:
    """All eight scheduled sessions with fake providers and subjects in ``root`` (never the study dirs)."""
    from . import analysis, fakes
    from . import schedule as sch
    from .backends import FakeBackend
    from .budget import generator_config
    from .providers import FakeGeneratorTransport, GeneratorClient
    from .resources import Caps, ResourceAccount
    from .runner import RunContext, run_blocks
    d = design_config()
    acct = ResourceAccount(root / "resources.jsonl", Caps.from_study_config(d))
    gt = FakeGeneratorTransport(fakes.ScenarioScript(), returned_model="fake-sonnet")
    ctx = RunContext(schedule=sch.build(d["schedule_seed"]), design=d, events=ChainLedger(root / "events.jsonl"), account=acct,
                     backend=FakeBackend(fakes.subject_outcome, elapsed_s=0.2), out_dir=root / "measured", launch_sha256="0" * 64,
                     generator=GeneratorClient(gt, generator_config(d, "fake-sonnet"), acct))
    summary = run_blocks(ctx)
    res = analysis.analyze(ctx.schedule, root / "events.jsonl", root / "analysis")
    rows = ctx.events.rows()
    seq = {r["event_type"]: [] for r in rows}
    for r in rows:
        seq[r["event_type"]].append(r)
    ordering = {}
    for block in ctx.schedule["blocks"]:
        c = block["case"]
        seals = [r["sequence"] for r in rows if r["event_type"] == "session_ended" and f".{c}." in r["entity_id"]]
        vals = [r["sequence"] for r in rows if r["event_type"] == "validation_started" and f".{c}." in r["entity_id"]]
        ordering[c] = bool(seals and vals and max(seals) < min(vals)) and \
            [r["entity_id"] for r in rows if r["event_type"] == "validation_started" and f".{c}." in r["entity_id"]] == block["validation_order"]
    # budget accounting: ledger settlements per session equal the session records
    st = acct.state()
    led_req = sum(v["generator_requests"] for v in st["charged"].values())
    sess = [r["payload"] for r in rows if r["event_type"] == "session_ended"]
    rec_req = sum(p["details"]["generator_calls"] for p in sess)
    rec_in = sum(p["details"]["input_tokens"] for p in sess)
    led_in = sum(v["input_tokens"] for v in st["charged"].values())
    caps_ok = all(p["details"]["generator_calls"] <= d["search"]["max_generator_calls"] and p["details"]["input_tokens"] <= d["search"]["max_input_tokens"]
                  and p["details"]["output_tokens"] <= d["search"]["max_output_tokens"] and p["details"]["usd"] <= d["search"]["max_usd"] for p in sess)
    from .packet import leak_scan
    harness_leaks = sorted({m for b in gt.sent for msg in b["messages"] if msg["role"] == "user" for c in msg["content"]
                            if c.get("type") == "text" for m in leak_scan(c["text"])})
    terminals = {p["id"]: p["terminal"] for p in sess}
    ok = (summary["stopped"] is None and len(sess) == 8 and len(seq.get("validation_outcome", [])) == 8 and all(ordering.values())
          and led_req == rec_req == len(gt.sent) and abs(led_in - rec_in) < 1e-6 and caps_ok and not harness_leaks
          and not st["open"] and ChainLedger(root / "events.jsonl").verify() == len(rows) and all(terminals.values()))
    return {"ok": ok, "sessions_ended": len(sess), "validations": len(seq.get("validation_outcome", [])), "stopped": summary["stopped"],
            "seal_before_validation_and_scheduled_order": ordering, "terminals": terminals,
            "accounting": {"ledger_generator_requests": led_req, "session_generator_calls": rec_req, "wire_requests": len(gt.sent),
                           "ledger_input_tokens": led_in, "session_input_tokens": rec_in, "open_reservations": len(st["open"]),
                           "per_session_caps_respected": caps_ok},
            "harness_text_leaks": harness_leaks, "labels": {k: sum(1 for r in res["rows"] if r["validation_outcome"] == k)
                                                            for k in ("VALIDATED_WITNESS", "NO_WITNESS_WITHIN_BUDGET", "NO_SUBMISSION",
                                                                      "INVALID_CANDIDATE", "COUNTERPART_FAILURE", "UNRESOLVED")},
            "attrition": res["attrition"], "gate_live_feasibility": res["gate_live_feasibility"],
            "note": "fake providers and subjects: no credentials, network or containers; outcomes are synthetic"}


def cmd_dry_run(a) -> int:
    root = Path(tempfile.mkdtemp(prefix="w2a-dryrun-"))
    r = dry_run(root)
    write_json(PREP_DIR / "dry_run.json", _stamp({"artifact": "w2a_dry_run_v1", "scratch_dir": str(root), **r}, "dry-run"))
    _print({k: r[k] for k in ("ok", "sessions_ended", "validations", "terminals", "accounting")})
    return 0 if r["ok"] else 1


def cmd_regressions(a) -> int:
    from .regressions import run_all
    r = run_all()
    write_json(PREP_DIR / "w1_regressions.json", _stamp(r, "regressions"))
    for c in r["checks"]:
        print(f"[{'PASS' if c['pass'] else 'FAIL'}] {c['id']}: {c['expectation']}")
    return 0 if r["ok"] else 1


def cmd_budget_check(a) -> int:
    from .budget import check
    r = check()
    f = r["findings"]
    ok = (f["admission_estimate_conservative"] and f["backend_build_timeout_matches_reservation"] and f["configured_input_cap_equals_derived_rule"]
          and f["final_call_admissible_in_every_configured_projection"] and f["vcpu_timeout_bound_fits"]
          and f["growth_bound_covers_w1_response_bytes"] and f["w1_build_and_attempt_durations_within_bounds"])
    write_json(PREP_DIR / "budget_check.json", _stamp({**r, "ok": ok}, "budget-check"))
    _print(f)
    return 0 if ok else 1


def cmd_prepare(a) -> int:
    rc = 0
    for fn in (cmd_verify_design, cmd_verify_w1, cmd_reproduce_w1_audit, cmd_provenance, cmd_schedule, cmd_render, cmd_test,
               cmd_regressions, cmd_dry_run, cmd_budget_check):
        print(f"== {fn.__name__[4:].replace('_', '-')}")
        rc = rc or fn(a)
    return rc


def cmd_preflight(a) -> int:
    from .launch import launch_gates, offline_gates, provider_gates, ready
    off, prov = offline_gates(), provider_gates()
    gs = off + prov + launch_gates()
    write_json(PREP_DIR / "gates.json", {"utc": utc_now(), "gates": gs})
    for g in gs:
        print(f"[{g['status']:4}] ({g['group']}) {g['gate']}" + (f" -- {g['detail']}" if g["detail"] and g["status"] != "PASS" else ""))
    if ready(gs):
        verdict = "READY_FOR_MEASURED_LAUNCH"
    elif ready(off):
        verdict = "OFFLINE_READY; provider/launch gates open (NOT_READY for measured launch)"
    else:
        verdict = "NOT_READY"
    print(verdict)
    return 0 if ready(gs) else 2


def cmd_package_freeze(a) -> int:
    from .launch import write_package_freeze
    try:
        p = write_package_freeze()
    except RuntimeError as exc:
        print(f"REFUSED: {exc}")
        return 2
    print(f"wrote {p}")
    return 0


def cmd_verify_package(a) -> int:
    from .launch import verify_package_freeze
    p = verify_package_freeze()
    print("PASS: executable package freeze verifies" if not p else "FAIL: " + "; ".join(p))
    return 0 if not p else 1


def cmd_smoke(a) -> int:
    """One synthetic, non-case request with the W2A request shape; only with recorded authorization."""
    from .common import canonical_bytes, sha256_bytes
    from .launch import GENERATOR_KEY_ENV, load_launch_config, smoke_body, verify_package_freeze
    from .providers import AnthropicTransport
    if not a.authorization:
        print("REFUSED: --authorization with the researcher's recorded text is required")
        return 2
    if verify_package_freeze():
        print("REFUSED: the executable package freeze does not verify")
        return 2
    key = os.environ.get(GENERATOR_KEY_ENV)
    if not key:
        print(f"REFUSED: {GENERATOR_KEY_ENV} is not set")
        return 2
    led = ChainLedger(EVENTS)
    prior = led.find(event_type="provider_smoke", entity_id="generator")
    if prior:
        failed = all(not r["payload"].get("returned_model") for r in prior)
        used = [r for r in led.find(event_type="smoke_deviation") if r["payload"].get("authorization") == a.deviation]
        if not (a.deviation and failed and not used and len(prior) < 2):
            print("REFUSED: a smoke request already exists (one more only after a failure, with --deviation authorization)")
            return 2
        led.append("smoke", "smoke_deviation", "generator", {"authorization": a.deviation, "prior": [r["payload"]["request_sha256"] for r in prior]})
    lc = load_launch_config()
    d = design_config()
    body = smoke_body(d["generator"]["requested_model"])
    data = canonical_bytes(body)
    p = d["pricing_snapshot"]
    acct = account()
    rid = acct.reserve("smoke", "smoke.generator", {"usd": (2000 * p["cache_write_per_mtok_usd"] + 1024 * p["output_per_mtok_usd"]) / 1e6,
                                                     "input_tokens": 2000, "output_tokens": 1024, "generator_requests": 1})
    wr = AnthropicTransport(key, d["generator"]["auth"]).post(d["generator"]["endpoint"], data, 120)
    resp = json.loads(wr.body) if wr.status == 200 else None
    u = (resp or {}).get("usage") or {}
    inp = int(u.get("input_tokens", 2000)) + int(u.get("cache_creation_input_tokens") or 0) + int(u.get("cache_read_input_tokens") or 0)
    out = int(u.get("output_tokens", 1024))
    usd = (inp * p["cache_write_per_mtok_usd"] + out * p["output_per_mtok_usd"]) / 1e6
    acct.settle(rid, {"usd": usd, "input_tokens": inp, "output_tokens": out, "generator_requests": 1}, {"http_status": wr.status})
    returned = (resp or {}).get("model")
    tool_use = any(c.get("type") == "tool_use" and c.get("name") == "report_ready" for c in (resp or {}).get("content") or [])
    safe = {k: v for k, v in wr.headers.items() if k.lower() in ("content-type", "server", "request-id", "x-request-id", "retry-after")}
    led.append("smoke", "provider_smoke", "generator", {"request_sha256": sha256_bytes(data), "http_status": wr.status, "returned_model": returned,
                                                         "tool_use_returned": tool_use, "stop_reason": (resp or {}).get("stop_reason"),
                                                         "usage": u, "authorization": a.authorization, "error": wr.error,
                                                         "response_headers": safe, "response_body_head": wr.body[:2000].decode("utf-8", "replace")})
    lc["generator"]["returned_identity"] = returned
    lc["generator"]["returned_identity_status"] = f"observed by the authorized W2A smoke {utc_now()}" if returned else "smoke failed"
    lc["generator"]["credential_present"] = True
    lc["smoke"] = {"http_status": wr.status, "returned_model": returned, "tool_use_returned": tool_use, "usage": u, "utc": utc_now()}
    lc["smoke_authorization_record"] = a.authorization
    write_json(LAUNCH_CONFIG, lc)
    _print(lc["smoke"])
    return 0 if returned and tool_use else 1


def cmd_confirm_pricing(a) -> int:
    from .launch import load_launch_config
    if not a.source:
        print("REFUSED: --source describing the current price list and date is required")
        return 2
    lc = load_launch_config()
    lc["pricing_confirmed"] = {"source": a.source, "utc": utc_now(), "snapshot": design_config()["pricing_snapshot"]}
    write_json(LAUNCH_CONFIG, lc)
    print("recorded pricing confirmation in launch_config.json")
    return 0


def cmd_launch_freeze(a) -> int:
    from .launch import load_launch_config, offline_gates, provider_gates, write_launch_freeze
    lc = load_launch_config()
    gs = offline_gates() + provider_gates()
    rows = "\n".join(f"| {g['group']} | {g['gate']} | {g['status']} | {g['evidence']} |" for g in gs)
    LAUNCH_RECORD.write_text(
        "# W2A launch record\n\n"
        f"- Written: {utc_now()}\n- Package freeze: `PACKAGE_FREEZE.sha256` {normalized_sha256(PACKAGE_FREEZE) if PACKAGE_FREEZE.exists() else 'ABSENT'}\n"
        f"- Generator: requested `{lc['generator']['requested_model']}`, returned `{lc['generator']['returned_identity']}` via {lc['generator']['endpoint']}\n"
        f"- Smoke authorization: {lc.get('smoke_authorization_record')}\n- Pricing confirmation: {json.dumps(lc.get('pricing_confirmed'))}\n\n"
        "| Group | Gate | Status | Evidence |\n|---|---|---|---|\n" + rows + "\n", encoding="utf-8", newline="\n")
    try:
        p = write_launch_freeze()
    except RuntimeError as exc:
        print(f"REFUSED: {exc}")
        return 2
    print(f"wrote {p}")
    return 0


def cmd_verify_launch(a) -> int:
    from .launch import verify_launch_freeze
    p = verify_launch_freeze()
    print("PASS: launch freeze verifies" if not p else "FAIL: " + "; ".join(p))
    return 0 if not p else 1


def cmd_run(a) -> int:
    from .backends import DockerBackend
    from .budget import generator_config
    from .launch import GENERATOR_KEY_ENV, launch_gates, load_launch_config, offline_gates, provider_gates, ready
    from .providers import AnthropicTransport, GeneratorClient
    from .runner import RunContext, run_blocks
    from .packet import pinned_inputs
    if not a.authorize:
        print("REFUSED: explicit measured-run authorization (--authorize) is required")
        return 2
    gs = offline_gates() + provider_gates() + launch_gates()
    if not ready(gs):
        for g in gs:
            if g["status"] != "PASS":
                print(f"[{g['status']}] {g['gate']} {g['detail']}")
        print("REFUSED: NOT_READY")
        return 2
    d = design_config()
    lc = load_launch_config()
    lc["measured_run_authorization"] = {"text": a.authorize, "utc": utc_now()}
    acct = account()
    gen = GeneratorClient(AnthropicTransport(os.environ[GENERATOR_KEY_ENV], d["generator"]["auth"]), generator_config(d), acct)
    events = ChainLedger(EVENTS)
    events.append("search", "measured_run_invoked", "w2a", {"authorize": a.authorize, "utc": utc_now(),
                                                             "launch_freeze_sha256": normalized_sha256(LAUNCH_FREEZE)})
    ctx = RunContext(schedule=read_json(SCHEDULE), design=d, events=events, account=acct, backend=DockerBackend(pinned_inputs()["images"]),
                     out_dir=MEASURED_DIR, launch_sha256=normalized_sha256(LAUNCH_FREEZE), generator=gen)
    summary = run_blocks(ctx, resume_note=a.resume_review)
    _print(summary)
    return 0 if summary["stopped"] is None else 3


def cmd_seal(a) -> int:
    if RAW_SEAL.exists():
        print("REFUSED: raw_seal.sha256 already exists")
        return 2
    files = sorted([p for p in MEASURED_DIR.rglob("*") if p.is_file()] + [EVENTS, RESOURCE_LEDGER])
    lines = [f"# W2A raw collection seal; utc {utc_now()}"] + [f"{normalized_sha256(p)}  {p.relative_to(STUDY_DIR).as_posix()}" for p in files]
    RAW_SEAL.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {RAW_SEAL} ({len(files)} files)")
    return 0


def cmd_analyze(a) -> int:
    from . import analysis
    events = Path(a.events) if a.events else EVENTS
    out = Path(a.out) if a.out else ANALYSIS_DIR
    analysis.analyze(read_json(SCHEDULE), events, out)
    print((out / "report.md").read_text(encoding="utf-8"))
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="w2a.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("verify-design", cmd_verify_design), ("verify-w1", cmd_verify_w1), ("reproduce-w1-audit", cmd_reproduce_w1_audit),
                     ("provenance", cmd_provenance), ("schedule", cmd_schedule), ("render", cmd_render), ("test", cmd_test),
                     ("dry-run", cmd_dry_run), ("regressions", cmd_regressions), ("budget-check", cmd_budget_check),
                     ("prepare", cmd_prepare), ("preflight", cmd_preflight), ("package-freeze", cmd_package_freeze),
                     ("verify-package", cmd_verify_package), ("launch-freeze", cmd_launch_freeze),
                     ("verify-launch", cmd_verify_launch), ("seal", cmd_seal)):
        sub.add_parser(name).set_defaults(fn=fn)
    s = sub.add_parser("smoke")
    s.add_argument("--authorization", default=None)
    s.add_argument("--deviation", default=None)
    s.set_defaults(fn=cmd_smoke)
    c = sub.add_parser("confirm-pricing")
    c.add_argument("--source", default=None)
    c.set_defaults(fn=cmd_confirm_pricing)
    r = sub.add_parser("run")
    r.add_argument("--authorize", default=None)
    r.add_argument("--resume-review", default=None)
    r.set_defaults(fn=cmd_run)
    an = sub.add_parser("analyze")
    an.add_argument("--events", default=None)
    an.add_argument("--out", default=None)
    an.set_defaults(fn=cmd_analyze)
    args = ap.parse_args(argv)
    return args.fn(args)
