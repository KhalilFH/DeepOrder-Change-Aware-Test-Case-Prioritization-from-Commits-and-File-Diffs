# Experiment Registry

Record material experiments here.

## Entry format

### EXXXX — Experiment name

- Date:
- Commit:
- Branch:
- Research question:
- Hypothesis:
- Dataset / subject:
- Inputs:
- Configuration:
- Command:
- Evaluation protocol:
- Metrics:
- Result:
- Interpretation:
- Limitations:
- Artifacts:

### EXC1 — CPU configuration and defect visibility

- Date: 2026-09-25; status: design frozen, not executed.
- Baseline commit: `3f984da9095d19afc239a91945043758da43deec`; branch: `research/revival-2026` at design preparation.
- Question: does CPU bandwidth limitation change supported detection of known product defects, including its interaction with accept-on-pass retry?
- Subjects: fixed six prior Go pairs; enrollment requires structural validity, not a pass/fail-rate window.
- Configuration: unrestricted R versus two-CPU-bandwidth L on a verified 16-CPU VM, fixed GOMAXPROCS=16, P1/P3/P3-retain.
- Design: ten matched blocks per subject, four profile/variant cells, three attempts/cell; 720 measured attempts if all six enroll.
- Metrics: paired supported-blocking contrasts, missingness bounds, evidence retention, nuisance where independently established, and cost.
- Result: none. No implementation, runtime checks, calibration or measured runs performed by the design-freeze pass.
- Command: pending implementation and validation; no executable CLI is asserted.
- Artifacts: [C1 package](../../research_runs/ci_configuration_2026_09/README.md), [analysis plan](../../research_runs/ci_configuration_2026_09/analysis_plan.md).

#### EXC1 completion update — 2026-09-25

- Status: 720 scheduled attempts already collected across batches A/B; post-collection annotation and frozen analysis completed and independently checked.
- Identity: design 8/8 and executable launch freeze 71/71 match. Raw measured hashes unchanged; no implementation edits.
- Result: C2 passes; C3 signals for etcd5509 P1/P3 only, in the direction of greater blocking under CPU limitation. All primary simultaneous intervals include zero. Acceptable variants passed 360/360; nuisance reduction remains unmeasured.
- Interpretation: descriptive pilot and a fresh-confirmation candidate; no population or adaptive-assessor claim.
- Artifacts: [review](../../research_runs/ci_configuration_2026_09/analysis_audit/POST_COLLECTION_REVIEW.md), [frozen analysis outputs](../../research_runs/ci_configuration_2026_09/analysis/report.md), [independent arithmetic](../../research_runs/ci_configuration_2026_09/analysis_audit/independent_verification.json).
