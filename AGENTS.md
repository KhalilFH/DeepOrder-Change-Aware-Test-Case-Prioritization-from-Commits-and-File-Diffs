# Agent Instructions

This is an active research repository. Preserve scientific traceability, reproducibility, and temporal validity.

## Research context

**Current state:** read `docs/research/RESEARCH_STATE.md` before proposing or implementing research changes.

**Trajectory:** read `docs/research/TRAJECTORY.md` when reconstructing why the project reached its current direction, comparing prior research phases, or changing that direction.

**Experiments:** read `docs/research/EXPERIMENTS.md` when designing, running, reproducing, or interpreting an experiment.

**Decisions:** read `docs/research/DECISIONS.md` when making, revisiting, or challenging a methodological or architectural decision.

## Research guardrails

Separate observed evidence, experimental results, interpretation, hypotheses, and proposals.

Preserve meaningful negative results.

Keep temporal evaluation causal: training and features must use only information available before the evaluated cycle, except when future information is explicitly used as a retrospective evaluation oracle.

Prefer reproducible commands and explicit configuration over manual procedures.

Stage intended files explicitly. Large datasets, generated artifacts, credentials, and local agent/runtime state stay out of Git.

Do not rewrite shared research history.
