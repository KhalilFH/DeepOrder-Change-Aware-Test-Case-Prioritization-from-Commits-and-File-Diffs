"""Tests for the E1 direct-policy check driver (AMENDMENTS.md sections 2 and 3).

Docker is faked, so these tests exercise the driver's refusals, cost guard and
structural stops without running a container. Synthetic inputs validate the
implementation only and never enter empirical results.
"""

import collections
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

E1 = Path(__file__).resolve().parents[2] / "research_runs" / "ci_sensitivity_2026_09" / "e1"
sys.path.insert(0, str(E1))

import run_direct as rd  # noqa: E402
from ledger import V_BAD, V_OK, Ledger, read_records  # noqa: E402
from policy import P1, P3, reduce_block  # noqa: E402
from runner import Attempt, DirectOutcome, FakeExecutor, Runner  # noqa: E402

PLAN = rd.load_plan(E1 / "direct_checks_plan.json")
MANIFESTS = rd.load_manifests(E1 / "manifests.json")


def ok(status):
    return Attempt(status, f"=== RUN TestX\nexit {status}\n", "")


def scripted_for(plan, p3_trace=(1, 0)):
    """One P1 attempt per P1 check; `p3_trace` for each P3 check."""
    out = []
    for c in plan:
        out += [ok(1)] if c.policy == P1 else [ok(s) for s in p3_trace]
    return out


class FakeDocker:
    def __init__(self, info=True, images=True, names=(), leak=None):
        self._info = iter(info) if isinstance(info, (list, tuple)) else None
        self._info_default = info if self._info is None else True
        self.images = images
        self.names = list(names)
        self.leak = leak  # callable returning names to report after a check

    def info_ok(self):
        return next(self._info, True) if self._info is not None else self._info_default

    def image_present(self, image):
        return self.images

    def container_names(self):
        return self.leak() if self.leak else list(self.names)


class DriverCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.paths = {ep: root / ep / "attempts.jsonl" for ep in MANIFESTS}
        self.lines = []

    def tearDown(self):
        self._tmp.cleanup()

    def run_checks(self, executor, docker=None, **kw):
        return rd.run_checks(
            PLAN, MANIFESTS, self.paths, docker or FakeDocker(), self.lines.append,
            runner_factory=lambda m: Runner(m, executor), **kw,
        )

    def record(self, episode, block, version, statuses):
        runner = Runner(MANIFESTS[episode], FakeExecutor([ok(s) for s in statuses]))
        with Ledger(self.paths[episode]) as led:
            for i, _ in enumerate(statuses, start=1):
                runner.run_attempt(led, block, version, i)


class PlanTest(unittest.TestCase):
    def test_frozen_plan_loads_in_block_order(self):
        self.assertEqual([c.block for c in PLAN], list(range(101, 113)))
        self.assertEqual([c.episode for c in PLAN], ["etcd5509"] * 6 + ["etcd7492"] * 6)

    def test_frozen_plan_is_balanced_on_every_factor_pair(self):
        for key in (lambda c: (c.episode, c.version), lambda c: (c.episode, c.policy),
                    lambda c: (c.version, c.policy)):
            self.assertEqual(set(collections.Counter(map(key, PLAN)).values()), {3})

    def test_refuses_plan_with_another_hash(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "plan.json"
            p.write_bytes((E1 / "direct_checks_plan.json").read_bytes() + b"\n")
            with self.assertRaisesRegex(rd.DriverError, "not the frozen value"):
                rd.load_plan(p)

    def test_refuses_seed_that_breaks_the_seed_rule(self):
        doc = json.loads((E1 / "direct_checks_plan.json").read_text(encoding="utf-8"))
        doc["checks"][0]["seed"] += 1
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "plan.json"
            p.write_text(json.dumps(doc), encoding="utf-8")
            with self.assertRaisesRegex(rd.DriverError, "seed rule"):
                rd.load_plan(p, hashlib.sha256(p.read_bytes()).hexdigest())

    def test_manifests_hash_to_frozen_values(self):
        self.assertEqual(set(MANIFESTS), {"etcd5509", "etcd7492"})


class CostTest(unittest.TestCase):
    def test_hard_bounds_match_amendment(self):
        self.assertEqual(round(rd.hard_bound_vcpu_h(P1, 60), 2), 0.41)
        self.assertEqual(round(rd.hard_bound_vcpu_h(P3, 60), 2), 1.23)
        self.assertEqual(round(rd.hard_bound_vcpu_h(P1, 65), 2), 0.43)
        self.assertEqual(round(rd.hard_bound_vcpu_h(P3, 65), 2), 1.29)

    def test_cost_so_far_counts_only_direct_range_attempts(self):
        rows = [{"block": 5, "elapsed_s": 1000.0}, {"block": 101, "elapsed_s": 222.96}]
        self.assertAlmostEqual(rd.cost_so_far(rows), 10.61 + 16 * 225 / 3600)


class StoppingRuleTest(unittest.TestCase):
    def test_sound_traces(self):
        for policy, trace in [(P1, [1]), (P1, [0]), (P3, [0]), (P3, [1, 0]), (P3, [1, 1, 0]),
                              (P3, [1, 1, 1]), (P3, [None, 1, 0]), (P3, [None, None, None])]:
            self.assertEqual(rd.stopping_problems(policy, trace), [], (policy, trace))

    def test_mismatched_traces(self):
        for policy, trace in [(P1, []), (P1, [1, 0]), (P3, [0, 1]), (P3, [1]), (P3, [1, 1]),
                              (P3, [1, 1, 1, 1])]:
            self.assertNotEqual(rd.stopping_problems(policy, trace), [], (policy, trace))


class PreflightTest(unittest.TestCase):
    def test_clean_host_passes(self):
        self.assertEqual(rd.preflight(FakeDocker(), MANIFESTS), [])

    def test_docker_down_is_reported_alone(self):
        self.assertEqual(rd.preflight(FakeDocker(info=False), MANIFESTS), ["docker info failed"])

    def test_existing_containers_and_missing_images_refuse(self):
        problems = rd.preflight(FakeDocker(images=False, names=["other"]), MANIFESTS)
        self.assertEqual(sum("not present locally" in p for p in problems), 4)
        self.assertTrue(any("lists 1 container" in p for p in problems))


class RunTest(DriverCase):
    def test_full_run_executes_the_plan_in_order(self):
        ex = FakeExecutor(scripted_for(PLAN))
        self.assertEqual(self.run_checks(ex), rd.EXIT_DONE)
        self.assertEqual(self.lines[-1], "DONE")
        self.assertEqual(len(self.lines), 13)
        for c in PLAN:
            rows = [r for r in read_records(self.paths[c.episode]) if r["block"] == c.block]
            self.assertEqual({r["version"] for r in rows}, {c.version})
            self.assertEqual({r["seed"] for r in rows}, {c.seed})
            self.assertEqual(len(rows), 1 if c.policy == P1 else 2)

    def test_guard_stops_before_executing(self):
        ex = FakeExecutor([])
        self.assertEqual(self.run_checks(ex, measured=16.0), rd.EXIT_GUARD)
        self.assertEqual(ex.calls, [])
        self.assertIn("GUARD STOP before block 101", self.lines[-1])

    def test_guard_admits_a_check_just_under_the_line(self):
        first = rd.hard_bound_vcpu_h(PLAN[0].policy, MANIFESTS["etcd5509"].timeout_s)
        ex = FakeExecutor(scripted_for(PLAN[:1]))
        code = self.run_checks(ex, measured=17.0 - first - 0.001)
        self.assertEqual(code, rd.EXIT_GUARD)  # block 101 ran; its cost blocks block 102
        self.assertEqual(len(ex.calls), 2)
        self.assertIn("GUARD STOP before block 102", self.lines[-1])

    def test_docker_info_failure_stops_before_the_check(self):
        ex = FakeExecutor([])
        self.assertEqual(self.run_checks(ex, FakeDocker(info=False)), rd.EXIT_DOCKER)
        self.assertEqual(ex.calls, [])

    def test_leftover_container_is_a_structural_mismatch(self):
        ex = FakeExecutor(scripted_for(PLAN))
        leak = lambda: [c[c.index("--name") + 1] for c in ex.calls]  # noqa: E731
        self.assertEqual(self.run_checks(ex, FakeDocker(leak=leak)), rd.EXIT_MISMATCH)
        self.assertIn("containers still present", self.lines[-1])
        self.assertEqual({r["block"] for r in read_records(self.paths["etcd5509"])}, {101})

    def test_runner_breaking_the_stopping_rule_is_a_mismatch(self):
        class BadRunner:
            def run_policy_direct(self, led, block, version, policy, seed=None, reserved_from=None):
                return DirectOutcome(block, version, policy, reduce_block(P3, [0, 1]), [0, 1])

        code = rd.run_checks(PLAN, MANIFESTS, self.paths, FakeDocker(), self.lines.append,
                             runner_factory=lambda m: BadRunner())
        self.assertEqual(code, rd.EXIT_MISMATCH)
        self.assertIn("P3 continued after exit 0", self.lines[-1])
        self.assertIn("ledger disagrees", self.lines[-1])


class ResumeTest(DriverCase):
    def test_resumes_from_the_next_unrecorded_check(self):
        ex = FakeExecutor(scripted_for(PLAN))
        self.assertEqual(self.run_checks(ex, FakeDocker(info=[True, True, False])), rd.EXIT_DOCKER)
        self.assertEqual(self.run_checks(ex), rd.EXIT_DONE)
        self.assertIn("RESUME at block 103 (2 checks recorded)", self.lines)

    def test_refuses_an_unsound_recorded_check(self):
        self.record("etcd5509", 101, V_OK, [1])  # P3 stopped after one failure
        with self.assertRaisesRegex(rd.DriverError, "block 101 is recorded but unsound"):
            self.run_checks(FakeExecutor([]))

    def test_refuses_recorded_checks_that_are_not_a_prefix(self):
        self.record("etcd5509", 102, V_BAD, [0])
        with self.assertRaisesRegex(rd.DriverError, "not a prefix"):
            self.run_checks(FakeExecutor([]))

    def test_refuses_an_unplanned_direct_block(self):
        self.record("etcd5509", 107, V_BAD, [0])
        with self.assertRaisesRegex(rd.DriverError, "not in the plan"):
            self.run_checks(FakeExecutor([]))


if __name__ == "__main__":
    unittest.main()
