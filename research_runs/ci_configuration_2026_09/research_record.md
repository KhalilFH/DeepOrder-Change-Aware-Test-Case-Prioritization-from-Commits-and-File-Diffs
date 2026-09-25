# C1 readiness, amendments and resource record

## Material Passport

- Created: 2026-09-25.
- Current status: **DESIGN FROZEN v1; NO C1 BUILDS, CALIBRATION OR MEASURED RUNS**. R000 remains the original drafting record; R001 records subsequent adoption.
- Repository baseline: `3f984da9095d19afc239a91945043758da43deec`, branch `research/revival-2026`.
- Before drafting, `git status --short` showed no changes. Git emitted a permission warning for the user's global ignore file; no claim is made about inaccessible external files.
- Authority: user requested preparation of the necessary files to start experiments as with the previous study. This entry records document preparation only.
- Source reads and protocol design are not validation of local Docker state.

## R000: initial decision record

**Established evidence:** the old study closed E2 under G1b, and F1 completed a separate Airavata mapping audit. Source reports below are preserved unchanged.

**Proposal:** C1 compares resource profiles on the fixed six restored pairs, without selecting a fresh intermediate failure-rate window. This is a new protocol, not a rescue amendment to Q0 or E2.

**Not established:** artifact readiness today, resource enforcement, six-card oracle validity under CPU limitation, material effects, nuisance reduction, novelty, or industrial usefulness.

**Next action:** execute task 1 in [README.md](README.md), the read-only runtime/artifact inventory, when instructed. No implementation or subject execution occurred while drafting this package.

## Readiness board

| Item | Current status | Evidence required |
|---|---|---|
| Six historical source records | inspected | subject register links |
| Current Docker/host identity | NOT CHECKED | `readiness.md`, environment manifest |
| Current image/archive availability | NOT CHECKED | image inventory and per-pair checks |
| Six counterpart dossiers | PENDING | subject manifest and blob/dependency evidence |
| Profile-capable C1 adapter | NOT IMPLEMENTED | future code and validation results |
| All six C1 oracle cards | NOT VALIDATED | reviewed rules and replay report |
| Calibration / controls | NOT RUN | separate ledgers and check report |
| Schedule / cost forecast | NOT GENERATED | literal schedule and conservative projection |
| Launch freeze | NOT CREATED | launch record and verified checksums |
| Batch A / B | NOT RUN | measured ledgers |
| Analysis / interpretation | NOT RUN | complete or inconclusive report |

## R001: design adoption and coding handoff, 2026-09-25

- Authority: user requested a frozen, launch-ready package, a prompt for another coding agent, and commit/push; explicitly no experiment execution by this preparation agent.
- Action: freeze the scientific design and implementation handoff; preserve the honest distinction between design readiness and measured-launch readiness. No runtime checks or calibration claimed.
- Pre-freeze clarification: isolation/timeout validation requires two fresh helper containers per profile, four helper attempts total; the maximum fixed calibration/control/helper count is 64 rather than 62. No observations informed this clarification.
- Evidence: [DESIGN_FREEZE.md](DESIGN_FREEZE.md), `DESIGN_FREEZE.sha256`, [HANDOFF_PROMPT.md](HANDOFF_PROMPT.md).
- This record remains append-only and is excluded from the immutable design checksum. Future events never overwrite R000 or R001.
- Next: coding agent performs bounded preparation, implementation and validation and returns an executable launch record, or an explicit no-go. Measured batches remain unexecuted until a later launch instruction.

## Historical input identities

SHA-256 of bytes read at drafting time; these are input provenance, **not a C1 launch freeze**. Paths are repository-relative.

| Path | SHA-256 |
|---|---|
| `research_runs/ci_sensitivity_2026_09/feasibility_report.md` | `688230410f6e68fa3e0c9437d1c67e3e5ae99c422dc5b2b89c0018817de27a4e` |
| `research_runs/ci_sensitivity_2026_09/f1/report.md` | `42168004779048342462493db0586b97447cb0339ac5c5f7d2f9ab159c9f8cbe` |
| `e1_harness/runner.py` | `be3c39d816e609c2ead8108145e8acb026aa91acd78fc28e1c0338e8bbd255aa` |
| `e1_harness/ledger.py` | `9e51b801dba5f034cc1818192d86314e41f93343a4efe6eaa3053cbf8f8a34f3` |
| `e1_harness/policy.py` | `b5a2e4ba6638a7a6ae565b0962b47c0af9bf07466bfa0473773b240918ff7da4` |
| `e1_harness/oracle.py` | `20a494f00b87d52a035b8a1d31b40d31ca46d9037854a5b0caafcf04b20a89a0` |
| `e1_harness/analysis.py` | `bc27c7de7ebce6bd42c56749c134b76945f13c615bf0f0533336f5528ee1a841` |

## New-study resource ledger

Zero execution spend here means **no C1 execution performed by this drafting pass**. Planning/tool-reading time is not measured and is not zero human effort. Historical Q0/E1 spending is outside this ledger.

| Stage | Adopted cap (allocated vCPU-h) | Recorded C1 execution spend | Status |
|---|---:|---:|---|
| Preparation/rebuild | 8 | 0 | not started |
| Validation/calibration | 6 | 0 | not started |
| Measured blocks | 24 | 0 | not started |
| Analysis/archive | 2 | 0 | not started |
| Total | 40 | 0 | adopted design budget; execution not started |

Append dated events; never backfill unknown human hours as estimates presented as measurements. Each event records stage/job ID, UTC start/end, profile/CPU accounting basis, elapsed time, reserved/charged capacity-hours, measured CPU or unknown, active researcher minutes or unknown, and cumulative balance. Build/probe costs count even if a pair is excluded. Profile L's 2-vCPU accounting does not mean the host reservation costs less.

## Amendment/event template

Copy this structure below for each future event; do not treat blank fields as completed checks:

- ID / UTC date / author:
- Stage and affected subjects/artifacts:
- Trigger: operational problem, validity concern, planned gate or design revision:
- Observations already visible when the decision was made:
- Evidence paths and hashes:
- Decision and rationale; authorization reference if applicable:
- Effect on original estimand, budget, inclusion or frozen files:
- Earlier results kept unchanged; new outputs labelled:
- Next action and stop/resume boundary:

Post-data amendments cannot become preregistered primary choices. Preserve raw data, mechanical classifications and the original analysis alongside any sensitivity analysis.

## Final report skeleton

1. Actual enrolled and unavailable subjects, counterpart types, host/profiles and deviations.
2. Runtime validity, oracle coverage, missingness, source/image preservation and cost.
3. Per-subject/profile/policy numerators, denominators and complete scheduled-block bounds.
4. Primary contrasts and their assumption-dependent intervals; separate batch results.
5. Retained versus masked evidence, raw discrimination, actual nuisance evidence or its absence.
6. What ordinary repetitions/signatures explain; whether a more complex assessor is needed.
7. Explicit gate decision: fresh confirmation justified, inconclusive, or close.
8. Reproduction commands, hashes, data availability and limitations.

Do not report a favorable outcome in advance. A closed study with no useful configuration effect or with sufficient ordinary assessment is a valid deliverable.

## R002: implementation handoff: inventory, preparation, implementation (2026-09-25)

- ID / UTC date / author: R002 / 2026-09-25 / C1 implementation agent (single agent, no delegation), acting under `HANDOFF_PROMPT.md`.
- Stage and affected subjects/artifacts: Phase 0 inventory, Phase 1 preparation, Phase 2 implementation. All six subjects. New files: `readiness.md`, `subject_manifest.json`, `environment_manifest.json`, `prep/`, `resources/`, `events.jsonl`, `schedule.csv`, `schedule.json`, `calibration/plan.json`, and the `c1_harness/` package.
- Trigger: planned gate (the handoff).
- Observations already visible when decisions were made:
  - Design freeze verified: 8/8 digests match in the checkout and in commit `721d885`.
  - All 12 images present, with IDs equal to the durable records (grpc1859's were never recorded; identity is inferred).
  - In-image checks passed 6/6.
  - Profile probes: the first failed on a probe timing bug; the second passed.
  - Oracle replay agrees 630/630.
  - No subject test had been executed by C1 when the schedule and calibration plan were written.
- Evidence paths and hashes: `readiness.md` sections 1–6 and `prep/*.json`. Hashes are bound in `FREEZE.sha256` if a launch freeze is written.
- Decision and rationale:
  - All six subjects are `READY_HISTORICAL`, so C0 passes on structural evidence.
  - The schedule was generated over all six, before calibration.
  - The CPU profiles are enforced through `docker create` plus `docker inspect` of every container before it starts, plus a helper cgroup probe at every executing session start.
  - Implementation choices within the contract:
    - An unrelated running container stops collection; this is a validity alarm with no threshold in the design.
    - Host load is recorded but not gated.
    - CPU time is `null` (not instrumented).
- Effect on original estimand, budget, inclusion or frozen files: none. No frozen file edited. No amendment.
- Earlier results kept unchanged; new outputs labelled: Q0/E1/F1 files were read only. `e1_harness/` is unchanged; its 193 tests pass.
- Next action and stop/resume boundary: fixed calibration (smoke, identity, direct, helpers) under the validation cap. Stop before measured blocks.
- Resource use: preparation 0.258 allocated vCPU-h of 8, with host reservation equal. Agent wall-clock from 11:34Z is logged in `resources/resource_ledger.jsonl`; human effort is unknown.

## R003: post-collection verification, annotation and analysis (2026-09-25)

- Authority: researcher asked to verify that experiments were done and proceed with measured annotation and analysis. Earlier pre-collection holds do not prevent this requested post-collection work.
- Initial state: both measured sessions were already complete, with all 720 scheduled attempts. No measured annotation or analysis output existed. The existing implementation and run artifacts were uncommitted; this pass neither commits them nor infers earlier collection authorization from the current request.
- Verification: 8/8 design and 71/71 executable-freeze entries match. Measured/event/resource chains verified; exact scheduled identities and actual recorded order match. Raw input hashes were sealed before annotation and remained unchanged afterwards. All recorded profile and cleanup checks passed.
- Work: ran frozen `annotate --stage measured`, then `analyze --out analysis`, without overrides or replacement. Added a separate independent arithmetic audit; all primary counts, contrasts, batch directions and C3 flags agree. No frozen implementation/design or raw measured record changed.
- Results: 540 passes and 180 mechanical focal witnesses; all 360 acceptable-variant attempts passed; zero unresolved/invalid. C2 passes. C3 passes for etcd5509 under P1/P3 only; limited CPU gives greater supported blocking there. Every primary confidence interval includes zero. No nuisance reduction established.
- Evidence: [post-collection review](analysis_audit/POST_COLLECTION_REVIEW.md), [raw seal](analysis_audit/pre_analysis_seal.json), [independent verification](analysis_audit/independent_verification.json), [mechanical report](analysis/report.md).
- Cost: 0.002832 analysis vCPU-h charged for the three timed computation jobs; 1.997168 remains of the 2.0 cap. No new subject execution. Human/agent reasoning effort unmeasured.
- Disposition: completed pilot with a prespecified development signal, not a confirmed effect. Any C4 confirmation requires a separate protocol and fresh data. Existing readiness-board entries above are historical snapshots; this event is the current completion record.

## R004: signal-validity audit and budget reconciliation (2026-09-25)

- Authority: the researcher asked for a post-C1 signal-validity audit, then asked for its STOP result to be recorded and the budget reconciled.
- Work:
  - An offline, exploratory and post hoc audit in `signal_audit/`.
  - No containers, builds, subject executions, new observations, label changes or frozen-file edits.
  - Design freeze 8/8 (also against the committed bytes), launch freeze 71/71, raw seal 12/12 and every chain verified before analysis.
- Result: **STOP**; no C4 confirmation of the etcd5509 signal.
  - Under a common per-attempt rate, the frozen C3 gate fires for etcd5509 with probability about 0.41.
  - P3 counts equal p³ arithmetic.
  - The P1 gap comes from three R first-attempt passes whose research-only retries both failed.
  - The oracle positives match the historical leaked-read-lock deadlock, with no generic-delay signature.
  - A plausible small effect would need about 400 matched blocks.
  - Frozen observations and outputs are unchanged. See [the audit](signal_audit/SIGNAL_VALIDITY_AUDIT.md).
- Budget reconciliation:
  - `signal_audit/s07_reconcile_budget.py` appended 11 analysis-stage charges (`signal-audit-v1-01` … `-11`) to `resources/resource_ledger.jsonl`, using `c1_harness.budget.ResourceLedger`.
  - The rows cover the 10 runs logged in `signal_audit/cost_log.jsonl`, plus the reconciliation job itself: 0.578649 vCPU-h in total, on a conservative 16-vCPU basis.
  - The charges were recorded retrospectively. No reservations were opened at run time, and none were fabricated.
  - The chain verifies at 1072 rows. The analysis stage has now spent 0.581481 of 2.0; 1.418519 remains.
- Documentation: the audit report's statement that its charges were not in the resource ledger was true when the report was written. This event supersedes it; the report is left unchanged to keep its manifest hash valid.
