"""Local validation of F3 stage outputs (METHOD_CONTRACT.md "Stage acceptance").

A stage output is accepted only if the response was complete (not ``max_tokens``) and the
tool input passes these checks. An empty object, an empty claim list or an empty judgment
list is never accepted. Explicit ``unknown`` judgments are distinct from missing judgments.
"""

from __future__ import annotations

import re
from typing import Any

from .config import search_config

CATEGORIES = ("input_action", "ordering", "resource_state", "observable_consequence")
JUDGMENTS = ("supported", "contradicted", "unknown")
SPAN_RE = re.compile(r"^(?P<fid>[^:\s]+):(?P<a>\d+)(?:-(?P<b>\d+))?$")


def parse_span(span: Any, packet: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """Parse ``file_id:start-end`` (or ``file_id:line``). An unprefixed path is accepted only
    when it names exactly one packet file (``shared/<path>``); production paths need a version."""
    cap = search_config()["plan_limits"]["span_chars"]
    if not isinstance(span, str) or not span.strip():
        return None, "span must be a non-empty string"
    span = span.strip()
    if len(span) > cap:
        return None, f"span longer than {cap} characters"
    m = SPAN_RE.match(span)
    if not m:
        return None, f"span {span!r} is not file_id:start-end"
    fid, a = m.group("fid"), int(m.group("a"))
    b = int(m.group("b")) if m.group("b") else a
    files = packet["files"]
    if fid not in files:
        candidates = [f for f in files if f.split("/", 1)[1] == fid]
        if len(candidates) == 1:
            fid = candidates[0]
        elif len(candidates) > 1:
            return None, f"span {span!r} is ambiguous; prefix defective/ or repaired/"
        else:
            return None, f"span {span!r} names no packet file"
    n = len(files[fid].split("\n"))
    if not (1 <= a <= b <= n):
        return None, f"span {span!r} is outside 1-{n} or reversed"
    return {"file_id": fid, "start": a, "end": b, "text": f"{fid}:{a}-{b}"}, None


def _text(value: Any, name: str, cap: int, errors: list[str], required: bool = True) -> str:
    if not isinstance(value, str) or (required and not value.strip()):
        errors.append(f"{name} must be a non-empty string")
        return ""
    if len(value) > cap:
        errors.append(f"{name} exceeds {cap} characters")
    return value.strip()


def validate_plan(raw: Any, packet: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    lim = search_config()["plan_limits"]
    errors: list[str] = []
    if not isinstance(raw, dict) or not raw:
        return None, ["submit_plan input is empty; obligation, claims, intervention and uncertainties are required"]
    obligation = _text(raw.get("obligation"), "obligation", lim["obligation_chars"], errors)
    intervention = _text(raw.get("intervention"), "intervention", lim["intervention_chars"], errors)
    unc = raw.get("uncertainties")
    if not isinstance(unc, list):
        errors.append("uncertainties must be a list (it may be empty)")
        unc = []
    if len(unc) > lim["uncertainties_max"]:
        errors.append(f"at most {lim['uncertainties_max']} uncertainties")
    for i, u in enumerate(unc):
        _text(u, f"uncertainties[{i}]", lim["uncertainty_chars"], errors)
    claims_raw = raw.get("claims")
    if not isinstance(claims_raw, list) or not claims_raw:
        errors.append("claims must be a non-empty list")
        claims_raw = []
    if len(claims_raw) > lim["claims_max"]:
        errors.append(f"at most {lim['claims_max']} claims ({len(claims_raw)} given)")
    ids: set[str] = set()
    claims = []
    for i, c in enumerate(claims_raw):
        where = f"claims[{i}]"
        if not isinstance(c, dict):
            errors.append(f"{where} must be an object")
            continue
        cid = c.get("id")
        if not isinstance(cid, str) or not re.fullmatch(lim["claim_id_pattern"], cid):
            errors.append(f"{where}.id must match {lim['claim_id_pattern']}")
        elif cid in ids:
            errors.append(f"{where}.id {cid!r} is duplicated")
        else:
            ids.add(cid)
        if c.get("category") not in CATEGORIES:
            errors.append(f"{where}.category must be one of {', '.join(CATEGORIES)}")
        prop = _text(c.get("proposition"), f"{where}.proposition", lim["proposition_chars"], errors)
        spans_raw = c.get("source_spans")
        spans = []
        if not isinstance(spans_raw, list) or not (lim["spans_per_claim_min"] <= len(spans_raw) <= lim["spans_per_claim_max"]):
            errors.append(f"{where}.source_spans must list {lim['spans_per_claim_min']}-{lim['spans_per_claim_max']} spans")
            spans_raw = spans_raw if isinstance(spans_raw, list) else []
        for s in spans_raw[:lim["spans_per_claim_max"]]:
            parsed, err = parse_span(s, packet)
            if err:
                errors.append(f"{where}: {err}")
            else:
                spans.append(parsed["text"])
        claims.append({"id": cid, "category": c.get("category"), "proposition": prop, "source_spans": spans})
    if errors:
        return None, errors
    return {"obligation": obligation, "claims": claims, "intervention": intervention,
            "uncertainties": [u.strip() for u in unc]}, []


def validate_judgments(raw: Any, claims: list[dict[str, Any]], packet: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    lim = search_config()["judgment_limits"]
    errors: list[str] = []
    if not isinstance(raw, dict) or not isinstance(raw.get("judgments"), list) or not raw["judgments"]:
        return None, ["judgments must be a non-empty list with exactly one entry per claim id: "
                      + ", ".join(c["id"] for c in claims)]
    want = [c["id"] for c in claims]
    table: dict[str, Any] = {}
    for i, j in enumerate(raw["judgments"]):
        where = f"judgments[{i}]"
        if not isinstance(j, dict):
            errors.append(f"{where} must be an object")
            continue
        cid = j.get("claim_id")
        if cid not in want:
            errors.append(f"{where}.claim_id {cid!r} is not a provided claim id")
            continue
        if cid in table:
            errors.append(f"{where}: claim {cid!r} judged more than once")
            continue
        verdict = j.get("judgment")
        if verdict not in JUDGMENTS:
            errors.append(f"{where}.judgment must be one of {', '.join(JUDGMENTS)}")
        reason = _text(j.get("reason"), f"{where}.reason", lim["reason_chars"], errors)
        spans_raw = j.get("source_spans")
        if not isinstance(spans_raw, list) or len(spans_raw) > lim["spans_max"]:
            errors.append(f"{where}.source_spans must be a list of at most {lim['spans_max']} spans")
            spans_raw = spans_raw if isinstance(spans_raw, list) else []
        spans = []
        for s in spans_raw[:lim["spans_max"]]:
            parsed, err = parse_span(s, packet)
            if err:
                errors.append(f"{where}: {err}")
            else:
                spans.append(parsed["text"])
        if verdict in ("supported", "contradicted") and not spans:
            errors.append(f"{where}: a {verdict} judgment needs at least one valid source span")
        table[cid] = {"judgment": verdict, "reason": reason, "source_spans": spans}
    missing = [c for c in want if c not in table]
    if missing:
        errors.append("missing judgments for claim ids: " + ", ".join(missing))
    if errors:
        return None, errors
    return {cid: table[cid] for cid in want}, []
