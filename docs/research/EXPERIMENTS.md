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
