---
status: accepted
---

# The relevance computation is a repo-only, per-commit module from day one

The research work must eventually become a live demo that runs on the company's own repository, per commit, in CI-time. The previous iteration was un-demoable because it was wired to hardcoded Kaggle/conda paths and precomputed CSVs. We therefore build the change-to-test relevance computation as a clean module with the signature `(repo checkout, commit) → per-test relevance scores` from the very first experiment, and have the research techniques (mutation coupling, coverage oracle) plug in as *offline validators around that same module* — rather than building a convenient research pipeline and re-engineering a demo later.

## Consequences

- The demo-shippable techniques (T0 path, T1 call-graph, T4 LLM extractor, T3 trained-then-inference) are exactly the module's cheap per-commit paths; the research-only techniques (T6 mutation, T7 coverage, T5 LLM-judge) wrap it offline.
- No portability/re-engineering tax when moving from paper to demo — the demo is the same code the experiments call.
- Constrains implementation choices: no notebook-only, path-hardcoded, or precomputed-artifact shortcuts in the relevance path.
