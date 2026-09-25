# F1 protocol — fault-mapping and evidence-validity audit (Airavata)

- **Frozen:** 2026-09-25, after the F1 start and before any recovery-search result or ranking was read. F1 started at `2026-09-25T09:50:16.856Z` (`f1_start_utc.txt`).
- **Authority:**
  - plan `NEXT_RESEARCH_ACTION_PLAN.md` §9 (the F1 design), triggered by gate G1b (ledger Addendum v9, A28; `feasibility_report.md`);
  - the researcher's instruction "start F1" of 2026-09-25.
- **Budget (plan §9):** three researcher-days and 10 allocated vCPU-hours. Human hours are recorded as `UNKNOWN` under the ledger's accounting rule. The agent/tool elapsed time and every compute run are recorded exactly.
- **What is already known before freezing:** the committed `step3_report.json` at `25eb6b7` was read to find the cohort (feasibility report §8, and this protocol's "Cohort" below). No ranking, dataset row or search result had been seen.

## Question and null (plan §9)

- **RQ:** does the Airavata HIST vs HIST+T0 conclusion depend on the one-failed-test-equals-one-fault assumption behind APFD?
- **Null:** the comparison is stable under the declared alternative mappings, or the inputs are insufficient to test stability.
- **Persistence labels:** the plan's second question applies only to a comparison scored with a next-execution persistence label. The primary comparison here is scored against the actual `Verdict` (report field `model`), so that question does not arise for it. If the recovery search finds a persistence-scored Airavata comparison, it is recorded but not added to this protocol.

## Primary comparison and cohort

- **Source:** `FINAL6/apache@airavata/step3_report.json` at commit `25eb6b7` ("T0 path-token relevance — clean NULL on airavata").
- **Arms:** `hist` and `hist_plus_t0` (exactly one feature added), as in that report's `arms`.
- **Cohort:** its `PRIMARY_small_fault` stratum, `m <= 4`, which has 30 cycles. The report's summary is: mean paired difference −0.0061, Wilcoxon p = 0.917, win/tie/loss 4/24/2.
- **Structure, from the report's `per_cycle` list:**
  - 16 cycles have `m = 1`, 1 has `m = 2` and 13 have `m = 3`;
  - for `m = 1` every mapping gives the same APFD, so only the 14 cycles with `m >= 2` can move.
- **No other cohort** (chronic, all-scored, other subjects) is in scope. HBase and Hive are excluded (plan §9).

## Declared fault mappings (plan §9)

For a cycle with `n` ranked tests and failing tests `F` (`|F| = m`), a mapping partitions `F` into faults. A fault is detected at the best rank among its tests.

APFD = 1 − (Σ over faults of its detection rank) / (n · k) + 1 / (2n), where `k` is the number of faults.

1. **M1, one failed test = one fault** (the reported metric): the partition into singletons.
2. **M2, one fault per cycle:** a single block, detected at the first failing test.
3. **M3, all partitions of `F`:** every set partition, with Bell(3) = 5 at most here.
   - These are logical sensitivity bounds, not equally likely causes.
   - No constraint is added unless it comes from independently inspected logs or issues; co-failure alone never counts.

**The same mapping always applies to both arms in a cycle.**

## Recovery of per-test rankings (plan §9: at most one day)

**Declared search locations,** searched in this order and each logged in `f1/recovery_search.md`:

1. **L1:** Git objects reachable from any local or remote ref of this repository (after `git fetch --all`), including branch `claude/t0-path-token-relevance-f13581`. Targets are per-cycle ranking outputs, `apache@airavata_enhanced_tcp_dataset.csv` and `test_name_map.csv`.
2. **L2:** this host's filesystem. Targets are the absolute paths recorded in the report (`C:\Users\kfhassen\…`), any `t0-path-token-relevance*` worktree, and any `tcpci_slice` directory.
3. **L3:** the public TCP-CI dataset's Airavata files, as **inputs only**. It holds no rankings.

**Stop:** at the first of:
- rankings recovered and verified (rules R1/R2);
- all of L1–L3 searched;
- 24 hours after the F1 start (`2026-09-26T09:50:16Z`).

**Recovery rules:**

- **R1, recovered artifact:** a stored per-cycle ranking for both arms counts as recovered if the M1 APFD recomputed from it equals the report's `apfd_hist` / `apfd_t0` for **every one** of the 30 cohort cycles, within 1e-9.
- **R2, deterministic re-run:** re-running `pipeline/step3_t0.py` exactly as at `25eb6b7`, on recovered inputs with the recorded arguments, counts as recovery **only under the same all-30-cycles equality test as R1**.
  - A re-run that fails the test is a finding and is not used.
  - No other model, feature, seed or setting may be tried to make it match. That would be "fitting a new model to fabricate the missing historical outputs" (plan §9).
  - **Researcher decision flagged:** whether R2 is acceptable at all. Until the researcher confirms it, an R2 result is reported but marked provisional.
- **If R1 and R2 both fail:** the ranking part stops, and F1 becomes a traceability/label-validity audit (plan §9).

## Analyses

- **A (always run; needs only the committed report):**
  - **What it computes:** logical bounds on the M2 and M3 APFD of each arm, from the report's per-cycle `m`, `n` and M1 APFD alone.
  - **The constraint:** M1 APFD fixes the sum of the `m` failing-test ranks, and the ranks are distinct integers in `[1, n]`.
  - **Outputs:** per-cycle and mean-difference ranges, and whether a sign reversal of the mean difference is logically possible under a common mapping.
  - **What it is:** a bound under stated arithmetic constraints, not an estimate.
- **B (only if rankings are recovered under R1, or R2 once confirmed):** exact M1, M2 and M3 APFD per cycle and arm, with:
  - within-cycle and mean-difference ranges;
  - win/tie/loss counts;
  - any sign reversal under a common mapping.
- **Verification before either:** recompute M1 from the inputs used and compare it with the report's per-cycle values. Any mismatch is recorded and stops that analysis.

## Reporting rules (plan §9)

- The ranges reflect mapping assumptions, not sampling confidence intervals.
- Cycles in one failure episode are correlated, so there is no naive significance test over cycles.
- Stability is a meaningful negative result. No further mappings are searched after this protocol, even if no reversal appears.

## Outputs

All under `f1/`:
- `protocol.md` (this file);
- `f1_start_utc.txt`;
- `recovery_search.md`;
- `analysis/` (scripts and their outputs);
- `report.md`.

Nothing is written into `pipeline/` or into existing experiment outputs.
