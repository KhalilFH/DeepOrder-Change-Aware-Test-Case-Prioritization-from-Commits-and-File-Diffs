# F1 report — does the Airavata "T0 is a null" conclusion depend on the fault mapping?

- **Date:** 2026-09-25. F1 ran from `09:50:16.856Z` (start) to about `10:08Z` (this report).
- **Protocol:** `f1/protocol.md` (SHA-256 `038ff077…`), frozen and committed (`65d43ff`) before any search result or ranking was read.
- **Authority:** gate G1b (ledger A28), the researcher's "start F1", and the researcher's R2 authorisation ("open it and do the work"; `recovery_search.md`).
- **Labels:** **observed** means read from a record or output; **result** means a pre-declared computation; interpretation is labelled where it appears.

## 1. Bottom line

1. **The per-test rankings were recovered and verified.**
   - No stored ranking existed (R1 failed).
   - Re-running the original pipeline, unchanged, on the public TCP-CI archive reproduced **all 82** scored cycles of the committed report exactly, not only the 30 in the cohort (R2 passed, tolerance 1e-9).
2. **The null conclusion is stable under every declared mapping.** The mean paired difference (HIST+T0 − HIST) over the 30 small-fault cycles is:

   | Mapping | Mean difference |
   |---|---:|
   | M1, one failing test = one fault (the reported metric) | −0.0061 |
   | M2, one fault per cycle | **+0.0007** |
   | M3, every grouping of failing tests into faults | [−0.0185, +0.0137] |

   Every value is small next to the report's own bootstrap interval [−0.043, +0.023]. No mapping produces a material T0 effect in either direction.
3. **The direction is not stable.** Under M2 the sign of the mean difference flips: T0 goes from very slightly worse to very slightly better. The report's reading, "no lift", survives. Any directional reading, such as "T0 slightly hurts", does not. It depends on the one-failure-one-fault assumption.
4. **The committed record alone could not have shown this (evidence gap).**
   - From its aggregates, the M2 mean difference could have been anywhere in [−0.070, +0.063] (Analysis A), which is wide enough to include a material effect.
   - Settling it needed the rankings, which were never saved. It also needed the inputs, which lived on another machine and were not in the repository.

## 2. What was done (observed)

| Step | What | Outcome |
|---|---|---|
| Protocol | froze the question, cohort, mappings M1–M3, recovery rules R1/R2, and Analyses A and B | committed `65d43ff` before searching |
| L1 Git | 16 refs, 64 commits | aggregates only (`step3_report.json` at `25eb6b7`); no rankings, no enhanced dataset, no name map |
| L2 filesystem | recorded paths; a bounded filename search | recorded paths absent; the public archive `TCP-CI-dataset.tar.gz` present in Downloads |
| Analysis A | bounds from the aggregates alone | M2 mean-difference range [−0.070, +0.063]; M3 range [−0.081, +0.073] |
| R2 environment | isolated venv, one pip resolution, fixed before any output | Python 3.14.3, scikit-learn 1.9.1, pandas 3.0.6, numpy 2.5.3, scipy 1.18.1 (`r2_run/pip_freeze.txt`) |
| Extract | one streaming pass over the local archive, same filter as `cloud/fetch_airavata_slice.py` | 7,594 files; Airavata's git repository bundled, so no clone was needed |
| Step 1 | `step1_name_join.py` at `25eb6b7` | PASS; 71.2% of cycles overlap (same as the original RESUME) |
| Schema | `TCP-CI_schema.py --name-map` at `25eb6b7` | 11,429 rows, 55 real test names, `FilesChanged` 98.6% filled (all as the original RESUME recorded) |
| Step 3 | the unchanged `step3_t0.py main()`, with its APFD function wrapped only to record each ranking | 10,044 ranked rows |
| R2 test | per-cycle `m`, `n`, `apfd_hist`, `apfd_t0` against the committed report | **0 mismatches in 82 cycles**; every ranking reproduces its own APFD |
| Analysis B | exact M1/M2/M3 on the recovered rankings | section 3 |

- **Archive identity:** 16,978,768,994 bytes, SHA-256 `6c73c9b826ff777ab569cca88859ec86176ac76e8d3cffeb739832958ef74087`, which matches the size the fetch script gives for Zenodo record 5532640. The digest is recorded here; it was not compared with a Zenodo checksum.

## 3. Analysis B results (result)

**Which cycles can move.** 16 of the 30 cycles have one failing test, and 1 has two tests at ranks 1–2 in both arms, so the mapping cannot change them. Of the 13 cycles with three failing tests, **9** change under some mapping.

**The cycles that decide the comparison** (failing-test ranks per arm; differences are HIST+T0 − HIST):

| Cycle | HIST ranks | HIST+T0 ranks | M1 | M2 | M3 range |
|---:|---|---|---:|---:|---|
| 469 | 2, 3, 4 | 1, 2, 3 | +0.020 | +0.020 | [+0.010, +0.029] |
| 476 | 1, 2, 4 | 1, 2, 34 | −0.196 | 0.000 | [−0.294, 0.000] |
| 484 | 22, 23, 37 | 22, 23, 24 | +0.085 | 0.000 | [0.000, +0.127] |
| 485 | 1, 2, 24 | 1, 2, 3 | +0.137 | 0.000 | [0.000, +0.206] |
| 493 | 22, 23, 24 | 1, 18, 24 | +0.170 | +0.412 | [+0.170, +0.412] |
| 494 | 1, 2, 5 | 22, 23, 24 | −0.399 | −0.412 | [−0.412, −0.392] |

- **Win/tie/loss for HIST+T0:** 4/24/2 under M1 and 2/27/1 under M2. Three of the six untied M1 cycles (476, 484, 485) differ only in where the **third** failing test lands. If those failures are one fault, the arms tie.
- **Signs:** 3 cycles change sign between M1 and M2. The mean difference changes sign too, from −0.0061 to +0.0007.
- **Scale:** the whole cohort result rests on a few cycles. Under M2, cycles 493 and 494 alone move the mean by about ±0.014 each, in opposite directions.
- Full tables: `analysis/analysis_b_cycles.csv`, `analysis/analysis_b_partitions.csv` and `analysis/analysis_b_summary.json`.

## 4. Interpretation

- **The null claim is robust.** "T0 does not lift per-cycle APFD on Airavata's small-fault cycles" holds under every declared mapping. The largest mean effect, in either direction, is under 0.02. Under the plan's §9 rule, **stability is a meaningful negative result.**
- **Directional sub-claims are not supported.** Any statement that T0 is slightly worse (M1 mean −0.006, 2 losses) depends on the one-failure-one-fault assumption. So does any statement that it is slightly better. Neither should be made.
- **The evidence gap is the transferable finding.** The August comparison was published with per-cycle aggregates only. They were enough to reproduce its own summary statistics, but not to test its sensitivity to the fault model: Analysis A's bounds would allow a ±0.07 mean effect. The gap was closable here only because the pipeline was deterministic, the inputs were public and the original code was preserved at a commit.
- **Not claimed:**
  - nothing about HBase, Hive or the persistence-label analyses, which are outside this protocol;
  - nothing about which mapping is causally correct, since no independent fault evidence was inspected;
  - no significance test, because cycles in one failure episode are correlated (plan §9).

## 5. Limits

- **Library versions:** the environment is a present-day resolution (scikit-learn 1.9.1), not the unrecorded original.
  - Every per-cycle APFD matches exactly.
  - For `m = 1` that pins the failing test's rank. For `m >= 2`, APFD pins only the **sum** of the failing ranks, so identical individual ranks are inferred from the deterministic code path and the exact 82-cycle match. They are not proven.
  - Only failing-test ranks enter any mapping.
- **Mapping bounds:** M3 ranges are logical bounds over groupings, not probabilities.
- **Scope:** one subject, one comparison, 30 cycles, a few of which dominate.
- **Human hours:** `UNKNOWN`.

## 6. Cost

- **Compute (one sequential job; measured from recorded timestamps):**

  | Step | Elapsed |
  |---|---:|
  | Extraction | 81.9 s |
  | Schema generation | 77.9 s |
  | Step 3 | 55.2 s |
  | Step 1, Analyses A and B, pip install | seconds each (Step 1's end was not recorded; the pip install was not timed) |

- **Total:** about 215 s ≈ **0.06 allocated vCPU-hours** on the 1-vCPU convention, or 0.96 on a conservative 16-vCPU basis. Either is far inside F1's 10 vCPU-hour cap.
- **Researcher time:** agent/tool elapsed about 18 minutes. Human hours are `UNKNOWN` (ledger accounting rule). F1's cap is three researcher-days.

## 7. Artifacts

| Path | Content |
|---|---|
| `protocol.md`, `f1_start_utc.txt` | frozen protocol and start time |
| `recovery_search.md` | L1–L3 search log, researcher decision, environment rule |
| `inputs/step3_report_25eb6b7.json` | committed report, blob `6ce7b665…` |
| `analysis/aggregate_bounds.py` + outputs | Analysis A |
| `analysis/extract_slice.py` | local extraction with the fetch script's filter |
| `analysis/r2_rerun_with_rankings.py` | observational wrapper around the unchanged `step3_t0.main()` |
| `analysis/r2_check_and_analysis_b.py` + outputs | R2 test (`r2_check.json`) and Analysis B |
| `r2_run/` | recovered `rankings.csv`, the re-run report, extraction manifest (per-file SHA-256), `test_name_map.csv`, step-1 gate report, logs, timestamps, `pip_freeze.txt`, SHA-256 of the five scripts as exported from `25eb6b7` |
| not committed | extracted slice and regenerated enhanced dataset (SHA-256 in `r2_run/uncommitted_outputs_sha256.txt`), in `C:\Users\Mega-PC\f1work\` |

**To reproduce:**
1. Extract with `analysis/extract_slice.py` from the archive above.
2. Run step 1 and the schema generator from `25eb6b7` with the commands in `r2_run/*.log`.
3. Run `analysis/r2_rerun_with_rankings.py`.
4. Run `analysis/r2_check_and_analysis_b.py`.

## 8. What F1 means for the plan (for the researcher)

- **Plan §9 "Continue":** "a reproducible material claim reversal or demonstrated evidence gap supports a methods/replication write-up."
  - Here there is **no material reversal**: the null is stable.
  - There **is a demonstrated evidence gap**: an aggregate-only record cannot test fault-model sensitivity.
- **Plan §9 also says** stability "is not a reason to search unlimited mappings until a reversal appears", so F1 stops here.
- **Open for the researcher:** whether this, together with `feasibility_report.md`, closes the month under G5, or whether the evidence-gap point is worth a short methods note.
