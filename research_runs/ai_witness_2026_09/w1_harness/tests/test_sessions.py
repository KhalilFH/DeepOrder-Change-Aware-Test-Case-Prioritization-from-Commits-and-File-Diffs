"""End-to-end offline tests of all five arms with fake subject and provider backends."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from w1_harness import analysis, fakes
from w1_harness.backends import FakeBackend
from w1_harness.common import W1Error, read_json
from w1_harness.config import SCHEDULE, design_config
from w1_harness.ledger import ChainLedger
from w1_harness.providers import (FakeGeneratorTransport, FakeJevTransport, GeneratorClient, GeneratorConfig,
                                  JevClient, JevConfig)
from w1_harness.resources import Caps, ResourceAccount
from w1_harness.runner import RunContext, run_blocks


def make_ctx(d: Path, blocks, returned_model="fake-opus", gen_transport=None):
    acct = ResourceAccount(d / "res.jsonl", Caps.from_study_config(design_config()))
    gt = gen_transport or FakeGeneratorTransport(fakes.generator_script, returned_model=returned_model)
    gen = GeneratorClient(gt, GeneratorConfig("claude-sonnet-5", "fake-opus", "medium", 4000, 120, 2.0, 10.0, "fake",
                                              endpoint="https://opencode.ai/zen/v1/messages", count_tokens_url=None,
                                              price_cache_write_per_mtok=2.5, price_cache_read_per_mtok=0.2,
                                              prompt_caching=True), acct)
    jt = FakeJevTransport(fakes.jev_choice)
    jev = JevClient(jt, JevConfig("jev-latest", "jev-fake-1.0", 30, 0.042, 0.0, "fake"), acct)
    ctx = RunContext(schedule=read_json(SCHEDULE), design=design_config(), events=ChainLedger(d / "events.jsonl"),
                     account=acct, backend=FakeBackend(fakes.subject_outcome, elapsed_s=0.5), out_dir=d / "measured",
                     launch_sha256="0" * 64, generator=gen, jev=jev, only_blocks=blocks)
    return ctx, gt, jt


class EndToEndTests(unittest.TestCase):
    def test_all_arms_two_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            ctx, gt, jt = make_ctx(d, ["w1.pool162.r1", "w1.k8s26980.r1"])
            summary = run_blocks(ctx)
            self.assertIsNone(summary["stopped"])
            self.assertEqual(len(summary["blocks_run"]), 2)
            rows = ctx.events.rows()
            ended = {r["entity_id"]: r["payload"] for r in rows if r["event_type"] == "session_ended"}
            self.assertEqual(len(ended), 10)
            outcomes = {r["payload"]["session_id"]: r["payload"] for r in rows if r["event_type"] == "validation_outcome"}
            self.assertEqual(len(outcomes), 10)
            # every final sealed before the first validation of its block
            for case in ("pool162", "k8s26980"):
                seal_seq = [r["sequence"] for r in rows if r["event_type"] == "final_sealed" and f".{case}." in r["entity_id"]]
                val_seq = [r["sequence"] for r in rows if r["event_type"] == "validation_started" and f".{case}." in r["entity_id"]]
                self.assertEqual(len(seal_seq), 5)
                self.assertLess(max(seal_seq), min(val_seq))
            # arms: B0 unchanged, AI arms submitted the probe; pool162 probe validates in the fake world
            self.assertEqual(outcomes["w1.pool162.r1.B2"]["outcome"], "VALIDATED_WITNESS")
            self.assertEqual(outcomes["w1.pool162.r1.B0"]["outcome"], "NO_WITNESS_WITHIN_BUDGET")
            self.assertEqual(outcomes["w1.k8s26980.r1.B3"]["outcome"], "NO_WITNESS_WITHIN_BUDGET")
            for sid, o in outcomes.items():
                self.assertEqual(sum(o["counts"]["V_bad"].values()), 15)
                self.assertEqual(sum(o["counts"]["V_ok"].values()), 15)
            # B4 used Jev (two claims, one malformed -> unknown) and at most 3 generator calls
            b4 = ended["w1.pool162.r1.B4"]["details"]
            self.assertEqual(b4["jev_evaluations"], 2)
            self.assertLessEqual(b4["generator_calls"], 3)
            judg = json.loads((d / "measured" / "w1.pool162.r1.B4" / "stages" / "judgments.json").read_text())
            self.assertEqual(judg["c2"]["judgment"], "unknown")
            self.assertEqual(judg["c1"]["judgment"], "supported")
            # fresh contexts: every stage conversation starts with a single user message
            first_msgs = [len(b["messages"]) for b in gt.sent]
            self.assertIn(1, first_msgs)
            # B1 recorded T3 inapplicability for k8s
            b1 = read_json(d / "measured" / "w1.k8s26980.r1.B1" / "final.json")
            self.assertIn("T3", b1["meta"]["inapplicable"])
            # analysis runs on the sealed records
            res = analysis.analyze(ctx.schedule, d / "events.jsonl", d / "analysis")
            self.assertEqual(res["table"]["pool162"]["B2"]["validated"], 1)
            self.assertFalse(res["complete"])
            self.assertEqual(ChainLedger(d / "events.jsonl").verify(), len(rows) + 0)

    def test_provider_drift_pauses(self):
        with tempfile.TemporaryDirectory() as d:
            ctx, gt, jt = make_ctx(Path(d), ["w1.k8s26980.r1"], returned_model="some-other-model")
            summary = run_blocks(ctx)
            self.assertIn("ProviderDrift", summary["stopped"])

    def test_resume_requires_review_and_never_reruns(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            ctx, gt, jt = make_ctx(d, ["w1.k8s26980.r1"])
            ctx.events.append("search", "session_started", "w1.k8s26980.r1.B0", {})
            with self.assertRaises(W1Error):
                run_blocks(ctx)
            run_blocks(ctx, resume_note="test review")
            rows = ctx.events.rows()
            b0_started = [r for r in rows if r["event_type"] == "session_started" and r["entity_id"] == "w1.k8s26980.r1.B0"]
            self.assertEqual(len(b0_started), 1)
            b0_end = [r["payload"] for r in rows if r["event_type"] == "session_ended" and r["entity_id"] == "w1.k8s26980.r1.B0"]
            self.assertEqual(b0_end[0]["reason_codes"], ["INTERRUPTED_INDETERMINATE"])
            outs = {r["payload"]["session_id"]: r["payload"]["outcome"] for r in rows if r["event_type"] == "validation_outcome"}
            self.assertEqual(outs["w1.k8s26980.r1.B0"], "NO_SUBMISSION")

    def test_provider_outage_is_no_submission_not_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            gt = FakeGeneratorTransport(fakes.generator_script, returned_model="fake-opus", fail_with=500)
            ctx, _, _ = make_ctx(d, ["w1.istio17860.r1"], gen_transport=gt)
            run_blocks(ctx)
            outs = {r["payload"]["session_id"]: r["payload"] for r in ctx.events.rows() if r["event_type"] == "validation_outcome"}
            for arm in ("B2", "B3", "B4"):
                self.assertEqual(outs[f"w1.istio17860.r1.{arm}"]["outcome"], "NO_SUBMISSION")
                self.assertTrue(all(s["status"] == "NOT_RUN" for s in outs[f"w1.istio17860.r1.{arm}"]["slots"]))


if __name__ == "__main__":
    unittest.main()
