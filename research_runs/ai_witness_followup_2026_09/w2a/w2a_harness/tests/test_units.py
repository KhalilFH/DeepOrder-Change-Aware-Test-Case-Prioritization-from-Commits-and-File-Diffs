"""Unit tests: stage validation, helper rule, schedule, reserves, tool semantics, evidence, leak screen."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from w2a_harness import fakes, prompts, schedule as sch, stagecheck
from w2a_harness.config import design_config
from w2a_harness.packet import load_packet
from w2a_harness.regressions import make_session
from w2a_harness.session import Conversation, IntegrityStop, run_f2, run_f3

GOOD_SPAN = "shared/test/end2end_test.go:6000-6008"


def plan(**over):
    p = {"obligation": "o", "intervention": "i", "uncertainties": [],
         "claims": [{"id": "c1", "category": "ordering", "proposition": "p", "source_spans": [GOOD_SPAN]}]}
    p.update(over)
    return p


class StageCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pkt = load_packet("grpc1859")

    def test_empty_and_malformed_plans_rejected(self):
        for bad in ({}, plan(claims=[]), plan(obligation=""), plan(claims=[{"id": "c1"}]),
                    plan(claims=[{"id": "c1", "category": "vibes", "proposition": "p", "source_spans": [GOOD_SPAN]}]),
                    plan(claims=[{"id": "c1", "category": "ordering", "proposition": "p", "source_spans": []}]),
                    plan(claims=[{"id": "c1", "category": "ordering", "proposition": "p", "source_spans": ["nofile.go:1-2"]}]),
                    plan(claims=[{"id": "c1", "category": "ordering", "proposition": "p", "source_spans": ["shared/test/end2end_test.go:6040-9999"]}]),
                    plan(claims=[{"id": "c1", "category": "ordering", "proposition": "p", "source_spans": ["transport/http2_client.go:1-5"]}]),
                    plan(claims=[{"id": "c1", "category": "ordering", "proposition": "p", "source_spans": [GOOD_SPAN]}] * 2),
                    plan(claims=[{"id": f"c{i}", "category": "ordering", "proposition": "p", "source_spans": [GOOD_SPAN]} for i in range(9)])):
            got, errors = stagecheck.validate_plan(bad, self.pkt)
            self.assertIsNone(got, bad)
            self.assertTrue(errors)

    def test_valid_plan_and_unprefixed_shared_path(self):
        got, errors = stagecheck.validate_plan(plan(claims=[{"id": "c1", "category": "ordering", "proposition": "p",
                                                              "source_spans": ["test/end2end_test.go:6000"]}]), self.pkt)
        self.assertEqual(errors, [])
        self.assertEqual(got["claims"][0]["source_spans"], ["shared/test/end2end_test.go:6000-6000"])

    def test_judgments_require_one_per_claim_and_keep_explicit_unknown(self):
        claims = [{"id": "c1"}, {"id": "c2"}]
        j = lambda cid, v, spans: {"claim_id": cid, "judgment": v, "source_spans": spans, "reason": "r"}  # noqa: E731
        for bad in ({"judgments": []}, {"judgments": [j("c1", "unknown", [])]},
                    {"judgments": [j("c1", "unknown", []), j("c1", "unknown", []), j("c2", "unknown", [])]},
                    {"judgments": [j("c1", "supported", []), j("c2", "unknown", [])]},
                    {"judgments": [j("c1", "maybe", []), j("c2", "unknown", [])]}):
            self.assertIsNone(stagecheck.validate_judgments(bad, claims, self.pkt)[0], bad)
        table, errors = stagecheck.validate_judgments({"judgments": [j("c2", "unknown", []), j("c1", "supported", [GOOD_SPAN])]}, claims, self.pkt)
        self.assertEqual(errors, [])
        self.assertEqual(list(table), ["c1", "c2"])
        self.assertEqual(table["c2"]["judgment"], "unknown")


class HelperRuleTests(unittest.TestCase):
    def test_rule_outputs(self):
        inc = {c: [(d["file_id"], d["start"], d["end"], d["rule"]) for d in load_packet(c)["helpers"]["included"]] for c in
               ("pool162", "grpc1859", "k8s26980", "istio17860")}
        self.assertIn(("shared/test/end2end_test.go", 6010, 6042, "H1"), inc["grpc1859"])
        self.assertIn(("shared/test/end2end_test.go", 409, 427, "H1"), inc["grpc1859"])
        self.assertEqual(inc["k8s26980"], [])
        self.assertTrue(any(r == "H2" and f.endswith("TestGenericObjectPool.java") for f, _, _, r in inc["pool162"]))
        self.assertFalse(any("instance_test.go" in f for f, *_ in inc["istio17860"]))  # errors.New is a package call
        for c, rows in inc.items():
            self.assertLessEqual(sum(e - s + 1 for _, s, e, _ in rows), design_config()["search"]["helper_rule"]["max_lines_per_case"])

    def test_helpers_rendered_identically_for_both_arms(self):
        with tempfile.TemporaryDirectory() as d:
            a, _ = make_session(Path(d) / "a", "grpc1859", "F2")
            b, _ = make_session(Path(d) / "b", "grpc1859", "F3")
            self.assertEqual(a.packet_ctx, b.packet_ctx)


class ScheduleTests(unittest.TestCase):
    def test_deterministic_complete(self):
        seed = design_config()["schedule_seed"]
        s1, s2 = sch.build(seed), sch.build(seed)
        self.assertEqual(s1, s2)
        self.assertEqual(sch.verify(s1), [])
        self.assertEqual(len(s1["sessions"]), 8)
        self.assertEqual(sorted(b["case"] for b in s1["blocks"]), sorted(["pool162", "grpc1859", "k8s26980", "istio17860"]))
        for b in s1["blocks"]:
            self.assertEqual(sorted(b["session_order"]), ["F2", "F3"])
        self.assertNotEqual(sch.build(seed + 1)["schedule_sha256"], s1["schedule_sha256"])


class ReserveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.s, _ = make_session(Path(self.tmp.name), "k8s26980", "F2")
        self.conv = Conversation("agent", "x")

    def tearDown(self):
        self.tmp.cleanup()

    def test_last_call_is_reserved_for_final(self):
        self.s.e.budget.generator_calls = 11
        self.assertEqual(self.s.admit(self.conv, "discretionary"), "calls")
        self.assertNotIsInstance(self.s.admit(self.conv, "final"), str)

    def test_time_reserve(self):
        self.s.t0 -= self.s.cfg["wall_seconds"] - self.s.FINAL_TIME - 20
        self.assertEqual(self.s.admit(self.conv, "discretionary"), "time")
        self.assertNotIsInstance(self.s.admit(self.conv, "final"), str)

    def test_input_reserve_covers_the_final_request(self):
        b = self.s.e.budget
        est = 30000
        b.used_input = b.max_input_tokens - (2 * est + self.s.G_MAX) + 1
        self.assertEqual(self.s.admit(self.conv, "discretionary", est_override=est), "input_tokens")
        b.used_input -= 1
        adm = self.s.admit(self.conv, "discretionary", est_override=est)
        self.assertNotIsInstance(adm, str)
        self.assertEqual(adm.held_back["input_tokens"], est + self.s.G_MAX)
        self.assertNotIsInstance(self.s.admit(self.conv, "final", est_override=est + self.s.G_MAX), str)

    def test_builds_and_pairs_keep_the_final_time(self):
        p = self.s.tool_submit_patch(fakes.probe_proposal(self.s.e.spec))
        self.s.t0 -= self.s.cfg["wall_seconds"] - 2 * (60 + 30) - self.s.FINAL_TIME + 1
        self.assertIn("final-call reserve", self.s.tool_build_pair(p["proposal_id"])["error"])


class ToolAndResponseTests(unittest.TestCase):
    def test_truncated_response_tools_not_executed(self):
        def script(body):
            if len(script.seen) == 0:
                script.seen.append(1)
                return {"content": [fakes.tu("submit_patch", {**fakes.probe_proposal(fakes.case_spec("k8s26980")), "rationale": "", "source_spans": []}, 1)],
                        "stop_reason": "max_tokens", "output_tokens": 4000}
            return {"content": [fakes.tu("submit_final", {"proposal_id": "unchanged", "rationale": "r", "source_spans": [], "obligation": "o",
                                                          "uncertainties": []}, 2)]}
        script.seen = []
        with tempfile.TemporaryDirectory() as d:
            s, gt = make_session(Path(d), "k8s26980", "F2", script)
            run_f2(s)
            self.assertEqual(s.patch_count, 0)
            self.assertEqual(s.counters["truncated_responses"], 1)
            self.assertEqual([m["role"] for m in gt.sent[1]["messages"]], ["user", "user"])
            self.assertEqual(s.terminal, "SEALED_DISCRETIONARY")

    def test_at_most_four_tool_uses_executed(self):
        read = lambda n: fakes.tu("read_source", {"file_id": "shared/pkg/controller/framework/doc.go", "start_line": 1, "end_line": 2}, n)  # noqa: E731

        def script(body):
            if len(body["messages"]) == 1:
                return {"content": [read(i) for i in range(5)]}
            return {"content": [fakes.tu("submit_final", {"proposal_id": "unchanged", "rationale": "r", "source_spans": [], "obligation": "o",
                                                          "uncertainties": []}, 9)]}
        with tempfile.TemporaryDirectory() as d:
            s, gt = make_session(Path(d), "k8s26980", "F2", script)
            run_f2(s)
            results = [c for c in gt.sent[1]["messages"][-1]["content"] if c["type"] == "tool_result"]
            self.assertEqual(len(results), 5)
            self.assertTrue(results[4].get("is_error"))
            self.assertEqual(len([e for e in s.evidence if e["kind"] == "read"]), 4)

    def test_final_call_executes_only_submit_final_and_refuses_illegal(self):
        with tempfile.TemporaryDirectory() as d:
            s, _ = make_session(Path(d), "k8s26980", "F2")
            r = s.tool_submit_patch({"edits": [], "new_files": [{"path": "pkg/controller/framework/w1_x_test.go",
                                                                  "content": "package framework\nimport \"os\"\nfunc TestX(t *testing.T) { os.Exit(1) }\n"}]})
            self.assertFalse(r["legal"])
            self.assertIn("error", s.tool_submit_final(r["proposal_id"], {}, "discretionary"))
            self.assertIsNone(s.final)

    def test_no_silent_fallback_to_unchanged(self):
        def script(body):
            return {"content": [{"type": "text", "text": "no tools"}]}
        with tempfile.TemporaryDirectory() as d:
            s, gt = make_session(Path(d), "istio17860", "F2", script)
            run_f2(s)
            self.assertIsNone(s.final)
            self.assertEqual(s.terminal, "FINAL_NO_SUBMIT")
            self.assertTrue(s.final_call_used)
            self.assertEqual(len(gt.sent), 12)

    def test_provider_failure_goes_to_final_call_in_f2_but_fails_f3_stage(self):
        with tempfile.TemporaryDirectory() as d:
            s, gt = make_session(Path(d) / "a", "k8s26980", "F2", lambda b: {"status": 500})
            run_f2(s)
            self.assertEqual(s.terminal, "FINAL_PROVIDER_FAILURE")
            self.assertEqual(len(gt.sent), 2)
            s3, gt3 = make_session(Path(d) / "b", "k8s26980", "F3", lambda b: {"status": 500})
            run_f3(s3)
            self.assertEqual(s3.terminal, "STAGE_FAILURE_PLAN")
            self.assertEqual(len(gt3.sent), 1)

    def test_model_text_with_marker_is_not_an_integrity_stop_but_harness_text_is(self):
        good = fakes.ScenarioScript()

        def script(body):
            names = {t["name"] for t in body["tools"]}
            if "submit_plan" in names:
                p = fakes.good_plan("istio17860")
                p["claims"][0]["proposition"] = "C1 depends on FOCAL_FAILURE wording"
                return {"content": [fakes.tu("submit_plan", p, 1)]}
            return good(body)
        with tempfile.TemporaryDirectory() as d:
            s, _ = make_session(Path(d), "istio17860", "F3", script)
            run_f3(s)
            self.assertEqual(s.stage_records["planner"]["accepted"], True)
            with self.assertRaises(IntegrityStop):
                s._scan("test", "text naming private_oracles")


class EvidenceTests(unittest.TestCase):
    def test_dedup_against_visible_and_cap(self):
        pkt = load_packet("grpc1859")
        entries = [{"file_id": "shared/test/end2end_test.go", "start": 6000, "end": 6042, "kind": "read"},
                   {"file_id": "shared/test/end2end_test.go", "start": 100, "end": 120, "kind": "read"},
                   {"file_id": "shared/test/end2end_test.go", "start": 110, "end": 130, "kind": "claim_span"}]
        text, stats = prompts.render_evidence(pkt, entries)
        # 6000-6008 (initial excerpt) and 6010-6042 (helper) are already visible; only the blank line 6009 remains
        self.assertEqual(stats["rendered"], ["shared/test/end2end_test.go:100-130", "shared/test/end2end_test.go:6009-6009"])
        big = [{"file_id": "shared/test/end2end_test.go", "start": 1000 + 300 * i, "end": 1299 + 300 * i, "kind": "read"} for i in range(4)]
        _, stats = prompts.render_evidence(pkt, big)
        self.assertLessEqual(stats["lines"], design_config()["search"]["evidence_carry"]["max_lines"])
        self.assertTrue(stats["omitted"])


if __name__ == "__main__":
    unittest.main()
