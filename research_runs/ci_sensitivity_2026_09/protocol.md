# CI policy sensitivity — starting protocol

## Freeze record

- Protocol identifier: `ci_policy_sensitivity_starting_protocol_v1`
- Freeze date: 2026-09-10
- Repository: `DeepOrder-Change-Aware-Test-Case-Prioritization-from-Commits-and-File-Diffs`
- Starting commit: `d967dbaaec257613c3e1f2440866801c71d0c00e`
- Worktree provenance: at verification time there were no tracked or staged changes, and `git status --porcelain=v1 --untracked-files=all` reported 2,460 expanded untracked files after this artifact was created. The exact pre-creation worktree status was not independently persisted. A pre-creation count of 2,459 untracked files can only be reconstructed by excluding this artifact from the verified post-creation count; it is not a directly captured fact. No stronger pre-creation provenance claim is made.
- Scope: Task 1 of Section 13 only. No subjects, environments, policies, or experiments have been executed by this record.
- Source plan: `docs/research/NEXT_RESEARCH_ACTION_PLAN.md` at the SHA-256 recorded below.

This file freezes the starting research record for the approved CI policy-sensitivity plan. It does not qualify subjects, establish execution readiness, or authorize work from Tasks 2–5.

## Locked questions and scope

### Feasibility question Q0

Can four usable episodes on at least two projects be qualified economically under the common scientific contract? A usable episode requires an independently justified product defect, acceptable counterpart, inspectable behavioral obligation and witness, identical target/harness and pinned commands across counterparts, a legitimate reset/condition protocol, interpretable outcomes, and acceptable restoration cost.

Q0 is a feasibility and artifact-validity stage, not an effectiveness experiment. Fewer than two qualified development episodes by day 7 stops E1. Fewer than four qualified episodes across two projects by day 10 stops E2. No mutant, forced fault, test-only repair, unverifiable counterpart, or flake label may substitute for a real product-defect episode.

### RQ1

Under the fixed protocol, does accept-on-pass retry produce a material loss of defect-supported blocking while reducing independently verified nuisance blocking? The provisional material margins are `0.10` absolute sensitivity loss and `0.05` absolute nuisance-block reduction. Sensitivity and nuisance are reported separately; absence of verified nuisance supports only a sensitivity statement.

### RQ2

Does a decision-relevant distinction remain after a strong ordinary repeated, paired, signature-aware assessment using the same oracle evidence and fixed observations? If the ordinary A2 baseline resolves the cases, ordinary assessment is sufficient for this cohort and no new assessor is warranted.

### E1 calibration question

Can the paired protocol measure P1/P3 decisions and attributable outcomes on two Q0-qualified intermittent defect episodes without conflating nuisance, product defects, and harness errors? E1 is descriptive calibration and a mechanism probe, not a significance or equivalence test.

## Locked policies and observables

- **P1, one attempt:** run the fixed command once; nonzero blocks and zero accepts.
- **P3, accept-on-pass retry:** run the same job with the predeclared reset, up to three total attempts; stop at the first zero and accept; block only after three nonzero attempts.
- **P3-retain:** execute the same P3 prefix and cost, but report `ACCEPT_WITH_PRIOR_FAILURE` when an earlier failure precedes a passing attempt. It is a reporting control, not an automatic block or escalation rule.

The policy consumes only available exit status. Oracle categories and later evidence are evaluator-only: `PASS`, `FOCAL_DEFECT_WITNESS`, `VERIFIED_NUISANCE`, `OTHER_DEFECT`, `UNRESOLVED`, and `HARNESS_INVALID`. Earlier failures remain in the ledger even when P3 accepts.

The first scope is fresh-process job retries with the same fixed command, reset recipe, target, condition family and environment. Selection, quarantine, learned models, and new predictive components are outside this freeze.

## Locked Q0 gate and budget

- Candidate roster: at most 12 primary candidates plus two nuisance/control candidates, ordered by source tier, project, issue ID and revision hash; at most two primary episodes per project.
- Qualification: run ten fresh single attempts per version. If structural checks pass, run ten more per version regardless of early outcomes.
- Intermittency criterion: at least two focal failures and two passes on `V_bad` across the 20 attempts at the frozen protocol.
- Counterpart rule: independent obligation/fix reasoning and successful witness checks; a contradictory focal witness leaves the pair unresolved.
- Q0 invalidity rule: preserve unresolved/invalid evidence; do not silently replace attempts or broaden defect definitions.
- Resource caps: 12 human hours for metadata/oracle triage; 20 allocated vCPU-hours for restoration and qualification; at most two human restoration hours and four allocated vCPU-hours per primary candidate.
- Q0 continuation: two qualified development episodes by day 7 for E1; four qualified episodes across at least two projects by day 10 for E2.

## Locked E1 design and budget

- Subjects: the first two Q0-qualified episodes in fixed roster order, preferably from different projects; never selected by observed policy loss.
- Collection: 20 paired blocks per episode, two versions per block, three attempts per version, across at least two time batches: 240 primitive attempts total.
- Direct checks: 12 actual early-stopping policy checks balanced across episodes, versions and P1/P3, compared structurally with the reducer.
- Controls: a small identity/no-change control and deterministic-failure control; charge their costs without increasing the episode count.
- Primary recorded quantities: focal sensitivity `S`, nuisance blocking `N`, `L = S(P1) - S(P3)`, `R = N(P1) - N(P3)`, raw blocking, retained prior evidence, prefix attempts and cost.
- Quality gate: invalid fraction at most 10%; structural reset/oracle/policy interpretation must remain valid; all outcomes and intermediate failures must be traceable.
- E1 budget: at most 20 allocated vCPU-hours, including direct checks, controls and implementation verification.
- E1 no-go: contradictory counterpart behavior, forced/synthetic intermittency, result-determining missing evidence, or unaffordable execution. Preserve a qualification/calibration failure report and do not rescue it by relabeling outcomes.

E1 data remain development-only. Any protocol amendment during E1 must be frozen before E2; it does not silently rewrite this starting record.

## Locked broader resource boundary

The plan’s total ceiling is 160 allocated vCPU-hours: Q0 20, E1 20, E2 80, optional E3 20, fallback F1 10, and environment/analysis reserve 10. Conditional allocations do not authorize extra sampling. E2 requires four qualified episodes across at least two projects and uses 100 paired blocks per episode; E3 is unavailable until E2 is complete and its eligibility gate passes. A failed gate triggers the plan’s declared fallback or scoped negative/inconclusive report; it does not broaden the research direction.

## Starting hashes

SHA-256 values were computed before this file was created.

| Role | Path | SHA-256 |
|---|---|---|
| Plan | `docs/research/NEXT_RESEARCH_ACTION_PLAN.md` | `84f1c189c1ce2d360f8e5d49d449797fda4bfc5e7096184ad998ff55fe7ed871` |
| Predecessor | `docs/research/change-aware-tcp-findings-2026-08.md` | `cfea79f0439a543544c28dd5f8941652969336cfff8803ecf2658a7cd9e0821f` |
| Predecessor | `docs/research/ADAPTIVE_CI_RESEARCH_PROGRAM.md` | `99e855df4ec14a57a66f9531ad38b2b07b5f1bb032a57127e516212a93efcc96` |
| Predecessor | `docs/research/INDEPENDENT_RESEARCH_VISION.md` | `6674c11de9d00d9bb364383398ce94bd995403b7b333ed917cf3b13a3ee40748` |
| Predecessor | `docs/research/RESEARCH_DIRECTION_DECISION.md` | `6ada383461d8fd02e755d167b8a439a3b517deb6a3857e470d6478f1bf45767f` |
| Predecessor | `docs/research/ORIGINALITY_AUDIT_AND_NEW_IDEAS.md` | `a83ac859ba5d6592f8e628b8aa4104e292dc1fe0750fb6aed44eb9dd8fe43599` |
| Predecessor | `docs/research/INDUSTRY_VALUE_AND_PERSONAL_ASSESSMENT.md` | `150a23e1fe69b656474b30951bfb11dc5a478069c23ab9c23b490ffd32757b79` |
| Pipeline | `pipeline/fault_structure_probe.py` | `558861fe5012e78a960a923b01838dd34dc774b43f6a8383e6bacd990efedd8a` |
| Pipeline | `pipeline/lrts_adapter.py` | `20867fdde3316353891cc3f295a0dced1bb07a3044647227f7352f2678d12533` |
| Pipeline | `pipeline/relevance_precise.py` | `d721c39434bf309d05abf2e92cd848f44d081880996442403962c1ea540f1902` |
| Pipeline | `pipeline/relevance_t0.py` | `69064d7680fd5c89ad4900f5f7cbd0f736cde6dc5d6ef753043124987dc68714` |
| Pipeline | `pipeline/step1_name_join.py` | `9e75aa9008549f33d6f00ebacaef9be5b44df1ad9acf144eca38dd3849ef35df` |
| Pipeline | `pipeline/step2_baseline.py` | `9fb0aadbc7fde893652909937eec26a4b070f1f55eb013ddaee9c8b0f9d60ba2` |
| Pipeline | `pipeline/step3_precise.py` | `3de94fa6cf1fc175df0e7b85f90f7b49668cb9056c174b55ac8c9e4b2c06acf3` |
| Pipeline | `pipeline/step3_regapfd.py` | `fbb53992d5ea13af9cefb9b7e69a58534b35fb909ef840f285808444e88d100c` |
| Pipeline | `pipeline/step3_t0.py` | `21e5da9113b41c055eda21817ff2acb34b7cde234f82b642fbaa6aeb932cb6c6` |

## Task boundary

Completed by this artifact: starting commit capture, the qualified worktree provenance recorded above, source and pipeline hashes, creation of the future run root, and the locked Q0/E1 protocol. The next plan task is runtime readiness; it is intentionally not performed here.
