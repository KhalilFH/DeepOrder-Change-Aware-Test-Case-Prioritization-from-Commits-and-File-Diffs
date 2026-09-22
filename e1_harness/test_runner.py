"""Tests for the E1 command runner and paired-block orchestration.

The runner's process execution is injected, so these tests exercise the
orchestration contract without Docker. Synthetic inputs validate the
implementation only and never enter empirical results.
"""

import tempfile
import unittest
from pathlib import Path

from ledger import Ledger, LedgerError, V_BAD, V_OK, exit_statuses_for, read_records
from policy import ACCEPT, BLOCK, P1, P3, reduce_block
from runner import (
    Attempt,
    FakeExecutor,
    Manifest,
    Runner,
    RunnerError,
)


def manifest(**kw):
    base = dict(
        episode="etcd5509",
        images={V_BAD: "etcd5509-bug", V_OK: "etcd5509-fix"},
        workdir="/go/src/github.com/coreos/etcd/clientv3/integration",
        argv=["/go/gobench.test", "-test.count", "1", "-test.run", "^TestX$"],
        timeout_s=45,
        condition="default",
    )
    base.update(kw)
    return Manifest(**base)


class RunnerTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "attempts.jsonl"

    def tearDown(self):
        self._tmp.cleanup()

    def runner(self, scripted, **mkw):
        self.executor = FakeExecutor(scripted)
        return Runner(manifest(**mkw), self.executor)


class TestManifest(unittest.TestCase):
    def test_hash_is_stable_and_content_dependent(self):
        self.assertEqual(manifest().sha256, manifest().sha256)
        self.assertNotEqual(manifest().sha256, manifest(timeout_s=46).sha256)

    def test_rejects_a_timeout_above_the_plan_ceiling(self):
        with self.assertRaises(RunnerError):
            manifest(timeout_s=121)

    def test_requires_an_image_for_both_versions(self):
        with self.assertRaises(RunnerError):
            manifest(images={V_BAD: "only-one"})


class TestSingleAttempt(RunnerTestCase):
    def test_records_the_observation_to_the_ledger(self):
        r = self.runner([Attempt(0, "ok", "")])
        with Ledger(self.path) as led:
            r.run_attempt(led, block=1, version=V_BAD, attempt=1)
        row = read_records(self.path)[0]
        self.assertEqual(row["exit_status"], 0)
        self.assertEqual(row["stdout"], "ok")
        self.assertEqual(row["version"], V_BAD)
        self.assertEqual(row["manifest_sha256"], r.manifest.sha256)

    def test_uses_the_image_of_the_version_under_test(self):
        r = self.runner([Attempt(0, "", ""), Attempt(0, "", "")])
        with Ledger(self.path) as led:
            r.run_attempt(led, block=1, version=V_BAD, attempt=1)
            r.run_attempt(led, block=1, version=V_OK, attempt=1)
        self.assertIn("etcd5509-bug", self.executor.calls[0])
        self.assertIn("etcd5509-fix", self.executor.calls[1])

    def test_each_attempt_is_a_fresh_disposable_container(self):
        # The reset recipe is "a new container per attempt"; --rm is what makes
        # it a reset rather than a reuse.
        r = self.runner([Attempt(0, "", "")])
        with Ledger(self.path) as led:
            r.run_attempt(led, block=1, version=V_BAD, attempt=1)
        argv = self.executor.calls[0]
        self.assertIn("run", argv)
        self.assertIn("--rm", argv)

    def test_a_timeout_is_recorded_as_such_and_not_as_a_clean_failure(self):
        r = self.runner([Attempt(None, "", "timed out", timed_out=True)])
        with Ledger(self.path) as led:
            r.run_attempt(led, block=1, version=V_BAD, attempt=1)
        row = read_records(self.path)[0]
        self.assertTrue(row["timed_out"])
        self.assertIsNone(row["exit_status"])

    def test_the_runner_assigns_no_category(self):
        r = self.runner([Attempt(1, "FAIL: deadlock", "")])
        with Ledger(self.path) as led:
            r.run_attempt(led, block=1, version=V_BAD, attempt=1)
        row = read_records(self.path)[0]
        self.assertNotIn("category", row)
        self.assertNotIn("categories", row)


class TestPairedBlock(RunnerTestCase):
    def test_collects_three_attempts_per_version(self):
        r = self.runner([Attempt(0, "", "")] * 6)
        with Ledger(self.path) as led:
            r.run_block(led, block=1, seed=7)
        rows = read_records(self.path)
        self.assertEqual(len(rows), 6)
        self.assertEqual(sum(1 for x in rows if x["version"] == V_BAD), 3)
        self.assertEqual(sum(1 for x in rows if x["version"] == V_OK), 3)

    def test_collects_the_research_only_suffix_even_after_a_pass(self):
        # Plan 4.4: begin and complete blocks regardless of the first outcome.
        r = self.runner([Attempt(0, "", "")] * 6)
        with Ledger(self.path) as led:
            r.run_block(led, block=1, seed=7)
        statuses = exit_statuses_for(read_records(self.path), "etcd5509", 1, V_BAD)
        self.assertEqual(statuses, [0, 0, 0])

    def test_collects_all_three_even_when_the_first_attempt_fails(self):
        r = self.runner([Attempt(1, "", "")] * 6)
        with Ledger(self.path) as led:
            r.run_block(led, block=1, seed=7)
        self.assertEqual(len(read_records(self.path)), 6)

    def test_version_order_is_randomised_and_recorded(self):
        orders = set()
        for seed in range(12):
            with tempfile.TemporaryDirectory() as d:
                p = Path(d) / "a.jsonl"
                r = self.runner([Attempt(0, "", "")] * 6)
                with Ledger(p) as led:
                    outcome = r.run_block(led, block=1, seed=seed)
                first = read_records(p)[0]["version"]
                self.assertEqual(outcome.first_version, first)
                orders.add(first)
        self.assertEqual(orders, {V_BAD, V_OK}, "both orders must occur")

    def test_the_same_seed_gives_the_same_order(self):
        def order(seed):
            with tempfile.TemporaryDirectory() as d:
                r = self.runner([Attempt(0, "", "")] * 6)
                with Ledger(Path(d) / "a.jsonl") as led:
                    return r.run_block(led, block=1, seed=seed).first_version

        self.assertEqual(order(99), order(99))

    def test_the_seed_is_recorded_on_every_attempt(self):
        r = self.runner([Attempt(0, "", "")] * 6)
        with Ledger(self.path) as led:
            r.run_block(led, block=1, seed=1234)
        self.assertTrue(all(x["seed"] == 1234 for x in read_records(self.path)))

    def test_a_block_cannot_be_recorded_twice(self):
        r = self.runner([Attempt(0, "", "")] * 12)
        with Ledger(self.path) as led:
            r.run_block(led, block=1, seed=7)
            with self.assertRaises(LedgerError):
                r.run_block(led, block=1, seed=7)


class TestDirectPolicyExecution(RunnerTestCase):
    """The 12 direct-policy checks: real early stopping, not replay."""

    def test_p1_executes_exactly_one_attempt(self):
        r = self.runner([Attempt(1, "", "")] * 3)
        with Ledger(self.path) as led:
            outcome = r.run_policy_direct(led, block=50, version=V_BAD, policy=P1)
        self.assertEqual(len(self.executor.calls), 1)
        self.assertEqual(outcome.decision.final_status, BLOCK)

    def test_p3_stops_at_the_first_pass(self):
        r = self.runner([Attempt(1, "", ""), Attempt(0, "", ""), Attempt(1, "", "")])
        with Ledger(self.path) as led:
            outcome = r.run_policy_direct(led, block=51, version=V_BAD, policy=P3)
        self.assertEqual(len(self.executor.calls), 2, "the third attempt must not run")
        self.assertEqual(outcome.decision.final_status, ACCEPT)
        self.assertEqual(outcome.decision.attempts_consumed, 2)

    def test_p3_runs_all_three_when_every_attempt_fails(self):
        r = self.runner([Attempt(1, "", "")] * 3)
        with Ledger(self.path) as led:
            outcome = r.run_policy_direct(led, block=52, version=V_BAD, policy=P3)
        self.assertEqual(len(self.executor.calls), 3)
        self.assertEqual(outcome.decision.final_status, BLOCK)

    def test_only_the_executed_attempts_reach_the_ledger(self):
        r = self.runner([Attempt(0, "", ""), Attempt(1, "", ""), Attempt(1, "", "")])
        with Ledger(self.path) as led:
            r.run_policy_direct(led, block=53, version=V_BAD, policy=P3)
        self.assertEqual(len(read_records(self.path)), 1)

    def test_direct_execution_agrees_with_replaying_the_same_trace(self):
        # This is the structural check the plan's direct-policy step exists for.
        for scripted in (
            [Attempt(0, "", "")],
            [Attempt(1, "", ""), Attempt(0, "", "")],
            [Attempt(1, "", ""), Attempt(1, "", ""), Attempt(0, "", "")],
            [Attempt(1, "", ""), Attempt(1, "", ""), Attempt(1, "", "")],
        ):
            with self.subTest(n=len(scripted)):
                with tempfile.TemporaryDirectory() as d:
                    p = Path(d) / "a.jsonl"
                    r = self.runner(list(scripted))
                    with Ledger(p) as led:
                        direct = r.run_policy_direct(led, block=1, version=V_BAD, policy=P3)
                    replayed = reduce_block(
                        P3, exit_statuses_for(read_records(p), "etcd5509", 1, V_BAD)
                    )
                    self.assertEqual(direct.decision.final_status, replayed.final_status)
                    self.assertEqual(
                        direct.decision.attempts_consumed, replayed.attempts_consumed
                    )

    def test_direct_blocks_are_kept_out_of_the_measured_block_range(self):
        r = self.runner([Attempt(0, "", "")])
        with Ledger(self.path) as led:
            with self.assertRaises(RunnerError):
                r.run_policy_direct(led, block=1, version=V_BAD, policy=P3,
                                    reserved_from=50)


class TestExecutorFailures(RunnerTestCase):
    def test_a_runner_that_runs_out_of_scripted_attempts_raises(self):
        r = self.runner([Attempt(0, "", "")])
        with Ledger(self.path) as led:
            r.run_attempt(led, block=1, version=V_BAD, attempt=1)
            with self.assertRaises(RunnerError):
                r.run_attempt(led, block=1, version=V_BAD, attempt=2)

    def test_an_executor_crash_is_recorded_as_a_null_exit_rather_than_lost(self):
        r = self.runner([Attempt(None, "", "docker: daemon not running")])
        with Ledger(self.path) as led:
            r.run_attempt(led, block=1, version=V_BAD, attempt=1)
        row = read_records(self.path)[0]
        self.assertIsNone(row["exit_status"])
        self.assertIn("daemon", row["stderr"])


if __name__ == "__main__":
    unittest.main()
