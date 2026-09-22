"""Tests for the E1 analysis script.

Synthetic truth-table inputs only: they validate the implementation and never
enter empirical results (plan, Experiment 1).
"""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from analysis import (
    AnalysisError,
    analyse,
    clopper_pearson,
    main,
    margin_position,
    paired_contrast,
    parse_blocks,
)
from ledger import AttemptRecord, Ledger, V_BAD, V_OK, read_records
from oracle import annotate, write_annotations
from policy import (
    ACCEPT,
    BLOCK,
    FOCAL_DEFECT_WITNESS,
    HARNESS_INVALID,
    INDETERMINATE,
    OTHER_DEFECT,
    P1,
    P3,
    P3_RETAIN,
    PASS,
    UNRESOLVED,
    VERIFIED_NUISANCE,
)

F, P, U, X, NU, OD = FOCAL_DEFECT_WITNESS, PASS, UNRESOLVED, HARNESS_INVALID, VERIFIED_NUISANCE, OTHER_DEFECT
EXIT = {F: 2, P: 0, U: 1, X: None, NU: 1, OD: 1}


class Fixture:
    """A ledger plus hand-written annotations, one category per attempt."""

    def __init__(self, directory: Path, episode="etcd5509"):
        self.dir = directory
        self.episode = episode
        self.ledger = directory / "attempts.jsonl"
        self.annotations = directory / "annotations.jsonl"
        self.labels: dict[tuple, str] = {}
        self._led = Ledger(self.ledger).__enter__()

    def block(self, block, bad=(P, P, P), ok=(P, P, P), elapsed=1.0):
        for version, labels in ((V_BAD, bad), (V_OK, ok)):
            for attempt, label in enumerate(labels, start=1):
                if label is None:
                    continue  # a missing attempt
                self._led.append(
                    AttemptRecord(
                        episode=self.episode, block=block, version=version, attempt=attempt,
                        exit_status=EXIT[label], started_utc=f"2026-09-22T10:{block:02d}:00.000000Z",
                        ended_utc="2026-09-22T10:00:01.000000Z", elapsed_s=elapsed,
                        timed_out=False, condition="default", seed=block,
                        manifest_sha256="a" * 64, runner_version="e1-runner/1",
                        stdout="", stderr="",
                    )
                )
                self.labels[(self.episode, block, version, attempt)] = label
        return self

    def close(self):
        self._led.__exit__(None, None, None)
        rows = []
        for r in read_records(self.ledger):
            label = self.labels[(r["episode"], r["block"], r["version"], r["attempt"])]
            rows.append(
                {
                    "episode": r["episode"], "block": r["block"], "version": r["version"],
                    "attempt": r["attempt"], "record_seq": r["seq"], "record_sha256": r["sha256"],
                    "categories": [label], "signatures": [], "reason": "fixture",
                    "source": "mechanical", "oracle_version": "fixture", "oracle_sha256": "0" * 64,
                }
            )
        self.annotations.write_text("".join(json.dumps(a) + "\n" for a in rows), encoding="utf-8")
        return self


class AnalysisCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def run_analysis(self, fx, blocks, **kw):
        result, rows = analyse(fx.ledger, fx.annotations, parse_blocks(blocks), 2.0, **kw)
        return result["episodes"][0], rows


class TestClopperPearson(unittest.TestCase):
    def test_zero_of_twenty(self):
        lo, hi = clopper_pearson(0, 20, 0.05)
        self.assertEqual(0.0, lo)
        self.assertAlmostEqual(1 - 0.025 ** (1 / 20), hi, places=6)

    def test_all_of_twenty(self):
        lo, hi = clopper_pearson(20, 20, 0.05)
        self.assertAlmostEqual(0.025 ** (1 / 20), lo, places=6)
        self.assertEqual(1.0, hi)

    def test_textbook_value(self):
        lo, hi = clopper_pearson(5, 20, 0.05)
        self.assertAlmostEqual(0.0866, lo, places=4)
        self.assertAlmostEqual(0.4910, hi, places=4)

    def test_no_data(self):
        self.assertEqual((0.0, 1.0), clopper_pearson(0, 0, 0.05))


class TestPairedContrast(unittest.TestCase):
    def test_zero_discordance_still_has_width(self):
        c = paired_contrast([1] * 20, [1] * 20, 0.025)
        self.assertEqual(0.0, c["estimate"])
        lo, hi = c["interval"]
        self.assertLess(lo, 0.0)
        self.assertGreater(hi, 0.0)
        self.assertAlmostEqual(-hi, lo)

    def test_best_worst_fills_unknowns_both_ways(self):
        c = paired_contrast([1, 0, None], [0, 0, None], 0.025)
        self.assertEqual(2, c["complete_blocks"])
        self.assertEqual(0.5, c["estimate"])
        self.assertEqual([0.0, 2 / 3], c["best_worst"])

    def test_margin_position(self):
        self.assertEqual("upper bound below margin", margin_position([-0.05, 0.08], 0.10))
        self.assertEqual("interval contains margin", margin_position([-0.05, 0.3], 0.10))
        self.assertEqual("lower bound above margin", margin_position([0.2, 0.6], 0.10))


class TestParseBlocks(unittest.TestCase):
    def test_ranges(self):
        self.assertEqual([1, 2, 3, 7], parse_blocks("1-3, 7"))
        self.assertEqual([], parse_blocks(None))
        with self.assertRaises(AnalysisError):
            parse_blocks("5-1")


class TestIndicators(AnalysisCase):
    def fixture(self):
        return (
            Fixture(self.dir)
            .block(1, bad=(F, P, P))            # P1 blocks on focal; P3 accepts after it
            .block(2, bad=(F, F, F), ok=(NU, P, P))  # both block on focal; P1 nuisance block
            .block(3, bad=(P, F, F))            # witnesses only in the suffix
            .block(4, bad=(X, P, P))            # harness-invalid first attempt
            .block(5, bad=(U, U, U))            # blocked, but on unresolved evidence
            .close()
        )

    def test_sensitivity_and_its_contrast(self):
        ep, _ = self.run_analysis(self.fixture(), "1-5")
        self.assertEqual({"count": 2, "denominator": 3, "undetermined": 2}, {k: ep["S"][P1][k] for k in ("count", "denominator", "undetermined")})
        self.assertEqual(1, ep["S"][P3]["count"])
        self.assertEqual(3, ep["S"][P3]["denominator"])
        L = ep["L"]
        self.assertEqual((3, 1, 0), (L["complete_blocks"], L["positive"], L["negative"]))
        self.assertAlmostEqual(1 / 3, L["estimate"])
        self.assertEqual([-0.2, 0.6], [round(x, 6) for x in L["best_worst"]])

    def test_p3_retain_matches_p3_and_flags_prior_failure(self):
        ep, rows = self.run_analysis(self.fixture(), "1-5")
        self.assertEqual(ep["S"][P3], ep["S"][P3_RETAIN])
        # block 1 V_bad (focal then pass) and block 2 V_ok (nuisance then pass)
        self.assertEqual(2, ep["accept_with_prior_failure"])
        flagged = [r for r in rows if r["report_flag"]]
        self.assertEqual({P3_RETAIN}, {r["policy"] for r in flagged})

    def test_nuisance_and_its_contrast(self):
        ep, _ = self.run_analysis(self.fixture(), "1-5")
        self.assertEqual(1, ep["N"][P1]["count"])
        self.assertEqual(0, ep["N"][P3]["count"])
        self.assertEqual(1, ep["R"]["positive"])

    def test_witness_accounting(self):
        ep, _ = self.run_analysis(self.fixture(), "1-5")
        w = ep["focal_witnesses_V_bad"]
        self.assertEqual(6, w[P1]["generated"])
        self.assertEqual((2, 0, 4), (w[P1]["in_prefix"], w[P1]["ignored_by_gate"], w[P1]["research_only"]))
        self.assertEqual((4, 1, 2), (w[P3]["in_prefix"], w[P3]["ignored_by_gate"], w[P3]["research_only"]))

    def test_invalid_block_and_indeterminate_decision(self):
        ep, rows = self.run_analysis(self.fixture(), "1-5")
        self.assertEqual([4], ep["invalid_blocks"])
        self.assertAlmostEqual(0.2, ep["invalid_fraction"])
        b4 = [r for r in rows if r["block"] == 4 and r["version"] == V_BAD]
        self.assertEqual({INDETERMINATE}, {r["final_status"] for r in b4})
        self.assertTrue(all(r["indicator_value"] == "" for r in b4))

    def test_decision_rows_list_consumed_attempts(self):
        _, rows = self.run_analysis(self.fixture(), "1-5")
        r = next(r for r in rows if (r["block"], r["version"], r["policy"]) == (1, V_BAD, P3))
        self.assertEqual(ACCEPT, r["final_status"])
        self.assertEqual(2, len(r["consumed_attempt_ids"].split()))
        self.assertTrue(r["research_only_attempt_ids"].startswith("a3:seq"))
        self.assertEqual(f"{F} | {P}", r["prefix_categories"])

    def test_prefix_cost(self):
        ep, _ = self.run_analysis(self.fixture(), "1-5")
        # V_bad prefixes under P3: b1 2, b2 3, b3 1, b4 1 (stops at invalid), b5 3
        self.assertEqual(10, ep["prefix_cost"][f"{P3}/{V_BAD}"]["attempts"])
        self.assertEqual(5, ep["prefix_cost"][f"{P1}/{V_BAD}"]["attempts"])
        # b4's invalid attempt was consumed but has no exit status to charge? It
        # still ran: its elapsed time counts.
        self.assertEqual(10.0, ep["prefix_cost"][f"{P3}/{V_BAD}"]["wall_s"])
        self.assertAlmostEqual(10.0 * 2 / 3600, ep["prefix_cost"][f"{P3}/{V_BAD}"]["allocated_vcpu_h"], places=6)


class TestConservativeRules(AnalysisCase):
    def test_other_defect_block_is_determined_not_sensitivity(self):
        fx = Fixture(self.dir).block(1, bad=(OD, OD, OD)).close()
        ep, _ = self.run_analysis(fx, "1")
        self.assertEqual((0, 1), (ep["S"][P1]["count"], ep["S"][P1]["denominator"]))

    def test_unresolved_on_v_ok_leaves_nuisance_undetermined(self):
        fx = Fixture(self.dir).block(1, ok=(U, U, U)).close()
        ep, _ = self.run_analysis(fx, "1")
        self.assertEqual(1, ep["N"][P1]["undetermined"])
        self.assertEqual([-1.0, 1.0], ep["R"]["best_worst"])

    def test_other_defect_on_v_ok_is_not_nuisance(self):
        fx = Fixture(self.dir).block(1, ok=(NU, OD, OD)).close()
        ep, _ = self.run_analysis(fx, "1")
        self.assertEqual((0, 1, 0), (ep["N"][P3]["count"], ep["N"][P3]["denominator"], ep["N"][P3]["undetermined"]))

    def test_declared_block_with_no_records_is_missing(self):
        fx = Fixture(self.dir).block(1).close()
        ep, _ = self.run_analysis(fx, "1-2")
        self.assertEqual([2], ep["missing_blocks"])
        self.assertEqual([2], ep["invalid_blocks"])
        self.assertEqual(1, ep["S"][P1]["undetermined"])

    def test_truncated_block_is_invalid(self):
        fx = Fixture(self.dir).block(1, bad=(F, None, None)).close()
        ep, rows = self.run_analysis(fx, "1")
        self.assertEqual([1], ep["invalid_blocks"])
        p1 = next(r for r in rows if (r["version"], r["policy"]) == (V_BAD, P1))
        self.assertEqual(BLOCK, p1["final_status"])  # P1 never needed attempt 2
        p3 = next(r for r in rows if (r["version"], r["policy"]) == (V_BAD, P3))
        self.assertEqual(INDETERMINATE, p3["final_status"])

    def test_counterpart_witness_is_flagged(self):
        fx = Fixture(self.dir).block(1, ok=(P, F, P)).close()
        ep, _ = self.run_analysis(fx, "1")
        self.assertEqual(1, len(ep["counterpart_focal_witnesses"]))


class TestInputContracts(AnalysisCase):
    def test_blocks_must_be_declared(self):
        fx = Fixture(self.dir).block(1).close()
        with self.assertRaises(AnalysisError):
            analyse(fx.ledger, fx.annotations, [], 2.0)

    def test_measured_and_direct_blocks_are_disjoint(self):
        fx = Fixture(self.dir).block(1).close()
        with self.assertRaises(AnalysisError):
            analyse(fx.ledger, fx.annotations, [1], 2.0, direct=[1])

    def test_every_record_needs_an_annotation(self):
        fx = Fixture(self.dir).block(1).close()
        lines = fx.annotations.read_text(encoding="utf-8").splitlines()
        fx.annotations.write_text("\n".join(lines[1:]) + "\n", encoding="utf-8")
        with self.assertRaises(AnalysisError):
            analyse(fx.ledger, fx.annotations, [1], 2.0)

    def test_duplicate_annotation_is_refused(self):
        fx = Fixture(self.dir).block(1).close()
        first = fx.annotations.read_text(encoding="utf-8").splitlines()[0]
        with open(fx.annotations, "a", encoding="utf-8") as fh:
            fh.write(first + "\n")
        with self.assertRaises(AnalysisError):
            analyse(fx.ledger, fx.annotations, [1], 2.0)

    def test_bonferroni_family_counts_every_contrast(self):
        fx = Fixture(self.dir).block(1).close()
        result, _ = analyse(fx.ledger, fx.annotations, [1], 2.0)
        self.assertEqual(2, result["meta"]["contrast_family"])
        self.assertAlmostEqual(0.05 / 4, result["meta"]["alpha_each"])


class TestDirectChecks(AnalysisCase):
    def test_structural_consistency(self):
        fx = (
            Fixture(self.dir)
            .block(1)
            .block(101, bad=(U, P, None), ok=(P, None, None))
            .block(102, bad=(P, U, None), ok=(U, U, U))
            .close()
        )
        ep, _ = self.run_analysis(fx, "1", direct=[101, 102])
        by = {(d["block"], d["version"]): d for d in ep["direct_checks"]}
        self.assertEqual([P3], by[(101, V_BAD)]["consistent_with"])
        self.assertEqual([P1, P3], by[(101, V_OK)]["consistent_with"])
        self.assertTrue(by[(102, V_BAD)]["structural_mismatch"])  # ran on after a pass
        self.assertEqual({P3: BLOCK}, by[(102, V_OK)]["decisions"])
        # direct-check blocks never reach S or N
        self.assertEqual(1, ep["S"][P1]["denominator"])


@unittest.skipUnless(
    (Path(__file__).resolve().parents[2] / "research_runs/ci_sensitivity_2026_09/task5_artifacts").is_dir(),
    "Q0 artifacts not present",
)
class TestEndToEnd(AnalysisCase):
    """Real Q0 output text through ledger -> oracle -> analysis -> files."""

    def test_pipeline(self):
        base = Path(__file__).resolve().parents[2] / "research_runs/ci_sensitivity_2026_09/task5_artifacts/etcd5509/attempts"
        witness = (base / "vbad_attempt_2.log").read_text(encoding="utf-8")
        passing = (base / "vbad_attempt_1.log").read_text(encoding="utf-8")
        ledger = self.dir / "attempts.jsonl"
        plan = {V_BAD: [(2, witness), (0, passing), (0, passing)], V_OK: [(0, passing)] * 3}
        with Ledger(ledger) as led:
            for version, attempts in plan.items():
                for i, (code, text) in enumerate(attempts, start=1):
                    led.append(
                        AttemptRecord(
                            episode="etcd5509", block=1, version=version, attempt=i,
                            exit_status=code, started_utc="2026-09-22T10:00:00.000000Z",
                            ended_utc="2026-09-22T10:00:01.000000Z", elapsed_s=1.0,
                            timed_out=False, condition="default", seed=1,
                            manifest_sha256="a" * 64, runner_version="e1-runner/1",
                            stdout=text, stderr="",
                        )
                    )
        annotations = self.dir / "annotations.jsonl"
        write_annotations(annotations, annotate(read_records(ledger)), replace=False)
        out = self.dir / "analysis"
        with contextlib.redirect_stdout(io.StringIO()):
            main([
                "--ledger", str(ledger), "--annotations", str(annotations), "--blocks", "1",
                "--allocated-vcpus", "2", "--out", str(out),
            ])
        summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
        ep = summary["episodes"][0]
        self.assertEqual(1, ep["S"][P1]["count"])  # P1 blocks on the witness
        self.assertEqual(0, ep["S"][P3]["count"])  # P3 accepts on attempt 2
        self.assertEqual(1, ep["L"]["positive"])
        self.assertTrue((out / "policy_decisions.csv").exists())
        self.assertIn("## etcd5509", (out / "report.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
