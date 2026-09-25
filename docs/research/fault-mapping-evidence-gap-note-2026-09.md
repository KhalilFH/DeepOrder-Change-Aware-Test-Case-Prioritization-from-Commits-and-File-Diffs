# Per-cycle APFD alone cannot show whether a CI prioritization result depends on the fault model

*A short methods note from the F1 audit, 2026-09-25.*

- **Status:** draft for the researcher.
- **Evidence:** everything here comes from `research_runs/ci_sensitivity_2026_09/f1/`:
  - the protocol, frozen before any result;
  - the recovered rankings;
  - Analyses A and B, both reproducible byte for byte.
- **What it audits:** the Airavata comparison in [change-aware-tcp-findings-2026-08.md](change-aware-tcp-findings-2026-08.md), commit `25eb6b7`.

## The point in one paragraph

CI datasets have failing tests, not faults, so test-prioritization studies usually score APFD by treating each failing test as its own fault. When a run has several failing tests, that per-run APFD keeps only the **sum** of their ranks. It throws away the one thing a different fault model needs: which failing test came first.

A comparison published as per-run APFD values therefore cannot be checked for fault-model sensitivity afterwards, even when its own summary statistics reproduce perfectly. In the one case audited here, the conclusion survived once the rankings were recovered. The record alone could not have established that.

## Why the information is lost

For a run with `n` ranked tests and `m` failing tests, the usual metric (M1, one failing test = one fault) is:

`APFD = 1 − S / (n·m) + 1 / (2n)`, where `S` is the sum of the failing tests' ranks.

- **M1 needs only `S`.** Many different rankings share the same `S`.
- **An alternative fault model needs more.** For example, M2 (all of a run's failures are one fault) scores only the **first** failing rank. Any grouping of failing tests into faults scores the first rank within each group. So these models depend on exactly the detail that `S` hides.
- **When M1 is enough:** if `m = 1`, M1 is the whole story. Otherwise a reader of per-run APFD cannot tell how a different fault model would score either arm.

## The case: Airavata, HIST vs HIST+T0

- **The claim audited:** "adding path-token relevance (T0) to a history-only model does not lift per-cycle APFD" on 30 small-fault CI runs (at most 4 failing tests).
- **Reported result:** mean difference −0.006; win/tie/loss 4/24/2; bootstrap interval [−0.043, +0.023].
- **Which runs can move:** 16 runs have one failing test, and 14 have two or three.

**What the record allows (Analysis A).** We took every set of ranks consistent with each run's recorded APFD, and every assignment of those ranks to tests. Under M2, the mean difference could then be anywhere in **[−0.070, +0.063]**. That is wide enough to contain a material effect in either direction.

**What the rankings show (Analysis B).** The rankings had never been saved. They were recovered by re-running the unchanged pipeline on the public TCP-CI archive, and the re-run reproduced all 82 recorded runs exactly.

| Fault model | Mean difference (HIST+T0 − HIST) | Win/tie/loss |
|---|---:|---|
| M1: each failing test is a fault (reported) | −0.0061 | 4/24/2 |
| M2: one fault per run | **+0.0007** | 2/27/1 |
| M3: every grouping of failing tests into faults | [−0.0185, +0.0137] | — |

**A worked example: run 484,** with 51 tests and 3 failures.

| Arm | Failing-test ranks |
|---|---|
| HIST | 22, 23, 37 |
| HIST+T0 | 22, 23, 24 |

- **Under M1**, T0 "wins" by +0.085.
- **From the recorded APFD alone**, the M2 difference could be anything from −0.41 to +0.49.
- **Under M2 it is exactly 0.** Both arms find their first failure at rank 22. The whole M1 win comes from where the third failing test landed. The same is true of runs 476 and 485.

## What this means

- **For this claim:** the null is stable under every fault model tried, since no mean effect exceeds 0.02. The direction is not stable. "T0 slightly hurts" and "T0 slightly helps" are both artifacts of the fault model, and neither should be stated.
- **For CI prioritization studies in general** (interpretation): with failing tests as proxy faults, a per-run APFD difference in runs with several failures can be carried entirely by the placement of a second or third failure. A single fault would have been caught at the same rank in both arms. Whether that difference is real depends on a fault model the study never states.

## Recommendations for this repository's future comparisons

1. **Store the evidence, not just the score.**
   - For every scored run and arm, save the ranked identities and verdicts, or at least the failing tests' ranks.
   - The Airavata rankings take 1.5 MB. Their absence nearly made this audit impossible.
2. **Report at least two fault models whenever any scored run has more than one failure:**
   - M1 (each failing test is a fault);
   - M2 (first failure per run, equivalent to rank-of-first-failure).

   If they disagree in sign, report the comparison as fault-model-dependent.
3. **Report the failure-count profile:** how many runs have `m = 1`, `m = 2`, and so on. Readers can then see how many runs the fault model can affect.
4. **Report which runs carry the effect.** Here two runs (493 and 494) each moved the M2 mean by about ±0.014, in opposite directions.
5. **Pin what a re-run needs:** input archive digest, library versions and the commit.
   - Recovery succeeded here only because the pipeline was deterministic, the input archive was public and the original code was preserved at a commit.
   - The library versions were not recorded, so the re-run environment was a guess that happened to match exactly.

## Limits

- **Sample:** one subject, one comparison and 30 correlated runs, a few of which dominate. No significance test is made.
- **Fault models:** M1–M3 are logical alternatives. No independent fault evidence was inspected to say which one is correct.
- **Rank recovery:** for runs with two or three failures, identical individual ranks are inferred from the exact APFD match and the deterministic code path, not proven.
- **Scope:** HBase, Hive and the persistence-label analyses in the August findings were not audited.

## Reproduction

The commands and artifacts are listed in `research_runs/ci_sensitivity_2026_09/f1/report.md` §7, with the results in:
- `f1/analysis/aggregate_bounds_summary.json` (Analysis A);
- `f1/analysis/analysis_b_summary.json` (Analysis B);
- `f1/analysis/r2_check.json` (the 82-run equality test).
