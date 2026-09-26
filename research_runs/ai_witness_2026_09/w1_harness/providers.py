"""Provider adapters with reservation-before-send budget enforcement.

Transports
----------
* ``AnthropicTransport``: raw HTTPS to the Claude Messages API (``POST /v1/messages``)
  and the free token-counting endpoint (``POST /v1/messages/count_tokens``), stdlib only.
  Raw HTTP instead of the SDK keeps the exact request bytes auditable and avoids the
  SDK's automatic retries (the protocol forbids silent retries). Fallbacks and fast
  mode are never requested (they would substitute or reprice the frozen model).
* ``JevTransport``: raw HTTPS to TypeSafe ``POST /v1/systemone`` (typed choice).
* ``FakeGeneratorTransport`` / ``FakeJevTransport``: scripted, offline.

Every request is admitted only after reserving its maximum input/output tokens and
USD against the session ceilings (60k input / 8k output / USD 8 per AI session,
across ALL provider requests) and the study ceilings (resources.py). One wire
request = one counted request; there is no retry. A request whose completion is
unknown (timeout, connection loss after send) is INDETERMINATE and stays charged
at its reservation. A returned model identity different from the frozen one raises
``ProviderDrift`` (pause affected sessions).
"""

from __future__ import annotations

import json
import math
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from .common import W1Error, canonical_bytes, monotonic, sha256_bytes, utc_now

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_COUNT_URL = "https://api.anthropic.com/v1/messages/count_tokens"
ANTHROPIC_MODELS_URL = "https://api.anthropic.com/v1/models/"
ANTHROPIC_VERSION = "2023-06-01"
JEV_URL = "https://api.typesafe.ai/v1/systemone"
USER_AGENT = "w1-harness/1.0 (research; python-urllib)"
COUNT_MARGIN = 1.05
COUNT_PAD = 64


class ProviderDrift(W1Error):
    """Returned model identity differs from the frozen launch identity."""


class BudgetDenied(W1Error):
    """The request cannot be admitted within the session or study ceilings."""


@dataclass
class WireResult:
    status: int | None
    headers: dict[str, str]
    body: bytes
    elapsed_s: float
    error: str | None = None
    sent: bool = True


class Transport(Protocol):
    def post(self, url: str, payload: bytes, timeout_s: float) -> WireResult: ...


def _http_post(url: str, payload: bytes, headers: dict[str, str], timeout_s: float) -> WireResult:
    # Explicit, fixed User-Agent: some gateways behind bot filtering reject the default "Python-urllib/x.y".
    req = urllib.request.Request(url, data=payload, method="POST", headers={"user-agent": USER_AGENT, **headers})
    t0 = monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return WireResult(resp.status, dict(resp.headers.items()), resp.read(), monotonic() - t0)
    except urllib.error.HTTPError as exc:
        return WireResult(exc.code, dict(exc.headers.items()) if exc.headers else {}, exc.read() or b"", monotonic() - t0,
                          f"HTTP {exc.code}")
    except (socket.timeout, TimeoutError) as exc:
        return WireResult(None, {}, b"", monotonic() - t0, f"timeout: {exc!r}")
    except urllib.error.URLError as exc:
        sent = not isinstance(exc.reason, (ConnectionRefusedError, socket.gaierror))
        return WireResult(None, {}, b"", monotonic() - t0, f"connection: {exc.reason!r}", sent=sent)


class AnthropicTransport:
    """Anthropic-Messages-format transport. ``auth`` is ``x-api-key`` (Anthropic) or ``bearer``
    (Anthropic-compatible gateways such as OpenCode Zen, ``Authorization: Bearer``)."""

    def __init__(self, api_key: str, auth: str = "x-api-key"):
        if not api_key:
            raise W1Error("no generator API key")
        if auth not in ("x-api-key", "bearer", "both"):
            raise W1Error(f"unknown auth style {auth!r}")
        self._key = api_key
        self._auth = auth

    def _headers(self) -> dict[str, str]:
        cred: dict[str, str] = {}
        if self._auth in ("x-api-key", "both"):
            cred["x-api-key"] = self._key
        if self._auth in ("bearer", "both"):
            cred["authorization"] = f"Bearer {self._key}"
        return {**cred, "anthropic-version": ANTHROPIC_VERSION, "content-type": "application/json"}

    def post(self, url: str, payload: bytes, timeout_s: float) -> WireResult:
        return _http_post(url, payload, self._headers(), timeout_s)

    def get_model(self, model: str, timeout_s: float = 30) -> WireResult:
        req = urllib.request.Request(ANTHROPIC_MODELS_URL + model, method="GET", headers=self._headers())
        t0 = monotonic()
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                return WireResult(resp.status, dict(resp.headers.items()), resp.read(), monotonic() - t0)
        except urllib.error.HTTPError as exc:
            return WireResult(exc.code, {}, exc.read() or b"", monotonic() - t0, f"HTTP {exc.code}")


class JevTransport:
    def __init__(self, api_key: str):
        if not api_key:
            raise W1Error("no Jev API key")
        self._key = api_key

    def post(self, url: str, payload: bytes, timeout_s: float) -> WireResult:
        return _http_post(url, payload, {"authorization": f"Bearer {self._key}", "content-type": "application/json"}, timeout_s)


# --------------------------------------------------------------------------- configuration

@dataclass(frozen=True)
class GeneratorConfig:
    requested_model: str
    expected_returned_model: str | None
    effort: str
    max_tokens_per_request: int
    request_timeout_s: float
    price_input_per_mtok: float
    price_output_per_mtok: float
    pricing_identity: str
    endpoint: str = ANTHROPIC_URL
    count_tokens_url: str | None = ANTHROPIC_COUNT_URL  # None: conservative local admission estimate
    price_cache_write_per_mtok: float | None = None  # default 1.25x input
    price_cache_read_per_mtok: float | None = None  # default 0.1x input
    prompt_caching: bool = False  # explicit breakpoint on the first (packet-bearing) user message

    def settings_payload(self) -> dict[str, Any]:
        return {"thinking": {"type": "adaptive"}, "output_config": {"effort": self.effort}, "tool_choice": {"type": "auto"}}

    @property
    def p_cache_write(self) -> float:
        return self.price_cache_write_per_mtok if self.price_cache_write_per_mtok is not None else 1.25 * self.price_input_per_mtok

    @property
    def p_cache_read(self) -> float:
        return self.price_cache_read_per_mtok if self.price_cache_read_per_mtok is not None else 0.1 * self.price_input_per_mtok

    def usd(self, base_in: float, cache_write: float, cache_read: float, out: float) -> float:
        return (base_in * self.price_input_per_mtok + cache_write * self.p_cache_write + cache_read * self.p_cache_read
                + out * self.price_output_per_mtok) / 1e6

    def reserve_usd(self, est_in: float, max_out: float) -> float:
        """Upper bound: every input token at the dearest input rate (base or cache write)."""
        return (est_in * max(self.price_input_per_mtok, self.p_cache_write) + max_out * self.price_output_per_mtok) / 1e6


LOCAL_ADMISSION_BYTES_PER_TOKEN = 2.0
LOCAL_ADMISSION_PAD = 512
"""Without a token-count endpoint, admission assumes one token per 2 UTF-8 bytes of the JSON request
(the current Claude tokenizer averages roughly 3 characters per token on code, and JSON escaping
inflates bytes further) plus 512 tokens for tool-use system overhead. Actual reported usage is what
is charged; an actual exceeding its estimate is recorded as an overrun, never erased."""


def with_cache_breakpoint(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Copy of ``messages`` with an explicit ephemeral breakpoint on the first user message's last block.

    The first message is byte-identical on every request of a stage conversation, so the marker never
    moves and earlier content is never edited (append-only history)."""
    out = [dict(m) for m in messages]
    first = out[0]
    content = [dict(b) for b in first["content"]]
    content[-1]["cache_control"] = {"type": "ephemeral"}
    out[0] = dict(first, content=content)
    return out


@dataclass(frozen=True)
class JevConfig:
    requested_model: str
    expected_returned_model: str | None
    request_timeout_s: float
    price_input_per_mtok: float
    price_output_per_mtok: float
    pricing_identity: str


@dataclass
class SessionBudget:
    """Per-session ceilings (study_config.json search.*), across all provider requests."""
    max_input_tokens: int
    max_output_tokens: int
    max_usd: float
    max_generator_calls: int
    max_jev_evaluations: int
    used_input: int = 0
    used_output: int = 0
    used_usd: float = 0.0
    generator_calls: int = 0
    jev_evaluations: int = 0
    reserved_input: int = 0
    reserved_output: int = 0
    reserved_usd: float = 0.0

    def remaining(self) -> dict[str, Any]:
        return {
            "input_tokens": self.max_input_tokens - self.used_input - self.reserved_input,
            "output_tokens": self.max_output_tokens - self.used_output - self.reserved_output,
            "usd": round(self.max_usd - self.used_usd - self.reserved_usd, 6),
            "generator_calls": self.max_generator_calls - self.generator_calls,
            "jev_evaluations": self.max_jev_evaluations - self.jev_evaluations,
        }


@dataclass
class RequestRecord:
    id: str
    session_id: str | None
    provider: str
    requested_model: str
    returned_model: str | None
    request_sha256: str
    response_sha256: str | None
    status: str
    elapsed_seconds: float
    input_tokens: int | None
    output_tokens: int | None
    usd: float | None
    usage_provenance: str
    details: dict[str, Any] = field(default_factory=dict)

    def payload(self) -> dict[str, Any]:
        return {"kind": "request", "id": self.id, "session_id": self.session_id, "provider": self.provider,
                "requested_model": self.requested_model, "returned_model": self.returned_model,
                "request_sha256": self.request_sha256, "response_sha256": self.response_sha256, "status": self.status,
                "elapsed_seconds": round(self.elapsed_seconds, 3), "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens, "usd": None if self.usd is None else round(self.usd, 6),
                "usage_provenance": self.usage_provenance, "details": self.details}


Recorder = Callable[[str, dict[str, Any], bytes | None, bytes | None], None]
"""(event_type, payload, request_bytes, response_bytes) -> persist before returning."""


def _usd(inp: float, out: float, pin: float, pout: float) -> float:
    return inp * pin / 1e6 + out * pout / 1e6


class GeneratorClient:
    def __init__(self, transport: Transport, cfg: GeneratorConfig, account: Any, stage_label: str = "search"):
        self.t = transport
        self.cfg = cfg
        self.account = account
        self.stage_label = stage_label

    def count_tokens(self, body: dict[str, Any], request_id: str = "", record: Recorder | None = None) -> tuple[int, str]:
        """Admission count via the free count_tokens endpoint (+5% +64 margin); UTF-8 byte bound if unavailable.

        The count request is itself logged (it is a wire request, unbilled, not a generation call)."""
        if self.cfg.count_tokens_url is None:
            n = math.ceil(len(canonical_bytes(body)) / LOCAL_ADMISSION_BYTES_PER_TOKEN) + LOCAL_ADMISSION_PAD
            return n, "local_estimate_utf8_bytes_div_2_plus_512"
        cbody = {k: body[k] for k in ("model", "system", "messages", "tools", "thinking", "tool_choice") if k in body}
        data = canonical_bytes(cbody)
        r = self.t.post(self.cfg.count_tokens_url, data, 30)
        counted = None
        if r.status == 200:
            try:
                counted = int(json.loads(r.body)["input_tokens"])
            except (ValueError, KeyError):
                counted = None
        if record:
            record("token_count", {"request_id": request_id + ".count", "http_status": r.status, "error": r.error,
                                   "request_sha256": sha256_bytes(data), "input_tokens": counted,
                                   "elapsed_seconds": round(r.elapsed_s, 3), "usd": 0.0}, None, None)
        if counted is not None:
            return math.ceil(counted * COUNT_MARGIN) + COUNT_PAD, "count_tokens_endpoint"
        return len(canonical_bytes(body)) + COUNT_PAD, "utf8_byte_upper_bound"

    def create(self, request_id: str, session_id: str | None, body: dict[str, Any], budget: SessionBudget,
               deadline_remaining_s: float, record: Recorder) -> tuple[RequestRecord, dict[str, Any] | None]:
        if budget.generator_calls >= budget.max_generator_calls:
            raise BudgetDenied("generator call cap reached")
        timeout = min(self.cfg.request_timeout_s, deadline_remaining_s - 5)
        if timeout < 20:
            raise BudgetDenied("insufficient session time for a bounded provider request")
        rem = budget.remaining()
        est_in, provenance = self.count_tokens(body, request_id, record)
        max_out = min(self.cfg.max_tokens_per_request, rem["output_tokens"])
        if max_out < 1024:
            raise BudgetDenied(f"output-token ceiling leaves {max_out} tokens")
        if est_in > rem["input_tokens"]:
            raise BudgetDenied(f"input-token ceiling: need {est_in}, remaining {rem['input_tokens']}")
        body = dict(body, max_tokens=max_out)
        res_usd = self.cfg.reserve_usd(est_in, max_out)
        if res_usd > rem["usd"]:
            raise BudgetDenied(f"session USD ceiling: need {res_usd:.4f}, remaining {rem['usd']}")
        rid = self.account.reserve(self.stage_label, request_id, {"usd": res_usd, "input_tokens": est_in,
                                                                   "output_tokens": max_out, "generator_requests": 1})
        budget.reserved_input += est_in
        budget.reserved_output += max_out
        budget.reserved_usd += res_usd
        budget.generator_calls += 1
        data = canonical_bytes(body)
        pending = RequestRecord(request_id, session_id, "generator", self.cfg.requested_model, None, sha256_bytes(data), None,
                                "PENDING", 0.0, None, None, None, "unknown",
                                {"reserved": {"input_tokens": est_in, "output_tokens": max_out, "usd": res_usd},
                                 "admission_count": provenance, "sent_utc": utc_now(), "timeout_s": timeout})
        record("request_pending", pending.payload(), data, None)
        wr = self.t.post(self.cfg.endpoint, data, timeout)
        budget.reserved_input -= est_in
        budget.reserved_output -= max_out
        budget.reserved_usd -= res_usd
        details = dict(pending.details, completed_utc=utc_now(), http_status=wr.status, error=wr.error,
                       provider_request_id=wr.headers.get("request-id") or wr.headers.get("Request-Id"))
        if wr.status == 200:
            parsed: dict[str, Any] = {}
            try:
                parsed = resp = json.loads(wr.body)
                if not resp.get("model"):
                    raise ValueError("model identity not reported")
                u = resp.get("usage") or {}
                base = int(u.get("input_tokens", 0))
                cw = int(u.get("cache_creation_input_tokens") or 0)
                cr = int(u.get("cache_read_input_tokens") or 0)
                inp = base + cw + cr  # every input token counts toward the token ceilings, cached or not
                out = int(u.get("output_tokens", 0))
                if "input_tokens" not in u or "output_tokens" not in u:
                    raise ValueError("usage not reported")
                usd = self.cfg.usd(base, cw, cr, out)
                details["usage_breakdown"] = {"input": base, "cache_write": cw, "cache_read": cr, "output": out}
                if inp > est_in:
                    details["admission_overrun_tokens"] = inp - est_in
            except (ValueError, TypeError, AttributeError) as exc:
                resp, inp, out, usd = None, est_in, max_out, res_usd
                details["unusable_response"] = str(exc)
            returned = parsed.get("model") if isinstance(parsed, dict) else None
            details.update(stop_reason=resp.get("stop_reason") if resp else None, pricing_identity=self.cfg.pricing_identity)
            rec = RequestRecord(request_id, session_id, "generator", self.cfg.requested_model, returned, pending.request_sha256,
                                sha256_bytes(wr.body), "COMPLETED" if resp else "INDETERMINATE", wr.elapsed_s, inp, out, usd,
                                "provider_reported" if resp else "bounded_estimate", details)
            budget.used_input += inp
            budget.used_output += out
            budget.used_usd += usd
            self.account.settle(rid, {"usd": usd, "input_tokens": inp, "output_tokens": out, "generator_requests": 1},
                                {"status": rec.status})
            record("request_completed", rec.payload(), None, wr.body)
            if self.cfg.expected_returned_model and returned is not None and returned != self.cfg.expected_returned_model:
                raise ProviderDrift(f"generator returned {returned!r}, frozen {self.cfg.expected_returned_model!r}")
            return rec, resp
        known_reject = wr.status is not None and 400 <= wr.status < 500 and wr.status not in (408, 409, 429)
        known_unsent = not wr.sent
        if known_reject or known_unsent:
            inp = out = 0
            usd = 0.0
            status = "FAILED" if known_reject else "REJECTED_BEFORE_SEND"
            prov = "provider_reported" if known_reject else "bounded_estimate"
        else:  # 5xx, 408/409/429, timeout or lost connection after send: completion unknown
            inp, out, usd = est_in, max_out, res_usd
            status = "INDETERMINATE"
            prov = "bounded_estimate"
        budget.used_input += inp
        budget.used_output += out
        budget.used_usd += usd
        self.account.settle(rid, {"usd": usd, "input_tokens": inp, "output_tokens": out, "generator_requests": 1},
                            {"status": status})
        rec = RequestRecord(request_id, session_id, "generator", self.cfg.requested_model, None, pending.request_sha256,
                            sha256_bytes(wr.body) if wr.body else None, status, wr.elapsed_s, inp, out, usd, prov, details)
        record("request_completed", rec.payload(), None, wr.body or None)
        return rec, None


class JevClient:
    def __init__(self, transport: Transport, cfg: JevConfig, account: Any, stage_label: str = "search"):
        self.t = transport
        self.cfg = cfg
        self.account = account
        self.stage_label = stage_label

    def evaluate(self, request_id: str, session_id: str | None, state: str, question: dict[str, Any],
                 budget: SessionBudget, deadline_remaining_s: float, record: Recorder) -> tuple[RequestRecord, dict[str, Any] | None]:
        if budget.jev_evaluations >= budget.max_jev_evaluations:
            raise BudgetDenied("Jev evaluation cap reached")
        timeout = min(self.cfg.request_timeout_s, deadline_remaining_s - 5)
        if timeout < 10:
            raise BudgetDenied("insufficient session time for a bounded Jev request")
        body = {"state": state, "model": self.cfg.requested_model, "questions": {"judgment": question}}
        data = canonical_bytes(body)
        est_in = len(data) + 512  # tokens <= bytes; pad for model-side question rendering
        est_out = 256
        rem = budget.remaining()
        if est_in > rem["input_tokens"] or est_out > rem["output_tokens"]:
            raise BudgetDenied("session token ceiling for Jev evaluation")
        res_usd = _usd(est_in, est_out, self.cfg.price_input_per_mtok, self.cfg.price_output_per_mtok)
        if res_usd > rem["usd"]:
            raise BudgetDenied("session USD ceiling for Jev evaluation")
        rid = self.account.reserve(self.stage_label, request_id, {"usd": res_usd, "input_tokens": est_in,
                                                                   "output_tokens": est_out, "jev_evaluations": 1})
        budget.jev_evaluations += 1
        pending = RequestRecord(request_id, session_id, "jev", self.cfg.requested_model, None, sha256_bytes(data), None,
                                "PENDING", 0.0, None, None, None, "unknown",
                                {"reserved": {"input_tokens": est_in, "output_tokens": est_out, "usd": res_usd},
                                 "sent_utc": utc_now(), "timeout_s": timeout})
        record("request_pending", pending.payload(), data, None)
        wr = self.t.post(JEV_URL, data, timeout)
        details = dict(pending.details, completed_utc=utc_now(), http_status=wr.status, error=wr.error,
                       provider_request_id=wr.headers.get("x-typesafe-request-id"))
        resp = None
        if wr.status == 200:
            try:
                resp = json.loads(wr.body)
            except ValueError:
                resp = None
        if resp is not None:
            u = resp.get("usage") or {}
            inp = int(u.get("input_tokens", u.get("prompt_tokens", 0)) or 0)
            out = int(u.get("output_tokens", u.get("completion_tokens", 0)) or 0)
            status, prov = "COMPLETED", "provider_reported"
        elif wr.status is not None and 400 <= wr.status < 500 and wr.status not in (408, 409, 429):
            inp = out = 0
            status, prov = "FAILED", "provider_reported"
        elif not wr.sent:
            inp = out = 0
            status, prov = "REJECTED_BEFORE_SEND", "bounded_estimate"
        else:
            inp, out = est_in, est_out
            status, prov = "INDETERMINATE", "bounded_estimate"
        usd = _usd(inp, out, self.cfg.price_input_per_mtok, self.cfg.price_output_per_mtok)
        budget.used_input += inp
        budget.used_output += out
        budget.used_usd += usd
        self.account.settle(rid, {"usd": usd, "input_tokens": inp, "output_tokens": out, "jev_evaluations": 1},
                            {"status": status})
        returned = resp.get("model") if resp else None
        details["pricing_identity"] = self.cfg.pricing_identity
        rec = RequestRecord(request_id, session_id, "jev", self.cfg.requested_model, returned, pending.request_sha256,
                            sha256_bytes(wr.body) if wr.body else None, status, wr.elapsed_s, inp, out, usd, prov, details)
        record("request_completed", rec.payload(), None, wr.body or None)
        if resp is not None and self.cfg.expected_returned_model and returned != self.cfg.expected_returned_model:
            raise ProviderDrift(f"Jev returned {returned!r}, frozen {self.cfg.expected_returned_model!r}")
        return rec, resp


def parse_jev_choice(resp: dict[str, Any] | None) -> tuple[str, dict[str, Any]]:
    """Frozen parser: the typed choice or ``unknown`` (malformed/missing stays charged)."""
    if not resp:
        return "unknown", {"parse": "no response"}
    ans = (resp.get("answers") or {}).get("judgment") or {}
    choice = ans.get("choice")
    if choice not in ("supported", "contradicted", "unknown"):
        return "unknown", {"parse": f"malformed choice {choice!r}"}
    return choice, {"parse": "ok", "confidence_raw": ans.get("confidence"), "probabilities_raw": ans.get("probabilities")}


# --------------------------------------------------------------------------- fakes

class FakeGeneratorTransport:
    """Offline scripted Messages API. ``script(body) -> response dict`` (without usage/model)."""

    def __init__(self, script: Callable[[dict[str, Any]], dict[str, Any]], model: str = "fake-opus",
                 fail_with: int | None = None, returned_model: str | None = None):
        self.script = script
        self.model = model
        self.returned_model = returned_model or model
        self.fail_with = fail_with
        self.sent: list[dict[str, Any]] = []

    def post(self, url: str, payload: bytes, timeout_s: float) -> WireResult:
        body = json.loads(payload)
        if url == ANTHROPIC_COUNT_URL:
            return WireResult(200, {}, json.dumps({"input_tokens": len(payload) // 4}).encode(), 0.0)
        self.sent.append(body)
        if self.fail_with == -1:
            return WireResult(None, {}, b"", 1.0, "timeout: fake")
        if self.fail_with:
            return WireResult(self.fail_with, {}, b'{"type":"error"}', 0.1, f"HTTP {self.fail_with}")
        out = self.script(body)
        resp = {"id": f"msg_fake_{len(self.sent)}", "type": "message", "role": "assistant", "model": self.returned_model,
                "content": out["content"], "stop_reason": out.get("stop_reason", "tool_use" if any(
                    c.get("type") == "tool_use" for c in out["content"]) else "end_turn"),
                "usage": {"input_tokens": len(payload) // 4, "output_tokens": out.get("output_tokens", 300)}}
        return WireResult(200, {"request-id": f"req_fake_{len(self.sent)}"}, json.dumps(resp).encode(), 0.05)


class FakeJevTransport:
    def __init__(self, choose: Callable[[dict[str, Any]], Any] | None = None, returned_model: str = "jev-fake-1.0"):
        self.choose = choose or (lambda body: "unknown")
        self.returned_model = returned_model
        self.sent: list[dict[str, Any]] = []

    def post(self, url: str, payload: bytes, timeout_s: float) -> WireResult:
        body = json.loads(payload)
        self.sent.append(body)
        choice = self.choose(body)
        if isinstance(choice, bytes):  # raw malformed body
            return WireResult(200, {}, choice, 0.02)
        resp = {"model": self.returned_model,
                "answers": {"judgment": {"type": "choice", "choice": choice, "confidence": 0.5,
                                         "probabilities": {"supported": 0.3, "contradicted": 0.2, "unknown": 0.5}}},
                "usage": {"input_tokens": len(payload) // 4, "output_tokens": 30}}
        return WireResult(200, {"x-typesafe-request-id": f"ts_fake_{len(self.sent)}"}, json.dumps(resp).encode(), 0.02)
