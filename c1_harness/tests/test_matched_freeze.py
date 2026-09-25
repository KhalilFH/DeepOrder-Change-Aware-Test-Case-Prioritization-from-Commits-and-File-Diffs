"""Matched R/L analysis on synthetic ledgers; conservative bounds; freeze tooling."""

import json
import tempfile
import unittest
from pathlib import Path

from ledger import AttemptRecord, Ledger, read_records
from oracle import write_annotations
from policy import P1, P3

from c1_harness import freeze
from c1_harness.cards import annotate
from c1_harness.matched import analyse, analyse_subject, write_outputs
from c1_harness.tests.fakes import K8S_FOCAL, K8S_OTHER, K8S_PASS

SID = "k8s26980"
OUTCOMES = {"F": (1, K8S_FOCAL), "U": (1, K8S_OTHER), "P": (0, K8S_PASS), "I": (None, "")}


def write_ledgers(root: Path, design: dict[tuple[str, str, int], str]) -> None:
    """design[(profile, version, block)] = e.g. 'FFF' (attempt outcomes in order); absent = missing."""
    for profile in ("R", "L"):
        with Ledger(root / "measured" / f"{SID}__{profile}.jsonl") as led:
            for (p, version, block), pattern in sorted(design.items()):
                if p != profile:
                    continue
                for attempt, code in enumerate(pattern, 1):
                    exit_status, text = OUTCOMES[code]
                    led.append(AttemptRecord(
                        episode=SID, block=block, version=version, attempt=attempt, exit_status=exit_status,
                        started_utc="s", ended_utc="e", elapsed_s=1.0, timed_out=False, condition=profile, seed=None,
                        manifest_sha256="m", runner_version="t", stdout=text, stderr="",
                        extra={"attempt_id": f"{SID}-b{block}-{profile}-{version}-a{attempt}", "job_elapsed_s": 1.5},
                    ))
    records = []
    for p in ("R", "L"):
        records += read_records(root / "measured" / f"{SID}__{p}.jsonl")
    write_annotations(root / "measured" / "annotations.jsonl", annotate(records), replace=True)


def scenario() -> dict[tuple[str, str, int], str]:
    d = {}
    for b in range(1, 11):
        d[("R", "V_bad", b)] = "FFF"
        d[("R", "V_ok", b)] = "PPP"
        d[("L", "V_ok", b)] = "PPP"
    for b in range(1, 6):
        d[("L", "V_bad", b)] = "FFF"
    for b in (6, 7, 8):
        d[("L", "V_bad", b)] = "PFF"  # witnesses only in the research suffix
    d[("L", "V_bad", 10)] = "UPP"  # block 9 missing on L/V_bad
    return d


class TestMatchedAnalysis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        write_ledgers(self.root, scenario())

    def tearDown(self):
        self.tmp.cleanup()

    def run_analysis(self, questioned=()):
        return analyse(self.root / "measured", self.root / "measured" / "annotations.jsonl", [SID],
                       {SID: "kubernetes"}, questioned=questioned)

    def test_primary_contrasts_and_missingness_bounds(self):
        s = self.run_analysis()["subjects"][0]
        p1 = s["primary_delta_S"][P1]
        self.assertEqual(p1["counts"], {"n_plus": 3, "n_minus": 0, "n_zero": 5, "missing": 2, "scheduled": 10})
        self.assertAlmostEqual(p1["estimate"], 3 / 8)
        self.assertEqual(p1["missing_bounds_all_scheduled"], [0.3, 0.5])
        p3 = s["primary_delta_S"][P3]
        self.assertEqual(p3["counts"]["n_plus"], 4)  # block 10: U then P accepts, so S=0 is known
        self.assertAlmostEqual(p3["estimate"], 4 / 9)
        self.assertEqual(p3["missing_bounds_all_scheduled"], [0.4, 0.5])
        self.assertAlmostEqual(p1["batches"]["A"]["estimate"], 0.0)
        self.assertAlmostEqual(p1["batches"]["B"]["estimate"], 3 / 3)  # blocks 6-8 complete, 9-10 unknown

    def test_family_size_and_interval_confidence(self):
        r = self.run_analysis()
        self.assertEqual(r["meta"]["family_K"], 2)
        self.assertAlmostEqual(r["meta"]["alpha_each_category_interval"], 0.05 / 4)
        iv = r["subjects"][0]["primary_delta_S"][P1]["interval"]
        self.assertTrue(iv[0] < 3 / 8 < iv[1])

    def test_research_suffix_never_supports_a_decision(self):
        s = self.run_analysis()["subjects"][0]
        # blocks 6-8 on L/V_bad pass first: P1 accepts and P3 accepts; their later witnesses are research-only
        self.assertEqual(s["S_rates"]["L/P3"]["count"], 5)
        self.assertEqual(s["E_rates"]["L/P1"]["count"], 5)

    def test_independent_crosscheck_agrees(self):
        s = self.run_analysis()["subjects"][0]
        self.assertTrue(s["crosscheck"]["agree"], s["crosscheck"])
        self.assertEqual(s["crosscheck"]["independent"], {"R/P1": 10, "R/P3": 10, "L/P1": 5, "L/P3": 5})

    def test_questioned_oracle_cannot_support_a_one(self):
        s = self.run_analysis(questioned=[SID])["subjects"][0]
        self.assertIsNone(s["primary_delta_S"][P1]["estimate"])
        # every R indicator unknown; L blocks 6-8 known 0: bounds (-5+0-2)/10 .. 10/10
        self.assertEqual(s["primary_delta_S"][P1]["missing_bounds_all_scheduled"], [-0.7, 1.0])

    def test_invalid_fraction_and_outputs(self):
        r = self.run_analysis()
        self.assertEqual(r["subjects"][0]["invalid"]["harness_invalid"], 0)
        write_outputs(r, self.root / "analysis")
        for name in ("attempt_index.csv", "policy_decisions.csv", "subject_contrasts.csv", "summary.json", "report.md"):
            self.assertTrue((self.root / "analysis" / name).exists(), name)
        summary = json.loads((self.root / "analysis" / "summary.json").read_text())
        self.assertFalse(summary["gates"]["C2"]["passed"])  # one subject cannot meet four pairs / two projects


class TestInvalidAttempts(unittest.TestCase):
    def test_invalid_first_attempt_makes_p1_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = scenario()
            d[("L", "V_bad", 1)] = "IFF"
            write_ledgers(root, d)
            r = analyse(root / "measured", root / "measured" / "annotations.jsonl", [SID], {SID: "kubernetes"})
            s = r["subjects"][0]
            self.assertEqual(s["invalid"]["harness_invalid"], 1)
            self.assertEqual(s["primary_delta_S"][P1]["counts"]["missing"], 3)


class TestFreeze(unittest.TestCase):
    def test_design_freeze_verifies_in_this_checkout(self):
        self.assertEqual(freeze.verify_design(), [])

    def test_normalized_hash_ignores_crlf(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a", Path(tmp) / "b"
            a.write_bytes(b"x\ny\n")
            b.write_bytes(b"x\r\ny\r\n")
            self.assertEqual(freeze.normalized_sha256(a), freeze.normalized_sha256(b))

    def test_launch_freeze_detects_any_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            study = root / "research_runs" / "ci_configuration_2026_09"
            study.mkdir(parents=True)
            files = []
            for name in ("DESIGN_FREEZE.sha256", "launch_record.md", "schedule.csv", "subject_manifest.json"):
                (study / name).write_text(name, newline="\n")
                files.append(study / name)
            saved = (freeze.REPO_ROOT, freeze.LAUNCH_FREEZE, freeze.verify_design)
            try:
                freeze.REPO_ROOT, freeze.LAUNCH_FREEZE = root, study / "FREEZE.sha256"
                freeze.verify_design = lambda: []
                self.assertEqual(freeze.verify_launch(), ["FREEZE.sha256 missing: no executable launch freeze exists"])
                freeze.write_launch_freeze(files, header="test")
                self.assertEqual(freeze.verify_launch(), [])
                (study / "schedule.csv").write_text("changed", newline="\n")
                self.assertTrue(freeze.verify_launch())
            finally:
                freeze.REPO_ROOT, freeze.LAUNCH_FREEZE, freeze.verify_design = saved


if __name__ == "__main__":
    unittest.main()
