"""W1 command line. Run from the repository root:

    python research_runs/ai_witness_2026_09/w1.py <command> [options]

Non-executing: verify-design, preflight, projection, launch-config, verify-launch, gates.
Offline: test, dry-run (fake providers and subjects; no containers, no network).
Preparation (charged): inventory, calibrate (once; fixed 16 attempts).
Provider smoke: smoke --provider {generator,jev} --authorization "<recorded researcher text>" (one synthetic
non-case request per provider, refused without authorization or when one already exists).
Measured: run --authorize "<researcher launch instruction>" (refused unless every gate passes).
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
from .common import read_json, utc_now, write_json
from .config import (EVENTS, LAUNCH_CONFIG, MEASURED_DIR, PREP_DIR, READINESS, SCHEDULE, account, design_config)
from .ledger import ChainLedger


def _print(obj: Any) -> None:
    print(json.dumps(obj, indent=1, sort_keys=True, default=str))


def cmd_verify_design(a) -> int:
    from .launch import verify_design
    r = verify_design()
    print(("PASS" if r["ok"] else "FAIL") + ": v1.2 design manifest, chained v1.1 and v1 integrity (verifier) and independent SHA-256 of 17 files")
    _print(r)
    return 0 if r["ok"] else 1


def cmd_inventory(a) -> int:
    from .inventory import write
    p = write()
    account().note("preparation", "inventory", {"path": "prep/inventory.json", "utc": utc_now()})
    print(f"wrote {p}")
    return 0


def cmd_test(a) -> int:
    from .launch import code_sha256
    suite = unittest.defaultTestLoader.discover(str(STUDY_DIR / "w1_harness" / "tests"), top_level_dir=str(STUDY_DIR))
    res = unittest.TextTestRunner(verbosity=1).run(suite)
    ok = res.wasSuccessful()
    write_json(PREP_DIR / "offline_tests.json", {"ok": ok, "tests_run": res.testsRun, "failures": len(res.failures),
                                                "errors": len(res.errors), "utc": utc_now(), "code_sha256": code_sha256(),
                                                "command": "python research_runs/ai_witness_2026_09/w1.py test"})
    return 0 if ok else 1


def cmd_dry_run(a) -> int:
    """Full 4 x 5 x 3 schedule with fake subjects and fake providers in a scratch directory."""
    from . import analysis, fakes
    from .backends import FakeBackend
    from .launch import code_sha256
    from .packet import leak_scan, load_packet
    from . import prompts, templates
    from .providers import FakeGeneratorTransport, FakeJevTransport, GeneratorClient, GeneratorConfig, JevClient, JevConfig
    from .resources import Caps, ResourceAccount
    from .runner import RunContext, run_blocks
    root = Path(tempfile.mkdtemp(prefix="w1-dryrun-"))
    acct = ResourceAccount(root / "resources.jsonl", Caps.from_study_config(design_config()))
    gt = FakeGeneratorTransport(fakes.generator_script, returned_model="fake-opus")
    jt = FakeJevTransport(fakes.jev_choice)
    ctx = RunContext(schedule=read_json(SCHEDULE), design=design_config(), events=ChainLedger(root / "events.jsonl"),
                     account=acct, backend=FakeBackend(fakes.subject_outcome, elapsed_s=0.2), out_dir=root / "measured",
                     launch_sha256="0" * 64,
                     generator=GeneratorClient(gt, GeneratorConfig("claude-sonnet-5", "fake-opus", "medium", 4000, 240, 2.0, 10.0, "dry-run",
                                                                   endpoint="https://opencode.ai/zen/v1/messages", count_tokens_url=None,
                                                                   price_cache_write_per_mtok=2.5, price_cache_read_per_mtok=0.2,
                                                                   prompt_caching=True), acct),
                     jev=JevClient(jt, JevConfig("jev-latest", "jev-fake-1.0", 30, 0.042, 0.0, "dry-run"), acct))
    summary = run_blocks(ctx)
    res = analysis.analyze(ctx.schedule, root / "events.jsonl", root / "analysis")
    rows = ctx.events.rows()
    leaks = {c: leak_scan(prompts.packet_context(load_packet(c), templates.bindings(c))) for c in CASES}
    sent_leaks = sorted({m for b in gt.sent for m in leak_scan(json.dumps(b))})
    ended = [r for r in rows if r["event_type"] == "session_ended"]
    outcomes = [r for r in rows if r["event_type"] == "validation_outcome"]
    ok = (summary["stopped"] is None and len(ended) == 60 and len(outcomes) == 60 and not any(leaks.values())
          and not sent_leaks and ChainLedger(root / "events.jsonl").verify() == len(rows))
    report = {"ok": ok, "utc": utc_now(), "scratch_dir": str(root), "code_sha256": code_sha256(),
              "sessions_ended": len(ended), "validations": len(outcomes), "stopped": summary["stopped"],
              "fake_generator_requests": len(gt.sent), "fake_jev_requests": len(jt.sent),
              "packet_leak_scan": leaks, "request_leak_scan": sent_leaks,
              "labels": {k: sum(1 for o in outcomes if o["payload"]["outcome"] == k) for k in
                         ("VALIDATED_WITNESS", "NO_WITNESS_WITHIN_BUDGET", "NO_SUBMISSION", "INVALID_CANDIDATE",
                          "COUNTERPART_FAILURE", "UNRESOLVED")},
              "note": "fake subjects and providers only: no containers, credentials or network; outcomes are synthetic",
              "command": "python research_runs/ai_witness_2026_09/w1.py dry-run"}
    write_json(PREP_DIR / "dry_run.json", report)
    _print(report)
    return 0 if ok else 1


def cmd_calibrate(a) -> int:
    from . import calibration
    r = calibration.run()
    _print(r)
    return 0


def cmd_launch_config(a) -> int:
    from .launch import launch_config
    existing = read_json(LAUNCH_CONFIG) if LAUNCH_CONFIG.exists() else {}
    cfg = launch_config()
    for k in ("live_smoke_authorization_record", "measured_run_authorization"):
        if existing.get(k):
            cfg[k] = existing[k]
    for prov in ("generator", "jev"):
        if (existing.get(prov) or {}).get("returned_identity"):
            cfg[prov]["returned_identity"] = existing[prov]["returned_identity"]
            cfg[prov]["returned_identity_status"] = existing[prov].get("returned_identity_status")
    write_json(LAUNCH_CONFIG, cfg)
    print(f"wrote {LAUNCH_CONFIG}")
    return 0


def cmd_projection(a) -> int:
    from .launch import projection
    p = projection()
    write_json(STUDY_DIR / "cost_projection.json", p)
    _print(p)
    return 0


def cmd_preflight(a) -> int:
    """Non-executing: no container is started and no provider request is sent."""
    from .launch import gates, ready
    gs = gates()
    write_json(PREP_DIR / "gates.json", {"utc": utc_now(), "gates": gs})
    for g in gs:
        print(f"[{g['status']:4}] {g['gate']}" + (f" -- {g['detail']}" if g["detail"] and g["status"] != "PASS" else ""))
    ok = ready(gs)
    print("READY_FOR_MEASURED_LAUNCH" if ok else "NOT_READY")
    return 0 if ok else 2


def cmd_verify_launch(a) -> int:
    from .launch import verify_freeze
    p = verify_freeze()
    print("PASS: executable launch freeze verifies" if not p else "FAIL: " + "; ".join(p))
    return 0 if not p else 1


def cmd_freeze(a) -> int:
    from .launch import write_freeze
    try:
        p = write_freeze()
    except RuntimeError as exc:
        print(f"REFUSED: {exc}")
        return 2
    print(f"wrote {p}")
    return 0


def cmd_smoke(a) -> int:
    """One synthetic, non-case request per provider, only with recorded researcher authorization."""
    from .launch import GENERATOR_KEY_ENV, JEV_KEY_ENV
    from .providers import AnthropicTransport, JevTransport, JEV_URL
    from .common import canonical_bytes, sha256_bytes
    if not a.authorization:
        print("REFUSED: --authorization with the researcher's recorded text is required")
        return 2
    cfg = read_json(LAUNCH_CONFIG)
    led = ChainLedger(EVENTS)
    prior = led.find(event_type="provider_smoke", entity_id=a.provider)
    if prior:
        # Design limit: one synthetic smoke per provider. Exactly one further request is possible only as a
        # researcher-authorized, recorded deviation after every earlier smoke failed to return an identity.
        failed = all(not r["payload"].get("returned_model") for r in prior)
        # each distinct recorded researcher authorization permits exactly one retry, and only after failures
        used = [r for r in led.find(event_type="smoke_deviation", entity_id=a.provider)
                if r["payload"].get("authorization") == a.deviation]
        if not (a.deviation and failed and not used):
            print(f"REFUSED: a {a.provider} smoke request already exists; at most one per provider"
                  + ("" if a.deviation else " (a single retry after a failure needs --deviation with recorded authorization)"))
            return 2
        led.append("smoke", "smoke_deviation", a.provider, {
            "authorization": a.deviation, "prior_requests": [r["payload"]["request_sha256"] for r in prior],
            "prior_http_status": [r["payload"]["http_status"] for r in prior],
            "note": "one additional synthetic smoke beyond study_config calibration.max_synthetic_smoke_requests_per_provider=1; "
                    "preparation-only deviation, no measured data exists"})
    acct = account()
    if a.provider == "generator":
        key = os.environ.get(GENERATOR_KEY_ENV)
        if not key:
            print(f"REFUSED: {GENERATOR_KEY_ENV} is not set (no existing access)")
            return 2
        body = {"model": cfg["generator"]["requested_model"], "max_tokens": 1024, "thinking": {"type": "adaptive"},
                "output_config": {"effort": "low"}, "messages": [{"role": "user", "content": "Reply with the single word: ready"}]}
        data = canonical_bytes(body)
        gp = cfg["pricing_snapshot"]["generator"]
        rid = acct.reserve("smoke", "smoke.generator", {"usd": (600 * gp["input_per_mtok_usd"] + 1024 * gp["output_per_mtok_usd"]) / 1e6,
                                                          "input_tokens": 600, "output_tokens": 1024, "generator_requests": 1})
        wr = AnthropicTransport(key, cfg["generator"]["auth"]).post(cfg["generator"]["endpoint"], data, 120)
        resp = json.loads(wr.body) if wr.status == 200 else None
        u = (resp or {}).get("usage") or {}
        inp, out = int(u.get("input_tokens", 600)), int(u.get("output_tokens", 1024))
        acct.settle(rid, {"usd": (inp * gp["input_per_mtok_usd"] + out * gp["output_per_mtok_usd"]) / 1e6, "input_tokens": inp,
                          "output_tokens": out, "generator_requests": 1})
        returned = (resp or {}).get("model")
    else:
        key = os.environ.get(JEV_KEY_ENV)
        if not key:
            print(f"REFUSED: {JEV_KEY_ENV} is not set")
            return 2
        body = {"state": "The sky is blue.", "model": cfg["jev"]["requested_model"],
                "questions": {"judgment": {"type": "choice", "instructions": "What colour is the sky in the state?",
                                           "criteria": {"blue": None, "green": None}}}}
        data = canonical_bytes(body)
        rid = acct.reserve("smoke", "smoke.jev", {"usd": 0.001, "input_tokens": 600, "output_tokens": 100, "jev_evaluations": 1})
        wr = JevTransport(key).post(JEV_URL, data, 60)
        resp = json.loads(wr.body) if wr.status == 200 else None
        u = (resp or {}).get("usage") or {}
        inp, out = int(u.get("input_tokens", 600)), int(u.get("output_tokens", 100))
        acct.settle(rid, {"usd": inp * 0.042 / 1e6, "input_tokens": inp, "output_tokens": out, "jev_evaluations": 1})
        returned = (resp or {}).get("model")
    safe_headers = {k: v for k, v in wr.headers.items() if k.lower() in (
        "content-type", "server", "cf-ray", "request-id", "x-request-id", "x-typesafe-request-id", "retry-after")}
    led.append("smoke", "provider_smoke", a.provider, {"request_sha256": sha256_bytes(data), "http_status": wr.status,
                                                        "returned_model": returned, "usage": u, "authorization": a.authorization,
                                                        "error": wr.error, "response_headers": safe_headers,
                                                        "response_body_head": wr.body[:2000].decode("utf-8", "replace")})
    if returned:
        cfg[a.provider]["returned_identity"] = returned
        cfg[a.provider]["returned_identity_status"] = f"observed by authorized synthetic smoke {utc_now()}"
    cfg["live_smoke_authorization_record"] = a.authorization
    write_json(LAUNCH_CONFIG, cfg)
    _print({"provider": a.provider, "http_status": wr.status, "returned_model": returned, "usage": u})
    return 0 if returned else 1


def cmd_run(a) -> int:
    """Measured run: refuses unless every gate passes and the researcher's launch instruction is supplied."""
    from .launch import GENERATOR_KEY_ENV, JEV_KEY_ENV, gates, ready, verify_freeze
    from .backends import DockerBackend
    from .providers import AnthropicTransport, GeneratorClient, GeneratorConfig, JevClient, JevConfig, JevTransport
    from .qualify import image_ids
    from .runner import RunContext, run_blocks
    from .common import normalized_sha256
    if not a.authorize:
        print("REFUSED: explicit live-run authorization (--authorize) is required")
        return 2
    gs = gates()
    if not ready(gs):
        for g in gs:
            if g["status"] != "PASS":
                print(f"[{g['status']}] {g['gate']} {g['detail']}")
        print("REFUSED: NOT_READY")
        return 2
    fz = verify_freeze()
    if fz:
        print("REFUSED: launch freeze invalid: " + "; ".join(fz))
        return 2
    lc = read_json(LAUNCH_CONFIG)
    g, j, p = lc["generator"], lc["jev"], lc["pricing_snapshot"]
    acct = account()
    gen = GeneratorClient(AnthropicTransport(os.environ[GENERATOR_KEY_ENV], g["auth"]),
                          GeneratorConfig(g["requested_model"], g["returned_identity"], g["settings"]["output_config"]["effort"],
                                          g["settings"]["max_tokens_per_request"], g["settings"]["request_timeout_s"],
                                          p["generator"]["input_per_mtok_usd"], p["generator"]["output_per_mtok_usd"],
                                          p["generator"]["source"], endpoint=g["endpoint"],
                                          count_tokens_url=g.get("count_tokens_url"),
                                          price_cache_write_per_mtok=p["generator"]["cache_write_per_mtok_usd"],
                                          price_cache_read_per_mtok=p["generator"]["cache_read_per_mtok_usd"],
                                          prompt_caching=True), acct)
    jev = JevClient(JevTransport(os.environ[JEV_KEY_ENV]),
                    JevConfig(j["requested_model"], j["returned_identity"], 60, p["jev"]["input_per_mtok_usd"],
                              p["jev"]["output_per_mtok_usd"], p["jev"]["source"]), acct)
    events = ChainLedger(EVENTS)
    events.append("search", "measured_run_invoked", "w1", {"authorize": a.authorize, "utc": utc_now()})
    ctx = RunContext(schedule=read_json(SCHEDULE), design=design_config(), events=events, account=acct,
                     backend=DockerBackend(image_ids()), out_dir=MEASURED_DIR,
                     launch_sha256=normalized_sha256(STUDY_DIR / "FREEZE.sha256"), generator=gen, jev=jev)
    summary = run_blocks(ctx, resume_note=a.resume_review)
    _print(summary)
    return 0 if summary["stopped"] is None else 3


def cmd_analyze(a) -> int:
    from . import analysis
    events = Path(a.events) if a.events else EVENTS
    out = Path(a.out) if a.out else STUDY_DIR / "analysis"
    r = analysis.analyze(read_json(SCHEDULE), events, out)
    print((out / "report.md").read_text(encoding="utf-8"))
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="w1.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("verify-design", cmd_verify_design), ("inventory", cmd_inventory), ("test", cmd_test),
                     ("dry-run", cmd_dry_run), ("calibrate", cmd_calibrate), ("launch-config", cmd_launch_config),
                     ("projection", cmd_projection), ("preflight", cmd_preflight), ("verify-launch", cmd_verify_launch),
                     ("freeze", cmd_freeze)):
        sub.add_parser(name).set_defaults(fn=fn)
    s = sub.add_parser("smoke")
    s.add_argument("--provider", choices=["generator", "jev"], required=True)
    s.add_argument("--authorization", default=None)
    s.add_argument("--deviation", default=None, help="researcher authorization text for the single retry after a failed smoke")
    s.set_defaults(fn=cmd_smoke)
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
