---
status: accepted
---

# Path-based change-to-test relevance, not coverage-based

Test-case prioritization needs a signal of how relevant a commit's changes are to *each individual test*, but no coverage matrix, call graph, or test→file mapping exists in the data, and reconstructing real coverage would require re-instrumenting and re-running six upstream project suites we don't control. We therefore derive relevance from **textual/path matching** between the test's identity (`package.Class#method`) and the commit's changed file paths (`FilesChanged`) — starting with a single graded max path-token cosine (T0), later a static call-graph approximation (T1).

## Considered options

- **Real coverage matrix (T7)** — the principled signal, but requires instrumented re-runs of repos not present locally. Kept as an offline *oracle ceiling* to benchmark against, not as the primary mechanism.
- **Path/name matching (chosen)** — buildable today from `Name` + `FilesChanged`, repo-only, cheap enough to run per commit in a live demo.

## Consequences

- Relevance quality is bounded by naming conventions and is only as trustworthy as the `Test Name` column (see the name-mapping validation gate in `CONTEXT.md`).
- Because it is repo-only and per-commit, the same computation doubles as the shippable demo signal (see ADR 0004).
