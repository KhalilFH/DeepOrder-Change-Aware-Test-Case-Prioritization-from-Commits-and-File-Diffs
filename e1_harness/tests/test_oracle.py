"""Tests for the oracle classifier.

The strongest check here is `TestAgainstQ0Evidence`: the frozen signatures are
run over the 120 raw Q0 qualification logs preserved in the repository and must
reproduce every recorded label. Those logs are qualification evidence, not E1
data; using them to validate the classifier is what plan section 5 asks for
("evaluate the oracle against documented positive and acceptable executions
before evaluating retry behavior").
"""

import csv
import json
import tempfile
import unittest
from pathlib import Path

from ledger import AttemptRecord, Ledger, V_BAD, V_OK, read_records
from oracle import (
    CARDS,
    ETCD5509,
    ETCD7492,
    GRPC1859,
    MECHANICAL,
    OVERRIDE,
    OracleError,
    annotate,
    card_for,
    classify,
    load_overrides,
    parse_goroutines,
    write_annotations,
)
from policy import FOCAL_DEFECT_WITNESS, HARNESS_INVALID, PASS, UNRESOLVED, VERIFIED_NUISANCE

ARTIFACTS = (
    Path(__file__).resolve().parents[2]
    / "research_runs" / "ci_sensitivity_2026_09" / "task5_artifacts"
)


def read_log(relative):
    return (ARTIFACTS / relative).read_text(encoding="utf-8", errors="replace")


def cats(adjudication):
    return set(adjudication.categories)


def drop_goroutines(text, predicate):
    """Remove every dump block whose header+frames satisfy `predicate`."""
    out, block, in_block = [], [], False
    for line in text.splitlines():
        if line.startswith("goroutine ") and line.rstrip().endswith("]:"):
            in_block, block = True, [line]
            continue
        if in_block:
            if line.strip():
                block.append(line)
                continue
            if not predicate("\n".join(block)):
                out.extend(block)
            out.append(line)
            in_block, block = False, []
            continue
        out.append(line)
    if block and not predicate("\n".join(block)):
        out.extend(block)
    return "\n".join(out)


RUN_5509 = "=== RUN   TestKVGetErrConnClosed\n"


@unittest.skipUnless(ARTIFACTS.is_dir(), "Q0 artifacts not present")
class TestAgainstQ0Evidence(unittest.TestCase):
    """Every recorded Q0 label must be reproduced by the frozen cards."""

    def check(self, card, rows):
        for label, exit_status, log in rows:
            with self.subTest(log=log):
                got = classify(card, exit_status, read_log(log), "")
                self.assertEqual({label}, cats(got), got.reason)

    def test_etcd5509_all_40(self):
        path = ARTIFACTS / "etcd5509/attempts/results_final.csv"
        rows = []
        for r in csv.DictReader(path.read_text(encoding="utf-8").splitlines()):
            label = FOCAL_DEFECT_WITNESS if r["classification"].startswith("FOCAL") else r["classification"]
            rows.append((label, int(r["exit_code"]), f"etcd5509/attempts/{r['version']}_attempt_{r['attempt']}.log"))
        self.assertEqual(40, len(rows))
        self.assertEqual(16, sum(1 for r in rows if r[0] == FOCAL_DEFECT_WITNESS))
        self.check(ETCD5509, rows)

    def test_etcd7492_all_40(self):
        # results.csv has no label column; the restoration record names the
        # two focal attempts (V_bad 2 and 11) and states all others passed.
        path = ARTIFACTS / "etcd7492/build/results.csv"
        rows = []
        for r in csv.DictReader(path.read_text(encoding="utf-8").splitlines()):
            focal = r["version"] == "vbad" and r["attempt"] in ("2", "11")
            rows.append((FOCAL_DEFECT_WITNESS if focal else PASS, int(r["exit_code"]), f"etcd7492/build/{r['logfile']}"))
        self.assertEqual(40, len(rows))
        self.check(ETCD7492, rows)

    def test_grpc1859_all_40(self):
        path = ARTIFACTS / "grpc1859/run/results.csv"
        rows = []
        for r in csv.DictReader(path.read_text(encoding="utf-8").splitlines()):
            label = FOCAL_DEFECT_WITNESS if r["classification"].startswith("FOCAL") else r["classification"]
            rows.append((label, int(r["exit"]), f"grpc1859/run/logs/{r['version']}_{int(r['attempt']):02d}.log"))
        self.assertEqual(40, len(rows))
        self.check(GRPC1859, rows)

    def test_etcd7492_exploratory_witness(self):
        got = classify(ETCD7492, 2, read_log("etcd7492/build/attempts/exploratory_bug_4.log"), "")
        self.assertEqual({FOCAL_DEFECT_WITNESS}, cats(got))

    def test_the_three_etcd5509_dump_shapes_all_match(self):
        # Step 3b: attempt 2 = Close's own Lock; 4 = connMonitor's deferred
        # closure; 5 = connMonitor via retryConnection.
        for attempt in (2, 4, 5):
            with self.subTest(attempt=attempt):
                got = classify(ETCD5509, 2, read_log(f"etcd5509/attempts/vbad_attempt_{attempt}.log"), "")
                self.assertEqual(("a",), got.signatures)

    # Mutations of real witnesses: removing the evidence must remove the label.

    def test_5509_shape_ii_without_the_connmonitor_goroutine_is_unresolved(self):
        text = read_log("etcd5509/attempts/vbad_attempt_5.log")
        cut = drop_goroutines(text, lambda b: "connMonitor" in b and "RWMutex).Lock" in b)
        self.assertNotEqual(text, cut)
        got = classify(ETCD5509, 2, cut, "")
        self.assertEqual({UNRESOLVED}, cats(got))
        self.assertIn("timeout", got.reason)

    def test_5509_timeout_without_close_on_the_test_goroutine_is_unresolved(self):
        text = read_log("etcd5509/attempts/vbad_attempt_2.log")
        cut = drop_goroutines(text, lambda b: "TestKVGetErrConnClosed(" in b)
        self.assertEqual({UNRESOLVED}, cats(classify(ETCD5509, 2, cut, "")))

    def test_7492_without_the_keeper_goroutine_is_unresolved(self):
        text = read_log("etcd7492/build/attempts/vbad_attempt_2.log")
        cut = drop_goroutines(text, lambda b: "simpleTokenTTLKeeper).run" in b)
        self.assertEqual({UNRESOLVED}, cats(classify(ETCD7492, 2, cut, "")))

    def test_7492_without_the_blocked_token_caller_is_unresolved(self):
        text = read_log("etcd7492/build/attempts/vbad_attempt_2.log")
        cut = drop_goroutines(text, lambda b: "(*tokenSimple)." in b)
        self.assertEqual({UNRESOLVED}, cats(classify(ETCD7492, 2, cut, "")))

    def test_a_witness_needs_the_timeout_not_just_the_stacks(self):
        text = read_log("etcd7492/build/attempts/vbad_attempt_2.log")
        text = text.replace("panic: test timed out after 50s", "panic: something else")
        self.assertEqual({UNRESOLVED}, cats(classify(ETCD7492, 2, text, "")))

    def test_split_stdout_stderr_classifies_like_merged(self):
        # The E1 runner keeps the streams apart; Q0 merged them.
        text = read_log("etcd5509/attempts/vbad_attempt_5.log")
        head, dump = text.split("panic: test timed out", 1)
        got = classify(ETCD5509, 2, head, "panic: test timed out" + dump)
        self.assertEqual({FOCAL_DEFECT_WITNESS}, cats(got))


class TestHarnessInvalid(unittest.TestCase):
    def test_no_exit_status(self):
        got = classify(ETCD5509, None, "", "")
        self.assertEqual({HARNESS_INVALID}, cats(got))
        self.assertIn("ceiling", got.reason)

    def test_docker_exit_codes(self):
        for code in (125, 126, 127):
            with self.subTest(code=code):
                self.assertEqual({HARNESS_INVALID}, cats(classify(ETCD5509, code, RUN_5509, "")))

    def test_docker_error_text(self):
        got = classify(ETCD5509, 1, "", "docker: Error response from daemon: boom")
        self.assertEqual({HARNESS_INVALID}, cats(got))

    def test_target_never_ran(self):
        got = classify(ETCD5509, 0, "testing: warning: no tests to run\nPASS\n", "")
        self.assertEqual({HARNESS_INVALID}, cats(got))
        self.assertIn("-test.v", got.reason)

    def test_other_test_ran(self):
        got = classify(ETCD5509, 0, "=== RUN   TestKVGetErrConnClosedX\n--- PASS: TestKVGetErrConnClosedX (0.1s)\n", "")
        self.assertEqual({HARNESS_INVALID}, cats(got))

    def test_skipped(self):
        got = classify(ETCD5509, 0, RUN_5509 + "--- SKIP: TestKVGetErrConnClosed (0.00s)\nPASS\n", "")
        self.assertEqual({HARNESS_INVALID}, cats(got))


class TestOrdinaryOutcomes(unittest.TestCase):
    def test_clean_pass(self):
        got = classify(ETCD5509, 0, RUN_5509 + "--- PASS: TestKVGetErrConnClosed (0.05s)\nPASS\n", "")
        self.assertEqual({PASS}, cats(got))

    def test_exit_zero_with_fail_marker_is_unresolved(self):
        out = RUN_5509 + "--- FAIL: TestKVGetErrConnClosed (0.05s)\n"
        self.assertEqual({UNRESOLVED}, cats(classify(ETCD5509, 0, out, "")))

    def test_nonzero_despite_reported_pass_is_unresolved(self):
        out = RUN_5509 + "--- PASS: TestKVGetErrConnClosed (0.05s)\nFAIL\n"
        got = classify(ETCD5509, 1, out, "")
        self.assertEqual({UNRESOLVED}, cats(got))
        self.assertIn("reported PASS", got.reason)

    def test_unmatched_assertion_failure_is_unresolved_not_other_defect(self):
        out = RUN_5509 + "--- FAIL: TestKVGetErrConnClosed (0.05s)\n    kv_test.go:1: nope\nFAIL\n"
        got = classify(ETCD5509, 1, out, "")
        self.assertEqual({UNRESOLVED}, cats(got))

    def test_classifier_never_emits_nuisance_or_other_defect(self):
        for exit_status in (0, 1, 2):
            got = classify(ETCD5509, exit_status, RUN_5509 + "FAIL\n", "")
            self.assertTrue(cats(got) <= {PASS, FOCAL_DEFECT_WITNESS, UNRESOLVED, HARNESS_INVALID})


class TestSyntheticSignatures(unittest.TestCase):
    """Signatures that never fired in Q0; exercised on constructed dumps only."""

    PANIC_5509 = (
        RUN_5509
        + "panic: runtime error: invalid memory address or nil pointer dereference\n"
        "[signal SIGSEGV: segmentation violation]\n\n"
        "goroutine 71 [running]:\n"
        "github.com/coreos/etcd/clientv3.(*remoteClient).acquire(0xc4, 0x0)\n"
        "\t/go/src/github.com/coreos/etcd/clientv3/remote_client.go:90 +0x1\n"
        "github.com/coreos/etcd/clientv3/integration.TestKVGetErrConnClosed.func1(0xc4)\n"
        "\t/go/src/github.com/coreos/etcd/clientv3/integration/kv_test.go:290 +0x1\n"
        "created by github.com/coreos/etcd/clientv3/integration.TestKVGetErrConnClosed\n"
        "\t/go/src/github.com/coreos/etcd/clientv3/integration/kv_test.go:288 +0x1\n"
    )

    def test_5509_signature_b(self):
        got = classify(ETCD5509, 2, self.PANIC_5509, "")
        self.assertEqual({FOCAL_DEFECT_WITNESS}, cats(got))
        self.assertEqual(("b",), got.signatures)

    def test_5509_panic_elsewhere_is_unresolved(self):
        text = self.PANIC_5509.replace("(*remoteClient).acquire", "(*watcher).run")
        got = classify(ETCD5509, 2, text, "")
        self.assertEqual({UNRESOLVED}, cats(got))
        self.assertIn("panic", got.reason)

    GRPC_RUN = f"=== RUN   {GRPC1859.test_name}\n"

    def test_grpc_other_status_code_is_unresolved(self):
        out = (
            self.GRPC_RUN
            + f"--- FAIL: {GRPC1859.test_name} (1.00s)\n"
            "    end2end_test.go:6035: rpc error: code = Unavailable desc = x, want code: ResourceExhausted\nFAIL\n"
        )
        self.assertEqual({UNRESOLVED}, cats(classify(GRPC1859, 1, out, "")))

    def test_grpc_leak_signature_b(self):
        out = (
            self.GRPC_RUN
            + "    leakcheck.go:1: Leaked goroutine: goroutine 88 [select]:\n"
            "google.golang.org/grpc/transport.(*quotaPool).get(0xc4)\n"
            "\t/x/control.go:191 +0x1\n"
            "google.golang.org/grpc/transport.(*http2Client).Write(0xc4)\n"
            "\t/x/http2_client.go:700 +0x1\n"
            "\n"
            f"--- FAIL: {GRPC1859.test_name} (20.00s)\nFAIL\n"
        )
        got = classify(GRPC1859, 1, out, "")
        self.assertEqual(("b",), got.signatures)

    def test_grpc_leak_without_the_frames_is_unresolved(self):
        out = (
            self.GRPC_RUN
            + "    leakcheck.go:1: Leaked goroutine: goroutine 88 [select]:\n"
            "google.golang.org/grpc.(*addrConn).resetTransport(0xc4)\n\n"
            f"--- FAIL: {GRPC1859.test_name} (20.00s)\nFAIL\n"
        )
        self.assertEqual({UNRESOLVED}, cats(classify(GRPC1859, 1, out, "")))


class TestParseGoroutines(unittest.TestCase):
    def test_headers_frames_and_created_by(self):
        dump = (
            "noise\n"
            "goroutine 7 [chan receive, 2 minutes]:\n"
            "pkg.(*T).M(0x1, 0x2)\n"
            "\t/f.go:1 +0x1\n"
            "created by pkg.Spawn\n"
            "\t/f.go:2 +0x1\n"
            "\n"
            "prefix: goroutine 8 [select]:\n"
            "pkg.F(...)\n"
        )
        gs = parse_goroutines(dump)
        self.assertEqual([7, 8], [g.gid for g in gs])
        self.assertEqual("chan receive, 2 minutes", gs[0].state)
        self.assertEqual(("pkg.(*T).M", "created by pkg.Spawn"), gs[0].functions)
        self.assertEqual(("pkg.F",), gs[1].functions)


class TestCards(unittest.TestCase):
    def test_unknown_episode_is_refused(self):
        with self.assertRaises(OracleError):
            card_for("pool162")

    def test_registry(self):
        self.assertEqual({"etcd5509", "etcd7492", "grpc1859"}, set(CARDS))
        for card in CARDS.values():
            self.assertTrue(card.source and card.signatures)


def rec(block=1, version=V_BAD, attempt=1, exit_status=0, stdout=None):
    if stdout is None:
        stdout = RUN_5509 + "--- PASS: TestKVGetErrConnClosed (0.05s)\nPASS\n"
    return AttemptRecord(
        episode="etcd5509", block=block, version=version, attempt=attempt,
        exit_status=exit_status, started_utc="2026-09-22T10:00:00.000000Z",
        ended_utc="2026-09-22T10:00:01.000000Z", elapsed_s=1.0, timed_out=False,
        condition="default", seed=1, manifest_sha256="a" * 64,
        runner_version="e1-runner/1", stdout=stdout, stderr="",
    )


class TestAnnotateAndOverrides(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.ledger = self.dir / "attempts.jsonl"
        with Ledger(self.ledger) as led:
            led.append(rec(attempt=1))
            led.append(rec(version=V_OK, attempt=1, exit_status=1, stdout=RUN_5509 + "FAIL\n"))
        self.rows = read_records(self.ledger)

    def tearDown(self):
        self._tmp.cleanup()

    def write_overrides(self, *rows):
        path = self.dir / "overrides.jsonl"
        path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        return path

    def override(self, **kw):
        base = dict(
            record_sha256=self.rows[1]["sha256"], categories=[VERIFIED_NUISANCE],
            adjudicator="researcher", reason="port collision in harness",
            evidence="bind: address already in use at kv_test.go:1",
        )
        base.update(kw)
        return base

    def test_mechanical_annotation_carries_provenance(self):
        a = annotate(self.rows)
        self.assertEqual([PASS], a[0]["categories"])
        self.assertEqual([UNRESOLVED], a[1]["categories"])
        self.assertEqual(MECHANICAL, a[0]["source"])
        self.assertEqual(self.rows[0]["sha256"], a[0]["record_sha256"])
        self.assertEqual(64, len(a[0]["oracle_sha256"]))

    def test_override_replaces_but_keeps_the_mechanical_label(self):
        a = annotate(self.rows, load_overrides(self.write_overrides(self.override())))
        self.assertEqual([VERIFIED_NUISANCE], a[1]["categories"])
        self.assertEqual(OVERRIDE, a[1]["source"])
        self.assertEqual([UNRESOLVED], a[1]["mechanical"])
        self.assertIn("evidence", a[1]["override"])

    def test_override_needs_reason_and_evidence(self):
        for field in ("reason", "evidence", "adjudicator"):
            with self.subTest(field=field):
                with self.assertRaises(OracleError):
                    load_overrides(self.write_overrides(self.override(**{field: " "})))

    def test_override_rejects_unknown_category(self):
        with self.assertRaises(OracleError):
            load_overrides(self.write_overrides(self.override(categories=["FLAKY"])))

    def test_override_for_absent_record_is_an_error(self):
        with self.assertRaises(OracleError):
            annotate(self.rows, load_overrides(self.write_overrides(self.override(record_sha256="f" * 64))))

    def test_write_refuses_to_change_an_existing_file(self):
        out = self.dir / "annotations.jsonl"
        write_annotations(out, annotate(self.rows), replace=False)
        write_annotations(out, annotate(self.rows), replace=False)  # identical: fine
        changed = annotate(self.rows, load_overrides(self.write_overrides(self.override())))
        with self.assertRaises(OracleError):
            write_annotations(out, changed, replace=False)
        write_annotations(out, changed, replace=True)


if __name__ == "__main__":
    unittest.main()
