"""Profile arguments, inspection agreement, probes, and the container executor."""

import unittest

from c1_harness.dockerexec import ContainerSpec, DockerExecutor
from c1_harness.profiles import (
    GOMAXPROCS,
    L,
    PROFILES,
    R,
    evaluate_cgroup_probe,
    evaluate_go_probe,
    verify_inspect,
)
from c1_harness.tests.fakes import PROBE_OK, FakeCLI, inspect_doc

IMG = "sha256:" + "1" * 64
ARGV = ["/go/gobench.test", "-test.v", "-test.count", "1"]


class TestProfileArguments(unittest.TestCase):
    def test_only_cpu_arguments_differ(self):
        self.assertEqual(R.docker_args, ("-e", "GOMAXPROCS=16"))
        self.assertEqual(L.docker_args, ("--cpu-period=100000", "--cpu-quota=200000", "-e", "GOMAXPROCS=16"))
        self.assertEqual(R.docker_args[-2:], L.docker_args[-2:])

    def test_frozen_values(self):
        self.assertEqual((R.cpu_quota, R.cpu_period, R.allocated_vcpus), (0, 0, 16))
        self.assertEqual((L.cpu_quota, L.cpu_period, L.allocated_vcpus), (200000, 100000, 2))
        self.assertEqual(GOMAXPROCS, "16")
        self.assertEqual(set(PROFILES), {"R", "L"})

    def test_create_argv_is_literal_and_labelled(self):
        spec = ContainerSpec(name="n1", image=IMG, workdir="/w", argv=tuple(ARGV + ["-test.run", "^T$"]),
                             profile=L, attempt_id="a1", stage="smoke")
        argv = spec.create_argv()
        self.assertEqual(argv[:4], ["docker", "create", "--name", "n1"])
        self.assertIn("c1.attempt=a1", argv)
        self.assertEqual(argv[-7:], [IMG, *ARGV, "-test.run", "^T$"])
        self.assertIn("^T$", argv)  # regexp passed through untouched, no shell
        self.assertNotIn("--rm", argv)


class TestInspectVerification(unittest.TestCase):
    def check(self, profile, **overrides):
        doc = inspect_doc(profile, IMG, ARGV, "/w", **overrides)
        return verify_inspect(profile, doc, image_id=IMG, argv=ARGV, workdir="/w")

    def test_matching_configurations_pass(self):
        self.assertEqual(self.check(R), [])
        self.assertEqual(self.check(L), [])

    def test_label_alone_is_not_enforcement(self):
        doc = inspect_doc(R, IMG, ARGV, "/w")  # created without quota
        self.assertTrue(verify_inspect(L, doc, image_id=IMG, argv=ARGV, workdir="/w"))

    def test_each_deviation_is_caught(self):
        for key, value in (("HostConfig__CpuQuota", 100000), ("HostConfig__NanoCpus", 2_000_000_000),
                           ("HostConfig__CpusetCpus", "0-1"), ("HostConfig__Memory", 1 << 30),
                           ("Config__Env", ["GOMAXPROCS=2"]), ("Config__Env", []),
                           ("Config__Env", ["GOMAXPROCS=16", "GOMAXPROCS=16"]),
                           ("Config__Cmd", ARGV[:-1]), ("Config__WorkingDir", "/x"), ("Image", "sha256:x")):
            with self.subTest(key=key, value=value):
                if key == "Image":
                    doc = inspect_doc(L, "sha256:x", ARGV, "/w")
                    self.assertTrue(verify_inspect(L, doc, image_id=IMG, argv=ARGV, workdir="/w"))
                else:
                    self.assertTrue(self.check(L, **{key: value}))


class TestProbes(unittest.TestCase):
    def test_probe_fixtures(self):
        self.assertTrue(evaluate_cgroup_probe(R, PROBE_OK["R"])["passed"])
        l = evaluate_cgroup_probe(L, PROBE_OK["L"])
        self.assertTrue(l["passed"], l)
        self.assertAlmostEqual(l["observed_cpus"], 2.017, places=2)

    def test_probe_failures(self):
        self.assertFalse(evaluate_cgroup_probe(L, PROBE_OK["R"])["passed"])  # no quota
        self.assertFalse(evaluate_cgroup_probe(R, PROBE_OK["L"])["passed"])
        unthrottled = PROBE_OK["L"].replace("AFTER_nr_throttled=30", "AFTER_nr_throttled=0")
        self.assertFalse(evaluate_cgroup_probe(L, unthrottled)["passed"])
        self.assertFalse(evaluate_cgroup_probe(L, "garbage")["passed"])

    def test_go_probe(self):
        good = "GO_VERSION=go1.10.8\nGO_GOMAXPROCS=16\nGO_NUMCPU=16\nGO_ENV=16\nCPU_MAX=200000 100000\n"
        self.assertTrue(evaluate_go_probe(L, good)["passed"])
        self.assertFalse(evaluate_go_probe(L, good.replace("GO_GOMAXPROCS=16", "GO_GOMAXPROCS=2"))["passed"])
        self.assertFalse(evaluate_go_probe(R, good)["passed"])


class TestExecutor(unittest.TestCase):
    def spec(self, profile=L):
        return ContainerSpec(name="n1", image=IMG, workdir="/w", argv=tuple(ARGV), profile=profile,
                             attempt_id="a1", stage="t")

    def test_normal_attempt(self):
        cli = FakeCLI(inspect=inspect_doc(L, IMG, ARGV, "/w"), start=1, stdout=b"hello")
        res = DockerExecutor(run=cli).run(self.spec(), 60)
        self.assertEqual(res.exit_status, 1)
        self.assertTrue(res.profile_verified)
        self.assertTrue(res.cleanup_ok)
        self.assertEqual(res.stdout, "hello")
        order = [c[1] for c in cli.calls]
        self.assertEqual(order, ["create", "inspect", "start", "inspect", "rm", "ps"])
        self.assertEqual(cli.removed, {"cid123"})

    def test_unverified_profile_never_starts(self):
        cli = FakeCLI(inspect=inspect_doc(R, IMG, ARGV, "/w"))  # daemon applied no quota
        res = DockerExecutor(run=cli).run(self.spec(L), 60)
        self.assertFalse(res.profile_verified)
        self.assertTrue(res.profile_problems)
        self.assertIsNone(res.exit_status)
        self.assertNotIn("start", [c[1] for c in cli.calls])
        self.assertEqual(cli.removed, {"cid123"})

    def test_timeout_removes_only_its_own_container(self):
        cli = FakeCLI(inspect=inspect_doc(L, IMG, ARGV, "/w"), start="timeout")
        res = DockerExecutor(run=cli).run(self.spec(), 5)
        self.assertTrue(res.timed_out)
        self.assertIsNone(res.exit_status)
        self.assertEqual(res.stdout, "partial")
        rms = [c for c in cli.calls if c[1] == "rm"]
        self.assertEqual(rms, [["docker", "rm", "-f", "cid123"]])

    def test_cleanup_failure_is_reported(self):
        cli = FakeCLI(inspect=inspect_doc(L, IMG, ARGV, "/w"), start=0, absent_after_rm=False)
        res = DockerExecutor(run=cli).run(self.spec(), 60)
        self.assertFalse(res.cleanup_ok)

    def test_create_failure(self):
        cli = FakeCLI(inspect=inspect_doc(L, IMG, ARGV, "/w"), create_rc=125)
        res = DockerExecutor(run=cli).run(self.spec(), 60)
        self.assertIsNone(res.exit_status)
        self.assertTrue(res.error.startswith("docker create failed"))
        self.assertNotIn("start", [c[1] for c in cli.calls])


if __name__ == "__main__":
    unittest.main()
