"""Search sessions: shared tool semantics, budgets and the five arm algorithms.

One session = one case x arm x replicate, a fresh workspace and empty method memory,
at most 600 s elapsed (provider latency, parsing, builds, execution and orchestration
included). Tools (method_contract.md): read_source, submit_patch, build_pair, run_pair,
submit_final. Caps: 4 patch proposals, 6 paired executions; a pair is admitted only if
both variants' outer timeout + cleanup fit the remaining deadline, and a build pair only
if both bounded builds fit. Nothing starts without a reservation. Search feedback is the
raw build/test output and ordinary stacks, never the focal oracle.

The final submission is sealed (hash + elapsed time persisted) before any independent
validation exists. No submission is recorded as such; it is never silently replaced by
the unchanged overlay.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from . import templates
from .backends import BUILD_CLEANUP_S, BuildResult, SubjectBackend, Trace
from .casespec import CaseSpec
from .charging import vcpu_h
from .common import EMPTY_OVERLAY_SHA256, W1Error, monotonic, sha256_bytes, utc_now, write_json
from .ledger import ChainLedger
from .overlay import Materialized, OverlayError, materialize, unchanged
from .packet import leak_scan
from . import prompts
from .providers import (BudgetDenied, GeneratorClient, JevClient, ProviderDrift, SessionBudget, parse_jev_choice,
                        with_cache_breakpoint)

SEARCH_BUILD_TIMEOUT_S = 60
FEEDBACK_HEAD = 1000
FEEDBACK_TAIL = 3000


class IntegrityStop(W1Error):
    """Packet leak, sandbox escape, drift or cleanup failure: stop for review."""


def truncate_feedback(text: str) -> str:
    """Deterministic truncation policy for search feedback (head + tail, omitted range recorded)."""
    if len(text) <= FEEDBACK_HEAD + FEEDBACK_TAIL:
        return text
    omitted = len(text) - FEEDBACK_HEAD - FEEDBACK_TAIL
    return text[:FEEDBACK_HEAD] + f"\n[... {omitted} characters omitted by the fixed truncation policy ...]\n" + text[-FEEDBACK_TAIL:]


def ordinary_status(trace: Trace) -> str:
    """Search-phase bookkeeping only (never the focal oracle)."""
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
    template_id: str | None = None
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
    replicate: int
    spec: CaseSpec
    packet: dict[str, Any]
    originals: dict[str, str]
    backend: SubjectBackend
    account: Any
    recorder: SessionRecorder
    search_first: list[str]
    launch_sha256: str
    budget: SessionBudget
    generator: GeneratorClient | None = None
    jev: JevClient | None = None
    wall_seconds: float = 600.0
    max_patches: int = 4
    max_pairs: int = 6
    clock: Callable[[], float] = monotonic


class Session:
    def __init__(self, env: SessionEnv):
        self.e = env
        self.t0 = env.clock()
        self.proposals: dict[str, Proposal] = {}
        self.patch_count = 0
        self.pair_count = 0
        self.final: dict[str, Any] | None = None
        self.reason_codes: list[str] = []
        self.request_seq = 0
        self.source_reads: list[dict[str, Any]] = []
        self.run_seconds = 0.0
        self.packet_ctx = prompts.packet_context(env.packet, templates.bindings(env.case))
        leaks = leak_scan(self.packet_ctx)
        if leaks:
            raise IntegrityStop(f"packet leak markers in rendered context: {leaks}")

    # -- clock ---------------------------------------------------------------
    def elapsed(self) -> float:
        return self.e.clock() - self.t0

    def remaining(self) -> float:
        return self.e.wall_seconds - self.elapsed()

    def budget_view(self) -> dict[str, Any]:
        b = self.e.budget.remaining()
        return {"seconds": round(max(0.0, self.remaining()), 1), "patch_proposals": self.e.max_patches - self.patch_count,
                "paired_runs": self.e.max_pairs - self.pair_count, "generator_calls": b["generator_calls"],
                "input_tokens": b["input_tokens"], "output_tokens": b["output_tokens"], "usd": b["usd"]}

    # -- tools ---------------------------------------------------------------
    def tool_read_source(self, file_id: str, start: int, end: int) -> str:
        text = prompts.read_source(self.e.packet, file_id, start, end)
        self.source_reads.append({"file_id": file_id, "start": start, "end": end, "utc": utc_now()})
        self.e.recorder.event("source_access", self.e.session_id, {"file_id": file_id, "start": start, "end": end,
                                                                     "sha256": sha256_bytes(text.encode())})
        return text

    def tool_submit_patch(self, proposal: dict[str, Any] | None, template_id: str | None = None) -> dict[str, Any]:
        if self.final is not None:
            return {"error": "session already sealed"}
        if self.patch_count >= self.e.max_patches:
            return {"error": "patch proposal cap reached"}
        self.patch_count += 1
        pid = f"{self.e.session_id}.p{self.patch_count}"
        try:
            mat = materialize(proposal, self.e.originals, self.e.spec)
            err = None
        except OverlayError as exc:
            mat, err = None, f"malformed proposal: {exc}"
        prop = Proposal(pid, mat, err, template_id)
        self.proposals[pid] = prop
        body = {"proposal": proposal, "template_id": template_id, "error": err,
                "materialized": mat.summary() if mat else None, "files": mat.files if mat else None}
        h = self.e.recorder.write_blob(f"proposals/{pid}.json", json.dumps(body, sort_keys=True, indent=1).encode("utf-8"))
        self.e.recorder.event("patch_proposed", pid, {"record_sha256": h, "overlay_sha256": mat.overlay_sha256 if mat else None,
                                                      "legal": bool(mat and mat.legal), "error": err,
                                                      "violations": mat.violations if mat else [], "template_id": template_id})
        if err:
            return {"proposal_id": pid, "legal": False, "error": err}
        return {"proposal_id": pid, "legal": mat.legal, "violations": mat.violations, "overlay_sha256": mat.overlay_sha256,
                "run_selection": mat.run_selection}

    def _unchanged_proposal(self) -> Proposal:
        pid = f"{self.e.session_id}.unchanged"
        if pid not in self.proposals:
            self.proposals[pid] = Proposal(pid, unchanged(self.e.originals, self.e.spec), None, "T1")
        return self.proposals[pid]

    def _resolve(self, proposal_id: str) -> Proposal | None:
        if proposal_id == "unchanged":
            return self._unchanged_proposal()
        if proposal_id == "latest":
            named = [p for p in self.proposals if not p.endswith(".unchanged")]
            return self.proposals[named[-1]] if named else None
        return self.proposals.get(proposal_id)

    def tool_build_pair(self, proposal_id: str) -> dict[str, Any]:
        prop = self._resolve(proposal_id)
        if prop is None or prop.mat is None:
            return {"error": f"unknown or malformed proposal {proposal_id!r}"}
        if not prop.mat.legal:
            return {"error": "illegal proposal: not built", "violations": prop.mat.violations}
        if len(prop.builds) == 2:
            return self._build_feedback(prop)
        need = 2 * (SEARCH_BUILD_TIMEOUT_S + BUILD_CLEANUP_S)
        if self.remaining() < need:
            return {"error": f"insufficient session time for a bounded build pair ({need}s needed)"}
        for variant in ("V_bad", "V_ok"):
            rid = self.e.account.reserve("search", f"{prop.pid}.build.{variant}",
                                         {"vcpu_h": vcpu_h(SEARCH_BUILD_TIMEOUT_S + BUILD_CLEANUP_S)})
            b = self.e.backend.build(self.e.spec, variant, prop.mat, f"{prop.pid}")
            self.e.account.settle(rid, {"vcpu_h": vcpu_h(b.elapsed_s)}, {"exit_code": b.exit_code})
            prop.builds[variant] = b
            self.e.recorder.write_blob(f"builds/{prop.pid}.{variant}.log", b.log.encode("utf-8"))
            self.e.recorder.event("build", f"{prop.pid}.{variant}", {"ok": b.ok, "exit_code": b.exit_code,
                                                                       "artifact_sha256": b.artifact_sha256,
                                                                       "overlay_sha256": b.overlay_sha256,
                                                                       "elapsed_s": round(b.elapsed_s, 3)})
        return self._build_feedback(prop)

    @staticmethod
    def _label(variant: str) -> str:
        return "defective" if variant == "V_bad" else "repaired"

    def _build_feedback(self, prop: Proposal) -> dict[str, Any]:
        return {self._label(v): {"ok": b.ok, "output": truncate_feedback(b.log)} for v, b in prop.builds.items()}

    def tool_run_pair(self, proposal_id: str) -> dict[str, Any]:
        prop = self._resolve(proposal_id)
        if prop is None or prop.mat is None or len(prop.builds) < 2 or not all(b.ok for b in prop.builds.values()):
            return {"error": "proposal must be built successfully on both variants first"}
        if self.pair_count >= self.e.max_pairs:
            return {"error": "paired-run cap reached"}
        s = self.e.spec
        need = 2 * (s.outer + s.cleanup)
        if self.remaining() < need:
            return {"error": f"insufficient session time to admit a full pair ({need}s needed); no half pair is run"}
        first = self.e.search_first[self.pair_count]
        order = [first, "V_ok" if first == "V_bad" else "V_bad"]
        self.pair_count += 1
        pair_id = f"{prop.pid}.pair{self.pair_count}"
        out: dict[str, Any] = {"pair_id": pair_id}
        for variant in order:
            aid = f"{pair_id}.{variant}"
            rid = self.e.account.reserve("search", aid, {"vcpu_h": vcpu_h(s.outer + s.cleanup)})
            tr = self.e.backend.run(s, variant, prop.builds[variant], prop.mat.run_selection, aid, None)
            self.e.account.settle(rid, {"vcpu_h": vcpu_h(tr.elapsed_s)}, {"exit_code": tr.exit_code})
            self.run_seconds += tr.elapsed_s
            self._record_attempt(tr, "search", prop.mat.overlay_sha256, None, None, ordinary_status(tr))
            if tr.harness_error or not tr.cleanup_ok:
                raise IntegrityStop(f"{aid}: {tr.harness_error or 'cleanup failure'}")
            out[self._label(variant)] = {"exit_code": tr.exit_code, "outer_timeout": tr.outer_timeout,
                                         "output": truncate_feedback(tr.text)}
        prop.pairs.append({"pair_id": pair_id, **{self._label(v): out[self._label(v)]["exit_code"] for v in order},
                           "timeouts": {self._label(v): out[self._label(v)]["outer_timeout"] for v in order}})
        return out

    def _record_attempt(self, tr: Trace, phase: str, patch_sha: str, triplet: int | None, position: int | None,
                        status: str, cls: dict[str, Any] | None = None) -> dict[str, Any]:
        th = self.e.recorder.write_blob(f"traces/{tr.attempt_id}.log", tr.text.encode("utf-8"))
        payload = {"kind": "attempt", "id": tr.attempt_id, "session_id": self.e.session_id, "phase": phase,
                   "variant": tr.variant, "patch_sha256": patch_sha, "triplet": triplet, "position": position,
                   "seed": tr.details.get("seed"), "status": status, "elapsed_seconds": round(tr.elapsed_s, 3),
                   "trace_sha256": th, "premise_evidence": (cls or {}).get("premise_evidence", []),
                   "consequence_evidence": (cls or {}).get("consequence_evidence", []),
                   "details": {"argv": tr.argv, "exit_code": tr.exit_code, "outer_timeout": tr.outer_timeout,
                               "cleanup_ok": tr.cleanup_ok, "artifact_sha256": tr.artifact_sha256,
                               "started_utc": tr.started_utc, "ended_utc": tr.ended_utc,
                               "harness_error": tr.harness_error, **({"oracle": cls} if cls else {})}}
        self.e.recorder.event("attempt", tr.attempt_id, payload)
        return payload

    def tool_submit_final(self, proposal_id: str, meta: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.final is not None:
            return {"error": "already sealed"}
        if self.remaining() <= 0:
            self.reason_codes.append("FINAL_AFTER_DEADLINE")
            return {"error": "session deadline passed; no submission accepted"}
        prop = self._resolve(proposal_id)
        if prop is None:
            return {"error": f"unknown proposal {proposal_id!r}"}
        overlay_sha = prop.mat.overlay_sha256 if prop.mat else None
        self.final = {"proposal_id": prop.pid, "overlay_sha256": overlay_sha,
                      "unchanged": overlay_sha == EMPTY_OVERLAY_SHA256, "legal": bool(prop.mat and prop.mat.legal),
                      "malformed": prop.mat is None, "files": prop.mat.files if prop.mat else None,
                      "run_selection": prop.mat.run_selection if prop.mat else None,
                      "sealed_utc": utc_now(), "elapsed_seconds": round(self.elapsed(), 3), "meta": meta or {}}
        h = self.e.recorder.write_blob("final.json", json.dumps(self.final, sort_keys=True, indent=1).encode("utf-8"))
        self.e.recorder.event("final_sealed", self.e.session_id, {"final_record_sha256": h, "overlay_sha256": overlay_sha,
                                                                  "elapsed_seconds": self.final["elapsed_seconds"]})
        return {"sealed": True, "overlay_sha256": overlay_sha}

    # -- tool dispatch for model arms ------------------------------------------
    def dispatch(self, name: str, args: dict[str, Any]) -> tuple[str, bool]:
        try:
            if name == "read_source":
                return self.tool_read_source(str(args.get("file_id", "")), int(args.get("start_line", 1)), int(args.get("end_line", 1))), False
            if name == "submit_patch":
                prop = {"edits": args.get("edits") or [], "new_files": args.get("new_files") or []}
                return json.dumps(self.tool_submit_patch(prop), sort_keys=True), False
            if name == "build_pair":
                return json.dumps(self.tool_build_pair(str(args.get("proposal_id", ""))), sort_keys=True), False
            if name == "run_pair":
                return json.dumps(self.tool_run_pair(str(args.get("proposal_id", ""))), sort_keys=True), False
            if name == "submit_final":
                meta = {k: args.get(k) for k in ("rationale", "source_spans", "obligation", "uncertainties")}
                return json.dumps(self.tool_submit_final(str(args.get("proposal_id", "")), meta), sort_keys=True), False
        except (ValueError, TypeError) as exc:
            return f"ERROR: invalid tool input: {exc}", True
        return f"ERROR: tool {name!r} is not available in this stage", True

    # -- summary -------------------------------------------------------------
    def status_record(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        status = "SEALED" if self.final is not None else "NO_SUBMISSION"
        return {"kind": "session", "id": self.e.session_id, "case": self.e.case, "arm": self.e.arm,
                "replicate": self.e.replicate, "packet_sha256": self.e.packet["manifest"]["packet_sha256"],
                "launch_sha256": self.e.launch_sha256, "elapsed_search_seconds": round(self.elapsed(), 3),
                "final_patch_sha256": self.final["overlay_sha256"] if self.final else None,
                "status": status, "reason_codes": self.reason_codes,
                "details": {"patch_proposals": self.patch_count, "paired_runs": self.pair_count,
                            "generator_calls": self.e.budget.generator_calls, "jev_evaluations": self.e.budget.jev_evaluations,
                            "input_tokens": self.e.budget.used_input, "output_tokens": self.e.budget.used_output,
                            "usd": round(self.e.budget.used_usd, 6), "proposal_ids": list(self.proposals),
                            "pairs": [p for pr in self.proposals.values() for p in pr.pairs],
                            "final": {k: v for k, v in (self.final or {}).items() if k != "files"},
                            **(extra or {})}}


# =========================================================================== arms

def run_b0(s: Session) -> None:
    s.tool_build_pair("unchanged")
    prop = s._unchanged_proposal()
    if len(prop.builds) == 2 and all(b.ok for b in prop.builds.values()):
        while s.pair_count < s.e.max_pairs:
            r = s.tool_run_pair("unchanged")
            if "error" in r:
                break
    s.tool_submit_final("unchanged", {"rationale": "B0: unchanged supplied tests"})


def run_b1(s: Session) -> None:
    cands = templates.candidates(s.e.spec, s.e.originals)
    order: list[str] = []
    ids: dict[str, str] = {}
    inapplicable = {}
    for tid, proposal, reason in cands:
        if tid == "T1":
            ids[tid] = "unchanged"
            order.append(tid)
            continue
        if reason is not None:
            inapplicable[tid] = reason
            continue
        r = s.tool_submit_patch(proposal, tid)
        if r.get("legal"):
            ids[tid] = r["proposal_id"]
            order.append(tid)
        else:
            inapplicable[tid] = f"template failed the edit contract: {r.get('violations') or r.get('error')}"
    built = []
    for tid in order:
        fb = s.tool_build_pair(ids[tid])
        prop = s._resolve(ids[tid])
        if prop and len(prop.builds) == 2 and all(b.ok for b in prop.builds.values()):
            built.append(tid)
        elif "error" in fb and "insufficient" in fb["error"]:
            break
    i = 0
    while built and s.pair_count < s.e.max_pairs:
        r = s.tool_run_pair(ids[built[i % len(built)]])
        if "error" in r:
            break
        i += 1
    chosen = "T1"
    for tid in built:
        pairs = s._resolve(ids[tid]).pairs
        ok_fail = any(p.get("repaired") != 0 for p in pairs)
        signal = any(p.get("defective") not in (0, None) and p.get("repaired") == 0 for p in pairs)
        if signal and not ok_fail:
            chosen = tid
            break
    s.tool_submit_final(ids[chosen], {"rationale": f"B1 selection rule chose {chosen}", "template_order": order,
                                      "inapplicable": inapplicable})


def _call(s: Session, messages: list[dict[str, Any]], stage: str) -> tuple[dict[str, Any] | None, str | None]:
    """One capable-model request; returns (response, stop_code)."""
    s.request_seq += 1
    rid = f"{s.e.session_id}.req{s.request_seq:02d}"
    cfg = s.e.generator.cfg
    body = {"model": cfg.requested_model, "system": prompts.render_system(),
            "messages": with_cache_breakpoint(messages) if cfg.prompt_caching else messages,
            "tools": prompts.tool_defs(stage), **cfg.settings_payload()}
    rendered = json.dumps(body)
    leaks = leak_scan(rendered)
    if leaks:
        raise IntegrityStop(f"leak markers in request {rid}: {leaks}")
    try:
        rec, resp = s.e.generator.create(rid, s.e.session_id, body, s.e.budget, s.remaining(),
                                         s.e.recorder.provider_recorder)
    except BudgetDenied as exc:
        s.reason_codes.append("BUDGET_DENIED")
        s.e.recorder.event("budget_denied", rid, {"reason": str(exc), "stage": stage})
        return None, "budget"
    if resp is None:
        s.reason_codes.append(f"PROVIDER_{rec.status}")
        return None, "provider"
    if resp.get("stop_reason") == "refusal":
        s.reason_codes.append("PROVIDER_REFUSAL")
        return resp, "refusal"
    return resp, None


def _tool_loop(s: Session, messages: list[dict[str, Any]], stage: str, max_calls: int,
               stop_tools: set[str]) -> tuple[dict[str, Any] | None, str]:
    """Run a stage conversation (append-only). Returns (captured stop-tool input, end reason)."""
    calls = 0
    while calls < max_calls:
        resp, stop = _call(s, messages, stage)
        calls += 1
        if stop in ("budget", "provider"):
            return None, stop
        if resp is None:
            return None, "provider"
        messages.append({"role": "assistant", "content": resp.get("content") or []})
        if stop == "refusal":
            return None, "refusal"
        uses = [c for c in resp.get("content") or [] if c.get("type") == "tool_use"]
        if not uses:
            if calls < max_calls:
                messages.append({"role": "user", "content": [{"type": "text", "text": prompts.budget_text(s.budget_view()) +
                                                             "\n\n# Output\n" + prompts.STAGE_OUTPUT_INSTRUCTION[stage]}]})
            continue
        results = []
        captured = None
        for u in uses:
            name, args = u.get("name"), u.get("input") or {}
            if name in stop_tools and name not in ("submit_final",):
                captured = {"name": name, "input": args}
                results.append({"type": "tool_result", "tool_use_id": u.get("id"), "content": "received"})
                continue
            out, is_err = s.dispatch(name, args)
            results.append({"type": "tool_result", "tool_use_id": u.get("id"), "content": out, **({"is_error": True} if is_err else {})})
            if name == "submit_final" and s.final is not None:
                return {"name": name, "input": args}, "final"
        messages.append({"role": "user", "content": results + [{"type": "text", "text": prompts.budget_text(s.budget_view())}]})
        if captured:
            return captured, "captured"
    return None, "calls_exhausted"


def run_b2(s: Session) -> None:
    user = prompts.render_user("b2", s.packet_ctx, s.budget_view())
    messages = [{"role": "user", "content": [{"type": "text", "text": user}]}]
    _, end = _tool_loop(s, messages, "b2", s.e.budget.max_generator_calls, {"submit_final"})
    s.reason_codes.append(f"END_{end.upper()}")


def _plan_claims(plan: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not plan or not isinstance(plan.get("claims"), list):
        return []
    claims = []
    for c in plan["claims"][:8]:
        if isinstance(c, dict) and isinstance(c.get("id"), str) and isinstance(c.get("proposition"), str):
            claims.append({"id": c["id"], "category": c.get("category"), "proposition": c["proposition"],
                           "source_spans": [x for x in (c.get("source_spans") or []) if isinstance(x, str)]})
    return claims


def _span_text(s: Session, span: str) -> str | None:
    try:
        fid, rng = span.rsplit(":", 1)
        a, b = (int(x) for x in rng.split("-"))
    except ValueError:
        return None
    if fid not in s.e.packet["files"]:
        return None
    return f"{fid}:{a}-{b}\n" + prompts.read_source(s.e.packet, fid, a, min(b, a + 149))


def run_structured(s: Session) -> None:
    """B3 (capable-model judge) and B4 (Jev judge): identical planner/generator/repair prompts and settings."""
    arm = s.e.arm
    judge_calls = 1 if arm == "B3" else 0
    # Stage 1: planner (must leave at least one call for each remaining mandatory stage)
    reserve_after = judge_calls + 1
    user = prompts.render_user("planner", s.packet_ctx, s.budget_view())
    pmsgs = [{"role": "user", "content": [{"type": "text", "text": user}]}]
    cap = max(0, s.e.budget.max_generator_calls - s.e.budget.generator_calls - reserve_after)
    got, end = _tool_loop(s, pmsgs, "planner", cap, {"submit_plan"})
    plan = got["input"] if got else None
    claims = _plan_claims(plan)
    s.e.recorder.write_blob("stages/plan.json", json.dumps({"plan": plan, "claims": claims, "end": end}, sort_keys=True, indent=1).encode())
    s.e.recorder.event("stage_plan", s.e.session_id, {"end": end, "claims": len(claims), "plan_present": plan is not None})
    # Stage 2: judgments
    table = {c["id"]: {"judgment": "unknown", "source": "default"} for c in claims}
    if claims and arm == "B3":
        claims_txt = "## Claims to judge\n```json\n" + json.dumps(claims, sort_keys=True, indent=1) + "\n```"
        user = prompts.render_user("judge_b3", s.packet_ctx, s.budget_view(), [claims_txt])
        jmsgs = [{"role": "user", "content": [{"type": "text", "text": user}]}]
        cap = max(0, s.e.budget.max_generator_calls - s.e.budget.generator_calls - 1)
        got, jend = _tool_loop(s, jmsgs, "judge_b3", cap, {"submit_judgments"})
        for j in ((got or {}).get("input") or {}).get("judgments") or []:
            if isinstance(j, dict) and j.get("claim_id") in table and j.get("judgment") in ("supported", "contradicted", "unknown"):
                table[j["claim_id"]] = {"judgment": j["judgment"], "source": "capable_model", "reason": j.get("reason"),
                                        "source_spans": j.get("source_spans")}
    elif claims and arm == "B4":
        entry_ctx = prompts.initial_excerpts(s.e.packet)[:len(s.e.spec.entry_points)]
        for k, c in enumerate(claims, 1):
            contexts = [t for t in (_span_text(s, sp) for sp in c["source_spans"][:4]) if t] + entry_ctx
            state = prompts.render_jev_state(c, contexts)
            if leak_scan(state):
                raise IntegrityStop("leak markers in Jev state")
            rid = f"{s.e.session_id}.jev{k:02d}"
            try:
                rec, resp = s.e.jev.evaluate(rid, s.e.session_id, state, prompts.jev_question(), s.e.budget,
                                             s.remaining(), s.e.recorder.provider_recorder)
            except BudgetDenied as exc:
                s.reason_codes.append("JEV_BUDGET_DENIED")
                s.e.recorder.event("budget_denied", rid, {"reason": str(exc), "stage": "jev"})
                break
            choice, info = parse_jev_choice(resp)
            table[c["id"]] = {"judgment": choice, "source": "jev", "request_id": rid, **info}
    s.e.recorder.write_blob("stages/judgments.json", json.dumps(table, sort_keys=True, indent=1).encode())
    s.e.recorder.event("stage_judgments", s.e.session_id, {"claims": len(claims), "judge": "jev" if arm == "B4" else "capable_model",
                                                           "counts": {v: sum(1 for x in table.values() if x["judgment"] == v)
                                                                      for v in ("supported", "contradicted", "unknown")}})
    # Stage 3: generator, then the single optional repair turn (same conversation, append-only)
    plan_txt = "## Planner output\n```json\n" + json.dumps(plan, sort_keys=True, indent=1) + "\n```"
    table_txt = "## Judgment table\n```json\n" + json.dumps({k: v["judgment"] for k, v in table.items()}, sort_keys=True, indent=1) + "\n```"
    user = prompts.render_user("generator", s.packet_ctx, s.budget_view(), [plan_txt, table_txt])
    gmsgs = [{"role": "user", "content": [{"type": "text", "text": user}]}]
    cap = s.e.budget.max_generator_calls - s.e.budget.generator_calls
    _, gend = _gen_loop(s, gmsgs, "generator", cap)
    if s.final is None and gend in ("stopped",) and s.e.budget.max_generator_calls - s.e.budget.generator_calls > 0:
        repair_txt = "# Task\n" + prompts.sections()["repair"] + "\n\n" + prompts.budget_text(s.budget_view()) + \
                     "\n\n# Output\n" + prompts.STAGE_OUTPUT_INSTRUCTION["repair"]
        gmsgs.append({"role": "user", "content": [{"type": "text", "text": repair_txt}]})
        cap = s.e.budget.max_generator_calls - s.e.budget.generator_calls
        _, rend = _gen_loop(s, gmsgs, "repair", cap)
        s.reason_codes.append(f"REPAIR_END_{rend.upper()}")
    s.reason_codes.append(f"GENERATOR_END_{gend.upper()}")


def _gen_loop(s: Session, messages: list[dict[str, Any]], stage: str, max_calls: int) -> tuple[None, str]:
    """Generator/repair: tools until submit_final, a response without tool use ('stopped'), or no calls left."""
    calls = 0
    while calls < max_calls:
        resp, stop = _call(s, messages, stage)
        calls += 1
        if resp is None:
            return None, stop or "provider"
        messages.append({"role": "assistant", "content": resp.get("content") or []})
        if stop == "refusal":
            return None, "refusal"
        uses = [c for c in resp.get("content") or [] if c.get("type") == "tool_use"]
        if not uses:
            return None, "stopped"
        results = []
        for u in uses:
            out, is_err = s.dispatch(u.get("name"), u.get("input") or {})
            results.append({"type": "tool_result", "tool_use_id": u.get("id"), "content": out, **({"is_error": True} if is_err else {})})
            if s.final is not None:
                return None, "final"
        messages.append({"role": "user", "content": results + [{"type": "text", "text": prompts.budget_text(s.budget_view())}]})
    return None, "calls_exhausted"


ARM_RUNNERS = {"B0": run_b0, "B1": run_b1, "B2": run_b2, "B3": run_structured, "B4": run_structured}


def _primitive_seconds(s: Session) -> float:
    total = 0.0
    for p in s.proposals.values():
        total += sum(b.elapsed_s for b in p.builds.values())
    return total + s.run_seconds


def run_session(env: SessionEnv) -> dict[str, Any]:
    # The serial host stays reserved for the whole session (provider waiting included): reserve the
    # full wall allowance for orchestration/provider time; primitives reserve and settle their own
    # intervals, and the overhead settles as elapsed minus primitive time (no double charge).
    overhead_rid = env.account.reserve("search", f"{env.session_id}.overhead", {"vcpu_h": vcpu_h(env.wall_seconds)})
    s = Session(env)
    env.recorder.event("session_started", env.session_id, {"case": env.case, "arm": env.arm, "replicate": env.replicate,
                                                            "packet_sha256": env.packet["manifest"]["packet_sha256"],
                                                            "launch_sha256": env.launch_sha256})
    stop_exc: Exception | None = None
    try:
        ARM_RUNNERS[env.arm](s)
    except ProviderDrift as exc:
        s.reason_codes.append("PROVIDER_DRIFT")
        stop_exc = exc
    except IntegrityStop as exc:
        s.reason_codes.append("INTEGRITY_STOP")
        stop_exc = exc
    finally:
        residual = max(0.0, s.elapsed() - _primitive_seconds(s))
        env.account.settle(overhead_rid, {"vcpu_h": vcpu_h(residual)}, {"session_elapsed_s": round(s.elapsed(), 3),
                                                                       "orchestration_and_provider_s": round(residual, 3)})
    rec = s.status_record()
    if stop_exc is not None:
        rec["status"] = "UNRESOLVED"
        rec["details"]["stop"] = str(stop_exc)
    h = env.recorder.write_blob("session.json", json.dumps(rec, sort_keys=True, indent=1).encode("utf-8"))
    env.recorder.event("session_ended", env.session_id, {**rec, "record_sha256": h})
    if stop_exc is not None:
        raise stop_exc
    return rec
