"""End-to-end offline tests: eight-session fake batch, W1 regressions, runner pause/resume, W1 isolation."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from w2a_harness import W1_STUDY_DIR, fakes, schedule as sch
from w2a_harness.backends import FakeBackend
from w2a_harness.budget import generator_config
from w2a_harness.cli import dry_run
from w2a_harness.common import W1Error
from w2a_harness.config import design_config
from w2a_harness.ledger import ChainLedger
from w2a_harness.providers import FakeGeneratorTransport, GeneratorClient
from w2a_harness.regressions import run_all
from w2a_harness.resources import Caps, ResourceAccount
from w2a_harness.runner import RunContext, run_blocks


def ctx_for(d: Path, script=None, returned="fake-sonnet", blocks=None):
    cfg = design_config()
    acct = ResourceAccount(d / "res.jsonl", Caps.from_study_config(cfg))
    gt = FakeGeneratorTransport(script or fakes.ScenarioScript(), returned_model=returned)
    gen = GeneratorClient(gt, generator_config(cfg, "fake-sonnet"), acct)
    return RunContext(schedule=sch.build(cfg["schedule_seed"]), design=cfg, events=ChainLedger(d / "events.jsonl"), account=acct,
                      backend=FakeBackend(fakes.subject_outcome, elapsed_s=0.1), out_dir=d / "measured", launch_sha256="0" * 64,
                      generator=gen, only_blocks=blocks), gt


class EndToEnd(unittest.TestCase):
    def test_eight_session_dry_run(self):
        with tempfile.TemporaryDirectory() as d:
            r = dry_run(Path(d))
            self.assertTrue(r["ok"], r)
            self.assertEqual(r["sessions_ended"], 8)
            self.assertEqual(r["validations"], 8)
            self.assertTrue(all(r["seal_before_validation_and_scheduled_order"].values()))
            expected = {"w2a.pool162.F2": "SEALED_DISCRETIONARY", "w2a.pool162.F3": "SEALED_FINAL_CALL",
                        "w2a.k8s26980.F3": "STAGE_FAILURE_PLAN", "w2a.k8s26980.F2": "SEALED_FINAL_CALL",
                        "w2a.istio17860.F2": "FINAL_NO_SUBMIT"}
            for sid, term in expected.items():
                self.assertEqual(r["terminals"][sid], term)
            self.assertEqual(r["accounting"]["open_reservations"], 0)

    def test_w1_failure_regressions(self):
        r = run_all()
        self.assertTrue(r["ok"], [c["id"] for c in r["checks"] if not c["pass"]])
        self.assertEqual([c["id"] for c in r["checks"]], [f"R{i}" for i in range(1, 10)])

    def test_no_submission_is_not_validated(self):
        with tempfile.TemporaryDirectory() as d:
            ctx, _ = ctx_for(Path(d), blocks=["w2a.istio17860"])
            run_blocks(ctx)
            out = {r["payload"]["session_id"]: r["payload"] for r in ctx.events.rows() if r["event_type"] == "validation_outcome"}
            self.assertEqual(out["w2a.istio17860.F2"]["outcome"], "NO_SUBMISSION")
            self.assertTrue(all(s["status"] == "NOT_RUN" for s in out["w2a.istio17860.F2"]["slots"]))

    def test_provider_drift_pauses(self):
        with tempfile.TemporaryDirectory() as d:
            ctx, _ = ctx_for(Path(d), returned="claude-other", blocks=["w2a.grpc1859"])
            summary = run_blocks(ctx)
            self.assertIn("ProviderDrift", summary["stopped"])
            ended = [r["payload"] for r in ctx.events.rows() if r["event_type"] == "session_ended"]
            self.assertEqual(ended[0]["status"], "UNRESOLVED")
            self.assertFalse(any(r["event_type"] == "validation_started" for r in ctx.events.rows()))

    def test_resume_requires_review_and_never_reruns(self):
        with tempfile.TemporaryDirectory() as d:
            ctx, _ = ctx_for(Path(d), blocks=["w2a.k8s26980"])
            first = ctx.schedule["blocks"][[b["case"] for b in ctx.schedule["blocks"]].index("k8s26980")]["session_order"][0]
            sid = f"w2a.k8s26980.{first}"
            ctx.events.append("search", "session_started", sid, {})
            with self.assertRaises(W1Error):
                run_blocks(ctx)
            run_blocks(ctx, resume_note="test review")
            rows = ctx.events.rows()
            self.assertEqual(sum(1 for r in rows if r["event_type"] == "session_started" and r["entity_id"] == sid), 1)
            end = [r["payload"] for r in rows if r["event_type"] == "session_ended" and r["entity_id"] == sid]
            self.assertEqual(end[0]["terminal"], "INTERRUPTED_INDETERMINATE")

    def test_w1_study_is_not_written(self):
        watched = [W1_STUDY_DIR / "events.jsonl", W1_STUDY_DIR / "resources" / "resource_ledger.jsonl",
                   W1_STUDY_DIR / "postrun_audit" / "audit.json", W1_STUDY_DIR / "raw_seal.sha256"]
        before = {p: p.stat().st_mtime_ns for p in watched}
        with tempfile.TemporaryDirectory() as d:
            dry_run(Path(d))
        self.assertEqual(before, {p: p.stat().st_mtime_ns for p in watched})

    def test_requests_never_carry_w1_outcome_material(self):
        with tempfile.TemporaryDirectory() as d:
            ctx, gt = ctx_for(Path(d))
            run_blocks(ctx)
            first_msgs = json.dumps([b["messages"][0] for b in gt.sent])
            for marker in ("NO_SUBMISSION", "VALIDATED_WITNESS", "postrun_audit", "testWhenExhaustedBlockInterupt", "B3", "w1.pool162"):
                self.assertNotIn(marker, first_msgs)


if __name__ == "__main__":
    unittest.main()
