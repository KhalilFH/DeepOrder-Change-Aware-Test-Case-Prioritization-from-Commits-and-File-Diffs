"""Truth-table tests for the E1 policy reducer.

These are implementation-validation tests only. Per the plan (Experiment 1,
"Execution procedure" step 1), synthetic truth-table inputs validate the
implementation and NEVER enter empirical results.

Run with the stdlib (no third-party dependency):

    python -m unittest discover -s e1_harness -v

pytest also collects these if it is available.
"""

import unittest

from policy import (
    BLOCK,
    ACCEPT,
    INDETERMINATE,
    ACCEPT_WITH_PRIOR_FAILURE,
    P1,
    P3,
    P3_RETAIN,
    PolicyError,
    reduce_block,
    focal_evidence_in_prefix,
    blocked_solely_by_nuisance,
    FOCAL_DEFECT_WITNESS,
    VERIFIED_NUISANCE,
    OTHER_DEFECT,
    UNRESOLVED,
    PASS,
)

PASS_STATUS = 0
FAIL_STATUS = 1


class TestP1(unittest.TestCase):
    """P1: execute once. Zero exit accepts; nonzero blocks. Reads attempt 1 only."""

    def test_single_pass_accepts_consuming_one_attempt(self):
        d = reduce_block(P1, [PASS_STATUS])
        self.assertEqual(d.final_status, ACCEPT)
        self.assertEqual(d.attempts_consumed, 1)
        self.assertEqual(d.consumed_indices, (1,))

    def test_single_failure_blocks(self):
        d = reduce_block(P1, [FAIL_STATUS])
        self.assertEqual(d.final_status, BLOCK)
        self.assertEqual(d.attempts_consumed, 1)

    def test_ignores_the_research_only_suffix(self):
        # The block collected 3 attempts for efficiency; P1 must read only the first.
        d = reduce_block(P1, [FAIL_STATUS, PASS_STATUS, PASS_STATUS])
        self.assertEqual(d.final_status, BLOCK)
        self.assertEqual(d.attempts_consumed, 1)
        self.assertEqual(d.research_only_indices, (2, 3))

    def test_empty_block_is_indeterminate_not_a_block(self):
        d = reduce_block(P1, [])
        self.assertEqual(d.final_status, INDETERMINATE)
        self.assertEqual(d.attempts_consumed, 0)

    def test_missing_first_attempt_is_indeterminate(self):
        d = reduce_block(P1, [None, PASS_STATUS])
        self.assertEqual(d.final_status, INDETERMINATE)


class TestP3(unittest.TestCase):
    """P3: up to 3 attempts, stop at first zero exit; block only if all three fail."""

    def test_pass_first_accepts_without_retrying(self):
        d = reduce_block(P3, [PASS_STATUS, FAIL_STATUS, FAIL_STATUS])
        self.assertEqual(d.final_status, ACCEPT)
        self.assertEqual(d.attempts_consumed, 1)
        self.assertEqual(d.research_only_indices, (2, 3))

    def test_fail_then_pass_accepts_consuming_two(self):
        d = reduce_block(P3, [FAIL_STATUS, PASS_STATUS, FAIL_STATUS])
        self.assertEqual(d.final_status, ACCEPT)
        self.assertEqual(d.attempts_consumed, 2)
        self.assertEqual(d.consumed_indices, (1, 2))
        self.assertEqual(d.prior_failure_indices, (1,))

    def test_fail_fail_pass_accepts_consuming_three(self):
        d = reduce_block(P3, [FAIL_STATUS, FAIL_STATUS, PASS_STATUS])
        self.assertEqual(d.final_status, ACCEPT)
        self.assertEqual(d.attempts_consumed, 3)
        self.assertEqual(d.prior_failure_indices, (1, 2))

    def test_fail_fail_fail_blocks(self):
        d = reduce_block(P3, [FAIL_STATUS, FAIL_STATUS, FAIL_STATUS])
        self.assertEqual(d.final_status, BLOCK)
        self.assertEqual(d.attempts_consumed, 3)

    def test_a_pass_beyond_the_retry_budget_cannot_rescue_a_block(self):
        # Four attempts recorded; P3's budget is 3. The 4th is outside the policy
        # and must not turn a block into an accept.
        d = reduce_block(P3, [FAIL_STATUS, FAIL_STATUS, FAIL_STATUS, PASS_STATUS])
        self.assertEqual(d.final_status, BLOCK)
        self.assertEqual(d.attempts_consumed, 3)
        self.assertEqual(d.research_only_indices, (4,))

    def test_truncated_block_is_indeterminate_not_a_block(self):
        # Two failures recorded and no third attempt: the policy cannot decide.
        # Scoring this as a block would invent a decision the data does not support.
        d = reduce_block(P3, [FAIL_STATUS, FAIL_STATUS])
        self.assertEqual(d.final_status, INDETERMINATE)

    def test_missing_attempt_inside_the_consumed_prefix_is_indeterminate(self):
        d = reduce_block(P3, [FAIL_STATUS, None, PASS_STATUS])
        self.assertEqual(d.final_status, INDETERMINATE)

    def test_missing_attempt_outside_the_consumed_prefix_is_harmless(self):
        d = reduce_block(P3, [PASS_STATUS, None, None])
        self.assertEqual(d.final_status, ACCEPT)
        self.assertEqual(d.attempts_consumed, 1)


class TestP3Retain(unittest.TestCase):
    """P3-retain: same prefix and cost as P3; flags an accept that hid a failure."""

    def test_same_cost_and_status_as_p3_on_a_clean_pass(self):
        statuses = [PASS_STATUS, FAIL_STATUS, FAIL_STATUS]
        retain = reduce_block(P3_RETAIN, statuses)
        p3 = reduce_block(P3, statuses)
        self.assertEqual(retain.final_status, p3.final_status)
        self.assertEqual(retain.attempts_consumed, p3.attempts_consumed)
        self.assertIsNone(retain.report_flag)

    def test_flags_accept_with_prior_failure_and_links_the_failures(self):
        retain = reduce_block(P3_RETAIN, [FAIL_STATUS, FAIL_STATUS, PASS_STATUS])
        self.assertEqual(retain.final_status, ACCEPT)
        self.assertEqual(retain.report_flag, ACCEPT_WITH_PRIOR_FAILURE)
        self.assertEqual(retain.prior_failure_indices, (1, 2))

    def test_the_flag_is_not_a_block(self):
        # Explicitly: P3-retain is a reporting control, not an automatic block.
        retain = reduce_block(P3_RETAIN, [FAIL_STATUS, PASS_STATUS, PASS_STATUS])
        self.assertEqual(retain.final_status, ACCEPT)

    def test_retains_p3_result_when_all_attempts_fail(self):
        retain = reduce_block(P3_RETAIN, [FAIL_STATUS, FAIL_STATUS, FAIL_STATUS])
        self.assertEqual(retain.final_status, BLOCK)
        self.assertIsNone(retain.report_flag)


class TestCostAndPrefixIdentity(unittest.TestCase):
    """P1 and P3 share a prefix-generating procedure; that is what licenses replay."""

    def test_p1_prefix_is_a_prefix_of_the_p3_prefix(self):
        for statuses in (
            [PASS_STATUS, PASS_STATUS, PASS_STATUS],
            [FAIL_STATUS, PASS_STATUS, PASS_STATUS],
            [FAIL_STATUS, FAIL_STATUS, PASS_STATUS],
            [FAIL_STATUS, FAIL_STATUS, FAIL_STATUS],
        ):
            with self.subTest(statuses=statuses):
                p1 = reduce_block(P1, statuses)
                p3 = reduce_block(P3, statuses)
                self.assertEqual(
                    p3.consumed_indices[: p1.attempts_consumed], p1.consumed_indices
                )
                self.assertLessEqual(p1.attempts_consumed, p3.attempts_consumed)

    def test_p3_never_costs_more_than_the_retry_budget(self):
        d = reduce_block(P3, [FAIL_STATUS] * 10)
        self.assertEqual(d.attempts_consumed, 3)


class TestPolicyReadsOnlyExitStatus(unittest.TestCase):
    """The operational policy must not see oracle annotations (plan 4.2)."""

    def test_rejects_oracle_categories_passed_as_statuses(self):
        with self.assertRaises(PolicyError):
            reduce_block(P3, [FOCAL_DEFECT_WITNESS, PASS_STATUS])

    def test_rejects_an_unknown_policy(self):
        with self.assertRaises(PolicyError):
            reduce_block("P2-quarantine", [PASS_STATUS])

    def test_rejects_a_non_integer_status(self):
        with self.assertRaises(PolicyError):
            reduce_block(P1, ["0"])


class TestEvidenceRestrictedToVisiblePrefix(unittest.TestCase):
    """S counts focal evidence only where the policy could have seen it."""

    def test_focal_evidence_in_the_consumed_prefix_counts(self):
        statuses = [FAIL_STATUS, FAIL_STATUS, FAIL_STATUS]
        cats = [{FOCAL_DEFECT_WITNESS}, {UNRESOLVED}, {UNRESOLVED}]
        d = reduce_block(P3, statuses)
        self.assertTrue(focal_evidence_in_prefix(d, cats))

    def test_focal_evidence_only_in_the_research_suffix_does_not_count(self):
        # P3 accepted at attempt 1, so it never saw the later focal witness.
        statuses = [PASS_STATUS, FAIL_STATUS, FAIL_STATUS]
        cats = [{PASS}, {FOCAL_DEFECT_WITNESS}, {FOCAL_DEFECT_WITNESS}]
        d = reduce_block(P3, statuses)
        self.assertFalse(focal_evidence_in_prefix(d, cats))

    def test_p1_and_p3_can_disagree_on_the_same_block(self):
        # This is the sensitivity loss L the experiment exists to measure.
        statuses = [FAIL_STATUS, PASS_STATUS, PASS_STATUS]
        cats = [{FOCAL_DEFECT_WITNESS}, {PASS}, {PASS}]
        p1 = reduce_block(P1, statuses)
        p3 = reduce_block(P3, statuses)
        self.assertEqual(p1.final_status, BLOCK)
        self.assertTrue(focal_evidence_in_prefix(p1, cats))
        self.assertEqual(p3.final_status, ACCEPT)
        self.assertFalse(focal_evidence_in_prefix(p3, cats))

    def test_evidence_requires_a_block_not_merely_a_witness(self):
        # S is about the final blocking outcome being defect-supported.
        statuses = [FAIL_STATUS, PASS_STATUS, PASS_STATUS]
        cats = [{FOCAL_DEFECT_WITNESS}, {PASS}, {PASS}]
        d = reduce_block(P3, statuses)
        self.assertEqual(d.final_status, ACCEPT)
        self.assertFalse(focal_evidence_in_prefix(d, cats))

    def test_indeterminate_block_yields_no_evidence(self):
        d = reduce_block(P3, [FAIL_STATUS, FAIL_STATUS])
        self.assertFalse(focal_evidence_in_prefix(d, [{FOCAL_DEFECT_WITNESS}] * 2))

    def test_category_list_shorter_than_the_prefix_is_an_error(self):
        d = reduce_block(P3, [FAIL_STATUS, FAIL_STATUS, FAIL_STATUS])
        with self.assertRaises(PolicyError):
            focal_evidence_in_prefix(d, [{FOCAL_DEFECT_WITNESS}])


class TestNuisanceIsNotTheDefault(unittest.TestCase):
    """N counts only blocks caused solely by independently verified nuisance."""

    def test_block_solely_from_verified_nuisance_counts(self):
        d = reduce_block(P3, [FAIL_STATUS] * 3)
        cats = [{VERIFIED_NUISANCE}] * 3
        self.assertTrue(blocked_solely_by_nuisance(d, cats))

    def test_an_unresolved_failure_is_not_nuisance(self):
        d = reduce_block(P3, [FAIL_STATUS] * 3)
        cats = [{VERIFIED_NUISANCE}, {UNRESOLVED}, {VERIFIED_NUISANCE}]
        self.assertFalse(blocked_solely_by_nuisance(d, cats))

    def test_another_real_defect_is_not_nuisance(self):
        d = reduce_block(P3, [FAIL_STATUS] * 3)
        cats = [{VERIFIED_NUISANCE}, {OTHER_DEFECT}, {VERIFIED_NUISANCE}]
        self.assertFalse(blocked_solely_by_nuisance(d, cats))

    def test_a_focal_witness_is_not_nuisance(self):
        d = reduce_block(P3, [FAIL_STATUS] * 3)
        cats = [{VERIFIED_NUISANCE}, {FOCAL_DEFECT_WITNESS}, {VERIFIED_NUISANCE}]
        self.assertFalse(blocked_solely_by_nuisance(d, cats))

    def test_an_accept_is_never_a_nuisance_block(self):
        d = reduce_block(P3, [FAIL_STATUS, PASS_STATUS, PASS_STATUS])
        cats = [{VERIFIED_NUISANCE}, {PASS}, {PASS}]
        self.assertFalse(blocked_solely_by_nuisance(d, cats))

    def test_multiple_categories_on_one_attempt_are_not_flattened(self):
        # Plan 4.2: record sets; do not collapse two simultaneous causes.
        d = reduce_block(P3, [FAIL_STATUS] * 3)
        cats = [
            {VERIFIED_NUISANCE},
            {VERIFIED_NUISANCE, FOCAL_DEFECT_WITNESS},
            {VERIFIED_NUISANCE},
        ]
        self.assertFalse(blocked_solely_by_nuisance(d, cats))
        self.assertTrue(focal_evidence_in_prefix(d, cats))


if __name__ == "__main__":
    unittest.main()
