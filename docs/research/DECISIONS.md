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

### D002 — Prepare W1 as a retrospective supplied-test study with separate launch readiness

- Date: 2026-09-25.
- Status: adopted for preparation following the researcher's explicit request for the proposal, experiment and coding-agent prompt.
- Decision: freeze [W1 v1](../../research_runs/ai_witness_2026_09/DESIGN_FREEZE.md), keeping B3-versus-B2 structure and B4-versus-B3 Jev contrasts separate, with independently executed final-candidate validation and an explicit unchanged-test control.
- Rationale: historical cases expose different possible witness prerequisites, but source inspection and the old Jev summary probe do not establish executable model utility. Go tests backported from repairs preclude a uniform pre-fix-discovery claim.
- Alternatives deferred: immediately adding Jev relevance to TCP, treating explanation accuracy as effectiveness, increasing the historical roster, or measuring AI arms without a strong plain-model comparator.
- Consequences: complete implementation and bounded preparation first; verify provider access/identity and runtime before a separate measured launch. No purchase/reset or silent model substitution. Prior experiments and negative results remain unchanged; future confirmation needs fresh cases and a new protocol.

### D003 — Amend W1 generator family to Claude Opus 5.5 (design v1.1)

- Date: 2026-09-26.
- Status: adopted by researcher instruction; no W1 outcomes existed at amendment time.
- Context: W1 v1 fixed GPT-5.6 Sol as the requested generator family for B2–B4, and the W1 protocol requires a dated amendment for a model-family change.
- Decision: freeze [W1 v1.1](../../research_runs/ai_witness_2026_09/v1_1/AMENDMENT_2026-09-26.md) with Claude Opus 5.5 as the requested generator family. v1 is superseded and preserved byte-identical.
- Alternatives: reissuing v1 in place, which is simpler but violates the freeze rule to preserve v1 bytes.
- Evidence: v1 verifier 16/16 before the amendment; v1.1 verifier 17/17, including the v1 integrity check.
- Rationale: researcher's choice of generator. All arms still share one generator, so the B3-versus-B2 and B4-versus-B3 contrasts stay within one model.
- Consequences: W1 findings will describe Claude Opus 5.5, not GPT-5.6 Sol. Cost caps are unchanged and must be checked against the resolved model's pricing at launch; an infeasible cap is a NOT_READY gate or a further amendment.

### D004 — Amend W1 generator family to Claude Sonnet 5 (design v1.2)

- Date: 2026-09-26.
- Status: adopted by researcher instruction; before the amendment only the model-free calibration and fake dry runs had been observed.
- Context: the researcher wanted to spend less than the Claude Opus 5.5 projection (timeout bound USD 14.40) and has an OpenCode Zen key.
- Decision: freeze [W1 v1.2](../../research_runs/ai_witness_2026_09/v1_2/AMENDMENT_A2_2026-09-26.md) with Claude Sonnet 5 as the requested generator family, accessed through OpenCode Zen's Anthropic-compatible endpoint with prompt caching. v1.1 and v1 are superseded and preserved byte-identical.
- Alternatives: stay on Opus 5.5 with caching (no amendment; about USD 5–8 realistic); Haiku 4.5 (rejected: likely too weak, so a null result would be uninterpretable).
- Evidence: v1.2 verifier 17/17 with chained v1.1 and v1 checks; 44/44 offline tests; fake dry run of 60/60 sessions.
- Consequences: W1 findings will describe Claude Sonnet 5. Provider timeout bound falls to USD 8.28. The generator's returned identity through Zen still needs the authorized smoke request. The 8k output-token session ceiling against always-on thinking remains the main feasibility risk.

### D005 — Close W1 without advancing any method

- **Date:** 2026-09-26.
- **Status:** adopted. It applies the frozen engineering gates of the v1.2 analysis plan to a complete study with no unresolved integrity problem.
- **Context:** the W1 measured run completed 60/60 sessions and validations (EXW1 completion update).
  - No AI arm sealed a synthesized test.
  - B3 and B4 had zero witnesses everywhere.
  - B2's only witnesses were unchanged-overlay submissions on the istio control.
- **Decision:** no method advances.
  - Gate 1 (B3 over B2) is not met: B3 exceeds B2 on no case and is lower on the control; the identical-vector alternative fails.
  - Gate 2 (B4 over B3) is not met: identical all-zero vectors with no noncontrol successes.
  - Gate 3: no AI method beats B1, which matched or exceeded every AI arm at no provider cost.
  - Gate 4: no advancement from the control.
  - W1 is closed as a harness-feasibility null for Claude Sonnet 5 under v1.2.
- **Alternatives rejected:**
  - Rerunning W1, or amending its call and token ceilings, after seeing outcomes. This is forbidden by the protocol and would be an outcome-driven design change.
  - Reading the zero B3/B4 counts as evidence against structured analysis or Jev. Those arms never reached test generation.
  - Treating the istio B2 witnesses as AI-synthesized tests. They are the unchanged overlay.
- **Evidence:** [results report](../../research_runs/ai_witness_2026_09/results_report.md) and [frozen analysis](../../research_runs/ai_witness_2026_09/analysis/report.md). Raw data is sealed and the headline arithmetic was independently re-derived.
- **Rationale:** the gates are prespecified investment rules. No fresh-case enrollment follows automatically. The observed binding constraints (call caps, fresh per-stage conversations, cache-inclusive 60k input ceiling) are design questions, not effectiveness results.
- **Consequences:**
  - Any revisit of AI-assisted witness strengthening needs a new versioned protocol that establishes harness feasibility before measuring effectiveness. W1 cases cannot serve as its holdout.
  - The Jev-as-TCP-feature shortlist stays deferred.
  - C1, Q0/E1 and F1 results are unchanged.

### D006 — Adopt W2A v1.0 as a separate feasibility pilot, with a derived input cap

- **Date:** 2026-09-26.
- **Status:** adopted for preparation by the researcher's instruction to implement W2A through a launch-ready package. Launch remains a separate authorization.
- **Context:**
  - The W2A v0.1 proposal left the final-call reserve and budget feasibility to implementation.
  - The offline limit check replayed W1's recorded requests and rendered the actual W2A requests.
  - At the proposed 240k session input cap, F3 on pool162 cannot admit its planner once the final call and the first generation request are reserved. F3's smallest generation stage is one call.
- **Decision:**
  - Freeze [W2A v1.0](../../research_runs/ai_witness_followup_2026_09/w2a/design/README.md) as the proposal describes (four cases × F2/F3, Sonnet 5, no Jev).
  - Set the session input cap to 640k, the output of a declared rule: the smallest multiple of 40k at which input tokens do not bind, at W1 p90 growth, W1-typical stage sizes and W1 median/mean output.
  - Keep per-session USD 1.00 and study USD 8.10 as hard caps.
  - The remaining concrete rules are listed in [DESIGN_CHANGES.md](../../research_runs/ai_witness_followup_2026_09/w2a/design/DESIGN_CHANGES.md): final-call reserve, discarded truncations, local stage validation, legal-only seals, and terminal rules.
- **Alternatives rejected:**
  - Keeping 240k: the pilot would largely re-test W1's budget failure.
  - Raising the USD caps or the 24k output cap: this would change the researcher's money bound, and neither is contradicted under W1's typical output profile.
  - Extending the 600 s wall: W1 sessions used ≤ 84 s. The narrow gRPC pair window is recorded as a risk instead.
- **Consequences:**
  - W2A outcomes will describe this configuration only.
  - Any change after launch needs a new design version and batch.
  - W1 and W2A cases remain development data.
  - D005 is unchanged.
