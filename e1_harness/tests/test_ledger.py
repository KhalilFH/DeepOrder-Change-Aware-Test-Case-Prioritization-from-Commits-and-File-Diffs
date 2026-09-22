"""Tests for the append-only attempt ledger."""

import json
import tempfile
import unittest
from pathlib import Path

from ledger import (
    AttemptRecord,
    Ledger,
    LedgerError,
    V_BAD,
    V_OK,
    read_records,
    verify_chain,
)


def rec(block=1, version=V_BAD, attempt=1, exit_status=0, **kw):
    base = dict(
        episode="etcd5509",
        block=block,
        version=version,
        attempt=attempt,
        exit_status=exit_status,
        started_utc="2026-09-22T10:00:00.000000Z",
        ended_utc="2026-09-22T10:00:01.000000Z",
        elapsed_s=1.0,
        timed_out=False,
        condition="default",
        seed=1234,
        manifest_sha256="a" * 64,
        runner_version="e1-runner/1",
        stdout="ok\n",
        stderr="",
    )
    base.update(kw)
    return AttemptRecord(**base)


class LedgerTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "attempts.jsonl"

    def tearDown(self):
        self._tmp.cleanup()


class TestAppendOnly(LedgerTestCase):
    def test_writes_one_json_line_per_attempt(self):
        with Ledger(self.path) as led:
            led.append(rec(attempt=1))
            led.append(rec(attempt=2, exit_status=1))
        lines = self.path.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(json.loads(lines[0])["attempt"], 1)

    def test_reopening_appends_rather_than_truncating(self):
        with Ledger(self.path) as led:
            led.append(rec(attempt=1))
        with Ledger(self.path) as led:
            led.append(rec(attempt=2))
        self.assertEqual(len(read_records(self.path)), 2)

    def test_sequence_numbers_are_monotonic_across_reopen(self):
        with Ledger(self.path) as led:
            led.append(rec(attempt=1))
        with Ledger(self.path) as led:
            led.append(rec(attempt=2))
        self.assertEqual([r["seq"] for r in read_records(self.path)], [1, 2])

    def test_there_is_no_update_or_delete_api(self):
        # The strongest enforcement of append-only is the absence of the verbs.
        for verb in ("update", "delete", "remove", "overwrite", "truncate", "edit"):
            self.assertFalse(hasattr(Ledger, verb), f"Ledger should not expose {verb}")

    def test_duplicate_attempt_identity_is_refused(self):
        with Ledger(self.path) as led:
            led.append(rec(block=1, version=V_BAD, attempt=1))
            with self.assertRaises(LedgerError):
                led.append(rec(block=1, version=V_BAD, attempt=1))

    def test_duplicate_detection_survives_reopen(self):
        with Ledger(self.path) as led:
            led.append(rec(block=1, version=V_BAD, attempt=1))
        with Ledger(self.path) as led:
            with self.assertRaises(LedgerError):
                led.append(rec(block=1, version=V_BAD, attempt=1))

    def test_same_attempt_number_on_the_other_version_is_fine(self):
        with Ledger(self.path) as led:
            led.append(rec(version=V_BAD, attempt=1))
            led.append(rec(version=V_OK, attempt=1))
        self.assertEqual(len(read_records(self.path)), 2)


class TestTamperEvidence(LedgerTestCase):
    def test_chain_verifies_on_an_untouched_ledger(self):
        with Ledger(self.path) as led:
            for i in (1, 2, 3):
                led.append(rec(attempt=i))
        verify_chain(self.path)  # must not raise

    def test_editing_a_record_breaks_the_chain(self):
        with Ledger(self.path) as led:
            for i in (1, 2, 3):
                led.append(rec(attempt=i, exit_status=1))
        lines = self.path.read_text(encoding="utf-8").splitlines()
        first = json.loads(lines[0])
        first["exit_status"] = 0  # a failure quietly turned into a pass
        lines[0] = json.dumps(first)
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        with self.assertRaises(LedgerError):
            verify_chain(self.path)

    def test_deleting_a_record_breaks_the_chain(self):
        with Ledger(self.path) as led:
            for i in (1, 2, 3):
                led.append(rec(attempt=i))
        lines = self.path.read_text(encoding="utf-8").splitlines()
        del lines[1]
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        with self.assertRaises(LedgerError):
            verify_chain(self.path)

    def test_appending_after_a_verified_prefix_still_verifies(self):
        with Ledger(self.path) as led:
            led.append(rec(attempt=1))
        verify_chain(self.path)
        with Ledger(self.path) as led:
            led.append(rec(attempt=2))
        verify_chain(self.path)


class TestWhatIsRetained(LedgerTestCase):
    def test_retains_everything_the_plan_requires(self):
        with Ledger(self.path) as led:
            led.append(rec(exit_status=1, stdout="out", stderr="err", timed_out=True))
        r = read_records(self.path)[0]
        for field in (
            "exit_status", "stdout", "stderr", "elapsed_s", "timed_out",
            "started_utc", "ended_utc", "condition", "seed",
            "manifest_sha256", "runner_version", "episode", "block",
            "version", "attempt",
        ):
            self.assertIn(field, r, f"plan 4.2 requires {field} to be retained")

    def test_carries_no_oracle_annotation(self):
        # Classification is a separate evaluator step (plan 4.2). A runner that
        # wrote categories here would be adjudicating at capture time.
        with Ledger(self.path) as led:
            led.append(rec())
        r = read_records(self.path)[0]
        for forbidden in ("category", "categories", "classification", "verdict", "focal"):
            self.assertNotIn(forbidden, r)

    def test_a_harness_invalid_attempt_records_a_null_exit_status(self):
        with Ledger(self.path) as led:
            led.append(rec(exit_status=None, stderr="container failed to start"))
        self.assertIsNone(read_records(self.path)[0]["exit_status"])

    def test_rejects_an_unknown_version_label(self):
        with self.assertRaises(LedgerError):
            rec(version="V_maybe").validate()

    def test_rejects_an_attempt_number_outside_the_block(self):
        with self.assertRaises(LedgerError):
            rec(attempt=4).validate()
        with self.assertRaises(LedgerError):
            rec(attempt=0).validate()


class TestReplayIntoTheReducer(LedgerTestCase):
    def test_exit_statuses_come_back_in_attempt_order(self):
        from ledger import exit_statuses_for

        with Ledger(self.path) as led:
            # deliberately appended out of order
            led.append(rec(block=7, version=V_BAD, attempt=2, exit_status=0))
            led.append(rec(block=7, version=V_BAD, attempt=1, exit_status=1))
            led.append(rec(block=7, version=V_BAD, attempt=3, exit_status=1))
        self.assertEqual(
            exit_statuses_for(read_records(self.path), "etcd5509", 7, V_BAD), [1, 0, 1]
        )

    def test_a_gap_in_attempt_numbers_becomes_none(self):
        from ledger import exit_statuses_for

        with Ledger(self.path) as led:
            led.append(rec(block=7, version=V_BAD, attempt=1, exit_status=1))
            led.append(rec(block=7, version=V_BAD, attempt=3, exit_status=1))
        self.assertEqual(
            exit_statuses_for(read_records(self.path), "etcd5509", 7, V_BAD),
            [1, None, 1],
        )

    def test_the_replayed_prefix_drives_the_reducer(self):
        from ledger import exit_statuses_for
        from policy import P1, P3, BLOCK, ACCEPT, reduce_block

        with Ledger(self.path) as led:
            for i, st in enumerate([1, 0, 0], start=1):
                led.append(rec(block=3, version=V_BAD, attempt=i, exit_status=st))
        statuses = exit_statuses_for(read_records(self.path), "etcd5509", 3, V_BAD)
        self.assertEqual(reduce_block(P1, statuses).final_status, BLOCK)
        self.assertEqual(reduce_block(P3, statuses).final_status, ACCEPT)


if __name__ == "__main__":
    unittest.main()
