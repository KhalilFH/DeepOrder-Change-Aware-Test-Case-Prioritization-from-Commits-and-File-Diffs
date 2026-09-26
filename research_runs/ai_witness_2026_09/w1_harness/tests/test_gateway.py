"""Offline tests for the v1.2 generator path: OpenCode Zen (Anthropic-compatible, Bearer), caching, admission."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from w1_harness.config import design_config
from w1_harness.providers import (ANTHROPIC_COUNT_URL, AnthropicTransport, FakeGeneratorTransport, GeneratorClient,
                                  GeneratorConfig, SessionBudget, WireResult, with_cache_breakpoint)
from w1_harness.resources import Caps, ResourceAccount

ZEN = "https://opencode.ai/zen/v1/messages"


def zen_cfg(**kw):
    base = dict(endpoint=ZEN, count_tokens_url=None, price_cache_write_per_mtok=2.5, price_cache_read_per_mtok=0.2,
                prompt_caching=True)
    base.update(kw)
    return GeneratorConfig("claude-sonnet-5", "claude-sonnet-5", "medium", 4000, 120, 2.0, 10.0, "zen-test", **base)


def budget():
    s = design_config()["search"]
    return SessionBudget(s["max_input_tokens"], s["max_output_tokens"], s["max_usd"], 4, 0)


class RecordingTransport:
    def __init__(self, response: dict, status: int = 200):
        self.response = response
        self.status = status
        self.urls: list[str] = []

    def post(self, url, payload, timeout_s):
        self.urls.append(url)
        return WireResult(self.status, {}, json.dumps(self.response).encode(), 0.01)


class GatewayTests(unittest.TestCase):
    def acct(self, d):
        return ResourceAccount(Path(d) / "r.jsonl", Caps.from_study_config(design_config()))

    def test_bearer_header(self):
        t = AnthropicTransport("k-test", "bearer")
        h = t._headers()
        self.assertEqual(h["authorization"], "Bearer k-test")
        self.assertNotIn("x-api-key", h)
        self.assertIn("x-api-key", AnthropicTransport("k", "x-api-key")._headers())
        both = AnthropicTransport("k2", "both")._headers()
        self.assertEqual((both["x-api-key"], both["authorization"]), ("k2", "Bearer k2"))

    def test_local_admission_sends_no_count_request_and_prices_cache(self):
        with tempfile.TemporaryDirectory() as d:
            resp = {"model": "claude-sonnet-5", "content": [], "stop_reason": "end_turn",
                    "usage": {"input_tokens": 1000, "cache_creation_input_tokens": 8000, "cache_read_input_tokens": 0,
                              "output_tokens": 500}}
            t = RecordingTransport(resp)
            c = GeneratorClient(t, zen_cfg(), self.acct(d))
            b = budget()
            body = {"model": "claude-sonnet-5", "messages": [{"role": "user", "content": [{"type": "text", "text": "x" * 4000}]}]}
            rec, r = c.create("r1", "s", body, b, 500, lambda *a: None)
            self.assertEqual(t.urls, [ZEN])  # no count_tokens request
            self.assertNotIn(ANTHROPIC_COUNT_URL, t.urls)
            self.assertEqual(rec.details["admission_count"], "local_estimate_utf8_bytes_div_2_plus_512")
            self.assertEqual(rec.input_tokens, 9000)  # cached tokens count toward the ceiling
            self.assertAlmostEqual(rec.usd, (1000 * 2.0 + 8000 * 2.5 + 500 * 10.0) / 1e6)
            self.assertEqual(b.used_input, 9000)

    def test_missing_usage_is_indeterminate_and_charged_at_reservation(self):
        with tempfile.TemporaryDirectory() as d:
            t = RecordingTransport({"model": "claude-sonnet-5", "content": []})
            c = GeneratorClient(t, zen_cfg(), self.acct(d))
            b = budget()
            rec, r = c.create("r1", "s", {"model": "m", "messages": [{"role": "user", "content": "x"}]}, b, 500, lambda *a: None)
            self.assertEqual(rec.status, "INDETERMINATE")
            self.assertIsNone(r)
            self.assertGreater(b.used_output, 0)

    def test_cache_breakpoint_is_stable_and_does_not_edit_history(self):
        msgs = [{"role": "user", "content": [{"type": "text", "text": "packet"}]},
                {"role": "assistant", "content": [{"type": "text", "text": "a"}]},
                {"role": "user", "content": [{"type": "text", "text": "b"}]}]
        a = with_cache_breakpoint(msgs[:1])
        b = with_cache_breakpoint(msgs)
        self.assertEqual(a[0], b[0])
        self.assertEqual(b[0]["content"][-1]["cache_control"], {"type": "ephemeral"})
        self.assertNotIn("cache_control", msgs[0]["content"][-1])  # original untouched
        self.assertEqual(sum("cache_control" in blk for m in b for blk in m["content"]), 1)

    def test_session_requests_carry_one_breakpoint(self):
        from w1_harness.tests.test_sessions import make_ctx
        from w1_harness.runner import run_blocks
        with tempfile.TemporaryDirectory() as d:
            ctx, gt, jt = make_ctx(Path(d), ["w1.k8s26980.r1"])
            run_blocks(ctx)
            self.assertTrue(gt.sent)
            for body in gt.sent:
                marks = [blk for m in body["messages"] for blk in (m["content"] if isinstance(m["content"], list) else [])
                         if isinstance(blk, dict) and "cache_control" in blk]
                self.assertEqual(len(marks), 1)
                self.assertIn("cache_control", body["messages"][0]["content"][-1])
                self.assertNotIn("temperature", body)
                self.assertEqual(body["model"], "claude-sonnet-5")


if __name__ == "__main__":
    unittest.main()
