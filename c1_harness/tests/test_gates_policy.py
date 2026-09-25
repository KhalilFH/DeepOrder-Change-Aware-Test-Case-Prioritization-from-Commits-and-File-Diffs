"""Batch-A gate, and an exhaustive policy truth table over every 3-attempt prefix."""

import itertools
import json
import tempfile
import unittest
from pathlib import Path

from policy import ACCEPT, ACCEPT_WITH_PRIOR_FAILURE, BLOCK, INDETERMINATE, P1, P3, P3_RETAIN, reduce_block

from c1_harness.budget import ResourceLedger
from c1_harness.driver import Context, EventLog, ledger_path, run_measured_batch
from c1_harness.gates import gate_a, record_gate_a
from c1_harness.schedule import generate
from c1_harness.tests.fakes import K8S_FOCAL, K8S_PASS, FakeExecutor, go_pass, probe_aware, subject


def expected(policy, statuses):
    """Independent statement of the frozen policy semantics."""
    budget = 1 if policy == P1 else 3
    failures = 0
    for i in range(budget):
        if i >= len(statuses) or statuses[i] is None:
            return INDETERMINATE, i + (0 if i >= len(statuses) else 1), None
        if statuses[i] == 0:
            flag = ACCEPT_WITH_PRIOR_FAILURE if (policy == P3_RETAIN and failures) else None
            return ACCEPT, i + 1, flag
        failures += 1
    return BLOCK, budget, None


class TestPolicyTruthTable(unittest.TestCase):
    def test_every_prefix(self):
        for n in range(0, 4):
            for statuses in itertools.product((0, 1, None), repeat=n):
                for policy in (P1, P3, P3_RETAIN):
                    d = reduce_block(policy, list(statuses))
                    status, consumed, flag = expected(policy, list(statuses))
                    with self.subTest(policy=policy, statuses=statuses):
                        self.assertEqual(d.final_status, status)
                        self.assertEqual(d.attempts_consumed, consumed)
                        self.assertEqual(d.report_flag, flag)
                        self.assertEqual(d.research_only_indices, tuple(range(d.attempts_consumed + 1, n + 1)))


class TestGateA(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.subjects = {"k8s26980": subject("k8s26980"), "istio17860": subject("istio17860", outer=60)}
        self.rows = generate(list(self.subjects))["rows"]

    def tearDown(self):
        self.tmp.cleanup()

    def run_a(self, script):
        ctx = Context(study_dir=self.dir, executor=FakeExecutor(probe_aware(script)),
                      budget=ResourceLedger(self.dir / "r.jsonl"), events=EventLog(self.dir / "e.jsonl"),
                      sleep=lambda s: None, host_load=lambda: {})
        run_measured_batch(ctx, "A", self.subjects, self.rows, log=lambda s: None)
        return ctx

    def test_clean_batch_passes_and_computes_no_effects(self):
        def script(spec):
            if "k8s" in spec.name:
                return (1, K8S_FOCAL, False) if spec.image.startswith("sha256:bbb") else (0, K8S_PASS, False)
            return 0, go_pass("TestExitDuringWaitForLive"), False

        ctx = self.run_a(script)
        r = gate_a(ctx, self.subjects, self.rows)
        self.assertTrue(r["integrity_passed"], r["integrity_problems"])
        self.assertFalse(r["effects_computed"])
        self.assertFalse({"S", "primary_delta_S", "retry_loss", "estimate"} & set(json.dumps(r).split('"')))
        self.assertTrue(all(not d["stop_subject"] and d["missing"] == 0 for d in r["subjects"]))
        record_gate_a(ctx.events, r)
        self.assertEqual(ctx.events.rows()[-1]["kind"], "gate_a")

    def test_invalid_fraction_above_ten_percent_stops_the_subject(self):
        def script(spec):
            if "k8s" in spec.name and "-L-" in spec.name:
                return None, "", True  # outer timeout: no exit status -> HARNESS_INVALID
            if "k8s" in spec.name:
                return 0, K8S_PASS, False
            return 0, go_pass("TestExitDuringWaitForLive"), False

        ctx = self.run_a(script)
        r = gate_a(ctx, self.subjects, self.rows)
        k8s = next(d for d in r["subjects"] if d["subject"] == "k8s26980")
        self.assertEqual(k8s["harness_invalid"], 30)
        self.assertTrue(k8s["stop_subject"])
        record_gate_a(ctx.events, r)
        self.assertIn("subject_stopped", [e["kind"] for e in ctx.events.rows()])

    def test_gate_cannot_precede_batch_a(self):
        ctx = Context(study_dir=self.dir, executor=FakeExecutor(lambda s: (0, "", False)),
                      budget=ResourceLedger(self.dir / "r.jsonl"), events=EventLog(self.dir / "e.jsonl"),
                      sleep=lambda s: None, host_load=lambda: {})
        r = gate_a(ctx, self.subjects, self.rows)
        self.assertFalse(r["integrity_passed"])

    def test_tampered_ledger_fails_integrity(self):
        ctx = self.run_a(lambda spec: (0, K8S_PASS if "k8s" in spec.name else go_pass("TestExitDuringWaitForLive"), False))
        p = ledger_path(ctx, "measured", "istio17860", "R")
        p.write_text(p.read_text().replace('"exit_status":0', '"exit_status":1', 1), newline="\n")
        r = gate_a(ctx, self.subjects, self.rows)
        self.assertFalse(r["integrity_passed"])


if __name__ == "__main__":
    unittest.main()
