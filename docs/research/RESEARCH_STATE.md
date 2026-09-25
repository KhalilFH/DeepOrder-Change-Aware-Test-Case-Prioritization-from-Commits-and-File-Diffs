# Current Research State

This document is the authoritative description of the project's current research direction.

## Latest result — C1 post-collection review, 2026-09-25

C1 collection is complete: 720/720 attempts, both batches. Frozen mechanical annotation and matched analysis have now run, with independent arithmetic checks. All 360 acceptable-variant attempts passed; no nuisance reduction was observed. C2 passes; the C3 development signal occurs only for etcd5509, where limited CPU increased supported blocking (P1 7/10 to 10/10; P3 5/10 to 7/10). All primary simultaneous intervals include zero. This supports considering fresh confirmation, not a confirmed configuration effect or an adaptive-system claim.

See the [post-collection review](../../research_runs/ci_configuration_2026_09/analysis_audit/POST_COLLECTION_REVIEW.md) and [mechanical report](../../research_runs/ci_configuration_2026_09/analysis/report.md). This update supersedes the earlier pending-readiness status below. No new subject run, implementation change, commit or push occurred during analysis. C4 remains unstarted.

## Current routing update — 2026-09-25

**Adopted next work:** C1, CPU configuration and defect visibility. The researcher requested design freeze and an implementation handoff. Read the [C1 entry point](../../research_runs/ci_configuration_2026_09/README.md) and [design freeze](../../research_runs/ci_configuration_2026_09/DESIGN_FREEZE.md). The design is frozen; implementation, current artifact readiness and operational launch validation remain pending. No C1 executions are claimed.

**Established prior results:** Q0/E1 closed expansion under G1b (three qualified episodes; no nuisance observed in E1). F1 reproduced Airavata score records and found small descriptive effects under the declared fault mappings, with a demonstrated aggregate-record evidence gap. See the [feasibility report](../../research_runs/ci_sensitivity_2026_09/feasibility_report.md) and [F1 report](../../research_runs/ci_sensitivity_2026_09/f1/report.md).

This dated entry supersedes the unfilled legacy routing placeholders below for near-term execution. The Jev shortlist remains deferred; no benefit is established. Prior failed gates and historical findings remain unchanged.

## Current Research Question

To be reconstructed and confirmed from the existing Airavata, HBase, and Hive research trajectory before new canonical experiments are started.

## Current Evidence

Primary existing evidence includes:

- `docs/research/change-aware-tcp-findings-2026-08.md`
- the change-aware pipeline under `pipeline/`
- historical research branches
- existing experiment outputs and reports

## Established Results

To be consolidated from reproducible prior evidence.

## Active Hypotheses

To be defined after trajectory reconstruction.

## Rejected or Unsupported Hypotheses

To be reconstructed from prior negative and inconclusive experiments.

## Open Questions

To be defined after the baseline audit.

## Next Experiments

New experiments should follow from the reconstructed research state rather than from old branch names or abandoned hypotheses.

## Research Shortlist

### Jev semantic change-to-test relevance

- Added: 2026-09-18, following user agreement to shortlist the idea.
- Status: shortlisted; exploratory playground checks completed, but no integration or canonical experiment started.
- Hypothesis: TypeSafe AI's Jev could identify semantic relationships between a code change and a test that the current path/name relevance signal misses.
- Proposed integration: score a diff against test context and add the resulting relevance score as a feature in the existing prioritization pipeline.
- Prerequisite: complete trajectory reconstruction and the baseline evidence audit before defining a canonical experiment.
- Candidate comparison: history alone, history + current relevance, and history + current relevance + Jev, using a bounded offline temporal evaluation. Assess incremental ranking quality, latency, and cost.
- Evidence threshold: retain only if it adds measurable value over the cheap relevance baseline; existing findings suggest recurring/flaky failures limit the available gains. No benefit from Jev on this project's data has been established.
- Validity and reproducibility: use only context available before each evaluated test run; cache exact requests and responses and record model versions. Treat confidence as a model judgment, not an established test-failure probability. Assess possible foundation-model training contamination on historical repositories; causal request inputs alone do not rule it out. Any future-outcome labels remain retrospective evaluation oracles only.
- References: [TypeSafe documentation](https://docs.typesafe.ai/introduction), [launch announcement](https://typesafe.ai/blog/introducing-system-one-models-and-jev), and [existing project findings](change-aware-tcp-findings-2026-08.md).

#### Exploratory playground observations (2026-09-20)

- **Observed:** On a synthetic retry-boundary example, Jev distinguished a test of the modified boundary (1.99/2), a test of an unchanged case in the same function (0.99/2), and an unrelated test (0/2) across two playground calls.
- **Observed:** On a summarized real [Apache Commons Pool POOL-162 fix](https://github.com/apache/commons-pool/commit/674a6ba9877d2de7224306c83e7871e1eddeab93) with three test methods present at the [pre-fix parent](https://github.com/apache/commons-pool/tree/280c60ac3e918eb7fe8fb542847913bb5317cbc6/src/test/org/apache/commons/pool/impl), Jev `jev-1.13.0` scored `TestGenericObjectPool.testWhenExhaustedBlock` = 1/2, `TestGenericKeyedObjectPool.testWhenExhaustedGrow` = 1/2, and `TestStackObjectPool.testBorrowFromEmptyPoolWithNullFactory` = 0.01/2. The rubric's level 1 meant use of a changed implementation without interrupting a waiting borrower; level 0 meant an unrelated implementation. Playground request ID: `playground_1a1b009856466f44481af269f9ae45cde70`; reported usage: 852 input tokens, 46 output tokens, 116.7 ms evaluation time.
- **Interpretation and limit:** The observed classifications match the supplied rubric. None of those pre-fix tests exercises the interrupted-waiter behavior; the direct witness was added in the fix commit and cannot be treated as a prospective candidate. The state was a human summary of the patch and test methods, not raw source. This probe has no observed test outcomes, no T0 comparison, and no evidence of incremental TCP benefit. Reported timing is one API evaluation, not an end-to-end latency benchmark.
