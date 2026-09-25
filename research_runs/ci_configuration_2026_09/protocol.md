# C1 protocol — design freeze v1

## Material Passport

- Date: 2026-09-25; identifier: `c1_ci_configuration_visibility_v1`.
- Status: **adopted design, frozen before C1 implementation/calibration; not an executable-launch or execution record**. See [DESIGN_FREEZE.md](DESIGN_FREEZE.md).
- Baseline: `3f984da9095d19afc239a91945043758da43deec`.
- Scope: one host, six fixed existing subjects, two CPU profiles, fresh-container tests and three deterministic reporting/gating policies.

## 1. Evidence and hypotheses

**Established evidence:** the September Q0 records report focal-failure counts of 16, 2, 1, 18, 20 and 0 out of 20 on the six defective variants, respectively. All acceptable variants passed those 20 attempts. E1 observed five paired blocks in which P1 blocked with a focal witness and P3 accepted after a retry. No verified nuisance was observed. These are historical convenience-sample observations, not C1 data.

**Inference:** eligibility for the earlier experiment depended partly on observed frequency in one execution environment. CPU conditions might change visibility or the effect of retry, but the records do not establish that mechanism.

**Proposal:** preserve the six subjects and change one explicit resource setting. Do not require intermediate failure rates to enter C1.

- **RQ1:** How does a two-CPU bandwidth quota change defect-supported blocking relative to an unrestricted reference, under P1 and P3? Null: no difference for each subject/policy. Alternative: either direction, with 0.20 absolute difference as a pilot follow-up signal, not a significance threshold.
- **RQ2:** Does the configuration change the loss of supported blocking from P1 to P3? Null: equal retry loss across profiles. This interaction is secondary; CPU effects alone need not imply a new policy mechanism.
- **RQ3:** Are findings adequately described by ordinary paired repetitions, signatures, and uncertainty bounds? If yes, the result supports ordinary assessment; it does not justify a learned or adaptive assessor.

**Open question:** whether resource changes reduce independently established nuisance while preserving defect visibility. C1 can answer this only if verified nuisance is actually observed; it cannot manufacture a tradeoff by treating all fixed-version failures as nuisance.

## 2. Enrollment

Fixed order: `etcd5509`, `etcd7492`, `grpc1859`, `grpc2391`, `istio17860`, `k8s26980`. See [subject register](subject_register.md).

Enroll on structural evidence: product defect, justified counterpart, identical test/harness across variants, reproducible pinned images/dependencies, interpretable obligation and oracle, and a supported execution environment. Do not require a new focal failure or a pass/fail mix during preparation. Stable and unobserved defects are retained as informative conditions.

Distinguish a historical pair with an identical test backport from a controlled historical-fix reversal. A backported regression test permits retrospective assessment; it does not establish prospective test-selection capability.

Unavailable or invalid artifacts receive a reason and remain in the enrollment table. No replacement candidates, project shopping or new benchmark search. At least four structurally ready pairs across two projects are required to launch this pilot. Fewer means an artifact-feasibility report, with no measured C1 launch. Report omitted subjects and selection limits even when this gate passes.

## 3. Profiles: one resource intervention

Required host: the same class of Linux Docker VM with **16 visible logical CPUs** used for E1. Its actual identity, memory, kernel, engine, cgroup version and background load must be recorded anew. A different CPU count requires an explicit pre-data protocol revision; do not silently redefine the reference.

| Setting | R: reference | L: limited |
|---|---|---|
| CPU bandwidth quota | no container quota | 200000 microseconds per 100000-microsecond period |
| Docker resource arguments | no CPU-limit argument | `--cpu-period=100000 --cpu-quota=200000` |
| Runtime parallelism | explicit `GOMAXPROCS=16` | explicit `GOMAXPROCS=16` |
| CPU affinity | same unrestricted affinity | same unrestricted affinity |
| Memory/network/test/timeout/reset | fixed for the subject | identical |
| Allocated-capacity accounting | 16 vCPUs | 2 vCPUs |

This compares **CPU bandwidth**, not two pinned CPU cores, not different runtime parallelism, and not an entire cheaper cloud instance. Keep both profiles on the same VM. No stressor, artificial sleep, concurrency injection, changed timeout, environment rotation or test-source edit. Declaring `GOMAXPROCS` explicitly makes C1 a new controlled experiment; it is not an exact E1 rerun.

Docker documents quotas separately from affinity; configuration semantics were checked through Context7 against [Docker run reference](https://docs.docker.com/reference/cli/docker/container/run/) on 2026-09-25. Actual enforcement still needs runtime checks. Capture inspect/cgroup evidence outside the subject process and avoid monitoring that materially perturbs one profile only.

The code/test contract must permit execution under both profiles. A timeout under a constrained profile is not automatically a product defect. Review each oracle for generic slowness susceptibility before freeze; use `UNRESOLVED` where the witness cannot distinguish it. A matching focal signature on the acceptable variant triggers a pair-validity review, never automatic nuisance attribution.

## 4. Policies and observations

- P1: one attempt; zero accepts, nonzero blocks.
- P3: at most three attempts; accept on first zero, otherwise block.
- P3-retain: same execution and final gate as P3; flag acceptance preceded by failure.

Reuse E1's prefix semantics. Policies consume exit statuses only. Oracle annotations, counterpart outcomes and future attempts are evaluator-only. A policy may not inspect the research-only suffix collected after its stop point. A retained warning is not a blocked defect or a proven actionable diagnosis.

Preserve pass/fail, complete output, signature matches, elapsed time, actual CPU use where available, profile verification and provenance. Categories remain `PASS`, `FOCAL_DEFECT_WITNESS`, `VERIFIED_NUISANCE`, `OTHER_DEFECT`, `UNRESOLVED`, `HARNESS_INVALID`. Mechanical matching cannot establish nuisance or other-defect causality.

## 5. Sample and collection

Ten matched blocks per enrolled subject. Each block contains four cells: R/bad, R/ok, L/bad, L/ok. Collect three fresh-container attempts consecutively within each cell regardless of earlier outcomes. Twelve attempts/block; six subjects produce **720 measured attempts**. Four subjects produce 480. Old Q0/E1 attempts never enter C1 denominators.

Each block matches nearby executions, not identical random thread schedules. There are ten block observations per subject, not 120 independent defects. Runtime nondeterminism is not controlled by the ordering seed.

Generate the entire schedule before calibration outcomes are inspected:

- Batch A: blocks 1–5; batch B: blocks 6–10, on a separately timestamped session.
- Within each block index, sort enrolled subjects by SHA-256 of `c1-v1:subject-order:<block>:<subject>`.
- Within subject/block, sort the four fixed cell labels by SHA-256 of `c1-v1:cell-order:<subject>:<block>:<profile>:<variant>`.
- Ties break lexicographically. Save literal UTF-8 strings and resulting order. Do not redraw for appealing balance.
- Attempts within a cell remain 1, 2, 3. No overlapping subject jobs or builds. Fixed two-second pause after each attempt's cleanup; record additional delays and interruptions.

This deterministic hash order is a reproducible, outcome-independent ordering rule, not a claim of perfect balance. Report actual order balance. No outcome-driven stopping of individual cells, added repetitions or substitution of passes for missing attempts.

## 6. Budget and stopping

**Adopted new C1 ceiling: 40 allocated vCPU-hours**, independent of all old caps: preparation/rebuild 8, validation/calibration 6, measured collection 24, analysis/archive 2. Also log active researcher time; cap preparation at 8 active hours, at most 2 per pair. Unknown historical human time stays unknown. Do not transfer stage budgets silently.

Charge unrestricted builds/probes at 16; limited runs at 2 only after enforcement is verified. Include full research suffixes and cleanup in research spend. Record host-reservation cost (16 times total elapsed job time) separately: a two-CPU quota on an already reserved VM does not prove a smaller bill. Actual CPU seconds, elapsed time and capacity-hours are distinct fields.

Before collection, project cost from old durations plus fixed calibration, including a conservative timeout bound. The projection is not a promise. Before admitting each complete matched block, reserve `3 * (16 + 2) * 2 * (outer_timeout + 30 seconds cleanup + 2 seconds gap) / 3600` capacity-hours. This conservative reservation assumes both variants reach the subject timeout; release unused reservation after the block. Stop if the remaining measured cap cannot cover it. Record costs already spent even on failed preparation.

Stop the affected subject on a focal witness on its acceptable counterpart, an unapproved source/environment change, or invalid oracle assumptions. Stop all collection on corrupted provenance, unenforced profiles, cleanup failure, unknown running containers from this study, or budget exhaustion. Do not remove unrelated user containers. Preserve every affected observation.

After batch A, check only integrity, resource projection and validity. Stop a subject if more than 10% of its scheduled attempts so far are harness-invalid. Unresolved classifications are retained, not relabelled to pass. Comparative policy effects do not govern batch B. There is no significance-based early stopping.

## 7. Gates and disposition

| Gate | Pass | Otherwise |
|---|---|---|
| C0 structural readiness | at least four pairs/two projects, source/test/oracle/runtime dossier complete | close as artifact feasibility; no replacement search |
| C1 implementation readiness | CPU enforcement, identity/reset, policy-prefix and oracle checks pass; schedule, commands and budget frozen | repair implementation before measured data; keep failed checks |
| C2 pilot interpretability | completed comparisons for at least four pairs/two projects; at most 10% invalid attempts per analyzed subject; uncertainty bounds shown | report incomplete/inconclusive; no effect conclusion |
| C3 follow-up signal | at least one valid subject/policy has absolute primary contrast >=0.20, same nonzero direction in both batches, and conservative missing-label bounds retain that direction | no automatic expansion; close with descriptive findings |
| C4 confirmatory study | fresh data under a separately powered, preregistered design; preferably a new project/host; prior-art overlap resolved | no strong generalization or new-assessor claim |

C3 is a development triage rule, not statistical confirmation. Intervals may remain wide even when it passes. A null or uncertain pilot does not establish configuration equivalence. If ordinary signature-aware paired assessment suffices, retain it as the outcome rather than proposing a model.

## 8. Novelty and limits

Resource-sensitive flakiness is established prior work: [The Effects of Computational Resources on Flaky Tests](https://arxiv.org/abs/2310.12132), [Shaker artifacts](https://github.com/STAR-RG/shaker-artifacts-icsme). The repository's [originality audit](../../docs/research/ORIGINALITY_AUDIT_AND_NEW_IDEAS.md) also identifies mutation-guided CI assessment such as YourBase. C1 claims no discovery of resource effects or of CI assessment in general. Its proposed value is a controlled, independently grounded test of what happens to product-defect evidence under configurations and retry. A focused comparison is required before claiming novelty.

Six known subjects, one host, historical tests, coarse signatures, reconstruction drift and only ten blocks limit conclusions. Static TCP tables cannot supply missing configuration outcomes. Mutants are not substitutes for these defects. No agents, LLMs, model training, test selection, quarantine, generated tests, automatic release decisions or platform construction are included.
