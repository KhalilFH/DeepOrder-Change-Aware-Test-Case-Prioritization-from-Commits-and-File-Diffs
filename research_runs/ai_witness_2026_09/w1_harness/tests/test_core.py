"""Offline tests: ledgers, resources, overlays, schedule, oracles, validation rules, providers.

No credentials, provider calls or containers are used.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from w1_harness import ARMS, CASES, casespec, oracles, packet, schedule, templates
from w1_harness.common import EMPTY_OVERLAY_SHA256, read_json
from w1_harness.config import ORACLES_DIR, design_config
from w1_harness.ledger import ChainLedger, LedgerError
from w1_harness.overlay import OverlayError, materialize
from w1_harness.providers import (BudgetDenied, FakeGeneratorTransport, FakeJevTransport, GeneratorClient,
                                  GeneratorConfig, JevClient, JevConfig, ProviderDrift, SessionBudget, parse_jev_choice)
from w1_harness.resources import BudgetExceeded, Caps, ResourceAccount
from w1_harness.validation import classify_outcome, policy_visibility


def tmp_account(d: Path) -> ResourceAccount:
    return ResourceAccount(d / "res.jsonl", Caps.from_study_config(design_config()))


class LedgerTests(unittest.TestCase):
    def test_chain_and_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "e.jsonl"
            led = ChainLedger(p)
            for i in range(3):
                led.append("s", "t", f"e{i}", {"i": i})
            self.assertEqual(ChainLedger(p).verify(), 3)
            lines = p.read_text().splitlines()
            lines[1] = lines[1].replace('"i":1', '"i":9')
            p.write_text("\n".join(lines) + "\n")
            with self.assertRaises(LedgerError):
                ChainLedger(p).verify()

    def test_reorder_detected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "e.jsonl"
            led = ChainLedger(p)
            for i in range(3):
                led.append("s", "t", f"e{i}", {"i": i})
            lines = p.read_text().splitlines()
            p.write_text("\n".join([lines[0], lines[2], lines[1]]) + "\n")
            with self.assertRaises(LedgerError):
                ChainLedger(p).verify()


class ResourceTests(unittest.TestCase):
    def test_reservation_blocks_overrun_and_open_reservation_counts(self):
        with tempfile.TemporaryDirectory() as d:
            a = tmp_account(Path(d))
            rid = a.reserve("preparation", "x", {"vcpu_h": 79.0})
            with self.assertRaises(BudgetExceeded):
                a.reserve("calibration", "y", {"vcpu_h": 2.0})  # shares the 80 vCPU-h preparation subcap
            self.assertAlmostEqual(a.remaining()["vcpu_h_preparation"], 1.0)
            a.settle(rid, {"vcpu_h": 0.5})
            self.assertAlmostEqual(a.remaining()["vcpu_h_preparation"], 79.5)
            with self.assertRaises(BudgetExceeded):
                a.reserve("search", "z", {"usd": 301})

    def test_failed_and_interrupted_work_is_charged(self):
        with tempfile.TemporaryDirectory() as d:
            a = tmp_account(Path(d))
            a.reserve("search", "inflight", {"vcpu_h": 3.0, "usd": 2.0})  # never settled (crash)
            rem = a.remaining()
            self.assertAlmostEqual(rem["usd"], 298.0)
            self.assertAlmostEqual(rem["vcpu_h_total"], 397.0)


def _pkt(case):
    p = packet.load_packet(case)
    return p, packet.originals(p)


class OverlayTests(unittest.TestCase):
    def test_unchanged_hash(self):
        for case in CASES:
            p, orig = _pkt(case)
            m = materialize(None, orig, casespec.spec(case))
            self.assertEqual(m.overlay_sha256, EMPTY_OVERLAY_SHA256)
            self.assertTrue(m.legal)
            self.assertEqual(m.run_selection, list(casespec.spec(case).entry_points))

    def test_production_edit_rejected(self):
        p, orig = _pkt("k8s26980")
        with self.assertRaises(OverlayError):
            materialize({"edits": [{"path": "pkg/controller/framework/shared_informer.go", "old": "a", "new": "b"}]},
                        orig, casespec.spec("k8s26980"))
        with self.assertRaises(OverlayError):
            materialize({"edits": [], "new_files": [{"path": "pkg/controller/framework/../../x_test.go", "content": "x"}]},
                        orig, casespec.spec("k8s26980"))

    def test_assertion_removal_rejected(self):
        p, orig = _pkt("k8s26980")
        m = materialize({"edits": [{"path": "pkg/controller/framework/processor_listener_test.go",
                                    "old": '\t\tt.Errorf("Timeout after %v", wait.ForeverTestTimeout)\n', "new": ""}]},
                        orig, casespec.spec("k8s26980"))
        self.assertFalse(m.legal)
        self.assertTrue(any("insertion-only" in v for v in m.violations))

    def test_timeout_change_rejected(self):
        p, orig = _pkt("k8s26980")
        m = materialize({"edits": [{"path": "pkg/controller/framework/processor_listener_test.go",
                                    "old": "time.After(wait.ForeverTestTimeout)", "new": "time.After(10 * wait.ForeverTestTimeout)"}]},
                        orig, casespec.spec("k8s26980"))
        self.assertFalse(m.legal)

    def test_variant_identity_and_file_access_rejected(self):
        p, orig = _pkt("grpc1859")
        sp = casespec.spec("grpc1859")
        for body in ('ioutil.ReadFile("../transport/http2_client.go")', 'os.Getenv("X")', 'if strings.Contains(x, "bug_patch") {}',
                     "func TestMain(m *testing.M) {}", 't.Skip("x")', 'println("goroutine 5 [select]:")'):
            content = f"package test\n\nimport \"testing\"\n\nfunc TestProbe(t *testing.T) {{\n\t{body}\n}}\n"
            m = materialize({"edits": [], "new_files": [{"path": "test/w1_probe_test.go", "content": content}]}, orig, sp)
            self.assertFalse(m.legal, body)

    def test_forbidden_import_rejected(self):
        p, orig = _pkt("istio17860")
        content = 'package envoy\n\nimport (\n\t"os/exec"\n\t"testing"\n)\n\nfunc TestProbe(t *testing.T) { _ = exec.Command }\n'
        m = materialize({"edits": [], "new_files": [{"path": "pkg/envoy/w1_probe_test.go", "content": content}]}, orig,
                        casespec.spec("istio17860"))
        self.assertFalse(m.legal)

    def test_new_test_selected(self):
        p, orig = _pkt("istio17860")
        content = 'package envoy\n\nimport "testing"\n\nfunc TestProbeNew(t *testing.T) {}\n'
        m = materialize({"edits": [], "new_files": [{"path": "pkg/envoy/w1_probe_test.go", "content": content}]}, orig,
                        casespec.spec("istio17860"))
        self.assertTrue(m.legal, m.violations)
        self.assertEqual(m.run_selection, ["TestExitDuringWaitForLive", "TestProbeNew"])

    def test_java_rules(self):
        p, orig = _pkt("pool162")
        sp = casespec.spec("pool162")
        anchor = "public class TestGenericObjectPool extends TestBaseObjectPool {"
        path = "src/test/org/apache/commons/pool/impl/TestGenericObjectPool.java"
        ok = materialize({"edits": [{"path": path, "old": anchor, "new": anchor + "\n    public void testX() throws Exception {}\n"}]}, orig, sp)
        self.assertTrue(ok.legal, ok.violations)
        self.assertIn("org.apache.commons.pool.impl.TestGenericObjectPool#testX", ok.run_selection)
        bad = materialize({"edits": [{"path": path, "old": anchor, "new": anchor + "\n    public void testX() { System.exit(0); }\n"}]}, orig, sp)
        self.assertFalse(bad.legal)

    def test_templates_are_legal(self):
        for case in CASES:
            p, orig = _pkt(case)
            sp = casespec.spec(case)
            for tid, prop, reason in templates.candidates(sp, orig):
                if prop is None:
                    continue
                m = materialize(prop, orig, sp)
                self.assertTrue(m.legal, (case, tid, m.violations))
            self.assertLessEqual(len(templates.candidates(sp, orig)), 4)


class ScheduleTests(unittest.TestCase):
    def test_deterministic_complete(self):
        cfg = design_config()
        a = schedule.build(cfg["schedule_seed"])
        b = schedule.build(cfg["schedule_seed"])
        self.assertEqual(a, b)
        self.assertEqual(len(a["sessions"]), 4 * 5 * 3)
        self.assertEqual(schedule.verify(a), [])
        self.assertEqual(len(a["calibration"]), 16)
        for blk in a["blocks"]:
            self.assertEqual(sorted(blk["session_order"]), sorted(ARMS))

    def test_exclusions_preserve_rows_and_order(self):
        cfg = design_config()
        a = schedule.build(cfg["schedule_seed"])
        b = schedule.build(cfg["schedule_seed"], exclusions={"pool162": "reason"})
        self.assertEqual([s["session_id"] for s in a["sessions"]], [s["session_id"] for s in b["sessions"]])
        self.assertTrue(all(s["status"] == "EXCLUDED" for s in b["sessions"] if s["case"] == "pool162"))
        self.assertEqual([s["validation_triplets"] for s in a["sessions"]], [s["validation_triplets"] for s in b["sessions"]])

    def test_sealed_schedule_file_regenerates(self):
        from w1_harness.config import SCHEDULE
        s = read_json(SCHEDULE)
        self.assertEqual(schedule.verify(s), [])


class OracleFixtureTests(unittest.TestCase):
    def test_fixtures(self):
        for case in CASES:
            sp = casespec.spec(case)
            p, orig = _pkt(case)
            o = oracles.make_oracle(sp, p["files"], orig)
            exp = read_json(ORACLES_DIR / case / "fixtures" / "expected.json")["fixtures"]
            self.assertGreaterEqual(len(exp), 5)
            for f in exp:
                text = (ORACLES_DIR / case / "fixtures" / f"{f['name']}.txt").read_text(encoding="utf-8")
                base = ["org.apache.commons.pool.impl.TestGenericObjectPool#testWhenExhaustedBlock"] if case == "pool162" else list(sp.entry_points)
                c = oracles.classify(o, f["variant"], exit_code=f["exit"], text=text, outer_timeout=f["outer"], cleanup_ok=True,
                                     harness_error=None, selection=base + f.get("selection_extra", []), final_sources={})
                self.assertEqual((c.status, c.rule_id), (f["expect"], f["rule"]), (case, f["name"], c.reason))
                if c.status == oracles.FOCAL:
                    self.assertTrue(c.premise_evidence and c.consequence_evidence)

    def test_cleanup_failure_is_harness_invalid(self):
        sp = casespec.spec("k8s26980")
        p, orig = _pkt("k8s26980")
        o = oracles.make_oracle(sp, p["files"], orig)
        c = oracles.classify(o, "V_bad", exit_code=0, text="--- PASS: TestPopReleaseLock (0.00s)\n", outer_timeout=False,
                             cleanup_ok=False, harness_error=None, selection=["TestPopReleaseLock"], final_sources={})
        self.assertEqual(c.status, oracles.HARNESS_INVALID)


def slots(bad_statuses, ok_statuses):
    out = []
    for variant, sts in (("V_bad", bad_statuses), ("V_ok", ok_statuses)):
        for i, st in enumerate(sts):
            out.append({"variant": variant, "triplet": i // 3 + 1, "position": i % 3 + 1, "status": st})
    return out


P, F, N, U, H, X = "PASS", "FOCAL_FAILURE", "NONFOCAL_FAILURE", "UNRESOLVED", "HARNESS_INVALID", "NOT_RUN"


class ValidationRuleTests(unittest.TestCase):
    def test_validated(self):
        s = slots([F, P, P, F, P, P] + [P] * 9, [P] * 15)
        self.assertEqual(classify_outcome(s)[0], "VALIDATED_WITNESS")

    def test_repaired_failure_blocks(self):
        s = slots([F, P, P, F, P, P] + [P] * 9, [P] * 14 + [N])
        self.assertEqual(classify_outcome(s)[0], "COUNTERPART_FAILURE")
        s = slots([F, P, P, F, P, P] + [P] * 9, [P] * 14 + [F])
        self.assertEqual(classify_outcome(s)[0], "COUNTERPART_FAILURE")

    def test_one_focal_triplet_insufficient(self):
        s = slots([F, F, F] + [P] * 12, [P] * 15)
        label, reasons = classify_outcome(s)
        self.assertEqual(label, "NO_WITNESS_WITHIN_BUDGET")
        self.assertIn("FOCAL_IN_ONE_TRIPLET", reasons)

    def test_unrelated_timeout_or_nonfocal_blocks(self):
        s = slots([F, P, P, F, P, N] + [P] * 9, [P] * 15)
        self.assertEqual(classify_outcome(s)[0], "NO_WITNESS_WITHIN_BUDGET")

    def test_missing_or_malformed(self):
        s = slots([F, P, P, F, P, P] + [P] * 8 + [X], [P] * 15)
        self.assertEqual(classify_outcome(s)[0], "UNRESOLVED")
        s = slots([F, P, P, F, P, U] + [P] * 9, [P] * 15)
        self.assertEqual(classify_outcome(s)[0], "UNRESOLVED")
        s = slots([F, P, P, F, P, P] + [P] * 9, [P] * 14 + [H])
        self.assertEqual(classify_outcome(s)[0], "UNRESOLVED")
        self.assertEqual(classify_outcome(slots([F] * 15, [P] * 14))[0], "UNRESOLVED")

    def test_policy_visibility(self):
        s = slots([F, F, F, P, F, P, F, P, P, P, P, P, P, P, F], [P] * 15)
        pv = policy_visibility(s)
        self.assertEqual(pv["P1"], [2, 2])
        self.assertEqual(pv["P3"], [1, 1])
        self.assertEqual(pv["P3_retain"], [4, 4])
        self.assertEqual(pv["focal_attempts"], [6, 6])
        s2 = slots([P, X, X] + [P] * 12, [P] * 15)
        pv2 = policy_visibility(s2)
        self.assertEqual(pv2["P3_retain"], [0, 1])
        self.assertEqual(pv2["P1"], [0, 0])


def gen_cfg(expected="fake-opus"):
    return GeneratorConfig("claude-sonnet-5", expected, "medium", 4000, 120, 2.0, 10.0, "test-pricing")


def budget(arm="B2"):
    s = design_config()["search"]
    return SessionBudget(s["max_input_tokens"], s["max_output_tokens"], s["max_usd"], s["max_generator_calls"][arm],
                         s["max_jev_evaluations"][arm])


class ProviderTests(unittest.TestCase):
    def body(self, size=100):
        return {"model": "claude-sonnet-5", "system": "s", "messages": [{"role": "user", "content": "x" * size}]}

    def test_call_cap_and_no_retry(self):
        with tempfile.TemporaryDirectory() as d:
            t = FakeGeneratorTransport(lambda b: {"content": [{"type": "text", "text": "ok"}]})
            c = GeneratorClient(t, gen_cfg(), tmp_account(Path(d)))
            b = budget("B4")
            events = []
            for i in range(3):
                c.create(f"r{i}", "s", self.body(), b, 500, lambda *a: events.append(a[0]))
            with self.assertRaises(BudgetDenied):
                c.create("r4", "s", self.body(), b, 500, lambda *a: None)
            self.assertEqual(len(t.sent), 3)

    def test_input_ceiling_across_requests(self):
        with tempfile.TemporaryDirectory() as d:
            t = FakeGeneratorTransport(lambda b: {"content": []})
            c = GeneratorClient(t, gen_cfg(), tmp_account(Path(d)))
            b = budget("B2")
            c.create("r1", "s", self.body(160000), b, 500, lambda *a: None)  # ~40k tokens by the fake count
            with self.assertRaises(BudgetDenied):
                c.create("r2", "s", self.body(160000), b, 500, lambda *a: None)

    def test_timeout_is_indeterminate_and_charged(self):
        with tempfile.TemporaryDirectory() as d:
            acct = tmp_account(Path(d))
            t = FakeGeneratorTransport(lambda b: {"content": []}, fail_with=-1)
            c = GeneratorClient(t, gen_cfg(), acct)
            b = budget("B2")
            rec, resp = c.create("r1", "s", self.body(), b, 500, lambda *a: None)
            self.assertIsNone(resp)
            self.assertEqual(rec.status, "INDETERMINATE")
            self.assertGreater(b.used_output, 0)
            self.assertEqual(len(t.sent), 1)
            self.assertGreater(300 - acct.remaining()["usd"], 0)

    def test_drift_raises(self):
        with tempfile.TemporaryDirectory() as d:
            t = FakeGeneratorTransport(lambda b: {"content": []}, returned_model="other-model")
            c = GeneratorClient(t, gen_cfg("fake-opus"), tmp_account(Path(d)))
            with self.assertRaises(ProviderDrift):
                c.create("r1", "s", self.body(), budget(), 500, lambda *a: None)

    def test_deadline_admission(self):
        with tempfile.TemporaryDirectory() as d:
            c = GeneratorClient(FakeGeneratorTransport(lambda b: {"content": []}), gen_cfg(), tmp_account(Path(d)))
            with self.assertRaises(BudgetDenied):
                c.create("r1", "s", self.body(), budget(), 10, lambda *a: None)

    def test_jev_malformed_is_unknown_and_charged(self):
        with tempfile.TemporaryDirectory() as d:
            t = FakeJevTransport(lambda body: b"{not json")
            c = JevClient(t, JevConfig("jev-latest", None, 30, 0.042, 0.0, "t"), tmp_account(Path(d)))
            b = budget("B4")
            rec, resp = c.evaluate("j1", "s", "state", {"type": "choice"}, b, 500, lambda *a: None)
            self.assertEqual(parse_jev_choice(resp)[0], "unknown")
            self.assertEqual(b.jev_evaluations, 1)
            self.assertEqual(rec.status, "INDETERMINATE")
            t2 = FakeJevTransport(lambda body: "supported", returned_model="jev-9")
            c2 = JevClient(t2, JevConfig("jev-latest", "jev-1.13.0", 30, 0.042, 0.0, "t"), tmp_account(Path(d)))
            with self.assertRaises(ProviderDrift):
                c2.evaluate("j2", "s", "state", {"type": "choice"}, b, 500, lambda *a: None)


class PromptTests(unittest.TestCase):
    def test_sections_verbatim_and_no_leaks(self):
        from w1_harness import prompts
        from w1_harness.config import DESIGN_DIR
        md = (DESIGN_DIR / "prompts.md").read_text(encoding="utf-8")
        for key, text in prompts.sections().items():
            self.assertIn(text, md)
        for case in CASES:
            p = packet.load_packet(case)
            ctx = prompts.packet_context(p, templates.bindings(case))
            for stage in ("b2", "planner", "judge_b3", "generator"):
                u = prompts.render_user(stage, ctx, {"seconds": 600})
                self.assertEqual(packet.leak_scan(u + prompts.render_system()), [], (case, stage))
            self.assertNotIn("testWhenExhaustedBlockInterupt", json.dumps(p))

    def test_strict_tools(self):
        from w1_harness import prompts
        for t in prompts.TOOLS.values():
            self.assertTrue(t["strict"])
            self.assertFalse(t["input_schema"]["additionalProperties"])


if __name__ == "__main__":
    unittest.main()


class ExtraGuardTests(unittest.TestCase):
    def test_overlay_size_and_new_file_limits(self):
        p, orig = _pkt("k8s26980")
        sp = casespec.spec("k8s26980")
        big = "package framework\n\nimport \"testing\"\n\nfunc TestBig(t *testing.T) {\n" + "\t_ = 1\n" * 450 + "}\n"
        m = materialize({"edits": [], "new_files": [{"path": "pkg/controller/framework/w1_big_test.go", "content": big}]}, orig, sp)
        self.assertFalse(m.legal)
        three = [{"path": f"pkg/controller/framework/w1_f{i}_test.go", "content": "package framework\n"} for i in range(3)]
        m = materialize({"edits": [], "new_files": three}, orig, sp)
        self.assertFalse(m.legal)

    def test_feedback_truncation_is_deterministic(self):
        from w1_harness.session import truncate_feedback
        text = "".join(f"line {i}\n" for i in range(5000))
        a, b = truncate_feedback(text), truncate_feedback(text)
        self.assertEqual(a, b)
        self.assertIn("omitted by the fixed truncation policy", a)
        self.assertLess(len(a), 4200)

    def test_empty_overlay_hash_constant(self):
        from w1_harness.overlay import overlay_hash
        self.assertEqual(overlay_hash({}), EMPTY_OVERLAY_SHA256)
