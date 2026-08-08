# Next steps — kickoff for the machine with the data

This is the execution handoff from the design session. **Read `../CONTEXT.md` and `adr/0001`–`0004` first** — they hold the why. This file holds the *what to do next*, in order. Do it on the machine where the traccar dataset lives.

## Milestone: T0 — prove the mechanism

The single goal of the first work session: **show that one test-specific relevance scalar lifts per-cycle APFD over history-only, on traccar.** Nothing else until this passes or fails cleanly.

### Step 0 — Get REAL data first (PREREQUISITE)
- **This is blocked on real data.** The committed `BugSwarm/BugSwarm@Traccar/traccar_traccar_high_failure_19pct_8735.csv` is **synthetic** (templated names `EdgeTest005…`, trivial `EdgeTest005 → File5.java` mapping — relevance baked into the numbering, so T0 would "succeed" tautologically). Use it ONLY as a **known-answer unit-test fixture**, never for results.
- **Chosen data path: build a real BugSwarm harvester → see [`HANDOFF-real-bugswarm-harvester.md`](HANDOFF-real-bugswarm-harvester.md).** Do that first. It runs reproduction in the cloud (local bandwidth is limited) and includes a fail-fast viability check.
- **Anchor = real traccar** once reproduced. **Fallback anchor = airavata (TCP-CI)** if the fail-fast check shows BugSwarm traccar lacks a usable CI timeline.
- Note: the earlier "traccar has 18.96% failures, best anchor" stat came from the *synthetic* data (harvester targets high failure by construction) — it is not a real property of traccar.

### Step 1 — Name-integrity gate (BLOCKING — see ADR 0002 / CONTEXT open risks)
- The `Test Name` → execution-row join provenance is unverified (`FINAL6/TCP-CI_schema.py:126` maps by sorted position, which may be wrong).
- Gate metric: **fraction of cycles that have any nonzero test↔diff path overlap** between derived test paths and `FilesChanged`.
- If near-zero → the mapping or path derivation is broken. **STOP. Fix the join by real test ID before trusting any APFD number.**

### Step 2 — Honest history-only baseline
- Train the history-only model. Report **per-cycle APFD** (NOT the old global number). Also report global APFD separately.
- This is the number T0 must beat.

### Step 3 — Add the T0 relevance scalar
- Compute **max path-token cosine**: tokenize test identity (`pkg.Class#method`, split on `/`, `.`, camelCase) and each changed path; TF-IDF cosine; take the max over the cycle's changed files. Graded [0,1], varies per test within a cycle.
- Add it as one feature to the SAME model (change one thing only). Keep the binary-Verdict objective (LTR comes later).

### Step 4 — Compare, honestly
- history-only vs history+T0: **per-cycle APFD, paired Wilcoxon across cycles + Vargha-Delaney A12, bootstrap CI.**
- Hard rule: **no broad try/except that swallows failed runs** — a degenerate run is a failure, not a data point.

### Exit
- **T0 lifts per-cycle APFD (significant, positive effect size)** → mechanism proven; proceed to T1 (call-graph) + T7 (coverage oracle), then T6 (mutation). See the roadmap in `CONTEXT.md`.
- **T0 does not lift it** → do not paper over it. That's a real result too; re-open the diagnosis (is the signal actually varying? is the Name mapping still lying?).

## Build constraint (ADR 0004)
Build the relevance computation as a `(repo checkout, commit) → per-test scores` module from the start. The demo and the research call the same module. No hardcoded Kaggle/conda paths, no notebook-only shortcuts in the relevance path.
