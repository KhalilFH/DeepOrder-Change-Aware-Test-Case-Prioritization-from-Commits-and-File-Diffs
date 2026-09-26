# W1 protocol v1

## Material Passport

- Frozen preparation: 2026-09-25. Status: prospective protocol for a retrospective development study; not results.
- Unit: one case × method × search replicate. Cases, not execution attempts, are the units of generalization.

## Enrollment and task

Fixed roster: pool162, grpc1859, k8s26980, istio17860. Enroll a case only if both variants, identical supplied tests, legal editing surface, source identities, execution environment and an independently implementable focal oracle are structurally qualified. Do not require a favorable failure-rate window or a successful positive control on the defective variant. No replacement subjects. At least three cases from three projects must qualify, including at least two of pool162/grpc1859/k8s26980. Report the full four-case roster and every exclusion.

All methods receive the same per-case production diff, source packet, supplied tests, deterministic retrieval output, editing rules, build/run interface, and timeouts. The direction of the production diff is explicitly defective → repaired. This is intentionally retrospective repair-informed test strengthening. Go test packages include tests backported from the repair; POOL uses the specified pre-fix candidates. Analyze and disclose these provenance strata. Do not call the Go inputs pre-fix test availability or the result discovery of an unknown bug.

Hold out the POOL repair-added regression test, issue discussions, human diagnoses, C1 results, oracle implementation and validation results from measured method packets. Coding/oracle preparation may inspect these materials. Method processes must not inherit the whole repository, unrelated logs, Git history, network browsing, or other methods' artifacts. This prevents request-time leakage, not model pretraining contamination. Any detected packet leak invalidates the affected matched block; keep its records and stop for review, without a free replacement.

## Fixed design

- Five arms B0–B4, defined in method_contract.md; no missing-arm substitution.
- Three search replicates per enrolled case and arm. Maximum 60 sessions for four cases; 45 for three cases.
- Each session has a maximum of 600 seconds of elapsed search time, including provider latency, parsing, compilation, execution, tool orchestration and repair. Shared source restoration is separate and reported.
- Each session can submit one immutable final test overlay, including an unchanged overlay. Up to four patch proposals and six paired executions (12 primitive runs) may occur during search. A pair means identical test overlay on both variants; do not selectively evaluate only the promising variant.
- Final submission seals before any independent validation result is available. Search observations are not validation observations. Record submission time; do not claim time to first valid candidate when earlier candidates were not independently validated.
- B0 has the same deadline but uses only unchanged-test execution. It need not waste the full allowance. All methods may stop early. Unused budgets cannot be transferred to another session.
- Search replicates use fresh workspaces/processes and empty method memory. Only immutable common build artifacts may be cached. No cross-session candidate reuse, response caches, conversational history or adaptive prompt tuning.

Create the complete search and validation schedule from the frozen seed before calibration outcomes. Within each replicate round, shuffle cases; within each case, shuffle the five arms. Seal all five final submissions for a case/round before validating any of them. Alternate the first variant using scheduled seeded draws. A subject run is serial; do not overlap methods on the same host. Randomization is reproducible implementation-defined Fisher–Yates, with the concrete schedule and generator code hashed at launch.

## Independent validation

Every legal, buildable final overlay receives exactly five matched triplets per variant: 15 primitive attempts on V_bad and 15 on V_ok. Illegal or unbuildable overlays are INVALID_CANDIDATE, with unexecuted validation slots explicitly marked not run for that reason; they are observed method failures, not missing-outcome upper-bound successes. Each primitive attempt starts a clean subject process/container and clean test state; this is not five process-internal repeats. Both variants use the same final tests, permitted instrumentation, per-triplet seed and resource configuration. Opaque variant IDs may be used; the test cannot branch on them. Preserve order within triplets.

These fixed 30 attempts replace the earlier broad proposal's alternative deterministic/stochastic replay counts. No extension after a promising result. No early efficacy stopping. Stop only for resource or integrity conditions in execution_plan.md; mark remaining cells not run.

A final candidate is a **VALIDATED_WITNESS** only if:

1. It obeys the edit contract and builds on both variants.
2. All 15 V_ok attempts complete as passes, with no missing or unresolved records.
3. At least two V_bad attempts in at least two distinct triplets have independently supported focal failures.
4. The frozen case oracle establishes the relevant premise and violated behavioral consequence. Exit code, arbitrary assertion failure or elapsed timeout alone is insufficient.
5. All other V_bad attempts are interpretable passes or supported focal failures; no unresolved/nonfocal/harness-invalid attempt is silently discarded.

This deliberately strict endpoint means a rare true witness may fail validation within the budget. That is a negative protocol outcome, not proof that the test can never reveal the defect. Report all component counts and individual focal evidence. Do not add a failing assertion merely to distinguish revisions.

## Limits and deviations

Complete B4 requires a qualified Jev adapter; B2–B4 require one identical frozen capable generator model/configuration. Requested model family is GPT-5.6 Sol from the researcher's earlier instruction. A desktop subagent model name does not prove an available API model or reproducible transport. Resolve the actual accessible transport and returned identity at launch; unresolved identity or access means NOT_READY, not a silent substitution.

Scientific changes to roster, arms, shared information, counts, budgets, endpoint, or model family require a dated amendment and a new version preserving v1. Actual pinned dependencies, compatible commands, prompt rendering, provider settings and oracle implementations are runtime launch fields, selected and documented before measured outcomes. No method tuning on W1 calibration or historical outcomes. W1 remains a development study even with careful controls.
