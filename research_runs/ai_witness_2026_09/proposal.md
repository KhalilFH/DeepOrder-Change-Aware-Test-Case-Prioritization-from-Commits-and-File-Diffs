# W1 proposal

## Material Passport

- Date: 2026-09-25. Type: experiment proposal; evidence and hypotheses are separated below.
- Primary inputs: the repository's recorded C1 outcomes, preserved source pairs, prior source inspection, and the two linked assessments in README.md.
- Human-read status: no claim that the researcher has personally read the cited papers. No W1 effectiveness results exist.

## Problem and proposed contribution

A relevant test can execute changed code without establishing the state, ordering, or subsequent observation needed to reveal a defect. Repeating such a test may help a scheduling problem but cannot supply an absent action or postcondition.

**Hypothesis:** explicitly identifying the missing prerequisite, with source evidence and an executable test intervention, improves witness yield or cost over a capable model given the same code and execution access. A second hypothesis is that Jev can perform the narrow prerequisite judgments more efficiently or accurately than the same capable model. These are separate claims.

The proposed representation connects four items: an obligation imposed by the production change; the test actions needed to reach it; the ordering/resource conditions needed to expose a violation; and the observation distinguishing defective from repaired behavior. Each assertion carries source locations and a supported/contradicted/unknown judgment. A patch is a hypothesis until independently executed and assessed.

For example, interruption handling may require more than throwing an exception: a subsequent borrower must still obtain capacity. For a lock/channel interaction, starting two goroutines does not prove the intended blocked-send premise occurred. These are development examples already known to the designers, not hidden answers or experimental discoveries.

## Why these cases

Historical evidence from C1: grpc1859 produced 5/60 focal failures, k8s26980 0/60, and istio17860 60/60 on defective variants. Those rates are protocol-specific. The first two offer different possible intervention needs; istio is an already-visible control. POOL-162 adds a Java interruption/resource case, but its old Jev probe used human summaries and had no executable comparison. The new study must restore and test it.

The earlier CI-configuration signal does not establish an AI benefit. W1 leaves C1, Q0/E1, and F1 intact and does not relabel their failures as defect-ground-truth training data.

## Research questions and decisive contrasts

| Question | Comparison | What would be informative |
|---|---|---|
| Can interventions improve the supplied test? | B1–B4 against B0 | Validated witness yield and cost on the same case |
| Does structured prerequisite analysis help? | B3 against B2 | Higher yield or lower cost beyond a strong plain-model baseline |
| Does Jev add incremental value? | B4 against B3 | Improvement attributable to substituting the judgment component |
| Does the result survive retry policy? | Fixed triplets of final-candidate validation | P1 versus accept-on-pass P3 versus retained evidence |

Primary outcome is independently validated witness yield. Explanation quality is secondary and cannot substitute for an executable witness. A no-change submission is allowed and may be the best answer for the already-visible control.

## Relation to existing work and novelty boundary

AI plus static analysis plus fuzzing is already represented by [Themis](https://www.usenix.org/conference/nsdi26/presentation/cao). Resource-intention inference combined with static checking is represented by [InferROI](https://arxiv.org/abs/2311.04448). Differential test generation also predates this proposal: [DiffTGen](https://cs.brown.edu/people/qxin/papers/testgen_issta17.pdf). [Fray](https://arxiv.org/abs/2501.12618) is a relevant controlled-scheduling baseline for compatible Java environments; compatibility with POOL-162 is unverified. Jev offers [typed evaluations](https://docs.typesafe.ai/introduction), not unrestricted test generation or independently verified defect truth.

The candidate contribution is therefore narrower: **does a source-linked assessment of witness prerequisites improve intervention selection under equal information and bounded resources, and does that improve evidence visible under retry?** W1 can establish feasibility and expose failure modes. Four familiar cases cannot establish broad novelty, generalization, calibrated defect probability, or prospective performance. Public-source model contamination remains possible even with clean request packets.

## Expected deliverables and continuation

Deliver an isolated runner, exact input packets and source identities, fixed baseline/template bank, versioned provider adapters, fixed session schedule, independent validation records, cost accounting, and a case-level report including every failure and exclusion.

Advance to a separately designed fresh-case study only under the engineering gates in analysis_plan.md. Do not select fresh cases, train a model, resume TCP, or grow the roster under W1. If static templates win, retain that result. If Jev adds no benefit, omit it from the next design.
