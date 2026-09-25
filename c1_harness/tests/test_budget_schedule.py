"""Budget admission and accounting; deterministic schedule generation."""

import hashlib
import tempfile
import unittest
from pathlib import Path

from c1_harness import STUDY_DIR, SUBJECT_ORDER
from c1_harness.budget import (
    STAGE_CAPS,
    BudgetError,
    ResourceLedger,
    attempt_reservation_vcpu_h,
    block_reservation_vcpu_h,
)
from c1_harness.schedule import BATCHES, cell_order, generate, subject_order, to_csv


class TestBudget(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ledger = ResourceLedger(Path(self.tmp.name) / "r.jsonl")

    def tearDown(self):
        self.tmp.cleanup()

    def test_caps_are_the_adopted_ones(self):
        self.assertEqual(STAGE_CAPS, {"preparation": 8.0, "validation": 6.0, "measured": 24.0, "analysis": 2.0})
        self.assertEqual(sum(STAGE_CAPS.values()), 40.0)

    def test_block_reservation_formula(self):
        # 3 * (16 + 2) * 2 * (outer + 30 + 2) / 3600
        self.assertAlmostEqual(block_reservation_vcpu_h(60), 3 * 18 * 2 * 92 / 3600)
        self.assertAlmostEqual(block_reservation_vcpu_h(120), 4.56)
        self.assertAlmostEqual(attempt_reservation_vcpu_h(16, 60), 16 * 92 / 3600)

    def test_charge_separates_allocated_and_host_reservation(self):
        row = self.ledger.charge(stage="validation", job_id="j", kind_of_job="attempt", basis_vcpus=2,
                                 basis_reason="verified L", job_elapsed_s=34.0, gap_s=2.0,
                                 started_utc="s", ended_utc="e", attempt_elapsed_s=33.0)
        self.assertAlmostEqual(row["charged_vcpu_h"], 2 * 36 / 3600)
        self.assertAlmostEqual(row["host_reservation_h"], 16 * 36 / 3600)
        self.assertIsNone(row["measured_cpu_s"])
        self.assertIn("not instrumented", row["measured_cpu_note"])

    def test_admission_refuses_beyond_the_stage_cap(self):
        self.ledger.admit("measured", "b1", 20.0)
        with self.assertRaises(BudgetError):
            self.ledger.admit("measured", "b2", 4.1)
        self.ledger.release("b1")
        self.ledger.admit("measured", "b2", 4.1)  # released capacity is available again
        self.assertAlmostEqual(self.ledger.remaining("measured"), 24.0 - 4.1)
        self.assertEqual(self.ledger.remaining("validation"), 6.0)  # nothing transfers between stages

    def test_spent_reduces_remaining_and_chain_detects_edits(self):
        self.ledger.charge(stage="measured", job_id="j", kind_of_job="a", basis_vcpus=16, basis_reason="R",
                           job_elapsed_s=3598.0, gap_s=2.0, started_utc="s", ended_utc="e")
        self.assertAlmostEqual(self.ledger.remaining("measured"), 8.0)
        self.assertEqual(self.ledger.verify(), 1)
        p = self.ledger.path
        p.write_text(p.read_text().replace('"basis_vcpus":16', '"basis_vcpus":2'), newline="\n")
        with self.assertRaises(BudgetError):
            self.ledger.verify()

    def test_duplicate_reservation_refused(self):
        self.ledger.admit("validation", "x", 0.1)
        with self.assertRaises(BudgetError):
            self.ledger.admit("validation", "x", 0.1)


class TestSchedule(unittest.TestCase):
    def test_protocol_hash_rule(self):
        order = subject_order(3, list(SUBJECT_ORDER))
        manual = sorted(SUBJECT_ORDER, key=lambda s: hashlib.sha256(f"c1-v1:subject-order:3:{s}".encode()).hexdigest())
        self.assertEqual([o["subject"] for o in order], manual)
        self.assertEqual(order[0]["string"], f"c1-v1:subject-order:3:{order[0]['subject']}")
        cells = cell_order("etcd5509", 7)
        manual_cells = sorted(((p, v) for p in "RL" for v in ("bad", "ok")),
                              key=lambda c: hashlib.sha256(f"c1-v1:cell-order:etcd5509:7:{c[0]}:{c[1]}".encode()).hexdigest())
        self.assertEqual([(c["profile"], c["variant"]) for c in cells], manual_cells)

    def test_shape_and_identity(self):
        s = generate(list(SUBJECT_ORDER))
        self.assertEqual(len(s["rows"]), 720)
        self.assertEqual(len({r["attempt_id"] for r in s["rows"]}), 720)
        self.assertEqual({r["block"] for r in s["rows"] if r["batch"] == "A"}, set(BATCHES["A"]))
        per_cell = {}
        for r in s["rows"]:
            per_cell.setdefault((r["subject"], r["block"], r["profile"], r["variant"]), []).append(r["attempt"])
        self.assertTrue(all(v == [1, 2, 3] for v in per_cell.values()))  # consecutive within a cell
        self.assertEqual(len(per_cell), 6 * 10 * 4)

    def test_deterministic_and_matches_saved_schedule(self):
        a = to_csv(generate(list(SUBJECT_ORDER))["rows"])
        b = to_csv(generate(list(SUBJECT_ORDER))["rows"])
        self.assertEqual(a, b)
        saved = STUDY_DIR / "schedule.csv"
        if saved.exists():
            self.assertEqual(saved.read_bytes().replace(b"\r\n", b"\n"), a.encode())

    def test_exclusion_moves_nothing_else(self):
        full = generate(list(SUBJECT_ORDER))["rows"]
        fewer = generate([s for s in SUBJECT_ORDER if s != "grpc1859"])["rows"]
        key = lambda rows: [(r["block"], r["subject"], r["profile"], r["variant"], r["attempt"]) for r in rows if r["subject"] != "grpc1859"]
        self.assertEqual(key(full), key(fewer))


if __name__ == "__main__":
    unittest.main()
