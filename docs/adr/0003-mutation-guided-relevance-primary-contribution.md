---
status: accepted
---

# Mutation-guided coupling as the primary novel contribution

Once change-to-test relevance is made test-specific, the strongest and most defensible signal of "does this change concern this test" is **fault coupling**: which tests kill mutants seeded in the *changed* code. We adopt mutation-guided coupling (T6) as the paper's novel core, benchmarked against a real coverage oracle (T7) as the ceiling and against the free path/call-graph signals (T0/T1) as the cheap end of the spectrum. This direction is chosen partly because it is directly aligned with the hosting lab's mutation-testing expertise (supervisors Papadakis and Khanfir), giving the work a differentiated angle rather than an incremental embedding tweak.

## Considered options

- **Learned relevance only (T3 contrastive encoder)** — kept as the *learned foil* to mutation coupling, not the headline, because it is less interpretable and less aligned with the lab's differentiator.
- **LLM-based relevance (T4/T5)** — kept as modern ablations; T5 is too costly per test×cycle to be the core and is used only on sampled subsets as a near-oracle.

## Consequences

- Mutation coupling is compute-heavy and offline — it is *evidence for why the cheap signal works*, never the signal shipped in a live demo (see ADR 0004).
- The paper's spine becomes a spectrum of relevance — free (path) → principled (call graph) → fault-based (mutation) — all reported against the coverage ceiling.
