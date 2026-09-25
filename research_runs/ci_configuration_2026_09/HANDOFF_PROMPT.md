# Prompt for the coding agent

Copy the text below into the coding agent. It authorizes preparation and prescribed validation, including bounded builds/calibration; it does **not** authorize measured C1 batches or publishing implementation changes.

---

Prepare this repository's C1 experiment for measured launch. Work as ONE agent. Do not delegate. Implement the frozen design; do not generate a new research vision.

Read AGENTS.md and the dated C1 entries in docs/research/RESEARCH_STATE.md, EXPERIMENTS.md, DECISIONS.md and TRAJECTORY.md. Then read every design file under research_runs/ci_configuration_2026_09/, starting with README.md and DESIGN_FREEZE.md. Independently verify every digest in DESIGN_FREEZE.sha256 before work. Treat historical Q0/E1/F1 outcomes as prior evidence, never new C1 observations.

Your objective is a validated, executable launch package, or a specific evidence-backed NOT_READY report. The scientific design is frozen; runtime readiness is not established. Do not mistake frozen documentation for runnable code.

Proceed in this order without repeatedly asking permission for work already covered here:

1. Perform the read-only runtime/artifact inventory and save readiness.md. Inspect the six existing source records, actual image availability, host/VM resources and existing harness interfaces. Record unknowns. Do not change host settings or run subjects during this inventory.
2. Prepare the fixed subject dossiers and pinned artifacts within the adopted preparation cap. Builds, necessary artifact/dependency retrieval and source/blob checks are authorized for these six subjects only. Preserve exact reconstruction differences and all failed attempts. No replacement search, source changes to force intermittency or mutable dependency guesses. Do not silently change host CPU allocation if the required 16-CPU environment is unavailable; report that constraint.
3. Implement the smallest isolated c1_harness adapter and study-local driver. Reuse E1 policy/ledger logic while preserving e1_harness, pipeline and historical result files. Enforce and verify the actual CPU profiles; a condition label is insufficient. Add the three missing subject oracle cards after source review. Implement matched R/L blocks, unique provenance, budget admission, timeout/cleanup, safe interruption/resume and the frozen analysis. Add focused offline tests and a dry-run CLI that never starts subject containers.
4. Generate and persist the complete outcome-independent schedule before inspecting calibration outcomes. Run the prescribed offline tests, profile checks and bounded fixed calibration/controls/direct checks only. Keep each stage separate from measured ledgers. Log resource use from the beginning. Do not repeat smoke runs until a desired outcome appears. Respect all stage caps and scientific validity gates; no live external model/API calls or unrelated infrastructure.
5. If all readiness gates pass, write launch_record.md and the separate executable FREEZE.sha256. Bind actual code/image/oracle identities, manifests, schedule, exclusions, observed check results, full budget projection and exact validated CLI commands. Verify both freezes. Include a non-executing preflight command and a measured-batch command that refuses to run without a valid launch freeze and remaining budget.

STOP before measured blocks 1–10. Do not run batch A or B, increase sample sizes, restart old E2/E3, train models, add agents, change profiles/metrics/oracle definitions from favorable outcomes, or claim effectiveness. Calibration and helper checks are permitted solely as specified in execution_plan.md and must be reported honestly.

Use explicit evidence-backed amendments for scientific conflicts; preserve v1 bytes. Ask for a design decision only when a real contract change is necessary, explaining the exact clause and evidence. Routine implementation choices are yours. A failed gate is a valid outcome, not something to bypass to finish the task.

Do not commit or push implementation changes in this handoff. The prior documentation commit/push authorization does not automatically extend to your changes. Leave code and artifacts reviewable, list exactly what changed, and avoid large image/dataset artifacts in Git.

Final response:
- READY_FOR_MEASURED_LAUNCH or NOT_READY, with the decisive evidence;
- files changed and tests/checks actually performed;
- enrolled/excluded subjects and unresolved oracle/artifact limitations;
- spend by stage, remaining budget and expected measured-run cost;
- design and executable-freeze verification results;
- exact repository-root preflight and batch-A commands, only if genuinely validated;
- a short copyable prompt for a subsequent measured-run session that verifies the launch freeze, runs batch A, applies the integrity/cost gate and does not inspect effects to decide continuation.

Do the implementation and validation work; do not stop after proposing another plan. If blocked, preserve completed work and the precise failing gate instead of presenting placeholders as launch-ready.
