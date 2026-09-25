"""Driver orchestration with a scripted executor: collection, stops, resume, budget."""

import tempfile
import unittest
from pathlib import Path

from ledger import read_records

from c1_harness.budget import ResourceLedger
from c1_harness.driver import (
    Context,
    EventLog,
    StopAll,
    calibration_plan,
    ledger_path,
    recorded_attempt_ids,
    run_direct,
    run_helpers,
    run_identity,
    run_measured_batch,
)
from c1_harness.schedule import generate
from c1_harness.subjects import V_BAD, V_OK
from c1_harness.tests.fakes import K8S_FOCAL, K8S_PASS, FakeExecutor, go_pass, probe_aware, subject

ISTIO_PASS = go_pass("TestExitDuringWaitForLive")


def default_script(spec):
    if spec.image.startswith("sha256:bbb") and "k8s" in spec.name:
        return 1, K8S_FOCAL, False
    return 0, (K8S_PASS if "k8s" in spec.name else ISTIO_PASS), False


class DriverCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.subjects = {"k8s26980": subject("k8s26980"), "istio17860": subject("istio17860", outer=60)}
        self.rows = generate(list(self.subjects))["rows"]

    def tearDown(self):
        self.tmp.cleanup()

    def ctx(self, executor):
        return Context(study_dir=self.dir, executor=executor, budget=ResourceLedger(self.dir / "r.jsonl"),
                       events=EventLog(self.dir / "events.jsonl"), sleep=lambda s: None,
                       host_load=lambda: {"host_load_percent": 5})


class TestMeasuredBatch(DriverCase):
    def test_full_triples_regardless_of_outcome(self):
        ex = FakeExecutor(probe_aware(default_script))
        ctx = self.ctx(ex)
        run_measured_batch(ctx, "A", self.subjects, self.rows, log=lambda s: None)
        for sid in self.subjects:
            for p in ("R", "L"):
                recs = read_records(ledger_path(ctx, "measured", sid, p))
                self.assertEqual(len(recs), 30)  # 5 blocks x 2 variants x 3 attempts
                self.assertTrue(all(r["condition"] == p and r["episode"] == sid for r in recs))
        bad = [r for r in read_records(ledger_path(ctx, "measured", "k8s26980", "R")) if r["version"] == V_BAD]
        self.assertTrue(all(r["exit_status"] == 1 for r in bad))  # no stop after a failure: suffix collected
        self.assertEqual(len(recorded_attempt_ids(ctx, "measured")), 120)
        self.assertEqual(ctx.budget.open_reservations(), {})
        kinds = [e["kind"] for e in ctx.events.rows()]
        self.assertEqual(kinds[0], "session_start")
        self.assertEqual(kinds[-1], "session_end")
        charges = [r for r in ctx.budget.rows() if r["kind"] == "charge" and r["job_kind"] == "attempt:measured"]
        self.assertEqual({r["basis_vcpus"] for r in charges if "-L-" in r["job_id"]}, {2})
        self.assertEqual({r["basis_vcpus"] for r in charges if "-R-" in r["job_id"]}, {16})

    def test_order_follows_the_schedule(self):
        ex = FakeExecutor(probe_aware(default_script))
        ctx = self.ctx(ex)
        run_measured_batch(ctx, "A", self.subjects, self.rows, log=lambda s: None)
        executed = [s.attempt_id for s in ex.runs if s.attempt_id.startswith("c1v1-measured-")]
        scheduled = [r["attempt_id"] for r in self.rows if r["batch"] == "A"]
        self.assertEqual(executed, scheduled)

    def test_unverified_profile_stops_everything(self):
        ex = FakeExecutor(probe_aware(default_script), verified=False)
        ctx = self.ctx(ex)
        with self.assertRaises(StopAll):
            run_measured_batch(ctx, "A", self.subjects, self.rows, log=lambda s: None)
        self.assertEqual(len(recorded_attempt_ids(ctx, "measured")), 1)  # the affected attempt is preserved
        self.assertEqual(ctx.events.rows()[-1]["outcome"], "stopped")
        self.assertEqual(ctx.budget.open_reservations(), {})

    def test_leftover_or_foreign_container_stops_before_work(self):
        for kw in ({"leftovers": ["abc"]}, {"running": [{"id": "x", "name": "user", "image": "y"}]}):
            with self.subTest(**{k: str(v) for k, v in kw.items()}):
                ex = FakeExecutor(probe_aware(default_script), **kw)
                ctx = Context(study_dir=self.dir / str(len(kw)), executor=ex, budget=ResourceLedger(self.dir / f"r{id(kw)}.jsonl"),
                              events=EventLog(self.dir / f"e{id(kw)}.jsonl"), sleep=lambda s: None, host_load=lambda: {})
                with self.assertRaises(StopAll):
                    run_measured_batch(ctx, "A", self.subjects, self.rows, log=lambda s: None)
                self.assertEqual(ex.runs, [])  # nothing starts, not even the probe helpers

    def test_acceptable_variant_focal_pauses_the_subject(self):
        def script(spec):
            if "k8s" in spec.name and spec.image.startswith("sha256:fff") and "-b2-" in spec.name:
                return 1, K8S_FOCAL, False
            return default_script(spec)

        ex = FakeExecutor(probe_aware(script))
        ctx = self.ctx(ex)
        run_measured_batch(ctx, "A", self.subjects, self.rows, log=lambda s: None)
        paused = [e for e in ctx.events.rows() if e["kind"] == "subject_paused"]
        self.assertEqual([e["subject"] for e in paused], ["k8s26980"])
        k8s_blocks = {int(r["block"]) for r in read_records(ledger_path(ctx, "measured", "k8s26980", "R"))}
        self.assertNotIn(3, k8s_blocks)
        istio = read_records(ledger_path(ctx, "measured", "istio17860", "R"))
        self.assertEqual(len(istio), 30)  # other subjects continue

    def test_resume_requires_review_and_never_repeats(self):
        calls = {"n": 0}

        class Interrupting(FakeExecutor):
            def run(self, spec, t, **kw):
                res = super().run(spec, t, **kw)
                if spec.attempt_id.startswith("c1v1-measured-"):
                    calls["n"] += 1
                    if calls["n"] == 20:
                        res.cleanup = {"verified_absent": False}
                return res

        ex = Interrupting(probe_aware(default_script))
        ctx = self.ctx(ex)
        with self.assertRaises(StopAll):
            run_measured_batch(ctx, "A", self.subjects, self.rows, log=lambda s: None)
        first = recorded_attempt_ids(ctx, "measured")
        self.assertEqual(len(first), 20)
        with self.assertRaises(StopAll):
            run_measured_batch(ctx, "A", self.subjects, self.rows, log=lambda s: None)  # no review note
        ex2 = FakeExecutor(probe_aware(default_script))
        ctx2 = self.ctx(ex2)
        run_measured_batch(ctx2, "A", self.subjects, self.rows, resume_review="reviewed: cleanup failure", log=lambda s: None)
        rerun = [s.attempt_id for s in ex2.runs if s.attempt_id.startswith("c1v1-measured-")]
        self.assertFalse(set(rerun) & first)
        incomplete = [e for e in ctx2.events.rows() if e["kind"] == "block_incomplete"]
        self.assertEqual(len(incomplete), 1)  # the partly collected matched block stays incomplete
        total = recorded_attempt_ids(ctx2, "measured")
        self.assertEqual(len(total), 120 - (12 - 8))  # 20 = 12 + 8: second block's last 4 attempts missing

    def test_batch_b_requires_gate_a(self):
        ctx = self.ctx(FakeExecutor(probe_aware(default_script)))
        with self.assertRaises(StopAll):
            run_measured_batch(ctx, "B", self.subjects, self.rows, log=lambda s: None)

    def test_budget_exhaustion_stops(self):
        ctx = self.ctx(FakeExecutor(probe_aware(default_script)))
        ctx.budget.admit("measured", "hog", 22.0)
        with self.assertRaises(StopAll):
            run_measured_batch(ctx, "A", self.subjects, self.rows, log=lambda s: None)
        self.assertIn("budget", ctx.events.rows()[-2]["reason"])

    def test_dry_run_never_executes(self):
        ex = FakeExecutor(probe_aware(default_script))
        plan = run_measured_batch(self.ctx(ex), "A", self.subjects, self.rows, dry_run=True)
        self.assertEqual(ex.runs, [])
        self.assertEqual(len(plan["plan"]), 10)
        self.assertEqual(plan["plan"][0]["status"], "to run")
        self.assertEqual(plan["plan"][0]["first_docker_create"][:2], ["docker", "create"])


class TestCalibrationStages(DriverCase):
    def test_direct_checks_stop_early_and_match_replay(self):
        ex = FakeExecutor(probe_aware(default_script))
        ctx = self.ctx(ex)
        ctx.enforcement_verified = True
        plan = calibration_plan(self.subjects)
        out = run_direct(ctx, self.subjects[plan["first_structurally_ready_subject"]], plan["direct"], log=lambda s: None)
        self.assertEqual(len(out), 8)
        self.assertTrue(all(r["decision_match"] and r["stopping_rule_respected"] for r in out))
        lengths = {(r["policy"], r["variant"]): len(r["executed"]) for r in out}
        self.assertEqual(lengths[("P1", "bad")], 1)
        self.assertEqual(lengths[("P3", "bad")], 3)
        self.assertEqual(lengths[("P3", "ok")], 1)  # accept-on-pass: attempts 2-3 never run

    def test_identity_uses_the_acceptable_image_in_both_slots(self):
        ex = FakeExecutor(probe_aware(default_script))
        ctx = self.ctx(ex)
        plan = calibration_plan(self.subjects)
        s = self.subjects[plan["first_structurally_ready_subject"]]
        run_identity(ctx, s, plan["identity"], log=lambda x: None)
        self.assertEqual({spec.image for spec in ex.runs}, {s.images[V_OK]})
        versions = {r["version"] for p in ("R", "L") for r in read_records(ledger_path(ctx, "identity", s.sid, p))}
        self.assertEqual(versions, {V_BAD, V_OK})

    def test_helpers(self):
        def script(spec):
            if "touch" in spec.argv[-1]:
                return 0, "WROTE h1\n", False
            return None, "ABSENT\nHOST h2\n", True

        ctx = self.ctx(FakeExecutor(script))
        out = run_helpers(ctx, log=lambda s: None)
        self.assertEqual(len(out), 4)
        self.assertTrue(all(r["passed"] for r in out))

    def test_calibration_plan_counts(self):
        plan = calibration_plan(self.subjects)
        self.assertEqual(plan["max_primitive_attempts"], {"smoke": 8, "identity": 12, "direct": 16, "helpers": 4})


if __name__ == "__main__":
    unittest.main()
