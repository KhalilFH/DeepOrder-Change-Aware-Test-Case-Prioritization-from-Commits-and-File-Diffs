"""Serial execution of the immutable W2A schedule (adapted from W1 runner.py).

* A block (one case) runs its two sessions in the scheduled order and seals both finals before
  validating either, in the scheduled validation order.
* Strictly serial: one subject process at a time.
* Resume: completed sessions/validations are skipped; a session or validation that started without
  an end record is recorded as UNRESOLVED (INTERRUPTED_INDETERMINATE) and never rerun. Resuming
  requires a review note.
* Pause on provider drift, integrity stops or exhausted study reservations.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .backends import SubjectBackend
from .casespec import spec
from .common import W1Error, read_json, utc_now
from .ledger import ChainLedger
from .oracles import make_oracle
from .packet import load_packet, originals
from .providers import GeneratorClient, ProviderDrift, SessionBudget
from .resources import BudgetExceeded, ResourceAccount
from .session import IntegrityStop, SessionEnv, SessionRecorder, run_session
from .validation import validate


@dataclass
class RunContext:
    schedule: dict[str, Any]
    design: dict[str, Any]
    events: ChainLedger
    account: ResourceAccount
    backend: SubjectBackend
    out_dir: Path
    launch_sha256: str
    generator: GeneratorClient
    clock: Callable[[], float] | None = None
    only_blocks: list[str] | None = None


def _state(events: ChainLedger) -> dict[str, set[str]]:
    started, ended, vstarted, vdone = set(), set(), set(), set()
    for row in events.iter_rows():
        et, eid = row["event_type"], row["entity_id"]
        if et == "session_started":
            started.add(eid)
        elif et == "session_ended":
            ended.add(eid)
        elif et == "validation_started":
            vstarted.add(eid)
        elif et == "validation_outcome":
            vdone.add(row["payload"]["session_id"])
    return {"started": started, "ended": ended, "vstarted": vstarted, "vdone": vdone}


def session_budget(design: dict[str, Any]) -> SessionBudget:
    s = design["search"]
    return SessionBudget(max_input_tokens=s["max_input_tokens"], max_output_tokens=s["max_output_tokens"],
                         max_usd=s["max_usd"], max_generator_calls=s["max_generator_calls"])


def run_blocks(ctx: RunContext, resume_note: str | None = None) -> dict[str, Any]:
    st = _state(ctx.events)
    interrupted = (st["started"] - st["ended"]) | {v for v in st["vstarted"] if v not in st["vdone"]}
    if interrupted and not resume_note:
        raise W1Error(f"prior in-flight work detected {sorted(interrupted)}; resume requires --resume-review")
    for sid in sorted(st["started"] - st["ended"]):
        ctx.events.append("search", "session_ended", sid, {"kind": "session", "id": sid, "status": "UNRESOLVED",
                                                           "terminal": "INTERRUPTED_INDETERMINATE",
                                                           "reason_codes": ["INTERRUPTED_INDETERMINATE"],
                                                           "details": {"resume_review": resume_note}})
    for sid in sorted(v for v in st["vstarted"] if v not in st["vdone"]):
        ctx.events.append("validation", "validation_outcome", sid, {"session_id": sid, "outcome": "UNRESOLVED",
                                                                    "reason_codes": ["INTERRUPTED_INDETERMINATE"],
                                                                    "resume_review": resume_note})
    st = _state(ctx.events)
    sessions = {s["session_id"]: s for s in ctx.schedule["sessions"]}
    summary: dict[str, Any] = {"blocks_run": [], "stopped": None}
    for block in ctx.schedule["blocks"]:
        if ctx.only_blocks and block["block_id"] not in ctx.only_blocks:
            continue
        case = block["case"]
        sp = spec(case)
        pkt = load_packet(case)
        orig = originals(pkt)
        oracle = make_oracle(sp, pkt["files"], orig)
        finals: dict[str, Any] = {}
        try:
            for arm in block["session_order"]:
                sid = f"w2a.{case}.{arm}"
                sdir = ctx.out_dir / sid
                if sid in st["ended"]:
                    finals[sid] = _load_final(sdir)
                    continue
                row = sessions[sid]
                env = SessionEnv(session_id=sid, case=case, arm=arm, spec=sp, packet=pkt, originals=orig,
                                 backend=ctx.backend, account=ctx.account,
                                 recorder=SessionRecorder(sdir, ctx.events, sid, "search"),
                                 search_first=row["search_pair_first_variant"], launch_sha256=ctx.launch_sha256,
                                 budget=session_budget(ctx.design), search=ctx.design["search"], generator=ctx.generator,
                                 **({"clock": ctx.clock} if ctx.clock else {}))
                run_session(env)
                finals[sid] = _load_final(sdir)
            for sid in block["validation_order"]:
                if sid in st["vdone"]:
                    continue
                vrec = SessionRecorder(ctx.out_dir / sid, ctx.events, sid, "validation")
                vrec.event("validation_started", sid, {"utc": utc_now(), "finals_sealed_in_block": sorted(k for k, v in finals.items() if v)})
                out = validate(sid, finals.get(sid), sp, orig, oracle, ctx.backend, ctx.account, vrec,
                               sessions[sid]["validation_triplets"])
                vrec.write_blob("validation/outcome.json", json.dumps(out, sort_keys=True, indent=1).encode("utf-8"))
                vrec.event("validation_outcome", sid, out)
            summary["blocks_run"].append(block["block_id"])
        except (ProviderDrift, IntegrityStop, BudgetExceeded) as exc:
            summary["stopped"] = f"{type(exc).__name__}: {exc}"
            ctx.events.append("search", "run_paused", block["block_id"], {"reason": summary["stopped"]})
            break
    return summary


def _load_final(sdir: Path) -> dict[str, Any] | None:
    p = sdir / "final.json"
    return read_json(p) if p.exists() else None
