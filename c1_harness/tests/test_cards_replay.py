"""Oracle cards: E1 cards unchanged, ported cards on synthetic fixtures, replay of old logs."""

import unittest

import oracle as e1_oracle
from policy import FOCAL_DEFECT_WITNESS, HARNESS_INVALID, PASS, UNRESOLVED

from c1_harness.cards import CARDS, annotate, classify_text, rule_hashes
from c1_harness.replay import replay
from c1_harness.tests.fakes import go_fail, go_pass

G = "TestGoAwayThenClose"
I = "TestExitDuringWaitForLive"
K = "TestPopReleaseLock"


class TestRegistry(unittest.TestCase):
    def test_six_cards_and_e1_cards_are_the_same_objects(self):
        self.assertEqual(set(CARDS), {"etcd5509", "etcd7492", "grpc1859", "grpc2391", "istio17860", "k8s26980"})
        for sid in ("etcd5509", "etcd7492", "grpc1859"):
            self.assertIs(CARDS[sid], e1_oracle.CARDS[sid])

    def test_rule_hashes_are_line_ending_independent(self):
        h = rule_hashes()
        self.assertEqual(len(h["e1_oracle_py"]), 64)
        self.assertEqual(h["e1_oracle_py"], e1_oracle.oracle_sha256())


class TestPortedCards(unittest.TestCase):
    def cats(self, subject, exit_status, text):
        return classify_text(subject, exit_status, text)

    def test_grpc2391(self):
        focal = go_fail(G, "UnaryCall(_) = _, rpc error: code = DeadlineExceeded desc = context deadline exceeded; want _, nil")
        self.assertEqual(self.cats("grpc2391", 1, focal), [FOCAL_DEFECT_WITNESS])
        other = go_fail(G, "UnaryCall(_) = _, rpc error: code = Unavailable desc = x; want _, nil")
        self.assertEqual(self.cats("grpc2391", 1, other), [UNRESOLVED])
        split = go_fail(G, "UnaryCall(_) = _, rpc error: code = Unavailable") + "DeadlineExceeded\n; want _, nil\n"
        self.assertEqual(self.cats("grpc2391", 1, split), [UNRESOLVED])  # the card requires one line
        leak = go_fail(G, "Leaked goroutine: goroutine 7 [select]:")
        self.assertEqual(self.cats("grpc2391", 1, leak), [UNRESOLVED])
        self.assertEqual(self.cats("grpc2391", 0, go_pass(G)), [PASS])

    def test_istio17860(self):
        self.assertEqual(self.cats("istio17860", 1, go_fail(I, "timed out waiting for epoch 1 to start")), [FOCAL_DEFECT_WITNESS])
        temporal = go_fail(I, "Expected <time.Time>: ... to be ~ <time.Time> (BeTemporally)")
        self.assertEqual(self.cats("istio17860", 1, temporal), [UNRESOLVED])
        self.assertEqual(self.cats("istio17860", 0, go_pass(I)), [PASS])

    def test_k8s26980(self):
        self.assertEqual(self.cats("k8s26980", 1, go_fail(K, "Timeout after 30s")), [FOCAL_DEFECT_WITNESS])
        dump = f"=== RUN   {K}\npanic: test timed out after 1m0s\n\ngoroutine 1 [running]:\nmain.main()\n"
        self.assertEqual(self.cats("k8s26980", 2, dump), [UNRESOLVED])
        self.assertEqual(self.cats("k8s26980", 1, go_fail(K, "Timeout after 10s")), [UNRESOLVED])

    def test_harness_invalid_forms(self):
        for sid, test in (("grpc2391", G), ("istio17860", I), ("k8s26980", K)):
            self.assertEqual(self.cats(sid, None, go_pass(test)), [HARNESS_INVALID])  # no exit status
            self.assertEqual(self.cats(sid, 1, "--- FAIL: something\n"), [HARNESS_INVALID])  # target never ran
            self.assertEqual(self.cats(sid, 125, "docker: Error response from daemon: x"), [HARNESS_INVALID])

    def test_annotate_records_both_rule_hashes(self):
        rec = {"episode": "k8s26980", "block": 1, "version": "V_bad", "attempt": 1, "seq": 1, "sha256": "x" * 64,
               "exit_status": 1, "stdout": go_fail(K, "Timeout after 30s"), "stderr": "", "extra": {"attempt_id": "a"}}
        [a] = annotate([rec])
        self.assertEqual(a["categories"], [FOCAL_DEFECT_WITNESS])
        self.assertEqual(a["attempt_id"], "a")
        self.assertEqual(len(a["cards_sha256"]), 64)
        self.assertIn("c1-cards/1", a["oracle_version"])


class TestReplayOfHistoricalLogs(unittest.TestCase):
    """Old logs are validation inputs only; this pins the replay result."""

    @classmethod
    def setUpClass(cls):
        cls.r = replay()

    def test_every_counted_q0_attempt_agrees(self):
        s = self.r["summary"]["q0_counted"]
        self.assertEqual(sorted(s), sorted(CARDS))
        for sid, c in s.items():
            self.assertEqual((c["logs"], c["disagree"]), (40, 0), sid)

    def test_negative_fixtures_never_match(self):
        must_not = [r for r in self.r["rows"]["uncounted"] if "must not" in r["expectation"]]
        self.assertTrue(any("expired-certificate" in r["expectation"] for r in must_not))
        self.assertTrue(all(r["agree"] for r in must_not))

    def test_e1_ledgers_reclassify_identically(self):
        rows = self.r["rows"]["e1_ledgers"]
        self.assertEqual(len(rows), 332)
        self.assertTrue(all(r["agree"] for r in rows))

    def test_k8s26980_has_no_positive_example(self):
        self.assertNotIn("k8s26980", self.r["focal_positive_logs_by_subject"])


if __name__ == "__main__":
    unittest.main()
