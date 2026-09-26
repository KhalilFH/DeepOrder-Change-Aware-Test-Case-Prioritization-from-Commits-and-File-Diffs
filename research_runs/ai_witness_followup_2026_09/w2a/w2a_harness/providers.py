"""Generator provider adapter with reservation-before-send accounting (adapted from W1 providers.py).

* ``AnthropicTransport``: raw HTTPS to an Anthropic-Messages-format endpoint (OpenCode Zen), stdlib
  only, exact request bytes recorded, no SDK retries. Fallbacks and fast mode are never requested.
* ``FakeGeneratorTransport``: scripted offline responses, including replay of recorded W1 responses.

Admission (how many tokens, which timeout) is decided by the session's reserve policy
(session.py); ``GeneratorClient.create`` re-checks the hard session and study ceilings before any
byte is sent, reserves the maximum cost, and settles provider-reported usage afterwards. One wire
request = one counted request; there is no retry. An unknown completion (timeout, 5xx, lost
connection after send) is INDETERMINATE and stays charged at its reservation. Every input token
counts toward the token ceilings, cached or not. A returned model identity different from the
frozen one raises ``ProviderDrift``.
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

ANTHROPIC_VERSION = "2023-06-01"
USER_AGENT = "w2a-harness/1.0 (research; python-urllib)"
LOCAL_ADMISSION_BYTES_PER_TOKEN = 2.0
LOCAL_ADMISSION_PAD = 512


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
    """``auth``: ``x-api-key``, ``bearer`` or ``both`` (Zen needed both headers in the W1 smoke)."""

    def __init__(self, api_key: str, auth: str = "both"):
        if not api_key:
            raise W1Error("no generator API key")
        if auth not in ("x-api-key", "bearer", "both"):
            raise W1Error(f"unknown auth style {auth!r}")
        self._key = api_key
        self._auth = auth

    def post(self, url: str, payload: bytes, timeout_s: float) -> WireResult:
        cred: dict[str, str] = {}
        if self._auth in ("x-api-key", "both"):
            cred["x-api-key"] = self._key
        if self._auth in ("bearer", "both"):
            cred["authorization"] = f"Bearer {self._key}"
        return _http_post(url, payload, {**cred, "anthropic-version": ANTHROPIC_VERSION, "content-type": "application/json"},
                          timeout_s)


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
    price_cache_write_per_mtok: float
    price_cache_read_per_mtok: float
    pricing_identity: str
    endpoint: str

    def settings_payload(self) -> dict[str, Any]:
        return {"thinking": {"type": "adaptive"}, "output_config": {"effort": self.effort}, "tool_choice": {"type": "auto"}}

    def usd(self, base_in: float, cache_write: float, cache_read: float, out: float) -> float:
        return (base_in * self.price_input_per_mtok + cache_write * self.price_cache_write_per_mtok
                + cache_read * self.price_cache_read_per_mtok + out * self.price_output_per_mtok) / 1e6

    def usd_upper(self, est_in: float, max_out: float) -> float:
        """Every input token at the dearest input rate (base or cache write)."""
        return (est_in * max(self.price_input_per_mtok, self.price_cache_write_per_mtok)
                + max_out * self.price_output_per_mtok) / 1e6


def estimate_input_tokens(body: dict[str, Any]) -> int:
    """Local admission estimate (Zen documents no token-count endpoint). W1 calibration: this
    overstated provider-reported input by 1.19-1.50x on all 119 measured requests."""
    return math.ceil(len(canonical_bytes(body)) / LOCAL_ADMISSION_BYTES_PER_TOKEN) + LOCAL_ADMISSION_PAD


def with_cache_breakpoints(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Copy with ephemeral breakpoints on the last block of the first message (stable stage prefix)
    and of the last message (incremental conversation prefix). Stored history is never edited."""
    out = [dict(m) for m in messages]
    for idx in sorted({0, len(out) - 1}):
        content = [dict(b) for b in out[idx]["content"]]
        content[-1]["cache_control"] = {"type": "ephemeral"}
        out[idx] = dict(out[idx], content=content)
    return out


@dataclass
class SessionBudget:
    max_input_tokens: int
    max_output_tokens: int
    max_usd: float
    max_generator_calls: int
    used_input: int = 0
    used_output: int = 0
    used_usd: float = 0.0
    generator_calls: int = 0
    reserved_input: int = 0
    reserved_output: int = 0
    reserved_usd: float = 0.0

    def remaining(self) -> dict[str, Any]:
        return {
            "input_tokens": self.max_input_tokens - self.used_input - self.reserved_input,
            "output_tokens": self.max_output_tokens - self.used_output - self.reserved_output,
            "usd": round(self.max_usd - self.used_usd - self.reserved_usd, 6),
            "generator_calls": self.max_generator_calls - self.generator_calls,
        }


@dataclass
class Admission:
    kind: str  # "discretionary" | "mandatory" | "final"
    est_input: int
    max_output: int
    timeout_s: float
    reserve_usd: float
    held_back: dict[str, Any] = field(default_factory=dict)


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


class GeneratorClient:
    def __init__(self, transport: Transport, cfg: GeneratorConfig, account: Any, stage_label: str = "search"):
        self.t = transport
        self.cfg = cfg
        self.account = account
        self.stage_label = stage_label

    def create(self, request_id: str, session_id: str | None, body: dict[str, Any], budget: SessionBudget,
               adm: Admission, record: Recorder) -> tuple[RequestRecord, dict[str, Any] | None]:
        rem = budget.remaining()
        if budget.generator_calls >= budget.max_generator_calls:
            raise BudgetDenied("generator call cap reached")
        if adm.est_input > rem["input_tokens"] or adm.max_output > rem["output_tokens"] or adm.max_output < 1:
            raise BudgetDenied(f"token ceiling: need {adm.est_input} in / {adm.max_output} out, remaining {rem}")
        res_usd = self.cfg.usd_upper(adm.est_input, adm.max_output)
        if res_usd > rem["usd"] + 1e-12:
            raise BudgetDenied(f"session USD ceiling: need {res_usd:.4f}, remaining {rem['usd']}")
        body = dict(body, max_tokens=adm.max_output)
        rid = self.account.reserve(self.stage_label, request_id, {"usd": res_usd, "input_tokens": adm.est_input,
                                                                   "output_tokens": adm.max_output, "generator_requests": 1})
        budget.reserved_input += adm.est_input
        budget.reserved_output += adm.max_output
        budget.reserved_usd += res_usd
        budget.generator_calls += 1
        data = canonical_bytes(body)
        pending = RequestRecord(request_id, session_id, "generator", self.cfg.requested_model, None, sha256_bytes(data), None,
                                "PENDING", 0.0, None, None, None, "unknown",
                                {"admission_kind": adm.kind, "reserved": {"input_tokens": adm.est_input, "output_tokens": adm.max_output,
                                                                          "usd": res_usd},
                                 "held_back_for_later": adm.held_back, "admission_count": "local_estimate_utf8_bytes_div_2_plus_512",
                                 "sent_utc": utc_now(), "timeout_s": round(adm.timeout_s, 3), "request_bytes": len(data)})
        record("request_pending", pending.payload(), data, None)
        wr = self.t.post(self.cfg.endpoint, data, adm.timeout_s)
        budget.reserved_input -= adm.est_input
        budget.reserved_output -= adm.max_output
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
                if "input_tokens" not in u or "output_tokens" not in u:
                    raise ValueError("usage not reported")
                base = int(u.get("input_tokens", 0))
                cw = int(u.get("cache_creation_input_tokens") or 0)
                cr = int(u.get("cache_read_input_tokens") or 0)
                inp = base + cw + cr
                out = int(u.get("output_tokens", 0))
                usd = self.cfg.usd(base, cw, cr, out)
                details["usage_breakdown"] = {"input": base, "cache_write": cw, "cache_read": cr, "output": out,
                                              "thinking": (u.get("output_tokens_details") or {}).get("thinking_tokens")}
                if inp > adm.est_input:
                    details["admission_overrun_tokens"] = inp - adm.est_input
            except (ValueError, TypeError, AttributeError) as exc:
                resp, inp, out, usd = None, adm.est_input, adm.max_output, res_usd
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
        if known_reject or not wr.sent:
            inp = out = 0
            usd = 0.0
            status = "FAILED" if known_reject else "REJECTED_BEFORE_SEND"
            prov = "provider_reported" if known_reject else "bounded_estimate"
        else:
            inp, out, usd = adm.est_input, adm.max_output, res_usd
            status, prov = "INDETERMINATE", "bounded_estimate"
        budget.used_input += inp
        budget.used_output += out
        budget.used_usd += usd
        self.account.settle(rid, {"usd": usd, "input_tokens": inp, "output_tokens": out, "generator_requests": 1},
                            {"status": status})
        rec = RequestRecord(request_id, session_id, "generator", self.cfg.requested_model, None, pending.request_sha256,
                            sha256_bytes(wr.body) if wr.body else None, status, wr.elapsed_s, inp, out, usd, prov, details)
        record("request_completed", rec.payload(), None, wr.body or None)
        return rec, None


# --------------------------------------------------------------------------- fakes

class FakeGeneratorTransport:
    """Offline scripted Messages API. ``script(body) -> response dict`` with ``content`` and optional
    ``stop_reason``/``output_tokens``/``status``/``raw`` (a complete recorded response to replay)."""

    def __init__(self, script: Callable[[dict[str, Any]], dict[str, Any]], returned_model: str = "fake-sonnet"):
        self.script = script
        self.returned_model = returned_model
        self.sent: list[dict[str, Any]] = []
        self.sent_bytes: list[int] = []

    def post(self, url: str, payload: bytes, timeout_s: float) -> WireResult:
        body = json.loads(payload)
        self.sent.append(body)
        self.sent_bytes.append(len(payload))
        out = self.script(body)
        if out.get("status") == "timeout":
            return WireResult(None, {}, b"", 1.0, "timeout: fake")
        if out.get("status"):
            return WireResult(int(out["status"]), {}, b'{"type":"error"}', 0.1, f"HTTP {out['status']}")
        if out.get("raw") is not None:
            resp = dict(out["raw"])
            resp["model"] = self.returned_model if out.get("keep_model") is not True else resp.get("model")
            return WireResult(200, {"request-id": f"req_replay_{len(self.sent)}"}, json.dumps(resp).encode(), 0.05)
        content = out["content"]
        resp = {"id": f"msg_fake_{len(self.sent)}", "type": "message", "role": "assistant", "model": self.returned_model,
                "content": content,
                "stop_reason": out.get("stop_reason", "tool_use" if any(c.get("type") == "tool_use" for c in content) else "end_turn"),
                "usage": {"input_tokens": len(payload) // 5, "output_tokens": out.get("output_tokens", 300),
                          "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}}
        return WireResult(200, {"request-id": f"req_fake_{len(self.sent)}"}, json.dumps(resp).encode(), 0.05)
