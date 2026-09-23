"""Tests for the E1 step-4 control driver (AMENDMENTS.md section 7).

Docker is faked, so these tests exercise the driver's refusals, cost guard and
structural stops without running a container. Synthetic inputs validate the
implementation only and never enter empirical results.
"""

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

E1 = Path(__file__).resolve().parents[2] / "research_runs" / "ci_sensitivity_2026_09" / "e1"
sys.path.insert(0, str(E1))

import run_controls as rc  # noqa: E402
import run_direct as rd  # noqa: E402
from ledger import V_BAD, V_OK, Ledger, read_records  # noqa: E402
from runner import Attempt, BlockOutcome, FakeExecutor, Runner  # noqa: E402

E1_MANIFESTS = rd.load_manifests(E1 / "manifests.json")
MANIFESTS = rc.load_manifests(E1 / "controls" / "manifests.json", E1_MANIFESTS)
PLAN = rc.load_plan(E1 / "controls" / "plan.json", MANIFESTS)


def ok(status):
    return Attempt(status, f"=== RUN TestX\nexit {status}\n", "")


def scripted_for(plan, status=0):
    return [ok(status) for _ in plan for _ in range(6)]


class FakeDocker:
    def __init__(self, info=True, images=True, names=(), leak=None):
        self._info = iter(info) if isinstance(info, (list, tuple)) else None
        self._info_default = info if self._info is None else True
        self.images = images
        self.names = list(names)
        self.leak = leak

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
        self.paths = {c: root / c / "attempts.jsonl" for c in MANIFESTS}
        self.lines = []

    def tearDown(self):
        self._tmp.cleanup()

    def run_controls(self, executor, docker=None, e1_records=(), **kw):
        return rc.run_controls(
            PLAN, MANIFESTS, self.paths, list(e1_records), docker or FakeDocker(), self.lines.append,
            runner_factory=lambda m: Runner(m, executor), **kw,
        )

    def record(self, control, block, version, attempts):
        runner = Runner(MANIFESTS[control], FakeExecutor([ok(0) for _ in attempts]))
        with Ledger(self.paths[control]) as led:
            for a in attempts:
                runner.run_attempt(led, block, version, a)


class PlanTest(unittest.TestCase):
    def test_frozen_plan_loads_in_control_order(self):
        self.assertEqual([(b.control, b.block) for b in PLAN], list(rc.PLAN_ORDER))
        self.assertEqual(len(PLAN), 13)

    def test_refuses_plan_with_another_hash(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "plan.json"
            p.write_bytes((E1 / "controls" / "plan.json").read_bytes() + b"\n")
            with self.assertRaisesRegex(rc.DriverError, "not the frozen value"):
                rc.load_plan(p, MANIFESTS)

    def test_refuses_seed_that_breaks_the_seed_rule(self):
        doc = json.loads((E1 / "controls" / "plan.json").read_text(encoding="utf-8"))
        doc["blocks"][0]["seed"] += 1
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "plan.json"
            p.write_text(json.dumps(doc), encoding="utf-8")
            with self.assertRaisesRegex(rc.DriverError, "seed rule"):
                rc.load_plan(p, MANIFESTS, hashlib.sha256(p.read_bytes()).hexdigest())


class ManifestTest(unittest.TestCase):
    def test_identity_manifests_put_both_roles_on_the_frozen_v_ok_image(self):
        for control, episode in rc.IDENTITY_OF.items():
            m, base = MANIFESTS[control], E1_MANIFESTS[episode]
            self.assertEqual(m.images, {V_BAD: base.images[V_OK], V_OK: base.images[V_OK]})
            self.assertEqual((m.episode, m.argv, m.timeout_s), (base.episode, base.argv, base.timeout_s))

    def test_detfail_manifest_is_the_declared_tls_variant(self):
        m = MANIFESTS["detfail_grpc1859"]
        self.assertEqual(m.episode, "grpc1859")
        self.assertNotEqual(m.images[V_BAD], m.images[V_OK])
        self.assertEqual(m.argv[-4:], ["-test.timeout", "10s", "-only_env", "tcp-tls-v1-balancer"])
        self.assertEqual(m.timeout_s, 25)

    def test_refuses_an_identity_manifest_on_the_v_bad_image(self):
        doc = json.loads((E1 / "controls" / "manifests.json").read_text(encoding="utf-8"))
        doc["identity_etcd5509"]["images"][V_BAD] = E1_MANIFESTS["etcd5509"].images[V_BAD]
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "manifests.json"
            p.write_text(json.dumps(doc), encoding="utf-8")
            tampered = rc.Manifest(**doc["identity_etcd5509"]).sha256
            frozen = {**rc.FROZEN_CONTROL_MANIFEST_SHA256, "identity_etcd5509": tampered}
            with mock.patch.object(rc, "FROZEN_CONTROL_MANIFEST_SHA256", frozen):
                with self.assertRaisesRegex(rc.DriverError, "both roles on its V_ok image"):
                    rc.load_manifests(p, E1_MANIFESTS)

    def test_refuses_a_manifest_with_another_hash(self):
        doc = json.loads((E1 / "controls" / "manifests.json").read_text(encoding="utf-8"))
        doc["detfail_grpc1859"]["timeout_s"] = 26
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "manifests.json"
            p.write_text(json.dumps(doc), encoding="utf-8")
            with self.assertRaisesRegex(rc.DriverError, "detfail_grpc1859: manifest sha256"):
                rc.load_manifests(p, E1_MANIFESTS)


class CostTest(unittest.TestCase):
    def test_block_hard_bounds_match_amendment(self):
        self.assertEqual(round(rc.block_hard_bound_vcpu_h(60), 2), 2.45)
        self.assertEqual(round(rc.block_hard_bound_vcpu_h(65), 2), 2.59)
        self.assertEqual(round(rc.block_hard_bound_vcpu_h(25), 2), 1.52)

    def test_cost_adds_control_attempts_to_e1_cost(self):
        e1 = [{"block": 5, "elapsed_s": 1000.0}, {"block": 101, "elapsed_s": 222.96}]
        controls = [{"block": 201, "elapsed_s": 7.96}]
        self.assertAlmostEqual(rc.cost_so_far(e1, controls), 10.61 + 16 * 225 / 3600 + 16 * 10 / 3600)


class RunTest(DriverCase):
    def test_full_run_executes_the_plan_in_order(self):
        ex = FakeExecutor(scripted_for(PLAN))
        self.assertEqual(self.run_controls(ex), rc.EXIT_DONE)
        self.assertEqual(self.lines[-1], "DONE")
        self.assertEqual(len(self.lines), 14)
        for b in PLAN:
            rows = [r for r in read_records(self.paths[b.control]) if r["block"] == b.block]
            self.assertEqual(len(rows), 6)
            self.assertEqual({r["seed"] for r in rows}, {b.seed})
            self.assertEqual({r["manifest_sha256"] for r in rows}, {MANIFESTS[b.control].sha256})

    def test_identity_attempts_run_the_v_ok_image_under_both_roles(self):
        ex = FakeExecutor(scripted_for(PLAN[:1]))
        self.run_controls(ex, FakeDocker(info=[True, False]))
        image = E1_MANIFESTS["etcd5509"].images[V_OK]
        self.assertEqual(len(ex.calls), 6)
        self.assertTrue(all(image in call for call in ex.calls))

    def test_guard_stops_before_executing(self):
        ex = FakeExecutor([])
        e1 = [{"block": 101, "elapsed_s": 3600 * 20 / 16}]
        self.assertEqual(self.run_controls(ex, e1_records=e1), rc.EXIT_GUARD)
        self.assertEqual(ex.calls, [])
        self.assertIn("GUARD STOP before identity_etcd5509 block 201", self.lines[-1])

    def test_guard_admits_a_block_just_under_the_line(self):
        first = rc.block_hard_bound_vcpu_h(MANIFESTS["identity_etcd5509"].timeout_s)
        spare = 20.0 - rd.MEASURED_COST_VCPU_H - first - 0.001
        e1 = [{"block": 101, "elapsed_s": spare * 3600 / 16 - rd.GAP_S}]
        ex = FakeExecutor(scripted_for(PLAN[:1]))
        self.assertEqual(self.run_controls(ex, e1_records=e1), rc.EXIT_GUARD)
        self.assertEqual(len(ex.calls), 6)  # block 201 ran; its cost blocks block 202
        self.assertIn("GUARD STOP before identity_etcd5509 block 202", self.lines[-1])

    def test_docker_info_failure_stops_before_the_block(self):
        ex = FakeExecutor([])
        self.assertEqual(self.run_controls(ex, FakeDocker(info=False)), rc.EXIT_DOCKER)
        self.assertEqual(ex.calls, [])

    def test_leftover_container_is_a_structural_mismatch(self):
        ex = FakeExecutor(scripted_for(PLAN))
        leak = lambda: [c[c.index("--name") + 1] for c in ex.calls]  # noqa: E731
        self.assertEqual(self.run_controls(ex, FakeDocker(leak=leak)), rc.EXIT_MISMATCH)
        self.assertIn("containers still present", self.lines[-1])
        self.assertEqual({r["block"] for r in read_records(self.paths["identity_etcd5509"])}, {201})

    def test_runner_recording_an_incomplete_block_is_a_mismatch(self):
        class ShortRunner:
            def __init__(self, manifest):
                self.inner = Runner(manifest, FakeExecutor([ok(0)] * 3))

            def run_block(self, led, block, seed):
                for a in (1, 2, 3):
                    self.inner.run_attempt(led, block, V_BAD, a, seed=seed)
                return BlockOutcome(block, V_BAD, seed, {V_BAD: [0, 0, 0], V_OK: [0, 0, 0]})

        code = rc.run_controls(PLAN, MANIFESTS, self.paths, [], FakeDocker(), self.lines.append,
                               runner_factory=ShortRunner)
        self.assertEqual(code, rc.EXIT_MISMATCH)
        self.assertIn("V_ok has attempts []", self.lines[-1])
        self.assertIn("ledger disagrees with the executed V_ok statuses", self.lines[-1])

    def test_statuses_are_printed_without_classification(self):
        ex = FakeExecutor(scripted_for(PLAN[:1], status=2))
        self.run_controls(ex, FakeDocker(info=[True, False]))
        self.assertRegex(self.lines[0], r'statuses=\{"V_bad": \[2, 2, 2\], "V_ok": \[2, 2, 2\]\}')


class ResumeTest(DriverCase):
    def test_resumes_from_the_next_unrecorded_block(self):
        ex = FakeExecutor(scripted_for(PLAN))
        self.assertEqual(self.run_controls(ex, FakeDocker(info=[True, True, False])), rc.EXIT_DOCKER)
        self.assertEqual(self.run_controls(ex), rc.EXIT_DONE)
        self.assertIn("RESUME at identity_etcd5509 block 203 (2 blocks recorded)", self.lines)

    def test_refuses_an_incomplete_recorded_block(self):
        self.record("identity_etcd5509", 201, V_BAD, [1, 2, 3])
        self.record("identity_etcd5509", 201, V_OK, [1])
        with self.assertRaisesRegex(rc.DriverError, "block 201 is recorded but incomplete"):
            self.run_controls(FakeExecutor([]))

    def test_refuses_recorded_blocks_that_are_not_a_prefix(self):
        self.record("identity_etcd5509", 202, V_BAD, [1])
        with self.assertRaisesRegex(rc.DriverError, "not a prefix"):
            self.run_controls(FakeExecutor([]))

    def test_refuses_an_unplanned_block(self):
        self.record("detfail_grpc1859", 201, V_BAD, [1])
        with self.assertRaisesRegex(rc.DriverError, "not in the plan"):
            self.run_controls(FakeExecutor([]))


if __name__ == "__main__":
    unittest.main()
