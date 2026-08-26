# Change-aware TCP on real CI: consolidated findings (airavata + LRTS/hbase)

**Date:** 2026-08-25. **Question:** does a *test-specific* change-to-test relevance signal improve
per-cycle test-case prioritization (APFD) over a history-only baseline on real CI test suites?

**Bottom line:** The relevance *mechanism is real* — change relevance surfaces genuine change-induced
regressions that history misses — but its *deployable aggregate value is modest*, because real long-running-CI
failure streams are dominated by recurring/flaky/confounding failures that no change signal can predict. History
is a near-optimal flakiness proxy; change relevance only adds value on the minority of first-time real
regressions. Cheap path/name relevance captures that value; heavier structural signals (call-graph, mutation)
do not add over it and are not worth building on this data.

---

## 1. Setup

- **Baseline (HIST):** gradient-boosted classifier on history-only features (`E1/E2/E3, DIST,
  CHANGE_IN_STATUS, PRIOR_FAIL_RATE, N_HIST, Duration, LastRunFeature`), target = actual `Verdict`, temporal
  prequential evaluation (train on cycles `< c`, test cycle `c`). Primary metric: **per-cycle APFD**; paired
  Wilcoxon + Vargha–Delaney A12 across cycles. (See `pipeline/step2_baseline.py`, `pipeline/step3_t0.py`.)
- **Relevance signals (each added as exactly one/two features; arms differ only by the added column):**
  - **T0** — path/name-token TF-IDF cosine between the test identity and the commit's changed files
    (`pipeline/relevance_t0.py`).
  - **Precise** — `exact_target_hit` (test's target class is a changed file) + `package_hit`
    (`pipeline/relevance_precise.py`).
  - **T1-lite** — static import-reachability: does the test transitively *import* a changed class? (viability
    gate only; scratchpad).
- **Subjects:**
  - **airavata** (TCP-CI): 55 test classes × 236 builds; failures are *chronic/recurring* (one ~21-test
    co-failing block ≈ 90% of failures).
  - **LRTS/hbase** (ISSTA 2024 dataset): adapted to the harness via `pipeline/lrts_adapter.py` (test-first,
    39 tests). **1,095,402 rows, 1,018 cycles, 1,956 test classes**; changed files from LRTS's shipped
    GitHub-compare JSONs; test identity is a Java FQN → `--identity fqn`. Small-fault cycles = `m ≤ 4`.

---

## 2. Results

### 2.1 Direct relevance vs history (per-cycle APFD, small-fault stratum)

| Subject / signal | n cycles | HIST | HIST+signal | mean diff | Wilcoxon p | A12 |
|---|---|---|---|---|---|---|
| airavata / T0 | 30 | 0.824 | 0.818 | **−0.006** | 0.92 | 0.49 |
| hbase / T0 (firmed) | 183 | 0.661 | 0.731 | **+0.069** | 0.10 | 0.54 |
| hbase / precise (exact+pkg) | 183 | 0.661 | 0.670 | **+0.009** | 0.70 | 0.50 |
| hbase / T1-lite import-reach | — | *viability gate: no-go* | | | | |

- **airavata:** T0 is a clean null — failures are recurring, so history already ranks them rank-1 (`E1=1`),
  leaving no headroom.
- **hbase:** T0 is a *weak/marginal* positive (+0.069, p≈0.10, boot95 [0.009, 0.130] barely excludes 0);
  precise name-matching is null (+0.009, p=0.70); import-reachability failed its viability gate (per-cycle
  failing-vs-passing separation ≈ coin flip, 48.6% of cycles; only 44% of transitive failures reachable ≤5 hops).
- **Why name/path relevance underperforms (diagnosed):** on hbase failing tests, `exact-target-hit` = 6.2%,
  `package-hit` = 31.5%, but `any-token-overlap` (what T0 sees) = **97.5%** — T0 fires almost always, so it
  barely discriminates. Precision (exact-hit) is too *sparse* (0.13% of all rows) for a model to exploit.

### 2.2 The failures are flakiness-dominated (why nothing beats history)

Classifying hbase's 596 small-fault failing test-executions by temporal signature:

| Signature | Share |
|---|---|
| isolated transient flip (P→F→P) — flaky, unpredictable | **56.9%** |
| recovers next run (F→P) | 73.2% |
| persistent / regression-like (F→F) | **25.8%** |
| from a habitually-flaky test (≥6 lifetime flips) | 61.2% |
| **of the "transitive" bucket (name-matching can't reach): flaky** | **86%** |

Median lifetime flips of a failing test = 8. **The apparent "transitive change-induced opportunity" (57.7% of
failures) is 86% flakiness mirage.** History wins because a habitually-flaky test has a high prior-fail-rate, so
history ranks it up — **history is effectively a flakiness predictor, and flakiness is the dominant failure mode.**

### 2.3 The mechanism *does* work on genuine regressions

Restricting to the **104 history-blind real regressions** (persistent F→F *and* `E1=0`, so history ranks them
low) and measuring their mean within-cycle percentile (1 = ranked first, 0.5 = random):

| Signal | mean pct | median | in top 20% |
|---|---|---|---|
| history (prior-fail-rate) | 0.655 | 0.491 | 37.5% |
| **T0** | **0.761** | **0.924** | **64.4%** |
| precise | 0.716 | 0.818 | 50.0% |
| import-reach | 0.560 | 0.500 | 21.2% |

**T0 ranks real regressions at the 92nd percentile vs history's 49th** — the aggregate null is *flakiness
dilution*, not a dead mechanism. A real regression is genuinely change-relevant; a flaky failure is not, and
flaky failures are the majority.

### 2.4 Deflake-then-prioritize (regression-APFD)

Re-scoring under **regression-APFD** (faults = persistent regressions only; transient flakes don't count),
model-free rankers, n=109 regression cycles:

| Ranker | mean regression-APFD | vs history |
|---|---|---|
| history (prior-fail-rate) | 0.760 | — |
| T0 | 0.798 | +0.039 (p=0.38) |
| deflaked `T0·(1−flaky)` | 0.783 | +0.024 (crude penalty hurt) |
| **combined `z(hist)+z(T0)−z(flaky)`** | **0.817** | **+0.058, p=0.084, win/loss 60/40** |

An **additive** flaky-discount + relevance beats history modestly; the naive multiplicative deflake hurt.

**Full-GB-model confirmation (regression-APFD, prequential GB, window 100, 108 cycles)** — the rigorous test
against the *real* deployed history model:

| Arm | mean reg-APFD | median | vs HIST |
|---|---|---|---|
| HIST (GB, FEATURES_FULL) | 0.606 | 0.688 | — |
| **HIST+T0** | **0.681** | **0.936** | **+0.075, Wilcoxon p=0.059, win/loss 36/25** |
| HIST+T0+flaky | 0.645 | 0.826 | +0.039, p=0.15 |

**Adding T0 to the real history model improves regression-APFD by +0.075 (marginally significant, p≈0.06;
median 0.94 vs 0.69).** This is *cleaner than the raw-APFD result* — evaluating on what matters (real
regressions, not flaky noise) makes relevance's value visible. **Methodological finding:** giving the GB model
the flaky-propensity *as a feature* HURT (0.645 < 0.681) — a Verdict-predicting model exploits it to predict
*flaky* failures. The deflake belongs at **ranking time** (explicit down-weight), not as a model feature.

#### Replication on a second subject: hive (external validity)

Same pipeline, same command (`step3_regapfd.py --identity fqn --train-window-cycles 100`), adapted hive dataset
(**2,758,143 rows, 2,131 cycles, 1,663 test classes**; 1 cycle without diff data; overlap gate passed).
Prequential GB, **198 scored regression cycles**:

| Arm | mean reg-APFD | median | vs HIST |
|---|---|---|---|
| HIST (GB, FEATURES_FULL) | 0.912 | 0.993 | — |
| **HIST+T0** | **0.941** | **0.996** | **+0.029, Wilcoxon p=0.028, win/loss 74/66** |
| HIST+T0+flaky | 0.941 | 0.995 | +0.029, p=0.056, win/loss 82/76 |

**What replicates (the qualitative headline holds on a second subject):** (a) HIST+T0 beats HIST on
regression-APFD — and on hive it is **statistically significant (p=0.028)**, cleaner than hbase's marginal
p≈0.06; (b) HIST+T0 is the best arm, and **adding flaky-propensity as a model feature does not improve on it**
(0.9407 vs 0.9414, a negligible −0.0007, and it *dilutes* significance to p=0.056) — consistent with hbase,
where the same feature clearly hurt. The "add T0, don't feed flaky-propensity to the model" conclusion holds
across both subjects.

**What does NOT replicate: the +0.075 magnitude.** Hive's lift is **+0.029, ~40% the size**. The cause is a
**ceiling effect** — hive's HIST baseline is already near-perfect (mean 0.912, **median 0.993**) vs hbase's 0.606
/ 0.688, so there is little headroom for relevance to add. This is a subject-property, not a contradiction: the
*direction and the significance* travel across subjects; the *magnitude* is governed by how much headroom the
history baseline leaves.

**Why the baselines differ — the two subjects span different failure regimes (this is the useful part of the
external-validity spread).** Fault-size distributions differ markedly:

| | hbase | hive |
|---|---|---|
| failing cycles | 43.1% | 69.1% |
| faults / failing cycle (mean / median / p90 / max) | 2.77 / 1 / 4 / 77 | **8.97 / 2 / 21 / 417** |
| overall fail-rate | 0.11% | 0.48% |
| HIST reg-APFD (mean / median) | 0.606 / 0.688 | **0.912 / 0.993** |

Hive has **denser, heavier-tailed fault sets** (4× the fail-rate; failing cycles carry ~3× more failures, with a
long tail to 417). Those failures are more **chronic/recurring** — a recurring failing test has a high
prior-fail-rate, so history ranks it top and regression-APFD is near-ceiling (the same mechanism that made
airavata a T0 null). hbase, by contrast, is sparser and flakier (median 1 fault/cycle), so history has more room
to be wrong and T0 has more to add. So across three subjects the picture is coherent: **the size of T0's lift
tracks the headroom the history baseline leaves — largest where history is weakest (hbase, +0.075), significant
but small where history is already near-ceiling (hive, +0.029), and null where failures are purely chronic
(airavata).**

---

## 3. Conclusion & contribution

1. **Change-aware relevance works for real regressions but is capped by CI flakiness.** On raw per-cycle APFD it
   barely beats history (hbase +0.069, p=0.10), because real regressions are a minority swamped by flaky
   failures and history already tracks the flaky majority. **Under regression-APFD (the objective that ignores
   flaky noise), adding T0 to the real history model gives +0.075, p≈0.06 (median 0.94 vs 0.69)** — a modest but
   marginally-significant, consistent gain. The value is concentrated in first-time regressions history is blind to.
2. **Deflake at ranking time, not in the model.** Feeding flaky-propensity as a model feature hurts (the model
   predicts flaky failures with it); an explicit ranking-time down-weight is the correct integration.
3. **Cheap beats heavy.** Path/name-token relevance (T0) carries essentially all the recoverable signal; precise
   name-matching, static import-reachability, and (by extension) full call-graph / mutation coupling add nothing
   over it on this data — the ceiling is set by the failure distribution, not technique sophistication.
4. **Actionable design:** *deflake-then-prioritize* — down-weight likely-flaky tests (causal flip-rate) and
   apply relevance to surface real regressions early among the rest.

This closes the original "revive the change-embedding idea" thesis with a diagnosed mechanism (the change signal
had to be made test-specific — done) and an honest ceiling (real CI is flakiness-dominated).

---

## 4. Threats to validity

- **Oracle metric:** regression-APFD and the "history-blind regression" subset use the *future* (does the
  failure persist) to define ground-truth faults. This is an evaluation oracle (standard for TCP ground truth),
  not a deployable metric; all *rankers* use only causal features.
- **Three subjects:** airavata (chronic-recurring, T0 null), hbase (flaky-dominated, +0.075 p≈0.06), hive
  (chronic/recurring, near-ceiling history, +0.029 p=0.028). The direction of the regression-APFD headline (add
  T0, don't feed flaky-propensity to the model) replicates across the two LRTS subjects; its magnitude is
  headroom-dependent. james and other LRTS subjects not yet run; all evidence is consistent with the
  headroom/flakiness thesis and LRTS's own "confounding failures" emphasis.
- **T1-lite approximation:** import graphs under-approximate reachability (miss same-package, reflection, DI).
  A T1-lite null is therefore weaker evidence than its positive would have been; but the clean-subset shows the
  cheap T0 already captures the recoverable signal, so a full call-graph is unlikely to change the conclusion.
- **Flaky labels are heuristic** (temporal-signature based), not injected ground truth.

---

## 5. Reproducibility

- **Pipeline (branch `claude/t0-path-token-relevance-f13581`):** `pipeline/lrts_adapter.py` (+ tests),
  `step2_baseline.py`, `step3_t0.py` (with `--identity`, `--small-fault-max`, `--chronic-min`,
  `--train-window-cycles`, `--max-eval-cycles`), `relevance_t0.py`, `relevance_precise.py`, `step3_precise.py`.
  `step3_regapfd.py`. 39 pytest tests green. Committed on that branch (`265a0b8`).
- **Data:** LRTS processed download extracted to `C:\long_running_test_suites\`; adapted hbase dataset +
  reports in `C:\h\`; hbase snapshot clone at `C:\hb\` (SHA `267d6219`).
- **Analysis scripts (scratchpad):** `relevance_ceiling.py`, `t6_opportunity.py`, `t1_graph_and_gate.py`,
  `flakiness_gate.py`, `clean_subset_experiment.py`, `dfp.py`, `regapfd.py`.
