---
status: accepted
---

# Every change signal must vary within a CI cycle

Investigation of the original results found that the commit-message and file-diff embeddings (CodeBERT/UniXcoder) are keyed only by build/commit, so **every test in a cycle receives an identical embedding** (`FINAL6/TCP-CI_schema.py:452,524-526`), while prioritization is scored by ordering tests *within* each cycle (`robust_tcp_framework.py:5348`, `1729`). A feature that is constant across a cycle's rows cannot reorder them, so the embeddings contributed zero discriminative signal to per-cycle APFD — this is the structural reason they underperformed (the observed negative "developer-intent" deltas are AUC-ROC regressions, the expected symptom of a constant feature adding noise). We therefore adopt a hard design rule: **any change-aware signal must vary between tests within the same cycle** (i.e. be test-specific), and this diagnosis is reframed as the project's primary scientific finding rather than a bug to hide.

## Consequences

- Rules out any technique built purely on commit-level text (the whole class of "embed the commit message better").
- Per-cycle APFD and global APFD must always be reported separately; the old global numbers were dominated by which cycles contained failures, not by true intra-cycle ordering.
- Label leakage and the temporal split were both checked and are clean — the cycle-constant structure is the sole explanation.
