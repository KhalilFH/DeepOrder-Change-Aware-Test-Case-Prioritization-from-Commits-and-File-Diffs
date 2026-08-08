# Context / Ubiquitous Language

Glossary for the change-aware test-case prioritization research project. Terms only — no implementation details.

## Core domain

- **Test Case Prioritization (TCP)** — Reordering a test suite so that failure-revealing tests run earlier. In this project TCP is evaluated *per CI cycle*: the ordering that matters is the ordering of tests **within a single build/commit**, not across the whole project history.

- **CI Cycle (Cycle / build)** — One integration run triggered by a commit. Has one commit message and one set of changed files. Contains many test executions. The unit within which prioritization ordering is scored.

- **Test execution (row)** — One test run within one cycle. Carries its own history features and its own outcome (Verdict). The atomic unit the model scores.

- **Verdict** — Outcome of a test execution. `fail = 1`, `pass = 0`. The current framework predicts this as a binary target and ranks by predicted failure probability.

- **Change-aware TCP** — The project's thesis: prioritize using signals from *what changed in this commit* (commit message + changed file paths), not only historical test outcomes. This is the author's own contribution, distinct from the baseline.

- **DeepOrder (baseline)** — Prior neural TCP method (Sharif et al. 2021) that learns a per-test **priority value** from history-only features and ranks by it. Here it is a *baseline and a codebase kickstart only* — not the author's idea. Original technique = regression on priority value; the author reframed to binary failure prediction.

- **Priority Value (PV)** — DeepOrder's hand-computed per-test score from history features (weighted recent failures + inverse-duration bonus). Used as a baseline ranking and, in the original, as a regression target.

## Change signals

- **Commit message embedding** — Vector from a frozen code language model (CodeBERT or UniXcoder) over the commit message text. A property of the *cycle*, shared by all tests in it. ⚠️ see [[embedding-is-cycle-constant]].

- **File-diff / changed-files embedding** — Vector from the frozen encoder over the changed file paths. Also a *cycle*-level property.

- **Encoder** — Frozen (not fine-tuned) pretrained model producing 768-dim vectors, reduced by PCA to 128. Two are compared: **CodeBERT** and **UniXcoder**.

## History features (per test execution, vary within a cycle)

- **E1, E2, E3** — Last three pass/fail outcomes for this test (prior runs).
- **DIST** — Cycles since this test last failed (0 if never).
- **CHANGE_IN_STATUS** — Count of pass↔fail transitions in recent history.
- **Duration feature / Last-run feature** — Normalized execution time and time-since-last-run.

## Evaluation

- **APFD** — Average Percentage of Faults Detected. Primary quality metric for an ordering; higher = failures found earlier. Computed per cycle.
- **APFDc** — Cost-aware APFD (weights by test duration).
- **NAPFD** — Normalized APFD (handles cycles where not all failures are reachable).
- **TTFF** — Time To First Failure. How long until the first failing test runs under the ordering.
- **Recall@k / Precision@k** — Failure retrieval quality in the top-k of the ordering.

## Model framings

- **basic** — History-only MLP.
- **enhanced** — Early fusion: history features concatenated with embeddings.
- **dual_branch** — Late fusion: separate history head and embedding head, then fused.

## Diagnosis (confirmed)

- **[[embedding-is-cycle-constant]]** — **CONFIRMED by code.** `CommitMsg` and `FilesChanged` are keyed only by `build_id` (`FINAL6/TCP-CI_schema.py:452,524-526`), so every test execution in a cycle gets a byte-identical change embedding. Prioritization is scored by *within-cycle* ranking (`robust_tcp_framework.py:5348-5355`, `1729-1740`). A feature block that is constant across a cycle's rows cannot reorder them → it contributes **zero** discriminative signal to per-cycle APFD. It can only float whole cycles in the (less meaningful) global APFD, or add noise to AUC — which is exactly the negative "developer-intent" AUC deltas observed. This is a *structural* failure guaranteed by the data schema, not a tuning problem. No label leakage; temporal split is clean (both ruled out).

- **Change-to-test relevance** — The implied fix direction: the change signal must be made **test-specific** to have intra-cycle discriminative power. This is the difference between "what changed in this commit" (cycle-level) and "how much does this commit's change concern *this* test" (test-level). The latter is what TCP actually needs. A true coverage/call-graph linkage does **not** exist in the data and would require re-instrumenting the source repos; the pragmatic, currently-buildable form is **path/name textual matching** between the test's identity and the changed file paths.

- **Path-token relevance** — The chosen first (control) instance of change-to-test relevance: tokenize the test's identity (`pkg.Class#method`, split on `/`, `.`, and camelCase) and each changed file path the same way, then take the **max TF-IDF cosine** over the cycle's changed files. A single graded scalar in [0,1] that — unlike the old cycle-constant embedding — **varies per test within a cycle**, so it can actually reorder tests. If this alone lifts per-cycle APFD over history-only, the thesis mechanism is proven. Later expanded with an **exact-target-hit** flag (`FooTest → Foo.java` present in the diff) and a **package-proximity** score.

- **Test Name** — Per-row test identity, a Java FQN `package.Class#method` (e.g. `org.traccar.test.EdgeTest005#testEdgeCase`). ⚠️ Provenance is unverified: the committed generator maps names to execution IDs **positionally** ([[name-mapping-unverified]]), so `Name` may be mis-attached. Must be validated before any name-derived signal is trusted.

- **FilesChanged** — Per-cycle list of real repo-relative changed paths (stringified Python list, truncated to first 5), e.g. `['src/main/java/.../File5.java', 'src/test/java/.../EdgeTest005.java']`. Cycle-level (same for every test in the cycle).

## Open / to verify

- **[[name-mapping-unverified]]** — Whether the real dataset's `Test Name` is joined to execution rows by a real test ID or by the buggy positional mapping ([TCP-CI_schema.py:126](FINAL6/TCP-CI_schema.py:126)) is **unknown** — data lives on another machine. Everything test-specific rests on this. Build gate: on the anchor project (traccar), measure the fraction of cycles with any nonzero test↔diff path overlap; near-zero ⇒ mapping or derivation is broken, stop before trusting any APFD.

## Committed technique roadmap

Every technique must produce a signal that **varies between tests within a cycle** (see [[embedding-is-cycle-constant]]) — otherwise it cannot move per-cycle APFD. Spine committed: **T0 → T1 + T7 → T6**, with **T3** as T6's learned foil and **T4/T5** as ablations. See [ADR 0003](docs/adr/0003-mutation-guided-relevance-primary-contribution.md).

- **T0 — Path-token relevance** — see [[change-to-test-relevance]] above. The proving control. *Ships in the demo.*
- **T1 — Call-graph reachability** — static analysis: from the changed files, which tests are reachable in the dependency graph. Test-specific, no training, more precise than path-matching. *Ships in the demo.*
- **T3 — Contrastive relevance encoder** — fine-tune the code encoder (the current ones are **frozen** — a second, independent weakness) on historical `(change → failing test)` vs `(change → passing test)` pairs, so it learns which changes break which tests. The learned foil to T6. *Ships in the demo (offline training, cheap inference).*
- **T4 — LLM change extractor** — one LLM call per commit to extract changed classes/methods/APIs and change intent, matched to each test. *Ships in the demo (if API allowed).* Ablation.
- **T5 — LLM relevance judge** — score each `(diff, test)` pair with an LLM. High cost (scales test×cycle) → used on a sampled subset as a near-oracle. Ablation, research-only.
- **T6 — Mutation-guided coupling** — relevance = which tests kill mutants seeded in the *changed* code. The **novel core contribution**, aligned with the lab's mutation-testing expertise. Research-only (too expensive per live commit); it is the *evidence*, not the shipped signal.
- **T7 — Coverage oracle** — real test→file coverage matrix from instrumented runs. Not novel, but sets the **ceiling** every other technique's number is reported against. Research-only.

- **Demo vs research split** — *Demo-shippable* (repo-only, per-commit, CI-time): T0, T1, T4, T3. *Research-only* (offline evidence/ceiling): T6, T7, T5. The demo and the research call the **same** relevance module; see [ADR 0004](docs/adr/0004-repo-only-per-commit-relevance-module.md).
