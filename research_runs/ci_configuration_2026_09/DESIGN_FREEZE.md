# C1 scientific design freeze v1

## Freeze record

- Date: 2026-09-25.
- Identifier: `c1_ci_configuration_visibility_v1`.
- Baseline before this documentation commit: `3f984da9095d19afc239a91945043758da43deec`.
- Authority: the researcher explicitly requested freezing the package, providing a coding-agent prompt, and committing/pushing it; no experiment execution by the preparing agent.
- Freeze evidence: `DESIGN_FREEZE.sha256` and the Git commit introducing this record. Git records the commit timestamp; no future commit hash is invented in this file.
- Status: **SCIENTIFIC DESIGN FROZEN; IMPLEMENTATION HANDOFF READY; MEASURED LAUNCH NOT YET READY**.

## What is fixed

Research questions, six-subject roster, structural enrollment, two CPU profiles, GOMAXPROCS, target commands/timeouts, policies, matched-block design, sampling/order rule, stage budgets, estimands, uncertainty treatment and go/no-go rules are fixed in the checksum-listed design files.

The exact current images, environment, executable command line, implementation hashes and test results cannot be frozen before they exist or are verified. Filling these fields is a validation task, not permission to change the design. No C1 builds, subject executions, calibration, measured runs or implementation changes were made by the design-freeze pass.

No ready-to-run measured command is supplied now because the C1 runner does not exist. The coding agent must produce and validate that command before declaring operational readiness. A checksum alone does not validate artifacts, enforce CPU settings or establish oracle correctness.

## Two freeze boundaries

1. **Design freeze (this record):** enables implementation and bounded preparation under [HANDOFF_PROMPT.md](HANDOFF_PROMPT.md). It is ready for that work now.
2. **Executable launch freeze (future):** `launch_record.md` plus `FREEZE.sha256`, after C0/C1 checks, offline tests, artifact/profile validation and prescribed calibration. It binds the actual code, images, manifests, schedule, accepted amendments and commands. Only this boundary can support a `READY_FOR_MEASURED_LAUNCH` claim.

The coding handoff stops after the second boundary. Running measured blocks requires the researcher's subsequent launch instruction. A `NOT_READY` report is the correct output if a required check fails; never fill unknown evidence with plausible values.

## Checksum scope

Immutable files: `.gitattributes`, `README.md`, `protocol.md`, `subject_register.md`, `execution_plan.md`, `analysis_plan.md`, `HANDOFF_PROMPT.md`, and this file. Paths in `DESIGN_FREEZE.sha256` are relative to this directory; values are SHA-256 of LF-normalized bytes, which the directory attributes preserve.

Excluded: the checksum file itself, `research_record.md`, future readiness/resource/event logs, future execution artifacts and repository-wide research routing documents. Their mutability is intentional. Exclusion is not permission to erase historical events.

Before implementation and before operational launch, independently recompute every listed digest and require exact agreement. Verify the committed bytes as well as the checkout bytes when transferring environments. Do not merely hash the checksum file and assume its entries match.

## Amendments

Preserve v1 files and checksums. If a contradiction or scientific problem is discovered, record a separate dated amendment specifying the exact affected clauses, reason, prior observations already seen, consequences and researcher decision. Routine implementation details within the contract need no new scientific approval. Changes to subjects, profiles, sample size, metrics, thresholds or budgets require explicit design adjudication; they cannot be silently implemented as fixes.

This does not reopen Q0/E1/E2 or F1. Their no-go and negative results remain unchanged. Initial assumptions can be falsified; failure to become launch-ready is an acceptable research outcome.
