"""Offline regressions for the execution failures the W1 audit found (postrun_audit/REVIEW.md).

Each check drives real W2A code with recorded W1 material (read-only) where it exists:
R1 grpc helper body absent from W1 initial context; R2/R3 truncated planner responses; R4 empty
judgment list; R5 placeholder patch; R6 run before build; R7 input-admission denials; R8
output-admission denial; R9 cross-stage re-reads. Outcomes are harness behaviour, not model results.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from . import W1_STUDY_DIR, fakes, prompts
from .backends import FakeBackend
from .budget import generator_config
from .casespec import spec
from .config import design_config
from .ledger import ChainLedger
from .packet import load_packet, originals
from .providers import FakeGeneratorTransport, GeneratorClient, SessionBudget
from .resources import Caps, ResourceAccount
from .session import Conversation, Session, SessionEnv, SessionRecorder, run_f3

W1M = W1_STUDY_DIR / "measured"


def make_session(root: Path, case: str, arm: str, script: Any = None) -> tuple[Session, FakeGeneratorTransport]:
    d = design_config()
    acct = ResourceAccount(root / f"{case}.{arm}.res.jsonl", Caps.from_study_config(d))
    gt = FakeGeneratorTransport(script or fakes.ScenarioScript(), returned_model="fake-sonnet")
    gen = GeneratorClient(gt, generator_config(d, "fake-sonnet"), acct)
    pkt = load_packet(case)
    s = d["search"]
    env = SessionEnv(session_id=f"w2a.{case}.{arm}", case=case, arm=arm, spec=spec(case), packet=pkt, originals=originals(pkt),
                     backend=FakeBackend(fakes.subject_outcome, elapsed_s=0.1), account=acct,
                     recorder=SessionRecorder(root / f"{case}.{arm}", ChainLedger(root / f"{case}.{arm}.events.jsonl"), f"w2a.{case}.{arm}"),
                     search_first=["V_bad", "V_ok"] * 3, launch_sha256="0" * 64,
                     budget=SessionBudget(s["max_input_tokens"], s["max_output_tokens"], s["max_usd"], s["max_generator_calls"]),
                     search=s, generator=gen)
    return Session(env), gt


def _w1_first_text(rel: str) -> str:
    return json.loads((W1M / rel).read_text(encoding="utf-8"))["messages"][0]["content"][0]["text"]


def r1_helper(root: Path) -> dict[str, Any]:
    marker = "func testClientDoesntDeadlockWhileWritingErrornousLargeMessages(t *testing.T, e env)"
    w1_has = marker in _w1_first_text("w1.grpc1859.r1.B3/requests/w1.grpc1859.r1.B3.req01.request.json")
    s, _ = make_session(root, "grpc1859", "F2")
    w2a_has = marker in s.packet_ctx and "6010" in s.packet_ctx
    return {"id": "R1", "w1_evidence": "w1.grpc1859.r1.B3 req01: helper body (end2end_test.go:6010-6042) absent; read three times across stages",
            "expectation": "W2A packet context includes the helper body by the fixed helper rule",
            "observed": {"w1_initial_context_has_helper": w1_has, "w2a_initial_context_has_helper": w2a_has},
            "pass": (not w1_has) and w2a_has}


class _Seq:
    """Scripted responses in order; afterwards a valid stage output."""

    def __init__(self, items: list[dict[str, Any]], then: Any):
        self.items, self.then, self.n = list(items), then, 0

    def __call__(self, body: dict[str, Any]) -> dict[str, Any]:
        self.n += 1
        return self.items.pop(0) if self.items else self.then(body)


def r2_r3_truncated_plans(root: Path) -> list[dict[str, Any]]:
    out = []
    for rid, replay in (("R2", "empty_plan_truncated"), ("R3", "partial_plan_truncated")):
        good = fakes.ScenarioScript()
        script = _Seq([{"raw": fakes.w1_replay(replay)}], lambda b: {"content": [fakes.tu("submit_plan", fakes.good_plan("pool162"), 7)]}
                      if "submit_plan" in {t["name"] for t in b["tools"]} else good(b))
        s, gt = make_session(root / rid, "pool162", "F3", script)
        box: dict[str, Any] = {}
        conv, end = s.mandatory_stage("planner", prompts.render_first("planner", s.packet_ctx, "state", [], 2),
                                      lambda a: (box.setdefault("plan", a) is not None, "accepted"), "judge")
        second = gt.sent[1] if len(gt.sent) > 1 else {}
        replayed_tool_ids = [c.get("id") for m in second.get("messages", []) for c in m.get("content", []) if c.get("type") == "tool_use"]
        notice = prompts.sections()["truncated"] in json.dumps(second.get("messages", [])[-1:])
        accepted_from_truncated = box.get("plan") == fakes.w1_replay(replay)["content"][-1].get("input")
        out.append({"id": rid, "w1_evidence": f"{fakes.W1_REPLAYS[replay]} (stop_reason max_tokens; W1 accepted it as stage completion)",
                    "expectation": "discarded: no tool call executed or replayed, fixed notice sent, stage continues and accepts only the next complete valid plan",
                    "observed": {"stage_end": end, "truncated_counter": s.counters["truncated_responses"],
                                 "truncated_tool_use_replayed": bool(replayed_tool_ids), "notice_sent": notice,
                                 "accepted_truncated_input": accepted_from_truncated},
                    "pass": end == "accepted" and s.counters["truncated_responses"] == 1 and not replayed_tool_ids and notice
                            and not accepted_from_truncated})
    return out


def r4_empty_judgments(root: Path) -> dict[str, Any]:
    from .stagecheck import validate_judgments
    pkt = load_packet("istio17860")
    raw = [c for c in fakes.w1_replay("empty_judgments")["content"] if c.get("type") == "tool_use"][0]["input"]
    claims = [{"id": f"C{i}"} for i in range(1, 8)]
    table, errors = validate_judgments(raw, claims, pkt)
    explicit = {"judgments": [{"claim_id": c["id"], "judgment": "unknown", "source_spans": [], "reason": "insufficient context"} for c in claims]}
    t2, e2 = validate_judgments(explicit, claims, pkt)
    return {"id": "R4", "w1_evidence": "w1.istio17860.r1.B3 req03: submit_judgments with [] against seven claims; W1 defaulted all to unknown",
            "expectation": "empty list rejected with the missing claim ids; seven explicit unknown judgments accepted and kept distinct",
            "observed": {"empty_rejected": table is None, "errors": errors[:2], "explicit_unknown_accepted": t2 is not None and not e2},
            "pass": table is None and bool(errors) and t2 is not None and all(v["judgment"] == "unknown" for v in t2.values())}


def r5_placeholder_patch(root: Path) -> dict[str, Any]:
    raw = json.loads((W1M / "w1.pool162.r1.B3/proposals/w1.pool162.r1.B3.p1.json").read_text(encoding="utf-8"))["proposal"]
    s, _ = make_session(root, "pool162", "F2")
    r = s.tool_submit_patch(raw)
    seal = s.tool_submit_final(r["proposal_id"], {}, "discretionary")
    build = s.tool_build_pair(r["proposal_id"])
    state = s.state_text("F2 agent stage", 5)
    return {"id": "R5", "w1_evidence": "w1.pool162.r1.B3 p1: edit to a file literally named 'placeholder' (sole W1 AI patch)",
            "expectation": "explicit malformed-proposal error, counted as a proposal, refused by build_pair and submit_final, shown as MALFORMED in the state",
            "observed": {"result": r, "seal": seal, "build": build, "state_marks_malformed": "MALFORMED" in state},
            "pass": r.get("legal") is False and "error" in r and "error" in seal and "error" in build and s.final is None
                    and s.patch_count == 1 and "MALFORMED" in state}


def r6_run_before_build(root: Path) -> dict[str, Any]:
    s, _ = make_session(root, "k8s26980", "F2")
    p = s.tool_submit_patch(fakes.probe_proposal(s.e.spec))
    r = s.tool_run_pair("latest")
    runs_before = len(s.e.backend.runs)
    state = s.state_text("F2 agent stage", 5)
    b = s.tool_build_pair(p["proposal_id"])
    r2 = s.tool_run_pair(p["proposal_id"])
    return {"id": "R6", "w1_evidence": "seven W1 B2/B3 sessions called run_pair before build_pair and spent calls on the generic error",
            "expectation": "explicit 'call build_pair first' error, nothing executed, pair budget untouched, state shows 'not built'; after building the pair runs",
            "observed": {"error": r.get("error"), "runs_executed_before_build": runs_before, "state_not_built": "not built" in state,
                         "after_build_run_ok": "defective" in r2},
            "pass": "build_pair first" in (r.get("error") or "") and runs_before == 0 and s.pair_count == 1 and "not built" in state
                    and "next" in b and "defective" in r2}


def r7_input_denials(root: Path) -> dict[str, Any]:
    """Replay the W1 input-admission denials against W2A admission, using W1's recorded estimates."""
    rows = [json.loads(x) for x in (W1_STUDY_DIR / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    denied = [r for r in rows if r["event_type"] == "budget_denied" and "input-token" in r["payload"]["reason"]]
    results = []
    for r in denied:
        sid = r["entity_id"].rsplit(".", 1)[0]
        prior = [x["payload"] for x in rows if x["event_type"] == "request_completed" and x["payload"].get("session_id") == sid]
        used = sum(x["input_tokens"] or 0 for x in prior)
        need = int(r["payload"]["reason"].split("need ")[1].split(",")[0])
        s, _ = make_session(root / sid, "pool162", "F2")
        s.e.budget.used_input = used
        s.e.budget.generator_calls = len(prior)
        conv = Conversation("agent", "x")
        adm = s.admit(conv, "discretionary", est_override=need)
        results.append({"w1_request": r["entity_id"], "w1_used_input": used, "w1_need": need,
                        "w2a_admitted": not isinstance(adm, str), "w2a_final_reserve_held": getattr(adm, "held_back", {}).get("input_tokens")})
    return {"id": "R7", "w1_evidence": f"{len(denied)} W1 input-token admission denials (all pool162)",
            "expectation": "each denied W1 request is admissible under W2A caps with the final-call reserve still held",
            "observed": results, "pass": len(results) == 6 and all(x["w2a_admitted"] for x in results)}


def r8_output_denial(root: Path) -> dict[str, Any]:
    s, _ = make_session(root, "pool162", "F3")
    cap = s.e.budget.max_output_tokens
    s.e.budget.used_output = cap - s.FINAL_OUT - 880
    s.e.budget.generator_calls = 5
    conv = Conversation("generator", "x")
    disc = s.admit(conv, "discretionary", est_override=20000)
    fin = s.admit(conv, "final", est_override=20000)
    return {"id": "R8", "w1_evidence": "w1.pool162.r3.B3.req03 denied: output-token ceiling left 880 tokens; session ended with no submission",
            "expectation": "a discretionary request that would eat the final reserve is refused, and the reserved final call is still admitted with 4,000 output tokens",
            "observed": {"discretionary": disc if isinstance(disc, str) else "admitted",
                         "final_max_output": None if isinstance(fin, str) else fin.max_output},
            "pass": disc == "output_tokens" and not isinstance(fin, str) and fin.max_output >= s.FINAL_OUT}


def r9_cross_stage_reads(root: Path) -> dict[str, Any]:
    """A planner read outside the visible packet context must reach the judge and generator stages."""
    target = {"file_id": "shared/test/end2end_test.go", "start_line": 400, "end_line": 430}
    base = fakes.ScenarioScript()

    def script(body: dict[str, Any]) -> dict[str, Any]:
        names = {t["name"] for t in body["tools"]}
        if "submit_plan" in names and len(body["messages"]) == 1:
            return {"content": [fakes.tu("read_source", {**target, "start_line": 430, "end_line": 460}, 1)]}
        if "submit_plan" in names:
            return {"content": [fakes.tu("submit_plan", fakes.good_plan("grpc1859"), 2)]}
        return base(body)

    s, gt = make_session(root, "grpc1859", "F3", script)
    run_f3(s)
    firsts = {("judge" if "submit_judgments" in {t["name"] for t in b["tools"]} else "planner" if "submit_plan" in {t["name"] for t in b["tools"]}
               else "generator"): b["messages"][0]["content"][0]["text"] for b in gt.sent}
    needle = "### `shared/test/end2end_test.go` lines 430-460"
    return {"id": "R9", "w1_evidence": "8 W1 read_source ranges repeated a range read in an earlier stage of the same session (fresh stage contexts)",
            "expectation": "the planner's read is carried (deduplicated, with provenance) into the judge and generator first messages",
            "observed": {"judge_has_read": needle in firsts.get("judge", ""), "generator_has_read": needle in firsts.get("generator", ""),
                         "terminal": s.terminal},
            "pass": needle in firsts.get("judge", "") and needle in firsts.get("generator", "")}


def run_all() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        checks = [r1_helper(root / "r1")] + r2_r3_truncated_plans(root / "r23") + [
            r4_empty_judgments(root / "r4"), r5_placeholder_patch(root / "r5"), r6_run_before_build(root / "r6"),
            r7_input_denials(root / "r7"), r8_output_denial(root / "r8"), r9_cross_stage_reads(root / "r9")]
    return {"artifact": "w2a_w1_regressions_v1", "ok": all(c["pass"] for c in checks), "checks": checks,
            "note": "offline harness regressions against recorded W1 failures; no provider or subject execution"}
