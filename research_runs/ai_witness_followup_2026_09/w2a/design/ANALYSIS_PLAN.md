# W2A analysis plan v1.0

## Material Passport

- Date: 2026-09-26. Prespecified descriptive feasibility analysis, implemented in `w2a_harness/analysis.py` (bound by the package freeze).
- There are no hypothesis tests, population intervals or diagnostic-accuracy claims. W2A is not compared with W1 as if contemporaneous.

## Unit and denominator

The unit is one session (case × arm). All eight scheduled sessions stay in the table. A session that never started is `NOT_RUN`. An interrupted session is `INTERRUPTED_INDETERMINATE`. A missing seal is NO_SUBMISSION, not a success. Repeated validation attempts are never pooled as independent cases.

## Primary feasibility table (per session)

**Stage and workflow steps:**

1. Plan accepted (F3 only).
2. Judgments accepted (F3 only).
3. A legal, non-empty (modified) proposal was made.
4. A modified proposal built on both variants.
5. A modified proposal completed a paired run.
6. A final was sealed, and whether it came from a discretionary call or the final call.
7. Final modified vs unchanged.
8. **Modified workflow complete**: the sealed final is a legal modified overlay that built on both variants and completed at least one paired run during search.
9. Validation outcome (W1 labels), reported separately from feasibility.

**Resources and terminal state:**

- calls (by stage), input/output tokens, USD and search seconds;
- truncated responses, rejected stage outputs, tool errors, admission denials by reason, and use of the final call;
- carried-evidence lines;
- the terminal reason.

**Attrition** counts per arm, over steps 1–9.

## Gates

### Gate 1 — offline readiness (evaluated before launch)

All of these pass on the frozen code:

- the offline tests;
- the W1 failure regressions R1–R9;
- the eight-session fake dry run: terminal accounting, seal-before-validation ordering, ledger = session accounting, per-session caps respected, no open reservations;
- the render leak check;
- the limit check.

Fake-provider success is not live feasibility evidence.

### Gate 2 — live workflow feasibility (the investment rule for this batch)

Gate 2 is met only if **both** arms satisfy all three conditions:

1. every session has a terminal reason other than `NOT_RUN` or `INTERRUPTED_INDETERMINATE`;
2. a final is sealed on at least **3 of 4** cases;
3. the modified workflow is complete on at least **2 of the 3 noncontrol** cases (pool162, grpc1859, k8s26980).

Retaining the unchanged overlay on istio17860 is acceptable. It counts toward sealing but never toward the modified-workflow condition. A validated witness is not required for Gate 2 and does not substitute for it.

### Decisions

- **Gate 2 fails for an arm:** preserve the whole batch and diagnose the remaining failures from the terminal reasons and attrition. Any revision is a new design version with a new batch; no failing session is extended or rerun.
- **Gate 2 passes:** prepare a separate effectiveness study with concurrent B0/B1 (unchanged/template), F2 and F3 controls. Jev enters only through an explicit structured versus structured-plus-Jev comparison. Fresh-case confirmation needs separately selected cases and a frozen protocol; W1/W2A cases stay development data.

## Interpretation limits

**Checks already considered.** Simpson's paradox (the control is kept separate). Ecological fallacy, selection and Berkson bias (four familiar cases). Collider bias (no conditioning on submission). Base-rate neglect. Regression to the mean against W1. Survivorship (all rows kept). Look-elsewhere and forking paths (gates fixed here). Confounding of the joint engineering changes.

**Per-case caveats:**

- **pool162:** the template bindings describe W1's T3 intervention.
- **grpc1859:** a rare-signal case where replacing the unchanged test can lose an existing witness.
- **k8s26980:** the unresolved ordering and observation challenge.
- **istio17860:** a control on which retaining the unchanged test is appropriate.
