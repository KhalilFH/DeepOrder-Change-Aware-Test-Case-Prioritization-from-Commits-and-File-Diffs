# Research Decisions

Record important methodological and architectural decisions here.

## Entry format

### DXXX — Decision title

- Date:
- Status:
- Context:
- Decision:
- Alternatives:
- Evidence:
- Rationale:
- Consequences:

### D001 — Freeze C1 design separately from executable readiness

- Date: 2026-09-25.
- Status: adopted by researcher request to freeze and hand off; no execution in this pass.
- Decision: freeze [C1](../../research_runs/ci_configuration_2026_09/DESIGN_FREEZE.md) for implementation and bounded validation, preserving a distinct executable launch gate. Do not claim runtime readiness before the runner, artifacts and controls are validated.
- Rationale: all six restored subjects can inform configuration sensitivity without selecting a favorable intermittency window. Existing evidence does not establish the proposed effect.
- Alternatives deferred: resume E2 by roster expansion, new predictive models, Jev integration and autonomous investigation.
- Consequences: Q0/E1 G1b no-go remains unchanged. Measured C1 runs wait for an executable freeze and subsequent launch instruction. See the [coding handoff](../../research_runs/ci_configuration_2026_09/HANDOFF_PROMPT.md).
