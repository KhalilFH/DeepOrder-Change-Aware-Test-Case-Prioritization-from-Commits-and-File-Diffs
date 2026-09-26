"""Limit check: W2A caps against actual serialized requests and backend resource accounting.

Offline and deterministic. Inputs: the actual rendered W2A stage requests for each case (built by
the real Session code with a transport that refuses to send), W1's recorded requests/responses and
ledger (read-only) for calibration, and the frozen design configuration. Outputs a JSON report.

The trajectory projection is a planning model, not a prediction: it replays fixed per-call growth
scenarios through the same admission rules the session uses.
"""

from __future__ import annotations

import json
import math
import statistics
import tempfile
from pathlib import Path
from typing import Any

from . import CASES, W1_STUDY_DIR
from .backends import BUILD_CLEANUP_S, BUILD_TIMEOUT_S, FakeBackend
from .casespec import spec
from .common import canonical_bytes, utc_now
from .config import design_config
from .ledger import ChainLedger
from .packet import load_packet, originals
from .providers import (FakeGeneratorTransport, GeneratorClient, GeneratorConfig, SessionBudget, estimate_input_tokens)
from .resources import Caps, ResourceAccount
from .session import SEARCH_BUILD_TIMEOUT_S, Conversation, Session, SessionEnv, SessionRecorder
from . import prompts


def _refuse(body: dict[str, Any]) -> dict[str, Any]:
    raise RuntimeError("budget check must not send requests")


def generator_config(d: dict[str, Any], expected: str | None = None) -> GeneratorConfig:
    p, g = d["pricing_snapshot"], d["generator"]
    return GeneratorConfig(g["requested_model"], expected or g["expected_returned_model"], g["effort"],
                           g["max_output_tokens_per_request"], g["request_timeout_s"], p["input_per_mtok_usd"],
                           p["output_per_mtok_usd"], p["cache_write_per_mtok_usd"], p["cache_read_per_mtok_usd"],
                           "W2A pricing snapshot", g["endpoint"])


def offline_session(case: str, arm: str, root: Path) -> Session:
    d = design_config()
    acct = ResourceAccount(root / f"{case}.{arm}.res.jsonl", Caps.from_study_config(d))
    gen = GeneratorClient(FakeGeneratorTransport(_refuse), generator_config(d), acct)
    pkt = load_packet(case)
    s = d["search"]
    env = SessionEnv(session_id=f"w2a.{case}.{arm}", case=case, arm=arm, spec=spec(case), packet=pkt, originals=originals(pkt),
                     backend=FakeBackend(), account=acct,
                     recorder=SessionRecorder(root / case / arm, ChainLedger(root / f"{case}.{arm}.events.jsonl"), f"w2a.{case}.{arm}"),
                     search_first=["V_bad"] * 6, launch_sha256="0" * 64,
                     budget=SessionBudget(s["max_input_tokens"], s["max_output_tokens"], s["max_usd"], s["max_generator_calls"]),
                     search=s, generator=gen)
    return Session(env)


def rendered_first_requests() -> dict[str, Any]:
    out: dict[str, Any] = {}
    with tempfile.TemporaryDirectory() as tmp:
        for case in CASES:
            s = offline_session(case, "F2", Path(tmp))
            rows = {}
            for stage, arm in (("agent", "F2"), ("planner", "F3")):
                first = prompts.render_first(stage, s.packet_ctx, s.state_text(f"{arm} {stage} stage", 11 if stage == "agent" else 2),
                                             [], 2 if stage == "planner" else None)
                body = s.body(Conversation(stage, first))
                n = len(canonical_bytes(body))
                rows[stage] = {"request_bytes": n, "admission_estimate_tokens": estimate_input_tokens(body)}
            out[case] = {"first_requests": rows, "stage_upper_bounds_tokens": s.ub,
                         "packet_context_chars": len(s.packet_ctx), "helper_lines": s.e.packet["helpers"]["total_lines"]}
    return out


# --------------------------------------------------------------------------- W1 calibration (read-only)

def w1_calibration() -> dict[str, Any]:
    measured = W1_STUDY_DIR / "measured"
    ratios, growth, outs, content_bytes, sig, per_token = [], [], [], [], [], []
    for sdir in sorted(measured.glob("w1.*")):
        reqs = sorted((sdir / "requests").glob("*.req*.request.json"))
        prev = None
        for rq in reqs:
            rs = rq.with_name(rq.name.replace(".request.", ".response."))
            if not rs.exists():
                continue
            raw = rq.read_bytes()
            body = json.loads(raw)
            resp = json.loads(rs.read_text(encoding="utf-8"))
            u = resp.get("usage") or {}
            actual = u.get("input_tokens", 0) + (u.get("cache_creation_input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0)
            est = math.ceil(len(raw) / 2) + 512
            ratios.append(est / actual)
            outs.append(u.get("output_tokens", 0))
            cb = len(json.dumps(resp.get("content") or [], separators=(",", ":")).encode())
            content_bytes.append(cb)
            sig += [len(c.get("signature", "")) for c in resp.get("content") or [] if c.get("type") == "thinking"]
            vis = cb - sum(len(c.get("signature", "")) for c in resp.get("content") or [])
            if u.get("output_tokens"):
                per_token.append(vis / max(1, u["output_tokens"] - ((u.get("output_tokens_details") or {}).get("thinking_tokens") or 0) or 1))
            if prev is not None and body["messages"][0] == prev[0]["messages"][0] and len(body["messages"]) > len(prev[0]["messages"]):
                growth.append(math.ceil((len(raw) - prev[1]) / 2))
            prev = (body, len(raw))
    plans, judgs = [], []
    for sdir in sorted(measured.glob("w1.*.B[34]")):
        pj = json.loads((sdir / "stages" / "plan.json").read_text(encoding="utf-8"))
        if pj.get("plan"):
            plans.append(len(json.dumps(pj["plan"], indent=1, sort_keys=True)))
        judgs.append(len(json.dumps(json.loads((sdir / "stages" / "judgments.json").read_text(encoding="utf-8")), indent=1, sort_keys=True)))
    rows = [json.loads(x) for x in (W1_STUDY_DIR / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    lat = sorted(r["payload"]["elapsed_seconds"] for r in rows if r["event_type"] == "request_completed"
                 and r["payload"].get("provider") == "generator" and r["payload"].get("session_id"))
    builds = sorted(r["payload"]["elapsed_s"] for r in rows if r["event_type"] == "build")
    attempts = sorted(r["payload"]["elapsed_seconds"] for r in rows if r["event_type"] == "attempt")

    def q(xs: list[float], p: float) -> float:
        return sorted(xs)[min(len(xs) - 1, int(p * len(xs)))]

    return {
        "requests": len(ratios),
        "admission_estimate_over_actual": {"min": round(min(ratios), 3), "median": round(statistics.median(ratios), 3), "max": round(max(ratios), 3)},
        "per_call_growth_est_tokens": {"n": len(growth), "median": statistics.median(growth), "p90": q(growth, 0.9), "max": max(growth)},
        "output_tokens": {"median": statistics.median(outs), "mean": round(statistics.mean(outs)), "p90": q(outs, 0.9), "max": max(outs),
                          "at_4000_cap": sum(1 for o in outs if o >= 4000)},
        "response_content_bytes": {"median": statistics.median(content_bytes), "max": max(content_bytes)},
        "thinking_signature_chars": {"median": statistics.median(sig) if sig else 0, "max": max(sig) if sig else 0},
        "latency_s": {"median": statistics.median(lat), "p90": q(lat, 0.9), "max": lat[-1]},
        "build_s_max": builds[-1], "attempt_s_max": attempts[-1],
        "plan_json_chars_max": max(plans), "judgments_json_chars_max": max(judgs),
        "source": "research_runs/ai_witness_2026_09 measured/ and events.jsonl (read-only)",
    }


# --------------------------------------------------------------------------- projections

def simulate(first: dict[str, int], ub: dict[str, int], cap_in: int, growth: int, cfg: dict[str, Any], ratio: float,
             sizes: str, extras: dict[str, int], out_tokens: int = 3301, price: dict[str, float] | None = None,
             cap_usd: float | None = None) -> dict[str, Any]:
    """Replay the session admission rules (input tokens, USD, calls) with a constant per-call growth.

    Reserve hold-backs always use the stage upper bounds, as the session does. Charged input per
    request = est / ratio (ratio = W1 minimum est/actual, the most expensive calibration). ``sizes``:
    "upper_bound" charges judge/generator requests at their upper bounds; "w1_typical" at the planner
    request plus W1-sized plan/judgment/evidence extras. USD: the stage's first request writes the
    whole prompt to the cache, later requests read the previous prefix and write the growth (two
    breakpoints); ``out_tokens`` output per call; admission reserves at the dearest input rate."""
    G, calls = cfg["final_reserve"]["input_growth_bound_tokens"], cfg["max_generator_calls"]
    FO, MO = cfg["final_reserve"]["output_tokens"], 4000
    price = price or {"read": 0.2, "write": 2.5, "out": 10.0, "dear": 2.5}
    cap_usd = cfg["max_usd"] if cap_usd is None else cap_usd

    def usd_upper(est: float, out: float) -> float:
        return (est * price["dear"] + out * price["out"]) / 1e6

    def cost(est: float, prev: float | None) -> float:
        act = est / ratio
        if prev is None:
            return (act * price["write"] + out_tokens * price["out"]) / 1e6
        pa = prev / ratio
        return (pa * price["read"] + (act - pa) * price["write"] + out_tokens * price["out"]) / 1e6

    out: dict[str, Any] = {}
    cap_out = cfg["max_output_tokens"]
    used, spent, est, n, prev, why, outs = 0.0, 0.0, first["agent"], 0, None, "calls", 0
    while n < calls - 1:
        if cap_out - outs - FO < 1024:
            why = "output_tokens"
            break
        if cap_in - used < 2 * est + G:
            why = "input_tokens"
            break
        if cap_usd - spent < usd_upper(est, MO) + usd_upper(est + G, FO):
            why = "usd"
            break
        used += est / ratio
        spent += cost(est, prev)
        outs += out_tokens
        prev, n, est = est, n + 1, est + growth
    out["F2"] = {"discretionary_calls": n, "stopped_by": why, "final_admissible": cap_in - used >= est and cap_usd - spent >= usd_upper(est, FO),
                 "input_used_before_final": round(used), "usd_before_final": round(spent, 4)}
    judge_first = ub["judge"] if sizes == "upper_bound" else min(ub["judge"], first["planner"] + extras["judge"])
    gen_first = ub["generator"] if sizes == "upper_bound" else min(ub["generator"], first["planner"] + extras["generator"])
    used, spent, n_mand, ok, outs = 0.0, 0.0, 0, True, 0
    hold_usd = usd_upper(ub["generator"], MO) + usd_upper(ub["generator"] + G, FO)
    for k, (stage_est, hold, p_) in enumerate(((first["planner"], ub["judge"], None), (first["planner"] + growth, ub["judge"], first["planner"]),
                                                (judge_first, 0, None), (judge_first + growth, 0, judge_first))):
        if cap_in - used >= stage_est + hold + 2 * ub["generator"] + G and cap_out - outs - FO >= 1024 and                 cap_usd - spent >= usd_upper(stage_est, MO) + hold_usd + (usd_upper(ub["judge"], MO) if hold else 0):
            used += stage_est / ratio
            spent += cost(stage_est, p_)
            outs += out_tokens
            n_mand += 1
        else:
            ok = False
            break
    est, n, prev, why = gen_first, 0, None, "calls"
    while ok and n_mand + n < calls - 1:
        if cap_out - outs - FO < 1024:
            why = "output_tokens"
            break
        if cap_in - used < 2 * est + G:
            why = "input_tokens"
            break
        if cap_usd - spent < usd_upper(est, MO) + usd_upper(est + G, FO):
            why = "usd"
            break
        used += est / ratio
        spent += cost(est, prev)
        outs += out_tokens
        prev, n, est = est, n + 1, est + growth
    out["F3"] = {"mandatory_calls_admitted": n_mand, "generator_discretionary_calls": n, "stopped_by": why if ok else "mandatory_stage",
                 "generation_stage_calls_incl_final": n + 1,
                 "final_admissible": ok and cap_in - used >= est and cap_usd - spent >= usd_upper(est, FO),
                 "input_used_before_final": round(used), "usd_before_final": round(spent, 4)}
    return out


def time_projection(cfg: dict[str, Any], lat: dict[str, float]) -> dict[str, Any]:
    fr = cfg["final_reserve"]["seconds"]
    wall = cfg["wall_seconds"]
    tout = design_config()["timeouts_seconds"]
    out: dict[str, Any] = {"final_call_reserve_s": fr, "build_pair_needs_s": 2 * (SEARCH_BUILD_TIMEOUT_S + BUILD_CLEANUP_S) + fr}
    for case in CASES:
        need = 2 * (tout[case]["outer"] + tout[case]["cleanup"]) + fr
        out[case] = {"pair_needs_remaining_s": need, "pair_admissible_until_elapsed_s": wall - need,
                     "build_pair_admissible_until_elapsed_s": wall - out["build_pair_needs_s"]}
    out["provider_seconds_for_12_calls"] = {k: round(12 * v, 1) for k, v in lat.items()}
    out["f3_elapsed_at_generation_start_s"] = {k: round(4 * v, 1) for k, v in lat.items()}
    return out


def derive_input_cap(rend: dict[str, Any], cfg: dict[str, Any], ratio: float, growth: int, extras: dict[str, int],
                     out_profiles: dict[str, int], price: dict[str, float]) -> int:
    """Design rule: the smallest multiple of 40,000 tokens at which input tokens are not the binding
    resource for any case or arm, at W1 p90 per-call growth, W1-typical stage sizes and the W1
    median and mean output profiles."""
    for cap in range(240000, 2000001, 40000):
        ok = True
        for r in rend.values():
            f = {"agent": r["first_requests"]["agent"]["admission_estimate_tokens"],
                 "planner": r["first_requests"]["planner"]["admission_estimate_tokens"]}
            for o in out_profiles.values():
                sim = simulate(f, r["stage_upper_bounds_tokens"], cap, growth, cfg, ratio, "w1_typical", extras, o, price)
                if sim["F2"]["stopped_by"] == "input_tokens" or sim["F3"]["stopped_by"] in ("input_tokens", "mandatory_stage"):
                    ok = False
        if ok:
            return cap
    raise RuntimeError("no input cap up to 2M satisfies the rule")


def check() -> dict[str, Any]:
    d = design_config()
    cfg = d["search"]
    cal = w1_calibration()
    rend = rendered_first_requests()
    ratio = cal["admission_estimate_over_actual"]["min"]
    p = d["pricing_snapshot"]
    dear = max(p["input_per_mtok_usd"], p["cache_write_per_mtok_usd"])
    price = {"read": p["cache_read_per_mtok_usd"], "write": p["cache_write_per_mtok_usd"], "out": p["output_per_mtok_usd"], "dear": dear}
    g = cal["per_call_growth_est_tokens"]
    scenarios = {"w1_median": g["median"], "w1_p90": g["p90"], "w1_max": g["max"]}
    outp = {"w1_median": cal["output_tokens"]["median"], "w1_mean": cal["output_tokens"]["mean"], "w1_p90": cal["output_tokens"]["p90"]}
    plan_b, judg_b = cal["plan_json_chars_max"], cal["judgments_json_chars_max"]
    extras = {"judge": math.ceil(1.3 * plan_b / 2) + g["p90"],
              "generator": math.ceil(1.3 * (plan_b + 1.5 * judg_b) / 2) + 2 * g["p90"]}
    cap_cfg = cfg["max_input_tokens"]

    def firsts(r: dict[str, Any]) -> dict[str, int]:
        return {"agent": r["first_requests"]["agent"]["admission_estimate_tokens"],
                "planner": r["first_requests"]["planner"]["admission_estimate_tokens"]}

    proj: dict[str, Any] = {}
    for sizes in ("w1_typical", "upper_bound"):
        for cap in (240000, cap_cfg):
            proj[f"{sizes}@{cap}@out_w1_mean"] = {case: {name: simulate(firsts(r), r["stage_upper_bounds_tokens"], cap, gr, cfg, ratio,
                                                                          sizes, extras, outp["w1_mean"], price)
                                                          for name, gr in scenarios.items()} for case, r in rend.items()}
    for oname, o in outp.items():
        proj[f"w1_typical@{cap_cfg}@out_{oname}"] = {case: {"w1_p90": simulate(firsts(r), r["stage_upper_bounds_tokens"], cap_cfg, g["p90"],
                                                                               cfg, ratio, "w1_typical", extras, o, price)}
                                                     for case, r in rend.items()}
    derived = derive_input_cap(rend, cfg, ratio, g["p90"], extras, {k: outp[k] for k in ("w1_median", "w1_mean")}, price)
    per_session_token_bound = (cap_cfg * dear + cfg["max_output_tokens"] * p["output_per_mtok_usd"]) / 1e6
    tout = d["timeouts_seconds"]
    vcpu = {"search_timeout_bound": round(8 * cfg["wall_seconds"] * 16 / 3600, 2),
            "validation_timeout_bound": round(sum(30 * (tout[c]["outer"] + tout[c]["cleanup"]) * 16 / 3600 for c in CASES) * 2, 2),
            "validation_builds": round(8 * 2 * (SEARCH_BUILD_TIMEOUT_S + BUILD_CLEANUP_S) * 16 / 3600, 2)}
    vcpu["measured_total_timeout_bound"] = round(sum(vcpu.values()), 2)
    vcpu["cap_measured"] = d["study_caps"]["allocated_vcpu_hours"] - d["study_caps"]["preparation_allocated_vcpu_hours"]
    vcpu["fits"] = vcpu["measured_total_timeout_bound"] <= vcpu["cap_measured"]

    def cells(key: str) -> list[dict[str, Any]]:
        return [v for c in proj[key].values() for v in c.values()]

    typ_mean = f"w1_typical@{cap_cfg}@out_w1_mean"
    findings = {
        "admission_estimate_conservative": ratio >= 1.0,
        "backend_build_timeout_matches_reservation": BUILD_TIMEOUT_S == SEARCH_BUILD_TIMEOUT_S,
        "w1_build_and_attempt_durations_within_bounds": cal["build_s_max"] < SEARCH_BUILD_TIMEOUT_S and cal["attempt_s_max"] < min(t["outer"] for t in tout.values()),
        "growth_bound_covers_w1_response_bytes": cal["response_content_bytes"]["max"] <= 36000,
        "proposal_240k_f3_starts_on_every_case_at_upper_bounds": all(v["F3"]["mandatory_calls_admitted"] >= 4 for v in cells("upper_bound@240000@out_w1_mean")),
        "proposal_240k_min_f3_generation_calls_typical": min(v["F3"]["generation_stage_calls_incl_final"] for v in cells("w1_typical@240000@out_w1_mean")),
        "derived_input_cap_rule_tokens": derived,
        "configured_input_cap_equals_derived_rule": cap_cfg == derived,
        "configured_min_f2_discretionary_calls_typical_p90_growth": min(v["w1_p90"]["F2"]["discretionary_calls"] for v in proj[typ_mean].values()),
        "configured_min_f3_generation_calls_typical_p90_growth": min(v["w1_p90"]["F3"]["generation_stage_calls_incl_final"] for v in proj[typ_mean].values()),
        "configured_min_f3_generation_calls_if_every_call_is_p90_output": min(v["w1_p90"]["F3"]["generation_stage_calls_incl_final"]
                                                                              for v in proj[f"w1_typical@{cap_cfg}@out_w1_p90"].values()),
        "final_call_admissible_in_every_configured_projection": all(v[a]["final_admissible"] for k in proj if f"@{cap_cfg}@" in k
                                                                    for v in cells(k) for a in ("F2", "F3")),
        "usd_hard_bound_session": cfg["max_usd"],
        "usd_token_price_bound_session": round(per_session_token_bound, 4),
        "usd_cap_binds_before_token_price_bound": cfg["max_usd"] < per_session_token_bound,
        "vcpu_timeout_bound_fits": vcpu["fits"],
    }
    return {"artifact": "w2a_budget_check_v1", "utc": utc_now(),
            "design_caps": {k: cfg[k] for k in ("max_generator_calls", "max_input_tokens", "max_output_tokens", "max_usd", "wall_seconds")},
            "final_reserve": cfg["final_reserve"], "w1_calibration": cal, "rendered": rend,
            "trajectory_projection": {"ratio_used": ratio, "growth_scenarios_est_tokens": scenarios, "output_profiles_tokens": outp,
                                      "typical_stage_extras_tokens": extras, "price": price, "projections": proj},
            "time_projection": time_projection(cfg, cal["latency_s"]), "allocated_vcpu_h": vcpu,
            "provider_bounds": {"batch_usd_hard_cap": round(8 * cfg["max_usd"], 2), "smoke_allowance_usd": 0.10,
                                "study_usd_cap": d["study_caps"]["provider_usd"],
                                "proposal_token_price_bound_240k_per_session": round((240000 * dear + 24000 * p["output_per_mtok_usd"]) / 1e6, 4)},
            "findings": findings}
