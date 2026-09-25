# Research Trajectory

This document records changes in scientific understanding and research direction.

It is not a code changelog.

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
