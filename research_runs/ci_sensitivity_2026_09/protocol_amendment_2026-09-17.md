# Protocol amendment — timing interpretation

- Amendment identifier: `ci_policy_sensitivity_timing_amendment_2026-09-17_v1`
- Amendment date: 2026-09-17
- Scope: timing interpretation and prospective operational-clock bookkeeping only
- Status: approved provenance amendment; no subject acquisition, restoration, qualification, E1, or F1 execution

## 1. Preservation of the original freeze

This amendment does not modify `protocol.md` and does not silently rewrite its original calendar interpretation. The September 10, 2026 freeze recorded in `protocol.md` remains historically authoritative for the starting protocol, its calendar framing, its gates, its scientific contract, and its resource ceilings.

The elapsed wall-clock interval after that freeze included setup, provenance inspection, source retrieval, evidence reconciliation, and tooling/document work. That elapsed interval is not treated by itself as an operational Q0 day count and does not, by itself, trigger the Q0 fallback. No candidate-acquisition or candidate-restoration action has started under this amendment as of its creation.

The hashes below make the decision point reproducible. They are hashes of the files as inspected before this amendment was written; none of those source files is modified by this amendment.

| Role | Path | SHA-256 |
|---|---|---|
| Original frozen protocol | `research_runs/ci_sensitivity_2026_09/protocol.md` | `67f2ea2913ee5566731d4f6e5f0c45a1c821d8a5058a23b0d5c8ae72341fdf45` |
| Task 3 artifact | `research_runs/ci_sensitivity_2026_09/baseline_applicability.md` | `6ef20f49e3cde8365266dd1a84c5afdc5372928fa42511a77252198928123ccb` |
| Task 4 artifact | `research_runs/ci_sensitivity_2026_09/candidate_cards.md` | `67b46c590ada9df2e32c09bda125965acdbc8fe56394e648b28c33ec9bf41a67` |

Task 4's earlier recommendation to restore POOL-162 first is preserved as historical provenance in `candidate_cards.md` and `baseline_applicability.md`. That recommendation is superseded prospectively by this amendment, before any Q0 qualification execution: the next bounded metadata action is B, concerning DBCP-65. This supersession changes neither the historical recommendation nor the original freeze.

## 2. Prospective operational clock

1. The operational Q0 clock begins prospectively at the first post-amendment candidate-acquisition or restoration action.
2. When that first action occurs, record its exact UTC timestamp in the contemporaneous ledger or action record. Do not backdate it to the September 10 freeze or to any setup/provenance/tooling event.
3. The creation and recording of this amendment are provenance work, not candidate acquisition or restoration, and do not start that clock.
4. Once the operational clock starts, unsuccessful metadata acquisition, restoration, qualification, and candidate rejection count normally. They cannot later be reclassified as setup.
5. Operational day 7 still requires at least two qualified primary intermittent episodes before E1.
6. Operational day 10 still requires at least four qualified episodes across at least two projects before E2.
7. If the required cohort cannot be obtained within the remaining source, candidate, human-hour, compute, and operational-day limits, F1/no-go applies as specified by the approved plan. The clock interpretation does not authorize a budget increase or a broadened defect definition.

## 3. Scientific criteria unchanged

All scientific criteria in the September 10 freeze remain unchanged:

- authentic product defect;
- independently supported `V_bad`/`V_ok`;
- identical and frozen target and harness;
- non-forced intermittency for primary episodes;
- at least two focal failures and at least two passes among 20 frozen-protocol `V_bad` attempts;
- acceptable-counterpart witness validity;
- causal and temporal integrity.

No source-order change converts a stable control into a primary intermittent episode. No later release is accepted as `V_ok` without the existing obligation/fix and witness reasoning.

## 4. Resource ceilings unchanged

The approved resource caps remain unchanged:

- 12 total metadata/oracle human hours;
- source-specific allowances from the approved plan, including the four-hour primary Java defect-lead allowance and the other source-order allowances;
- 20 allocated Q0 vCPU-hours;
- at most two human restoration hours and four allocated vCPU-hours per primary candidate;
- roster ceiling of 12 primary candidates plus two controls;
- first-active-ten-day combined ceiling of 40 allocated vCPU-hours.

The amendment is bookkeeping only. It does not reclassify setup as free research, release any cap, or authorize restoration of a previously deferred control without a new budgeted decision.

## 5. Revised near-term sequence

The approved near-term sequence is:

- **B:** perform one bounded DBCP-65 metadata pass.
- If B is unsuccessful, preserve DBCP-65 as `UNRESOLVED` and proceed conditionally to **C** under the remaining deterministic source order.
- Do not repeatedly reopen DBCP-65.
- Defer POOL-162 restoration unless later justified as a deliberately budgeted control.
- F1/no-go occurs when the required cohort cannot be obtained inside the remaining source, candidate, human-hour, compute, and operational-day limits.

B is metadata acquisition only. It is not restoration, qualification, E1, or F1. If B becomes the first candidate-acquisition action, its exact timestamp starts the operational Q0 clock and must be recorded then. If an earlier candidate-acquisition or restoration action occurs instead, that earlier action starts the clock and must be recorded without backdating.

## 6. Timing decision

The September 10 calendar remains the historical record. The operational day counter is a separate prospective counter anchored to the first post-amendment candidate-acquisition/restoration action. The distinction is required to avoid both silent rewriting of the freeze and retroactive treatment of unsuccessful post-start work as setup.

## Amendment verdict

**AMENDMENT VERDICT: PASS WITH ISSUES**

The interpretation is internally consistent and preserves the original freeze, gates, criteria, and caps. The issue is accounting precision: durable records do not provide exact human-hour expenditure for Task 3 or Task 4, so the amendment authorizes only a bounded, explicitly logged next pass rather than asserting a numeric remaining-hour balance.
