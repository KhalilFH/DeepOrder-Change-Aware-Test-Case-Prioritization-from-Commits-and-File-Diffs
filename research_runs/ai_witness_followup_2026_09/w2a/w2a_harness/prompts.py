"""Deterministic rendering of W2A model-facing text from the frozen ``design/PROMPTS.md``.

Semantic texts are read verbatim from PROMPTS.md sections; everything else inserted is
deterministic: packet content (W1 packets, unchanged), helper definitions (packet.py rule),
carried source evidence, validated plan/judgment table, stage limits and the harness state
block. Tool schemas are defined here and bound by the package freeze.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any

from . import DESIGN_DIR, templates
from .common import W1Error, canonical_json, sha256_text
from .config import search_config

PROMPTS_MD = DESIGN_DIR / "PROMPTS.md"
SECTION_NAMES = {
    "system": "System text",
    "f2": "F2 task",
    "planner": "F3 planner task",
    "judge": "F3 judge task",
    "generator": "F3 generator task",
    "final_call": "Final-call instruction",
    "truncated": "Truncated-response notice",
    "no_tool": "No-tool-call notice",
    "invalid_stage": "Invalid stage output notice",
    "final": "Final submission format",
}


@lru_cache(maxsize=1)
def sections() -> dict[str, str]:
    text = PROMPTS_MD.read_text(encoding="utf-8").replace("\r\n", "\n")
    out = {}
    for key, title in SECTION_NAMES.items():
        m = re.search(rf"^## {re.escape(title)}\n\n(.*?)(?=\n## |\Z)", text, re.S | re.M)
        if not m:
            raise W1Error(f"PROMPTS.md section missing: {title}")
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
        "description": "Read lines of an allowed packet file (at most 300 lines and 16,000 characters per read). Counts against the session budget through the tokens it adds to later requests.",
        "input_schema": _obj({"file_id": {"type": "string"}, "start_line": {"type": "integer"}, "end_line": {"type": "integer"}},
                             ["file_id", "start_line", "end_line"]),
    },
    "submit_patch": {
        "name": "submit_patch",
        "description": "Propose a test overlay: exact-snippet insertion edits to editable supplied test files and/or permitted new test files. Returns a proposal id and the static edit-contract result. Each call counts as one patch proposal, legal or not.",
        "input_schema": _obj({"edits": {"type": "array", "items": EDIT}, "new_files": {"type": "array", "items": NEWFILE},
                              "rationale": {"type": "string"}, "source_spans": SPANS},
                             ["edits", "new_files", "rationale", "source_spans"]),
    },
    "build_pair": {
        "name": "build_pair",
        "description": "Compile a legal proposal (its id, \"latest\" or \"unchanged\") against both production variants (defective and repaired). Returns ordinary build output. Required before run_pair.",
        "input_schema": _obj({"proposal_id": {"type": "string"}}, ["proposal_id"]),
    },
    "run_pair": {
        "name": "run_pair",
        "description": "Run a proposal already built on both variants (its id, \"latest\" or \"unchanged\") once on each variant (identical overlay, one paired execution). Returns raw test output and ordinary stacks, not an independent validation result.",
        "input_schema": _obj({"proposal_id": {"type": "string"}}, ["proposal_id"]),
    },
    "submit_final": {
        "name": "submit_final",
        "description": "Seal the one final immutable submission: a legal proposal id, \"latest\", or \"unchanged\". Ends the session.",
        "input_schema": _obj({"proposal_id": {"type": "string"}, "rationale": {"type": "string"}, "source_spans": SPANS,
                              "obligation": {"type": "string"}, "uncertainties": {"type": "array", "items": {"type": "string"}}},
                             ["proposal_id", "rationale", "source_spans", "obligation", "uncertainties"]),
    },
    "submit_plan": {
        "name": "submit_plan",
        "description": "Return the planner output (checked locally; invalid plans are returned with errors).",
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
        "description": "Return exactly one judgment per provided claim (checked locally; incomplete tables are returned with errors).",
        "input_schema": _obj({"judgments": {"type": "array", "items": _obj({
            "claim_id": {"type": "string"}, "judgment": {"type": "string", "enum": ["supported", "contradicted", "unknown"]},
            "source_spans": SPANS, "reason": {"type": "string"}}, ["claim_id", "judgment", "source_spans", "reason"])}},
            ["judgments"]),
    },
}
for _t in TOOLS.values():
    _t["strict"] = True

STAGE_TOOLS = {
    "agent": ["read_source", "submit_patch", "build_pair", "run_pair", "submit_final"],
    "planner": ["read_source", "submit_plan"],
    "judge": ["read_source", "submit_judgments"],
    "generator": ["read_source", "submit_patch", "build_pair", "run_pair", "submit_final"],
}
STAGE_TOOL_OF = {"planner": "submit_plan", "judge": "submit_judgments"}
STAGE_TASK = {"agent": "f2", "planner": "planner", "judge": "judge", "generator": "generator"}
STAGE_OUTPUT_INSTRUCTION = {
    "agent": "Use the tools. Seal the session with submit_final (a legal proposal id, \"latest\" or \"unchanged\").",
    "planner": "Return the plan by calling submit_plan (one to eight claims).",
    "judge": "Return the judgments by calling submit_judgments with exactly one entry per claim id.",
    "generator": "Use the tools. Seal the session with submit_final (a legal proposal id, \"latest\" or \"unchanged\").",
}


def tool_defs(stage: str) -> list[dict[str, Any]]:
    return [TOOLS[n] for n in STAGE_TOOLS[stage]]


def tools_sha256() -> str:
    return sha256_text(canonical_json({k: TOOLS[k] for k in sorted(TOOLS)}))


# --------------------------------------------------------------------------- source rendering

def numbered(packet: dict[str, Any], fid: str, a: int, b: int) -> str:
    lines = packet["files"][fid].split("\n")
    return "\n".join(f"{n:>5}  {lines[n - 1]}" for n in range(a, b + 1))


def block(packet: dict[str, Any], fid: str, a: int, b: int, note: str = "") -> str:
    return f"### `{fid}` lines {a}-{b}{note}\n```\n{numbered(packet, fid, a, b)}\n```"


def read_source(packet: dict[str, Any], file_id: str, start: int, end: int) -> tuple[str, dict[str, Any] | None]:
    """Bounded read: at most 300 lines and 16,000 characters (cut at a line boundary).

    Returns (text for the model, provenance record or None for an error)."""
    cfg = search_config()
    if file_id not in packet["files"]:
        return f"ERROR: unknown file_id {file_id!r}; use a file id from the allowed packet file list", None
    lines = packet["files"][file_id].split("\n")
    start = max(1, int(start))
    end = min(len(lines), int(end), start + cfg["read_source_max_lines"] - 1)
    if start > end:
        return f"ERROR: empty range; {file_id} has {len(lines)} lines", None
    cap = cfg["tool_result_char_caps"]["read_source"]
    out, used, last = [], 0, start - 1
    for n in range(start, end + 1):
        row = f"{n:>5}  {lines[n - 1]}"
        if used + len(row) + 1 > cap and out:
            break
        out.append(row)
        used += len(row) + 1
        last = n
    text = "\n".join(out)
    if last < end:
        text += f"\n[read truncated after line {last} at the 16,000-character limit; request lines {last + 1}-{end} separately]"
    return text, {"file_id": file_id, "start": start, "end": last}


# --------------------------------------------------------------------------- packet context

def packet_index(packet: dict[str, Any]) -> str:
    return "\n".join(f"- `{fid}` ({e['lines']} lines, {e['version']})" for fid, e in sorted(packet["manifest"]["files"].items()))


T0_TOP_TESTS = 15
T0_MAX_CALLEES = 25


def t0_compact(packet: dict[str, Any]) -> str:
    """Byte-identical to W1 prompts.t0_compact."""
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


def helper_section(packet: dict[str, Any]) -> str:
    h = packet["helpers"]
    if not h["included"]:
        return "## Entry-point helper definitions\nNone selected by the fixed helper rule."
    parts = ["## Entry-point helper definitions (fixed rule: direct test-side callees and JUnit 3 fixtures)"]
    for d in h["included"]:
        note = f" ({d['rule']}: {d['callee']} for {d['entry_point'].split('#')[-1]}"
        note += f"; clipped, definition ends at line {d['definition_end']})" if d["clipped"] else ")"
        parts.append(block(packet, d["file_id"], d["start"], d["end"], note))
    return "\n\n".join(parts)


def packet_context(packet: dict[str, Any]) -> str:
    excerpts = [block(packet, f, a, b) for f, a, b in packet["excerpt_ranges"]]
    parts = [
        "# Shared case packet",
        packet["build_run"].strip(),
        "## Production change (defective -> repaired)\n```diff\n" + packet["diff"].rstrip() + "\n```",
        "## Allowed packet files (read more with read_source)\n" + packet_index(packet),
        "## T0 static extraction\n```text\n" + t0_compact(packet) + "\n```",
        "## Shared template bindings (deterministic metadata)\n```json\n" + json.dumps(templates.bindings(packet["case"]), sort_keys=True, indent=1) + "\n```",
        "## Initial excerpts\n" + "\n\n".join(excerpts),
        helper_section(packet),
    ]
    return "\n\n".join(parts)


# --------------------------------------------------------------------------- evidence carry-over

def _merge(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    out: list[list[int]] = []
    for a, b in sorted(ranges):
        if out and a <= out[-1][1] + 1:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(a, b) for a, b in out]


def _subtract(a: int, b: int, cover: list[tuple[int, int]]) -> list[tuple[int, int]]:
    parts = [(a, b)]
    for x, y in cover:
        nxt = []
        for p, q in parts:
            if y < p or x > q:
                nxt.append((p, q))
                continue
            if p < x:
                nxt.append((p, x - 1))
            if y < q:
                nxt.append((y + 1, q))
        parts = nxt
    return parts


def render_evidence(packet: dict[str, Any], entries: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    """Carried source evidence: merged per file, minus ranges already visible in the packet
    context, in first-appearance order, capped at 600 lines / 36,000 characters."""
    cfg = search_config()["evidence_carry"]
    visible: dict[str, list[tuple[int, int]]] = {}
    for f, a, b in packet["excerpt_ranges"]:
        visible.setdefault(f, []).append((a, b))
    for d in packet["helpers"]["included"]:
        visible.setdefault(d["file_id"], []).append((d["start"], d["end"]))
    order: list[str] = []
    per: dict[str, list[tuple[int, int]]] = {}
    for e in entries:
        if e["file_id"] not in per:
            order.append(e["file_id"])
        per.setdefault(e["file_id"], []).append((e["start"], e["end"]))
    blocks, lines_used, chars_used, omitted, rendered = [], 0, 0, [], []
    for fid in order:
        for a, b in _merge(per[fid]):
            for p, q in _subtract(a, b, _merge(visible.get(fid, []))):
                n = q - p + 1
                text = block(packet, fid, p, q)
                if lines_used + n > cfg["max_lines"] or chars_used + len(text) > cfg["max_chars"]:
                    omitted.append(f"{fid}:{p}-{q}")
                    continue
                blocks.append(text)
                rendered.append(f"{fid}:{p}-{q}")
                lines_used += n
                chars_used += len(text)
    head = "## Source evidence carried from earlier stages (deduplicated; ranges already shown above are not repeated)"
    if not blocks:
        body = "No additional source was read or cited in earlier stages."
    else:
        body = "\n\n".join(blocks)
    if omitted:
        body += "\n\nOmitted by the fixed carry-over cap (read again with read_source if needed): " + ", ".join(omitted)
    return head + "\n" + body, {"rendered": rendered, "omitted": omitted, "lines": lines_used, "chars": chars_used}


# --------------------------------------------------------------------------- stage messages

def state_block(state: dict[str, Any]) -> str:
    """Harness state; bounded to 3,000 characters."""
    cap = search_config()["tool_result_char_caps"]["state_block"]
    rows = [f"## Harness state ({state['stage_label']})"]
    rows.append(f"- model calls: {state['calls_left']} discretionary left in this stage" +
                ("" if state.get("final_reserved") is False else "; the final call is reserved separately"))
    rows.append(f"- session budget left: input_tokens={state['input_tokens']}, output_tokens={state['output_tokens']}, "
                f"usd={state['usd']}, seconds={state['seconds']}")
    rows.append(f"- patch proposals left: {state['patches_left']}; paired runs left: {state['pairs_left']}")
    if state["proposals"]:
        rows.append("- proposals (\"latest\" = " + (state["latest"] or "none") + "):")
        for p in state["proposals"]:
            rows.append("  - " + p)
    else:
        rows.append("- proposals: none yet (\"unchanged\" is always available)")
    text = "\n".join(rows)
    if len(text) > cap:
        text = text[:cap - 60] + "\n[state block truncated at the fixed limit]"
    return text


def stage_limits(stage: str, max_calls: int | None) -> str:
    if stage in ("planner", "judge"):
        return (f"# Stage limits\nThis stage allows at most {max_calls} model calls, including any corrected resubmission. "
                f"Submit with {STAGE_TOOL_OF[stage]} no later than the last of them; a stage without an accepted output ends the session.")
    return "# Stage limits\nThe harness state lists the discretionary calls left; one final call is reserved for sealing."


def render_first(stage: str, packet_ctx: str, state_text: str, extra: list[str] | None = None,
                 max_calls: int | None = None) -> str:
    s = sections()
    blocks = [f"# Task\n{s[STAGE_TASK[stage]]}", f"# Final submission format\n{s['final']}", stage_limits(stage, max_calls),
              packet_ctx]
    blocks += extra or []
    blocks.append(state_text)
    blocks.append("# Output\n" + STAGE_OUTPUT_INSTRUCTION[stage])
    return "\n\n".join(blocks)


def render_system() -> str:
    return sections()["system"]


def plan_text(plan: dict[str, Any]) -> str:
    return "## Validated plan\n```json\n" + json.dumps(plan, sort_keys=True, indent=1) + "\n```"


def claims_text(claims: list[dict[str, Any]]) -> str:
    return "## Claims to judge\n```json\n" + json.dumps(claims, sort_keys=True, indent=1) + "\n```"


def judgments_text(table: dict[str, Any]) -> str:
    return "## Judgment table\n```json\n" + json.dumps(table, sort_keys=True, indent=1) + "\n```"
