# W1 artifact and runner contracts

## Material Passport

- Date: 2026-09-25. Required implementation outputs, not existing measurement artifacts.
- `artifact_schema.json` defines minimum machine-readable event payloads. Launch must bind exact serializers and cross-record validators.

## Required layout

| Path relative to study directory | Content |
|---|---|
| `prep/inventory.json` | Read-only environment/artifact inventory with unknowns |
| `prep/subjects/<case>/` | Reconstruction dossier, build logs, oracle fixtures and qualification decisions |
| `inputs/<case>/` | Immutable allowed source packet, source availability manifest, static context and shared template bindings |
| `private_oracles/<case>/` | Frozen oracle specification/code and withheld reference evidence, inaccessible to method processes |
| `calibration/` | Fixed schedule and all unchanged-test attempts, separate from measured records |
| `schedule.json` | All four cases × five arms × three replicates, calibration and validation order, seeds, exclusions |
| `launch_config.json` | Resolved provider/runtime fields, exact command arrays, prices and budgets; no credentials |
| `readiness.md`, `launch_record.md`, `FREEZE.sha256` | Gate evidence, launch authority and executable freeze |
| `events.jsonl`, `resources/` | Append-only ordered event ledger and reservations/charges from preparation onward |
| `measured/<session_id>/` | Requests, responses, source accesses, patches, build/run feedback, sealed final submission and validation traces |
| `raw_seal.sha256` | Hashes of completed raw artifacts after collection or terminal stop |
| `analysis/` | Case/arm outcomes, costs, policy visibility, missingness, deviations, report and input manifest |

Large source archives/images, API responses with sensitive metadata, caches and credentials stay out of Git. Preserve raw experiment evidence locally under explicit retention rules; redact credentials before writing. A sanitized request payload must retain exact experimental text and provider configuration; authorization headers are not experimental data.

## Stable IDs and chronology

Session ID format: `w1.<case>.r<1-3>.<B0-B4>`. Every provider request, patch proposal, primitive execution and validation attempt receives a deterministic parent-linked ID. Use UTC timestamps for chronology and monotonic elapsed time for deadlines/cost. Never infer missing rows from absent files alone; schedule status is authoritative.

Every event envelope contains schema_version, monotonically increasing sequence, UTC timestamp, stage, event_type, entity_id, previous_event_sha256 and payload. Hash UTF-8 canonical JSON (sorted object keys, compact separators, no NaN) of the envelope without its own event_sha256, and store the resulting event_sha256. Genesis previous hash is 64 zeros. Persist before claiming completion. This is an integrity chain, not a trusted external timestamp.

Minimum payload types are defined in artifact_schema.json: session, request, attempt. Add implementation-specific event types only in a versioned launch schema, never by dropping these fields. Cross-record validators must check unique IDs, parent references, monotonic sequencing, hash existence, configured counts, deadlines, provider budgets, identical patch hashes and schedule completeness.

## Session record

Record case, arm, replicate, input-packet hash, launch-freeze hash, start/seal time, elapsed search seconds, budget use, proposal hashes, paired-search executions, optional final-patch hash, final status and reason codes. `unchanged` has an explicit empty-overlay hash. No submission uses null; do not silently replace an absent model result with unchanged.

Keep provider failure, illegal patch, compile failure, resource stop and legitimate early submission distinguishable. Final success is assigned only by independent validation; a search session cannot declare itself successful.

## Request record

Record the exact prompt/source/tool schema bytes and hash; requested and returned model identities; settings; provider request ID; sent/completed UTC timestamps; duration; raw response hash; observed or estimated token counts with provenance; USD with pricing identity; request status; retries and parent request ID. An unknown completion remains indeterminate and charged/reserved conservatively until reconciled. No silent retry for a fresh result. Record Jev per-atom output; batching does not erase per-atom accounting.

## Primitive execution and oracle record

Record session/phase, opaque and decoded variant, candidate hash, subject/source/image identity, exact argv, working directory, environment allowlist, seed, triplet and position, monotonic duration, timeout/cleanup state, exit code, stdout/stderr/trace hashes, focal status and cited trace spans. Distinguish `PASS`, `FOCAL_FAILURE`, `NONFOCAL_FAILURE`, `UNRESOLVED`, `HARNESS_INVALID`, `NOT_RUN`. A result classifier uses frozen oracle code and never only a model judgment.

Every focal claim requires premise_evidence and consequence_evidence locators tied to immutable trace/source hashes. Store the oracle rule ID and human adjudication, if any. Ad hoc human overrides are not allowed during collection; disputes remain unresolved and any later sensitivity analysis is explicitly separate.

## CLI behavior required of implementation

Provide documented commands for inventory, offline tests, dry-run, bounded preparation/calibration, preflight, measured run, analysis and verification. These are interface requirements, not assertions that commands presently exist. The coding agent chooses the smallest implementation and supplies tested exact commands.

Dry-run never starts containers or providers. Preflight verifies hashes, resources, resolved settings, schedule and prior state without producing outcomes. Measured run refuses invalid launch freezes, unqualified fields, absent live-run authorization or exhausted reservations. Resume detects prior in-flight work and never duplicates it silently. Analysis reads sealed artifacts and writes to a separate output directory; verification cannot overwrite a file it is currently checking.
