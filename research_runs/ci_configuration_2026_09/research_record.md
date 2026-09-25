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
