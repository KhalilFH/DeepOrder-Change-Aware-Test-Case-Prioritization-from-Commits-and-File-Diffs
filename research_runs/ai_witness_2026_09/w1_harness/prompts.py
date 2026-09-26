"""Exact prompt rendering from the frozen templates in ``v1_2/prompts.md`` (byte-identical to v1 and v1.1).

The semantic texts are read verbatim from prompts.md sections (so the rendered
bytes are bound to the frozen design file) and combined with deterministic
insertions only: packet ids, source chunks, budgets, prior-stage output and
session feedback (prompts.md Material Passport). Tool schemas and the output
parser are defined here and hashed into the launch freeze.

Nothing from subject_register.md, the proposal's examples, human diagnoses or
oracle material is inserted; ``packet.leak_scan`` is applied to every rendering.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any

from . import DESIGN_DIR
from .common import W1Error, canonical_json, sha256_text

PROMPTS_MD = DESIGN_DIR / "prompts.md"
SECTION_NAMES = {
    "system": "Common system text for B2, B3 and B4 generator stages",
    "b2": "B2 task text",
    "planner": "B3/B4 stage 1: planner",
    "judge_b3": "B3 stage 2: capable-model judge",
    "jev": "B4 stage 2: Jev typed judgment",
    "generator": "B3/B4 stage 3: generator",
    "repair": "B3/B4 stage 4: optional repair",
    "final": "Common final submission format",
}
INITIAL_EXCERPT_MAX_LINES = 400
READ_MAX_LINES = 300


@lru_cache(maxsize=1)
def sections() -> dict[str, str]:
    text = PROMPTS_MD.read_text(encoding="utf-8").replace("\r\n", "\n")
    out = {}
    for key, title in SECTION_NAMES.items():
        m = re.search(rf"^## {re.escape(title)}\n\n(.*?)(?=\n## |\Z)", text, re.S | re.M)
        if not m:
            raise W1Error(f"prompts.md section missing: {title}")
        out[key] = m.group(1).strip()
    return out


def prompts_sha256() -> str:
    return sha256_text(PROMPTS_MD.read_text(encoding="utf-8").replace("\r\n", "\n"))


# --------------------------------------------------------------------------- tools

def _obj(props: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {"type": "object", "properties": props, "required": required, "additionalProperties": False}


SPANS = {"type": "array", "items": {"type": "string"}, "description": "file_id:start-end line ranges from the packet"}
EDIT = _obj({"path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}}, ["path", "old", "new"])
NEWFILE = _obj({"path": {"type": "string"}, "content": {"type": "string"}}, ["path", "content"])

TOOLS: dict[str, dict[str, Any]] = {
    "read_source": {
        "name": "read_source",
        "description": f"Read lines of an allowed packet file (at most {READ_MAX_LINES} lines per read). Counts against the session budget only through the tokens it adds to later requests.",
        "input_schema": _obj({"file_id": {"type": "string"}, "start_line": {"type": "integer"}, "end_line": {"type": "integer"}},
                             ["file_id", "start_line", "end_line"]),
    },
    "submit_patch": {
        "name": "submit_patch",
        "description": "Propose a test overlay: exact-snippet insertion edits to editable supplied test files and/or permitted new test files. Returns a proposal id and the static edit-contract result. Each call counts as one patch proposal.",
        "input_schema": _obj({"edits": {"type": "array", "items": EDIT}, "new_files": {"type": "array", "items": NEWFILE},
                              "rationale": {"type": "string"}, "source_spans": SPANS},
                             ["edits", "new_files", "rationale", "source_spans"]),
    },
    "build_pair": {
        "name": "build_pair",
        "description": "Compile a legal proposal (its id, \"latest\" or \"unchanged\") against both production variants (defective and repaired). Returns ordinary build output.",
        "input_schema": _obj({"proposal_id": {"type": "string"}}, ["proposal_id"]),
    },
    "run_pair": {
        "name": "run_pair",
        "description": "Run a built proposal (its id, \"latest\" or \"unchanged\") once on each variant (identical overlay, one paired execution). Returns raw test output and ordinary stacks, not an independent validation result.",
        "input_schema": _obj({"proposal_id": {"type": "string"}}, ["proposal_id"]),
    },
    "submit_final": {
        "name": "submit_final",
        "description": "Seal the one final immutable submission: a proposal id, \"latest\", or \"unchanged\". Ends the session.",
        "input_schema": _obj({"proposal_id": {"type": "string"}, "rationale": {"type": "string"}, "source_spans": SPANS,
                              "obligation": {"type": "string"}, "uncertainties": {"type": "array", "items": {"type": "string"}}},
                             ["proposal_id", "rationale", "source_spans", "obligation", "uncertainties"]),
    },
    "submit_plan": {
        "name": "submit_plan",
        "description": "Return the planner output.",
        "input_schema": _obj({
            "obligation": {"type": "string"},
            "claims": {"type": "array", "items": _obj({
                "id": {"type": "string"},
                "category": {"type": "string", "enum": ["input_action", "ordering", "resource_state", "observable_consequence"]},
                "proposition": {"type": "string"}, "source_spans": SPANS}, ["id", "category", "proposition", "source_spans"])},
            "intervention": {"type": "string"},
            "uncertainties": {"type": "array", "items": {"type": "string"}}},
            ["obligation", "claims", "intervention", "uncertainties"]),
    },
    "submit_judgments": {
        "name": "submit_judgments",
        "description": "Return one judgment per provided claim.",
        "input_schema": _obj({"judgments": {"type": "array", "items": _obj({
            "claim_id": {"type": "string"}, "judgment": {"type": "string", "enum": ["supported", "contradicted", "unknown"]},
            "source_spans": SPANS, "reason": {"type": "string"}}, ["claim_id", "judgment", "source_spans", "reason"])}},
            ["judgments"]),
    },
}
for _t in TOOLS.values():
    _t["strict"] = True

STAGE_TOOLS = {
    "b2": ["read_source", "submit_patch", "build_pair", "run_pair", "submit_final"],
    "planner": ["read_source", "submit_plan"],
    "judge_b3": ["read_source", "submit_judgments"],
    "generator": ["read_source", "submit_patch", "build_pair", "run_pair", "submit_final"],
    "repair": ["read_source", "submit_patch", "build_pair", "run_pair", "submit_final"],
}
STAGE_OUTPUT_INSTRUCTION = {
    "b2": "Use the tools. End the session by calling submit_final (a proposal id or \"unchanged\"); without it the session has no submission.",
    "planner": "Return the planner output by calling submit_plan (at most eight claims).",
    "judge_b3": "Return the judgments by calling submit_judgments with exactly one entry per claim id.",
    "generator": "Propose with submit_patch; use build_pair/run_pair as budget permits. Call submit_final to finish now, or stop after proposing to use the single optional repair stage.",
    "repair": "Call submit_final (a proposal id or \"unchanged\"); without it the session has no submission.",
}


def tool_defs(stage: str) -> list[dict[str, Any]]:
    return [TOOLS[n] for n in STAGE_TOOLS[stage]]


def tools_sha256() -> str:
    return sha256_text(canonical_json({k: TOOLS[k] for k in sorted(TOOLS)}))


# --------------------------------------------------------------------------- packet context

def packet_index(packet: dict[str, Any]) -> str:
    rows = []
    for fid, e in sorted(packet["manifest"]["files"].items()):
        rows.append(f"- `{fid}` ({e['lines']} lines, {e['version']})")
    return "\n".join(rows)


def _excerpt(packet: dict[str, Any], fid: str, a: int, b: int) -> str:
    lines = packet["files"][fid].split("\n")
    b = min(b, len(lines), a + INITIAL_EXCERPT_MAX_LINES - 1)
    body = "\n".join(f"{n:>5}  {lines[n - 1]}" for n in range(a, b + 1))
    return f"### `{fid}` lines {a}-{b}\n```\n{body}\n```"


def initial_excerpts(packet: dict[str, Any]) -> list[str]:
    """Deterministic initial excerpts: supplied entry-point tests, then changed functions (defective version)."""
    t0 = packet["t0"]
    out = []
    for r in t0.get("entry_point_ranks", []):
        path, rng = r["span"].rsplit(":", 1)
        a, b = (int(x) for x in rng.split("-"))
        out.append(_excerpt(packet, f"shared/{path}", a, b))
    seen = set()
    for c in t0["changed_functions"]:
        if c["version"] != "defective":
            continue
        path, rng = c["span"].rsplit(":", 1)
        if c["span"] in seen:
            continue
        seen.add(c["span"])
        a, b = (int(x) for x in rng.split("-"))
        out.append(_excerpt(packet, f"defective/{path}", a, b))
    return out


T0_TOP_TESTS = 15
T0_MAX_CALLEES = 25


def t0_compact(packet: dict[str, Any]) -> str:
    """Deterministic compact text rendering of t0.json (same data for every arm)."""
    t0 = packet["t0"]
    out = [f"tool: {t0['tool']} ({t0['limits']})", "", "Changed functions:"]
    for c in t0["changed_functions"]:
        lines = c["changed_lines"]
        out.append(f"- {c['version']} {c['function']} {c['span']} (changed lines {lines[0]}-{lines[-1]})")
    out += ["", f"Supplied tests ranked by changed-token overlap (top {T0_TOP_TESTS} of {t0['tests_ranked_total']}; ties lexical):"]
    for r in t0["test_ranking"][:T0_TOP_TESTS]:
        out.append(f"{r['rank']:>3}. {r['test']} {r['span']} score={r['score']}")
    out += ["", "Entry points:"]
    for e in t0.get("entry_point_ranks", []):
        out.append(f"- {e['entry_point']} rank={e['rank']} score={e['score']} {e['span']}")
    out += ["", f"Direct syntactic calls (unique callees in source order, first {T0_MAX_CALLEES}; definitions found in packet files):"]
    for d in t0["direct_calls"]:
        seen: list[str] = []
        items = []
        for c in d["calls"]:
            if c["callee"] in seen:
                continue
            seen.append(c["callee"])
            line = c["span"].rsplit(":", 1)[1]
            defs = c.get("definitions") or []
            items.append(f"{c['callee']}@L{line}" + (f" [def {defs[0]}]" if defs else ""))
        more = f" (+{len(seen) - T0_MAX_CALLEES} more)" if len(seen) > T0_MAX_CALLEES else ""
        out.append(f"- {d['caller']} {d['span']}: " + ", ".join(items[:T0_MAX_CALLEES]) + more)
    return "\n".join(out)


def packet_context(packet: dict[str, Any], bindings: dict[str, Any]) -> str:
    parts = [
        "# Shared case packet",
        packet["build_run"].strip(),
        "## Production change (defective -> repaired)\n```diff\n" + packet["diff"].rstrip() + "\n```",
        "## Allowed packet files (read more with read_source)\n" + packet_index(packet),
        "## T0 static extraction\n```text\n" + t0_compact(packet) + "\n```",
        "## Shared template bindings (deterministic metadata)\n```json\n" + json.dumps(bindings, sort_keys=True, indent=1) + "\n```",
        "## Initial excerpts\n" + "\n\n".join(initial_excerpts(packet)),
    ]
    return "\n\n".join(parts)


def budget_text(b: dict[str, Any]) -> str:
    return ("## Remaining session budget\n" + "\n".join(f"- {k}: {v}" for k, v in b.items()))


def render_user(stage: str, packet_ctx: str, budget: dict[str, Any], extra: list[str] | None = None) -> str:
    s = sections()
    task = s["b2"] if stage == "b2" else s[stage]
    blocks = [f"# Task\n{task}", f"# Final submission format\n{s['final']}", packet_ctx, budget_text(budget)]
    blocks += extra or []
    blocks.append("# Output\n" + STAGE_OUTPUT_INSTRUCTION[stage])
    return "\n\n".join(blocks)


def render_system() -> str:
    return sections()["system"]


def render_jev_state(claim: dict[str, Any], contexts: list[str]) -> str:
    return ("Atomic proposition:\n" + claim["proposition"] + "\n\nAllowed source context:\n" + "\n\n".join(contexts))


def jev_question() -> dict[str, Any]:
    """Typed choice question rendered from the frozen B4 stage-2 text."""
    return {
        "type": "choice",
        "instructions": "Does this source establish that the supplied test satisfies the stated prerequisite?",
        "criteria": {
            "supported": "affirmative source support",
            "contradicted": "affirmative incompatible behavior",
            "unknown": "insufficient or ambiguous evidence",
        },
    }


def read_source(packet: dict[str, Any], file_id: str, start: int, end: int) -> str:
    if file_id not in packet["files"]:
        return f"ERROR: unknown file_id {file_id!r}; see the allowed packet file list"
    lines = packet["files"][file_id].split("\n")
    start = max(1, int(start))
    end = min(len(lines), int(end), start + READ_MAX_LINES - 1)
    if start > end:
        return f"ERROR: empty range; {file_id} has {len(lines)} lines"
    return "\n".join(f"{n:>5}  {lines[n - 1]}" for n in range(start, end + 1))
