# Research Trajectory

This document records changes in scientific understanding and research direction.

It is not a code changelog.

### T005 — W2A feasibility pilot prepared; budget arithmetic corrected before launch

**Date:** 2026-09-26.

**Observed:** the W2A harness reproduces the W1 audit and handles every recorded W1 execution failure offline. Replaying W1's calibration against the actual W2A requests showed that the proposal's 240k input cap could not support its own call allocation once a final call is reserved. The cap was derived again (640k) with USD bounds unchanged.

**Interpretation:** the proposal's feasibility question is now executable. Whether a live Sonnet 5 agent completes the workflow is still unknown. Nothing about method effectiveness has changed.

**Next:** the researcher-authorized smoke and the eight-session measured batch, judged only by the frozen Gate 2.

### T004 — Trace-level correction and a proposed feasibility gate

**Date:** 2026-09-26, following the researcher's request to inspect W1 and continue.

**Observed:** [Offline audit](../../research_runs/ai_witness_2026_09/postrun_audit/REVIEW.md) confirms Sonnet 5 and W1's counts. Structured generation usually had one or two calls; all AI sessions ended within 84 seconds. Six denials concern input admission and one output admission, with four additional truncated responses. Required gRPC helper context was absent from initial excerpts and not carried across stages. Two empty plans and one empty judgment list were accepted as stage completion.

**Interpretation:** T003's feasibility explanation remains appropriate but its emphasis on redundant reads and input ceilings was incomplete. More wall time or more Jev calls alone does not address the observed workflow failures. No causal effect of a proposed fix has been established.

**Proposal:** [W2A v0.1](../../research_runs/ai_witness_followup_2026_09/v0_1/PROPOSAL.md) separates a repaired workflow's feasibility from effectiveness. Keep the generator fixed, verify the workflow offline, then use an independently frozen bounded development batch. This is a proposal, not an adopted result or live launch. D005 and all historical evidence remain unchanged.

## Legacy trajectory

The project predates the current research workflow. Existing branches, findings documents, and experiment artifacts contain prior work that must be reconstructed here.

## Entry format

### TXXX — Title

**Question**

**Prior state**

**Hypothesis**

**Action**

**Evidence**

**Result**

**Interpretation**

**Decision**

**Open questions**

### T001 — From the closed sensitivity pilot to configuration validation

**Date:** 2026-09-25.

**Prior evidence:** Q0 restored six Go pairs but only three met its frequency window; G1b stopped E2. E1 observed retry-masked focal witnesses without verified nuisance reduction. F1 retained the Airavata null interpretation under declared mappings while exposing missing ranking evidence in the original record.

**Inference:** a subject's observed failure frequency may depend on execution conditions. This is not yet demonstrated by these experiments.

**Decision:** the researcher adopted a frozen [C1 design](../../research_runs/ci_configuration_2026_09/DESIGN_FREEZE.md) comparing two CPU profiles on the fixed restored roster, without changing the old gates or outcomes. Implementation and bounded validation are handed off; measured execution remains pending.

**Open questions:** artifact recoverability today, oracle specificity under resource limitation, effect sizes, ordinary-assessment sufficiency and novelty beyond known resource-sensitive flakiness. No positive result is presumed.

### T002 — From visibility measurements to testing witness prerequisites

**Date:** 2026-09-25, after C1 collection and the AI case assessments.

**Observed evidence:** C1 recorded 5/60 defective focal failures for grpc1859, 0/60 for k8s26980 and 60/60 for istio17860. The earlier POOL-162 Jev probe judged human-provided summaries without executable outcomes. Source inspection identifies a missing explicit ordering premise in the supplied Kubernetes test, but does not prove the schedule responsible for recorded passes.

**Hypothesis:** some uninformative test outcomes require added actions, established ordering or a better observable consequence, rather than more repetitions alone. Explicit prerequisite assessment might guide those interventions; Jev might or might not improve that component.

**Action/decision:** prepare [W1](../../research_runs/ai_witness_2026_09/README.md) and its implementation handoff, with deterministic, plain-model and structured-model controls and independent validation. The researcher explicitly requested this experiment package. No W1 results yet.

**Interpretation boundary:** this revives selected cases as retrospective test-strengthening tasks without reopening old enrollment gates or rewriting negative results. Backported Go tests and known case histories make this development evidence, not a clean fresh-case holdout. A larger causal TCP claim remains deferred.

### T003 — From an AI witness hypothesis to a harness-feasibility null

**Date:** 2026-09-26, after the complete W1 measured run.

**Prior state:** T002 hypothesized that explicit prerequisite assessment, optionally with Jev judgments, could guide a capable model to strengthen uninformative tests. W1 v1.2 froze that test with Claude Sonnet 5 as the generator; the generator family changed from GPT-5.6 Sol to Claude Opus 5.5 to Claude Sonnet 5 before any provider call, for access and cost reasons.

**Observed evidence:**
- W1 completed 60/60 sessions and validations. No AI arm sealed a synthesized test; 32/36 AI sessions ended with NO_SUBMISSION on call or token ceilings.
- The validated witnesses were:
  - the unchanged test on grpc1859 (2/3, a rare signal) and on the istio control;
  - B1's resource-lifecycle template on pool162 (3/3);
  - no arm on k8s26980.

**Interpretation:** the frozen AI harness was infeasible for this model: fixed stages with 3–4 calls, fresh stage conversations and a cache-inclusive 60k input ceiling. The structured-analysis and Jev hypotheses are therefore untested, not refuted. A deterministic, source-bound template produced the only synthesized witness; ordinary unchanged repetition remained the only signal on grpc1859. Both are consistent with C1's finding that paired repetition with signatures remains sufficient.

**Decision:** no W1 method advances under the frozen gates. Any revisit of AI-assisted witness strengthening needs a new versioned protocol that treats harness feasibility (call budget, stage context, ceilings) as a design question before effectiveness. The W1 cases cannot serve as its holdout.

**Open questions:**
- Would a less constrained single-conversation agent budget reach test generation at all?
- Does the template result generalize beyond pool162's error-and-release structure?
- Can k8s26980's ordering premise be witnessed without scheduler control?
