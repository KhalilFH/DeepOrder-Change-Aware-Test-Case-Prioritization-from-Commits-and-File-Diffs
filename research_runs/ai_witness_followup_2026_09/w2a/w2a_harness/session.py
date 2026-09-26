"""W2A search sessions: F2 (plain agent) and F3 (planner -> judge -> generator).

One session = one case x arm, a fresh workspace and empty method memory, at most 600 s elapsed.
Shared primitives (read_source, submit_patch, build_pair, run_pair, submit_final), edit contract,
feedback truncation and reservation rules are identical across arms (METHOD_CONTRACT.md).

W2A changes relative to W1 (DESIGN_CHANGES.md):

* every harness turn carries an explicit state block (proposals, legality, build/run state, budgets);
  build-before-run and illegal-seal errors are explicit;
* a ``max_tokens`` response is discarded: none of its tool calls run, it is not appended to the
  conversation, and a fixed notice is sent in the next (charged) call;
* F3 plan/judgment outputs are accepted only after local validation (stagecheck.py);
* F3 later stages receive carried source evidence (reads and cited spans), the validated plan and
  the judgment table;
* one final model call is reserved (a call, 4,000 output tokens, 120 s and an input bound covering
  the conversation growth of the preceding call); discretionary requests, builds and pairs are
  admitted only if that reserve survives; only submit_final is executed in the final call.

The final submission is sealed (hash + elapsed time persisted) before any independent validation
exists. No submission is recorded as such; it is never silently replaced by the unchanged overlay.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from . import prompts, stagecheck
from .backends import BUILD_CLEANUP_S, BuildResult, SubjectBackend, Trace
from .casespec import CaseSpec
from .charging import vcpu_h
from .common import EMPTY_OVERLAY_SHA256, W1Error, canonical_bytes, monotonic, sha256_bytes, utc_now
from .ledger import ChainLedger
from .overlay import Materialized, OverlayError, materialize, unchanged
from .packet import leak_scan
from .providers import (Admission, BudgetDenied, GeneratorClient, ProviderDrift, SessionBudget, estimate_input_tokens,
                        with_cache_breakpoints)

SEARCH_BUILD_TIMEOUT_S = 60
FEEDBACK_HEAD = 1000
FEEDBACK_TAIL = 3000
JSON_ESCAPE_FACTOR = 1.3  # upper-bound inflation of text inside JSON request strings


class IntegrityStop(W1Error):
    """Packet leak, sandbox escape, drift or cleanup failure: stop for review."""


def truncate_feedback(text: str) -> str:
    """W1 policy: head 1,000 + tail 3,000 characters, omitted range recorded."""
    if len(text) <= FEEDBACK_HEAD + FEEDBACK_TAIL:
        return text
    omitted = len(text) - FEEDBACK_HEAD - FEEDBACK_TAIL
    return text[:FEEDBACK_HEAD] + f"\n[... {omitted} characters omitted by the fixed truncation policy ...]\n" + text[-FEEDBACK_TAIL:]


def ordinary_status(trace: Trace) -> str:
    if trace.harness_error or not trace.cleanup_ok:
        return "HARNESS_INVALID"
    if trace.outer_timeout or trace.exit_code is None:
        return "UNRESOLVED"
    return "PASS" if trace.exit_code == 0 else "NONFOCAL_FAILURE"


@dataclass
class Proposal:
    pid: str
    mat: Materialized | None
    error: str | None
    builds: dict[str, BuildResult] = field(default_factory=dict)
    pairs: list[dict[str, Any]] = field(default_factory=list)


class SessionRecorder:
    def __init__(self, session_dir: Path, events: ChainLedger, session_id: str, stage: str = "search"):
        self.dir = session_dir
        self.events = events
        self.sid = session_id
        self.stage = stage
        self.dir.mkdir(parents=True, exist_ok=True)

    def write_blob(self, rel: str, data: bytes) -> str:
        p = self.dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return sha256_bytes(data)

    def event(self, event_type: str, entity_id: str, payload: dict[str, Any]) -> None:
        self.events.append(self.stage, event_type, entity_id, payload)

    def provider_recorder(self, event_type: str, payload: dict[str, Any], req: bytes | None, resp: bytes | None) -> None:
        rid = payload.get("id") or payload.get("request_id")
        if req is not None:
            self.write_blob(f"requests/{rid}.request.json", req)
        if resp is not None:
            self.write_blob(f"requests/{rid}.response.json", resp)
        self.event(event_type, rid, payload)


@dataclass
class SessionEnv:
    session_id: str
    case: str
    arm: str
    spec: CaseSpec
    packet: dict[str, Any]
    originals: dict[str, str]
    backend: SubjectBackend
    account: Any
    recorder: SessionRecorder
    search_first: list[str]
    launch_sha256: str
    budget: SessionBudget
    search: dict[str, Any]
    generator: GeneratorClient
    clock: Callable[[], float] = monotonic


class Conversation:
    """One stage conversation; append-only history whose last message is the pending user turn."""

    def __init__(self, stage: str, first_text: str):
        self.stage = stage
        self.messages: list[dict[str, Any]] = [{"role": "user", "content": [{"type": "text", "text": first_text}]}]

    def append_assistant(self, content: list[dict[str, Any]]) -> None:
        self.messages.append({"role": "assistant", "content": content})

    def append_user(self, blocks: list[dict[str, Any]]) -> None:
        self.messages.append({"role": "user", "content": blocks})

    def add_to_pending(self, text: str) -> None:
        """Append a text block to the unsent final user message (never to a sent one)."""
        self.messages[-1] = dict(self.messages[-1], content=list(self.messages[-1]["content"]) + [{"type": "text", "text": text}])


class Session:
    def __init__(self, env: SessionEnv):
        self.e = env
        self.cfg = env.search
        self.t0 = env.clock()
        self.proposals: dict[str, Proposal] = {}
        self.patch_count = 0
        self.pair_count = 0
        self.final: dict[str, Any] | None = None
        self.reason_codes: list[str] = []
        self.terminal: str | None = None
        self.request_seq = 0
        self.evidence: list[dict[str, Any]] = []
        self.run_seconds = 0.0
        self.calls_by_stage: dict[str, int] = {}
        self.stage_records: dict[str, Any] = {}
        self.counters = {"truncated_responses": 0, "no_tool_responses": 0, "invalid_stage_outputs": 0,
                         "tool_errors": 0, "tool_uses_not_executed": 0, "final_call_ignored_tools": 0,
                         "admission_denials": 0, "growth_bound_exceeded": 0}
        self.denials: list[dict[str, Any]] = []
        self.final_call_used = False
        self.packet_ctx = prompts.packet_context(env.packet)
        # Leak screen on harness-authored text only (packet, static prompt texts; later: source reads and
        # carried evidence). Model-generated text echoed back (plans, patches, test output) is not screened.
        self._scan("packet context", self.packet_ctx)
        for key, text in prompts.sections().items():
            self._scan(f"prompt section {key}", text)
        fr = self.cfg["final_reserve"]
        self.FINAL_OUT = fr["output_tokens"]
        self.FINAL_TIME = fr["seconds"]
        self.G_MAX = fr["input_growth_bound_tokens"]
        self.MIN_OUT = self.cfg["min_request_output_tokens"]
        self.MIN_TIMEOUT = self.cfg["min_request_timeout_s"]
        self.ub = self._stage_upper_bounds()

    # -- integrity -----------------------------------------------------------
    def _scan(self, what: str, text: str) -> None:
        leaks = leak_scan(text)
        if leaks:
            raise IntegrityStop(f"held-out markers in harness-authored {what}: {leaks}")

    # -- clock ---------------------------------------------------------------
    def elapsed(self) -> float:
        return self.e.clock() - self.t0

    def remaining(self) -> float:
        return self.cfg["wall_seconds"] - self.elapsed()

    # -- request bodies and bounds ---------------------------------------------
    def body(self, conv: Conversation) -> dict[str, Any]:
        cfg = self.e.generator.cfg
        return {"model": cfg.requested_model, "system": prompts.render_system(),
                "messages": with_cache_breakpoints(conv.messages), "tools": prompts.tool_defs(conv.stage),
                **cfg.settings_payload()}

    def _stage_upper_bounds(self) -> dict[str, int]:
        """Upper bounds (estimated tokens) of the first judge and generator requests, from the rendered
        stage message without extras plus the byte caps of the extras (evidence, plan, judgments)."""
        pl, jl, ev = self.cfg["plan_limits"], self.cfg["judgment_limits"], self.cfg["evidence_carry"]
        claim = pl["proposition_chars"] + pl["spans_per_claim_max"] * pl["span_chars"] + 200
        claims_chars = pl["claims_max"] * claim
        plan_chars = claims_chars + pl["obligation_chars"] + pl["intervention_chars"] + pl["uncertainties_max"] * (pl["uncertainty_chars"] + 10) + 400
        judg_chars = pl["claims_max"] * (jl["reason_chars"] + jl["spans_max"] * pl["span_chars"] + 200)
        state_chars = self.cfg["tool_result_char_caps"]["state_block"]
        out = {}
        for stage, extra_chars in (("judge", ev["max_chars"] + claims_chars + state_chars),
                                   ("generator", ev["max_chars"] + plan_chars + judg_chars + state_chars)):
            conv = Conversation(stage, prompts.render_first(stage, self.packet_ctx, "", [], self.cfg["f3_stage_max_calls"].get(stage)))
            base = len(canonical_bytes(self.body(conv)))
            out[stage] = math.ceil((base + JSON_ESCAPE_FACTOR * extra_chars) / 2) + 512
        return out

    def _check_ub(self, stage: str, first_text: str) -> None:
        est = estimate_input_tokens(self.body(Conversation(stage, first_text)))
        if est > self.ub[stage]:
            self.counters["growth_bound_exceeded"] += 1
            self.e.recorder.event("upper_bound_exceeded", self.e.session_id, {"stage": stage, "est": est, "bound": self.ub[stage]})

    # -- admission and the final reserve ---------------------------------------
    def admit(self, conv: Conversation, kind: str, downstream: str | None = None, est_override: int | None = None) -> Admission | str:
        """``est_override`` exists only for offline replays of W1's recorded admission estimates."""
        b = self.e.budget
        rem = b.remaining()
        gen = self.e.generator.cfg
        est = est_override if est_override is not None else estimate_input_tokens(self.body(conv))
        remaining_s = self.remaining()
        if kind == "final":
            if rem["generator_calls"] < 1:
                return "calls"
            timeout = min(gen.request_timeout_s, remaining_s - 5)
            max_out = min(gen.max_tokens_per_request, rem["output_tokens"])
            hold_in, hold_usd, held = 0, 0.0, {}
        else:
            if rem["generator_calls"] < 1 + self.cfg["final_reserve"]["calls"]:
                return "calls"
            timeout = min(gen.request_timeout_s, remaining_s - self.FINAL_TIME - 5)
            max_out = min(gen.max_tokens_per_request, rem["output_tokens"] - self.FINAL_OUT)
            if kind == "discretionary":
                final_ub = est + self.G_MAX
                hold_in = final_ub
                hold_usd = gen.usd_upper(final_ub, self.FINAL_OUT)
            else:  # mandatory F3 stage: keep room for the downstream first requests and the final call
                gen_ub = self.ub["generator"]
                hold_in = gen_ub + gen_ub + self.G_MAX
                hold_usd = gen.usd_upper(gen_ub, gen.max_tokens_per_request) + gen.usd_upper(gen_ub + self.G_MAX, self.FINAL_OUT)
                if downstream == "judge":
                    hold_in += self.ub["judge"]
                    hold_usd += gen.usd_upper(self.ub["judge"], gen.max_tokens_per_request)
            held = {"input_tokens": hold_in, "output_tokens": self.FINAL_OUT, "usd": round(hold_usd, 6),
                    "seconds": self.FINAL_TIME, "calls": 1}
        if timeout < self.MIN_TIMEOUT:
            return "time"
        if max_out < self.MIN_OUT:
            return "output_tokens"
        if est + hold_in > rem["input_tokens"]:
            return "input_tokens"
        if gen.usd_upper(est, max_out) + hold_usd > rem["usd"] + 1e-12:
            return "usd"
        return Admission(kind, est, max_out, timeout, gen.usd_upper(est, max_out), held)

    # -- model call --------------------------------------------------------------
    def call(self, conv: Conversation, adm: Admission) -> tuple[dict[str, Any] | None, str | None]:
        self.request_seq += 1
        rid = f"{self.e.session_id}.req{self.request_seq:02d}"
        self.calls_by_stage[conv.stage] = self.calls_by_stage.get(conv.stage, 0) + 1
        try:
            rec, resp = self.e.generator.create(rid, self.e.session_id, self.body(conv), self.e.budget, adm,
                                                self.e.recorder.provider_recorder)
        except BudgetDenied as exc:  # defense in depth; the admission policy should prevent this
            self.reason_codes.append("HARD_CEILING_DENIED")
            self.e.recorder.event("budget_denied", rid, {"reason": str(exc), "stage": conv.stage, "kind": adm.kind})
            return None, "denied"
        if resp is None:
            self.reason_codes.append(f"PROVIDER_{rec.status}")
            return None, "provider"
        if resp.get("stop_reason") == "refusal":
            self.reason_codes.append("PROVIDER_REFUSAL")
            return resp, "refusal"
        if resp.get("stop_reason") == "max_tokens":
            self.counters["truncated_responses"] += 1
            self.e.recorder.event("response_truncated", rid, {"stage": conv.stage, "discarded_tool_uses": [
                c.get("name") for c in resp.get("content") or [] if c.get("type") == "tool_use"]})
            return resp, "truncated"
        return resp, None

    def deny(self, conv: Conversation, kind: str, why: str) -> None:
        self.counters["admission_denials"] += 1
        d = {"stage": conv.stage, "kind": kind, "reason": why, "remaining": self.e.budget.remaining(),
             "seconds_left": round(self.remaining(), 1)}
        self.denials.append(d)
        self.e.recorder.event("admission_denied", self.e.session_id, d)

    # -- state block -------------------------------------------------------------
    def proposal_line(self, p: Proposal) -> str:
        name = "unchanged" if p.pid.endswith(".unchanged") else p.pid.rsplit(".", 1)[1]
        if p.mat is None:
            return f"{name}: MALFORMED ({p.error})"[:300]
        legal = "legal" if p.mat.legal else "ILLEGAL (" + "; ".join(p.mat.violations)[:200] + ")"
        if not p.builds:
            build = "not built"
        else:
            build = ", ".join(f"{'defective' if v == 'V_bad' else 'repaired'} {'ok' if b.ok else 'FAILED'}"
                              for v, b in sorted(p.builds.items()))
        runs = f"paired runs {len(p.pairs)}"
        if p.pairs:
            last = p.pairs[-1]
            runs += f" (last: defective exit={last.get('defective')}, repaired exit={last.get('repaired')})"
        return f"{name}: {legal}; build: {build}; {runs}"

    def state_text(self, stage_label: str, calls_left: int, final_reserved: bool = True) -> str:
        rem = self.e.budget.remaining()
        named = [p for p in self.proposals.values()]
        latest = [p for p in self.proposals if not p.endswith(".unchanged")]
        st = {"stage_label": stage_label, "calls_left": calls_left, "final_reserved": final_reserved,
              "input_tokens": rem["input_tokens"], "output_tokens": rem["output_tokens"], "usd": rem["usd"],
              "seconds": round(max(0.0, self.remaining()), 1),
              "patches_left": self.cfg["max_patch_proposals"] - self.patch_count,
              "pairs_left": self.cfg["max_paired_runs"] - self.pair_count,
              "proposals": [self.proposal_line(p) for p in named],
              "latest": latest[-1].rsplit(".", 1)[1] if latest else None}
        return prompts.state_block(st)

    def discretionary_left(self) -> int:
        return max(0, self.e.budget.remaining()["generator_calls"] - self.cfg["final_reserve"]["calls"])

    # -- tools -----------------------------------------------------------------
    def tool_read_source(self, file_id: str, start: int, end: int, stage: str) -> str:
        text, prov = prompts.read_source(self.e.packet, file_id, start, end)
        self._scan("read_source result", text)
        if prov:
            self.evidence.append({**prov, "kind": "read", "stage": stage, "request": self.request_seq})
            self.e.recorder.event("source_access", self.e.session_id, {**prov, "stage": stage,
                                                                         "sha256": sha256_bytes(text.encode())})
        return text

    def tool_submit_patch(self, proposal: dict[str, Any]) -> dict[str, Any]:
        if self.final is not None:
            return {"error": "session already sealed"}
        if self.patch_count >= self.cfg["max_patch_proposals"]:
            return {"error": f"patch proposal cap reached ({self.cfg['max_patch_proposals']}); build, run or seal an existing proposal"}
        self.patch_count += 1
        pid = f"{self.e.session_id}.p{self.patch_count}"
        try:
            mat = materialize(proposal, self.e.originals, self.e.spec)
            err = None
        except OverlayError as exc:
            mat, err = None, f"malformed proposal: {exc}"
        prop = Proposal(pid, mat, err)
        self.proposals[pid] = prop
        body = {"proposal": proposal, "error": err, "materialized": mat.summary() if mat else None, "files": mat.files if mat else None}
        h = self.e.recorder.write_blob(f"proposals/{pid}.json", json.dumps(body, sort_keys=True, indent=1).encode("utf-8"))
        self.e.recorder.event("patch_proposed", pid, {"record_sha256": h, "overlay_sha256": mat.overlay_sha256 if mat else None,
                                                      "legal": bool(mat and mat.legal), "error": err,
                                                      "violations": mat.violations if mat else [],
                                                      "unchanged": bool(mat and mat.overlay_sha256 == EMPTY_OVERLAY_SHA256)})
        short = pid.rsplit(".", 1)[1]
        if err:
            return {"proposal_id": short, "legal": False, "error": err,
                    "note": "counted as a patch proposal; it cannot be built or sealed"}
        out = {"proposal_id": short, "legal": mat.legal, "violations": mat.violations, "run_selection": mat.run_selection}
        if mat.overlay_sha256 == EMPTY_OVERLAY_SHA256:
            out["note"] = "this proposal changes nothing (identical to \"unchanged\")"
        elif mat.legal:
            out["next"] = f"build_pair {short} before run_pair"
        return out

    def _unchanged_proposal(self) -> Proposal:
        pid = f"{self.e.session_id}.unchanged"
        if pid not in self.proposals:
            self.proposals[pid] = Proposal(pid, unchanged(self.e.originals, self.e.spec), None)
        return self.proposals[pid]

    def _resolve(self, proposal_id: str) -> Proposal | None:
        proposal_id = (proposal_id or "").strip()
        if proposal_id == "unchanged":
            return self._unchanged_proposal()
        if proposal_id == "latest":
            named = [p for p in self.proposals if not p.endswith(".unchanged")]
            return self.proposals[named[-1]] if named else None
        if proposal_id in self.proposals:
            return self.proposals[proposal_id]
        return self.proposals.get(f"{self.e.session_id}.{proposal_id}")

    @staticmethod
    def _label(variant: str) -> str:
        return "defective" if variant == "V_bad" else "repaired"

    def tool_build_pair(self, proposal_id: str) -> dict[str, Any]:
        prop = self._resolve(proposal_id)
        if prop is None:
            return {"error": f"unknown proposal {proposal_id!r}; see the proposals in the harness state"}
        if prop.mat is None:
            return {"error": f"proposal {proposal_id!r} is malformed and cannot be built: {prop.error}"}
        if not prop.mat.legal:
            return {"error": "illegal proposal: not built", "violations": prop.mat.violations}
        if len(prop.builds) == 2:
            return {"note": "already built", **self._build_feedback(prop)}
        need = 2 * (SEARCH_BUILD_TIMEOUT_S + BUILD_CLEANUP_S) + self.FINAL_TIME
        if self.remaining() < need:
            return {"error": f"insufficient session time for a bounded build pair plus the final-call reserve ({need}s needed)"}
        for variant in ("V_bad", "V_ok"):
            rid = self.e.account.reserve("search", f"{prop.pid}.build.{variant}",
                                         {"vcpu_h": vcpu_h(SEARCH_BUILD_TIMEOUT_S + BUILD_CLEANUP_S)})
            b = self.e.backend.build(self.e.spec, variant, prop.mat, prop.pid)
            self.e.account.settle(rid, {"vcpu_h": vcpu_h(b.elapsed_s)}, {"exit_code": b.exit_code})
            prop.builds[variant] = b
            self.e.recorder.write_blob(f"builds/{prop.pid}.{variant}.log", b.log.encode("utf-8"))
            self.e.recorder.event("build", f"{prop.pid}.{variant}", {"ok": b.ok, "exit_code": b.exit_code,
                                                                       "artifact_sha256": b.artifact_sha256,
                                                                       "overlay_sha256": b.overlay_sha256,
                                                                       "elapsed_s": round(b.elapsed_s, 3)})
        fb = self._build_feedback(prop)
        if all(b.ok for b in prop.builds.values()):
            fb["next"] = "run_pair may now execute this proposal"
        return fb

    def _build_feedback(self, prop: Proposal) -> dict[str, Any]:
        cap = self.cfg["tool_result_char_caps"]["feedback_per_variant"]
        return {self._label(v): {"ok": b.ok, "output": truncate_feedback(b.log)[:cap + 200]} for v, b in sorted(prop.builds.items())}

    def tool_run_pair(self, proposal_id: str) -> dict[str, Any]:
        prop = self._resolve(proposal_id)
        if prop is None:
            return {"error": f"unknown proposal {proposal_id!r}; see the proposals in the harness state"}
        if prop.mat is None or not prop.mat.legal:
            return {"error": f"proposal {proposal_id!r} is malformed or illegal and cannot run"}
        if len(prop.builds) < 2:
            return {"error": f"proposal {proposal_id!r} has not been built on both variants; call build_pair first (nothing was run)"}
        if not all(b.ok for b in prop.builds.values()):
            return {"error": f"proposal {proposal_id!r} failed to build on at least one variant; it cannot run (nothing was run)"}
        if self.pair_count >= self.cfg["max_paired_runs"]:
            return {"error": "paired-run cap reached"}
        s = self.e.spec
        need = 2 * (s.outer + s.cleanup) + self.FINAL_TIME
        if self.remaining() < need:
            return {"error": f"insufficient session time to admit a full pair plus the final-call reserve ({need}s needed); no half pair is run"}
        first = self.e.search_first[self.pair_count]
        order = [first, "V_ok" if first == "V_bad" else "V_bad"]
        self.pair_count += 1
        pair_id = f"{prop.pid}.pair{self.pair_count}"
        out: dict[str, Any] = {"pair_id": pair_id.rsplit(".", 2)[-2] + "." + pair_id.rsplit(".", 1)[1]}
        for variant in order:
            aid = f"{pair_id}.{variant}"
            rid = self.e.account.reserve("search", aid, {"vcpu_h": vcpu_h(s.outer + s.cleanup)})
            tr = self.e.backend.run(s, variant, prop.builds[variant], prop.mat.run_selection, aid, None)
            self.e.account.settle(rid, {"vcpu_h": vcpu_h(tr.elapsed_s)}, {"exit_code": tr.exit_code})
            self.run_seconds += tr.elapsed_s
            self._record_attempt(tr, prop.mat.overlay_sha256, ordinary_status(tr))
            if tr.harness_error or not tr.cleanup_ok:
                raise IntegrityStop(f"{aid}: {tr.harness_error or 'cleanup failure'}")
            out[self._label(variant)] = {"exit_code": tr.exit_code, "outer_timeout": tr.outer_timeout,
                                         "output": truncate_feedback(tr.text)}
        prop.pairs.append({"pair_id": pair_id, **{self._label(v): out[self._label(v)]["exit_code"] for v in order},
                           "timeouts": {self._label(v): out[self._label(v)]["outer_timeout"] for v in order}})
        return out

    def _record_attempt(self, tr: Trace, patch_sha: str, status: str) -> None:
        th = self.e.recorder.write_blob(f"traces/{tr.attempt_id}.log", tr.text.encode("utf-8"))
        self.e.recorder.event("attempt", tr.attempt_id, {
            "kind": "attempt", "id": tr.attempt_id, "session_id": self.e.session_id, "phase": "search",
            "variant": tr.variant, "patch_sha256": patch_sha, "triplet": None, "position": None,
            "seed": tr.details.get("seed"), "status": status, "elapsed_seconds": round(tr.elapsed_s, 3), "trace_sha256": th,
            "premise_evidence": [], "consequence_evidence": [],
            "details": {"argv": tr.argv, "exit_code": tr.exit_code, "outer_timeout": tr.outer_timeout,
                        "cleanup_ok": tr.cleanup_ok, "artifact_sha256": tr.artifact_sha256, "started_utc": tr.started_utc,
                        "ended_utc": tr.ended_utc, "harness_error": tr.harness_error}})

    def tool_submit_final(self, proposal_id: str, meta: dict[str, Any], via: str) -> dict[str, Any]:
        if self.final is not None:
            return {"error": "already sealed"}
        if self.remaining() <= 0:
            self.reason_codes.append("FINAL_AFTER_DEADLINE")
            return {"error": "session deadline passed; no submission accepted"}
        prop = self._resolve(proposal_id)
        if prop is None:
            return {"error": f"unknown proposal {proposal_id!r}; nothing sealed"}
        if prop.mat is None or not prop.mat.legal:
            why = prop.error if prop.mat is None else "; ".join(prop.mat.violations)
            return {"error": f"proposal {proposal_id!r} is malformed or illegal and cannot be sealed: {why}"}
        overlay_sha = prop.mat.overlay_sha256
        self.final = {"proposal_id": prop.pid, "overlay_sha256": overlay_sha, "unchanged": overlay_sha == EMPTY_OVERLAY_SHA256,
                      "legal": True, "malformed": False, "files": prop.mat.files, "run_selection": prop.mat.run_selection,
                      "built_in_search": len(prop.builds) == 2 and all(b.ok for b in prop.builds.values()),
                      "paired_runs_in_search": len(prop.pairs), "sealed_via": via,
                      "sealed_utc": utc_now(), "elapsed_seconds": round(self.elapsed(), 3), "meta": meta}
        h = self.e.recorder.write_blob("final.json", json.dumps(self.final, sort_keys=True, indent=1).encode("utf-8"))
        self.e.recorder.event("final_sealed", self.e.session_id, {"final_record_sha256": h, "overlay_sha256": overlay_sha,
                                                                  "unchanged": self.final["unchanged"], "sealed_via": via,
                                                                  "elapsed_seconds": self.final["elapsed_seconds"]})
        return {"sealed": True, "overlay_sha256": overlay_sha}

    def dispatch(self, stage: str, name: str, args: dict[str, Any], via: str = "discretionary") -> tuple[str, bool]:
        if name not in prompts.STAGE_TOOLS[stage] or name in prompts.STAGE_TOOL_OF.values():
            return f"ERROR: tool {name!r} is not available in this stage", True
        try:
            if name == "read_source":
                return self.tool_read_source(str(args.get("file_id", "")), int(args.get("start_line", 1)), int(args.get("end_line", 1)), stage), False
            if name == "submit_patch":
                r = self.tool_submit_patch({"edits": args.get("edits") or [], "new_files": args.get("new_files") or []})
            elif name == "build_pair":
                r = self.tool_build_pair(str(args.get("proposal_id", "")))
            elif name == "run_pair":
                r = self.tool_run_pair(str(args.get("proposal_id", "")))
            else:
                meta = {k: args.get(k) for k in ("rationale", "source_spans", "obligation", "uncertainties")}
                r = self.tool_submit_final(str(args.get("proposal_id", "")), meta, via)
        except (ValueError, TypeError) as exc:
            return f"ERROR: invalid tool input: {exc}", True
        text = json.dumps(r, sort_keys=True)
        if name == "submit_patch":
            text = text[:self.cfg["tool_result_char_caps"]["submit_patch"]]
        return text, "error" in r

    # -- response processing -----------------------------------------------------
    def execute(self, conv: Conversation, uses: list[dict[str, Any]], stage_tool: str | None = None,
                accept: Callable[[dict[str, Any]], tuple[bool, str]] | None = None) -> tuple[list[dict[str, Any]], bool]:
        """Execute at most four tool uses in order; returns (tool_result blocks, stage_output_accepted)."""
        limit = self.cfg["max_tool_uses_executed_per_response"]
        total_cap = self.cfg["tool_result_char_caps"]["per_response_total"]
        results, used, accepted = [], 0, False
        for i, u in enumerate(uses):
            name, args = u.get("name"), u.get("input") or {}
            if accepted or self.final is not None:
                out, err = "not executed: the stage output was already accepted in this response", True
            elif i >= limit:
                out, err = f"not executed: at most {limit} tool calls per response are executed", True
                self.counters["tool_uses_not_executed"] += 1
            elif stage_tool and name == stage_tool:
                ok, out = accept(args)  # type: ignore[misc]
                err = not ok
                accepted = ok
            else:
                out, err = self.dispatch(conv.stage, name, args)
            if err:
                self.counters["tool_errors"] += 1
            room = max(200, total_cap - used)
            if len(out) > room:
                out = out[:room] + f"\n[tool result truncated at the {total_cap}-character per-response limit]"
            used += len(out)
            results.append({"type": "tool_result", "tool_use_id": u.get("id"), "content": out, **({"is_error": True} if err else {})})
            if self.final is not None:
                break
        return results, accepted

    def _record_growth(self, conv: Conversation, before_bytes: int) -> None:
        grown = math.ceil((len(canonical_bytes(self.body(conv))) - before_bytes) / 2)
        if grown > self.G_MAX:
            self.counters["growth_bound_exceeded"] += 1
            self.e.recorder.event("growth_bound_exceeded", self.e.session_id, {"stage": conv.stage, "grown_tokens_est": grown})

    # -- loops ---------------------------------------------------------------------
    def agent_loop(self, conv: Conversation, stage_label: str) -> str:
        """Discretionary tool loop (F2 agent stage, F3 generator stage)."""
        while True:
            if self.final is not None:
                return "sealed"
            adm = self.admit(conv, "discretionary")
            if isinstance(adm, str):
                self.deny(conv, "discretionary", adm)
                return f"reserve_{adm}"
            before = len(canonical_bytes(self.body(conv)))
            resp, stop = self.call(conv, adm)
            if stop in ("provider", "denied"):
                return stop
            if stop == "refusal":
                return "refusal"
            if stop == "truncated":
                conv.append_user([{"type": "text", "text": prompts.sections()["truncated"] + "\n\n" +
                                   self.state_text(stage_label, self.discretionary_left())}])
                continue
            content = resp.get("content") or []
            uses = [c for c in content if c.get("type") == "tool_use"]
            conv.append_assistant(content)
            if not uses:
                self.counters["no_tool_responses"] += 1
                conv.append_user([{"type": "text", "text": prompts.sections()["no_tool"] + "\n\n" +
                                   self.state_text(stage_label, self.discretionary_left())}])
                self._record_growth(conv, before)
                continue
            results, _ = self.execute(conv, uses)
            if self.final is not None:
                return "sealed"
            conv.append_user(results + [{"type": "text", "text": self.state_text(stage_label, self.discretionary_left())}])
            self._record_growth(conv, before)

    def final_call(self, conv: Conversation) -> None:
        """The reserved final call: only submit_final is executed."""
        conv.add_to_pending(prompts.sections()["final_call"])
        adm = self.admit(conv, "final")
        if isinstance(adm, str):
            self.deny(conv, "final", adm)
            self.terminal = "FINAL_NOT_ADMITTED"
            return
        self.final_call_used = True
        resp, stop = self.call(conv, adm)
        if stop in ("provider", "denied"):
            self.terminal = "FINAL_PROVIDER_FAILURE"
            return
        if stop == "refusal":
            self.terminal = "PROVIDER_REFUSAL"
            return
        if stop == "truncated":
            self.terminal = "FINAL_TRUNCATED"
            return
        uses = [c for c in resp.get("content") or [] if c.get("type") == "tool_use"]
        finals = [u for u in uses if u.get("name") == "submit_final"]
        self.counters["final_call_ignored_tools"] += len(uses) - len(finals[:1])
        if not finals:
            self.terminal = "FINAL_NO_SUBMIT"
            return
        out, err = self.dispatch(conv.stage, "submit_final", finals[0].get("input") or {}, via="final_call")
        self.e.recorder.event("final_call_result", self.e.session_id, {"result": out[:500], "error": err})
        self.terminal = "SEALED_FINAL_CALL" if self.final is not None else "FINAL_REJECTED"

    def mandatory_stage(self, stage: str, first_text: str, accept: Callable[[dict[str, Any]], tuple[bool, str]],
                        downstream: str | None) -> tuple[Conversation, str]:
        """F3 planner/judge: at most N calls; accepted only after local validation."""
        max_calls = self.cfg["f3_stage_max_calls"][stage]
        conv = Conversation(stage, first_text)
        calls = 0
        tool = prompts.STAGE_TOOL_OF[stage]
        while calls < max_calls:
            adm = self.admit(conv, "mandatory", downstream)
            if isinstance(adm, str):
                self.deny(conv, "mandatory", adm)
                return conv, f"not_admitted_{adm}"
            resp, stop = self.call(conv, adm)
            calls += 1
            left = max_calls - calls
            if stop in ("provider", "denied", "refusal"):
                return conv, stop
            if stop == "truncated":
                conv.append_user([{"type": "text", "text": prompts.sections()["truncated"] + "\n\n" +
                                   self.state_text(f"F3 {stage} stage", left, True)}])
                continue
            content = resp.get("content") or []
            uses = [c for c in content if c.get("type") == "tool_use"]
            conv.append_assistant(content)
            if not uses:
                self.counters["no_tool_responses"] += 1
                conv.append_user([{"type": "text", "text": prompts.sections()["no_tool"] + "\n\n" +
                                   self.state_text(f"F3 {stage} stage", left, True)}])
                continue
            results, accepted = self.execute(conv, uses, tool, accept)
            if accepted:
                return conv, "accepted"
            notice = prompts.sections()["invalid_stage"] if any(u.get("name") == tool for u in uses) else ""
            conv.append_user(results + [{"type": "text", "text": (notice + "\n\n" if notice else "") +
                                         self.state_text(f"F3 {stage} stage", left, True)}])
        return conv, "calls_exhausted"

    # -- summary -------------------------------------------------------------------
    def status_record(self) -> dict[str, Any]:
        status = "SEALED" if self.final is not None else "NO_SUBMISSION"
        b = self.e.budget
        return {"kind": "session", "id": self.e.session_id, "case": self.e.case, "arm": self.e.arm,
                "packet_sha256": self.e.packet["manifest"]["packet_sha256"], "launch_sha256": self.e.launch_sha256,
                "elapsed_search_seconds": round(self.elapsed(), 3),
                "final_patch_sha256": self.final["overlay_sha256"] if self.final else None,
                "status": status, "terminal": self.terminal, "reason_codes": self.reason_codes,
                "details": {"patch_proposals": self.patch_count, "paired_runs": self.pair_count,
                            "generator_calls": b.generator_calls, "calls_by_stage": self.calls_by_stage,
                            "input_tokens": b.used_input, "output_tokens": b.used_output, "usd": round(b.used_usd, 6),
                            "counters": self.counters, "admission_denials": self.denials,
                            "final_call_used": self.final_call_used, "stage_records": self.stage_records,
                            "stage_upper_bounds_tokens": self.ub,
                            "evidence_entries": len(self.evidence),
                            "proposals": {pid.rsplit(".", 1)[1]: {"legal": bool(p.mat and p.mat.legal), "malformed": p.mat is None,
                                                                  "unchanged": bool(p.mat and p.mat.overlay_sha256 == EMPTY_OVERLAY_SHA256),
                                                                  "built_ok": len(p.builds) == 2 and all(x.ok for x in p.builds.values()),
                                                                  "paired_runs": len(p.pairs)}
                                          for pid, p in self.proposals.items()},
                            "pairs": [x for p in self.proposals.values() for x in p.pairs],
                            "final": {k: v for k, v in (self.final or {}).items() if k != "files"}}}


# =========================================================================== arms

def run_f2(s: Session) -> None:
    first = prompts.render_first("agent", s.packet_ctx, s.state_text("F2 agent stage", s.discretionary_left()))
    conv = Conversation("agent", first)
    end = s.agent_loop(conv, "F2 agent stage")
    s.stage_records["agent"] = {"end": end}
    if end == "sealed":
        s.terminal = "SEALED_DISCRETIONARY"
    elif end == "refusal":
        s.terminal = "PROVIDER_REFUSAL"
    else:
        s.final_call(conv)


def run_f3(s: Session) -> None:
    packet = s.e.packet
    # Stage 1: planner
    plan_box: dict[str, Any] = {}

    def accept_plan(args: dict[str, Any]) -> tuple[bool, str]:
        plan, errors = stagecheck.validate_plan(args, packet)
        if errors:
            s.counters["invalid_stage_outputs"] += 1
            s.e.recorder.event("stage_output_rejected", s.e.session_id, {"stage": "planner", "errors": errors[:20]})
            return False, "REJECTED: " + json.dumps({"errors": errors[:20]})
        plan_box["plan"] = plan
        return True, "accepted"

    first = prompts.render_first("planner", s.packet_ctx, s.state_text("F3 planner stage", s.cfg["f3_stage_max_calls"]["planner"]),
                                 [], s.cfg["f3_stage_max_calls"]["planner"])
    _, pend = s.mandatory_stage("planner", first, accept_plan, "judge")
    plan = plan_box.get("plan")
    s.e.recorder.write_blob("stages/plan.json", json.dumps({"plan": plan, "end": pend}, sort_keys=True, indent=1).encode())
    s.e.recorder.event("stage_plan", s.e.session_id, {"end": pend, "accepted": plan is not None,
                                                      "claims": len(plan["claims"]) if plan else 0})
    s.stage_records["planner"] = {"end": pend, "accepted": plan is not None, "calls": s.calls_by_stage.get("planner", 0)}
    if plan is None:
        s.terminal = "PROVIDER_REFUSAL" if pend == "refusal" else "STAGE_FAILURE_PLAN"
        return
    for c in plan["claims"]:
        for sp in c["source_spans"]:
            parsed, _ = stagecheck.parse_span(sp, packet)
            s.evidence.append({"file_id": parsed["file_id"], "start": parsed["start"],
                               "end": min(parsed["end"], parsed["start"] + s.cfg["evidence_carry"]["claim_span_max_lines"] - 1),
                               "kind": "claim_span", "stage": "planner"})
    # Stage 2: judge
    ev_text, ev_stats = prompts.render_evidence(packet, s.evidence)
    s._scan("carried evidence (judge)", ev_text)
    claims = plan["claims"]
    judge_box: dict[str, Any] = {}

    def accept_judgments(args: dict[str, Any]) -> tuple[bool, str]:
        table, errors = stagecheck.validate_judgments(args, claims, packet)
        if errors:
            s.counters["invalid_stage_outputs"] += 1
            s.e.recorder.event("stage_output_rejected", s.e.session_id, {"stage": "judge", "errors": errors[:20]})
            return False, "REJECTED: " + json.dumps({"errors": errors[:20]})
        judge_box["table"] = table
        return True, "accepted"

    first = prompts.render_first("judge", s.packet_ctx, s.state_text("F3 judge stage", s.cfg["f3_stage_max_calls"]["judge"]),
                                 [ev_text, prompts.claims_text(claims)], s.cfg["f3_stage_max_calls"]["judge"])
    s._check_ub("judge", first)
    _, jend = s.mandatory_stage("judge", first, accept_judgments, None)
    table = judge_box.get("table")
    s.e.recorder.write_blob("stages/judgments.json", json.dumps({"table": table, "end": jend}, sort_keys=True, indent=1).encode())
    counts = {v: sum(1 for x in (table or {}).values() if x["judgment"] == v) for v in stagecheck.JUDGMENTS}
    s.e.recorder.event("stage_judgments", s.e.session_id, {"end": jend, "accepted": table is not None, "counts": counts,
                                                           "carried_evidence": ev_stats})
    s.stage_records["judge"] = {"end": jend, "accepted": table is not None, "counts": counts,
                                "calls": s.calls_by_stage.get("judge", 0), "carried_evidence": ev_stats}
    if table is None:
        s.terminal = "PROVIDER_REFUSAL" if jend == "refusal" else "STAGE_FAILURE_JUDGMENT"
        return
    for t in table.values():
        for sp in t["source_spans"]:
            parsed, _ = stagecheck.parse_span(sp, packet)
            s.evidence.append({"file_id": parsed["file_id"], "start": parsed["start"],
                               "end": min(parsed["end"], parsed["start"] + s.cfg["evidence_carry"]["claim_span_max_lines"] - 1),
                               "kind": "judgment_span", "stage": "judge"})
    # Stage 3: generator (discretionary loop, then the reserved final call if not sealed)
    ev_text, ev_stats = prompts.render_evidence(packet, s.evidence)
    s._scan("carried evidence (generator)", ev_text)
    first = prompts.render_first("generator", s.packet_ctx, s.state_text("F3 generator stage", s.discretionary_left()),
                                 [ev_text, prompts.plan_text(plan), prompts.judgments_text(table)])
    s._check_ub("generator", first)
    conv = Conversation("generator", first)
    end = s.agent_loop(conv, "F3 generator stage")
    s.stage_records["generator"] = {"end": end, "carried_evidence": ev_stats}
    if end == "sealed":
        s.terminal = "SEALED_DISCRETIONARY"
    elif end == "refusal":
        s.terminal = "PROVIDER_REFUSAL"
    else:
        s.final_call(conv)


ARM_RUNNERS = {"F2": run_f2, "F3": run_f3}


def _primitive_seconds(s: Session) -> float:
    return sum(b.elapsed_s for p in s.proposals.values() for b in p.builds.values()) + s.run_seconds


def run_session(env: SessionEnv) -> dict[str, Any]:
    overhead_rid = env.account.reserve("search", f"{env.session_id}.overhead", {"vcpu_h": vcpu_h(env.search["wall_seconds"])})
    env.recorder.event("session_started", env.session_id, {"case": env.case, "arm": env.arm,
                                                            "packet_sha256": env.packet["manifest"]["packet_sha256"],
                                                            "launch_sha256": env.launch_sha256})
    stop_exc: Exception | None = None
    s: Session | None = None
    try:
        s = Session(env)
        ARM_RUNNERS[env.arm](s)
    except ProviderDrift as exc:
        stop_exc = exc
    except IntegrityStop as exc:
        stop_exc = exc
    finally:
        elapsed = s.elapsed() if s else 0.0
        residual = max(0.0, elapsed - (_primitive_seconds(s) if s else 0.0))
        env.account.settle(overhead_rid, {"vcpu_h": vcpu_h(residual)}, {"session_elapsed_s": round(elapsed, 3),
                                                                       "orchestration_and_provider_s": round(residual, 3)})
    if s is None:
        rec = {"kind": "session", "id": env.session_id, "case": env.case, "arm": env.arm, "status": "UNRESOLVED",
               "terminal": "INTEGRITY_STOP", "reason_codes": ["INTEGRITY_STOP"], "details": {"stop": str(stop_exc)}}
    else:
        rec = s.status_record()
        if stop_exc is not None:
            rec["status"] = "UNRESOLVED"
            rec["terminal"] = "PROVIDER_DRIFT" if isinstance(stop_exc, ProviderDrift) else "INTEGRITY_STOP"
            rec["details"]["stop"] = str(stop_exc)
    h = env.recorder.write_blob("session.json", json.dumps(rec, sort_keys=True, indent=1).encode("utf-8"))
    env.recorder.event("session_ended", env.session_id, {**rec, "record_sha256": h})
    if stop_exc is not None:
        raise stop_exc
    return rec
