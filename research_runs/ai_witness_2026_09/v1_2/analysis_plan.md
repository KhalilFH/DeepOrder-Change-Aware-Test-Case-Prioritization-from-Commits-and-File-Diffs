# W1 analysis plan v1

## Material Passport

- Date: 2026-09-25. Prespecified descriptive development-study analysis.
- No population-level significance, powered superiority, diagnostic-accuracy or causal TCP claim is planned.

## Primary endpoint and denominator

For each enrolled case and arm, report number of VALIDATED_WITNESS submissions out of the three scheduled search replicates, applying protocol.md exactly. Also report at-least-one-witness case coverage per arm. Always show the four-case roster; structurally excluded cases have excluded status, not zero success and not an undisclosed disappearance.

Every scheduled replicate remains visible. No submission, provider failure, budget exhaustion, illegal patch, compile failure and invalid final candidate are not successes. Incomplete independent validation is unresolved, not a repaired pass or verified negative. Report observed success/3 and a missingness interval [success/3, (success + unresolved scheduled replicates)/3]. This is an identification bound, not a confidence interval. Fully observed method failures are not included in the upper bound.

Classify final outcomes using these ordered rules: integrity/harness uncertainty → UNRESOLVED; no parseable final submission → NO_SUBMISSION; illegal patch or compile failure → INVALID_CANDIDATE; any independently attributable V_ok nonpass → COUNTERPART_FAILURE; incomplete or uninterpretable validation → UNRESOLVED; all success conditions → VALIDATED_WITNESS; otherwise → NO_WITNESS_WITHIN_BUDGET. Preserve reason codes and raw attempt states so this single label never hides a second problem.

## Comparisons

Tabulate B1/B2/B3/B4 minus B0 per case. The central structure contrast is B3 minus B2; the Jev contrast is B4 minus B3. Show differences in successful replicates (out of three) and case coverage; do not pool 1,800 attempts as independent samples. At most four heterogeneous, familiar cases do not support reliable population intervals. Do not claim superiority from whichever arm happens to win after multiple comparisons.

Separate POOL's pre-fix-candidate task from the Go repair-backported-test tasks. Show istio as a control and show the other cases individually. A high-yield unchanged control can inflate pooled averages; report results both with and without it without changing the primary roster.

## Cost and timing

Report actual input/output tokens, generator calls, Jev evaluations, provider USD, allocated vCPU-hours and elapsed wall time by arm/case/stage. Preserve failed calls and unsuccessful patches. Show common preparation and oracle-author effort separately; do not make it disappear by amortizing over hypothetical future deployments.

Define capped time to validated submission as submission elapsed seconds for a subsequently validated final candidate, otherwise 600 seconds. This is a budgeted utility summary, not a survival-analysis estimate or time to the first valid intermediate patch. Show its components and actual time consumed; an early unsuccessful stop can consume less than its assigned 600-second penalty. Never call unchanged submission at time zero a newly synthesized test.

USD per validated candidate is undefined when there are zero successes; report raw total cost and zero success rather than divide by zero or drop the arm. Do not add USD, human hours and CPU hours into one unexplained scalar.

## Retry-policy visibility

For every final candidate with complete interpretable validation, each defective triplet yields:

- P1 supported blocking: the first attempt is a supported focal failure.
- P3 accept-on-pass supported blocking: all three attempts are supported focal failures.
- P3-retain evidence: any attempt is a supported focal failure, even if a later pass would accept the change.

Report each out of five triplets, plus focal attempts out of 15. These are matched retrospective policy replays, not additional independent experiments. On acceptable variants report actual pass/fail outcomes; do not call any failure nuisance reduction without an independent nuisance classification. For incomplete triplets give lower/upper bounds consistent with observed attempts. A failed-but-nonfocal attempt is not supported blocking.

## Diagnosis and error analysis

Preserve source-linked claims and supported/contradicted/unknown responses. Describe unsupported certainty, missing input, unestablished ordering, absent postcondition, wasted intervention on an already adequate test, and false differential failures. These are explanatory categories, not prevalidated ground truth. Jev confidence remains a model score.

No headline diagnosis accuracy or false-adequate rate is permitted without a separately frozen reference-label procedure and independent assessors. If human assessment is added, record assessor exposure and agreement; do not silently count the proposal authors' known diagnoses as an independent test set. Execution remains the primary outcome.

## Engineering decisions after a complete study

These gates choose whether to invest in a fresh study; they are not significance thresholds. They apply only when all three replicates for every enrolled arm/case have complete outcomes and there is no unresolved integrity problem.

1. Consider structured analysis worth a fresh-case study if B3 exceeds B2's success count on at least two noncontrol cases from two projects without a lower count on another enrolled case; **or** has the identical per-case success vector, at least two noncontrol cases with successes, at least 20% lower mean capped time to validated submission, and no increase in total provider USD or allocated execution CPU cost.
2. Consider retaining Jev only if B4 meets that same incremental rule against B3. If B4 helps but B3 does not beat B2, also require and report the corresponding B4-versus-B2 comparison before advancing the combined method.
3. Compare any advancing AI method against B1 under the same rule. If a deterministic method is as good at lower cost, prioritize that explanation; do not claim the AI component is necessary.
4. No advancement from the already-visible istio control alone. Incomplete studies are inconclusive for these gates. No automatic fresh-case enrollment follows.

Regardless of gates, publish the full case table, invalid outputs, exclusions, resource stops and negative results in the local report. Fresh-case feasibility, larger confirmation and later causal TCP evaluation require new protocols; W1 data cannot serve as their untouched holdout.
