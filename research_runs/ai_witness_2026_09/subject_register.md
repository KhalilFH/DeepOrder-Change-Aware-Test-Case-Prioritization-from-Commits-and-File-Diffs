# W1 fixed subject register

## Material Passport

- Date: 2026-09-25. Source-derived qualification targets, not restored W1 artifacts.
- Canonical Go reconstruction evidence: ../ci_configuration_2026_09/subject_manifest.json and ../ci_sensitivity_2026_09/task5_artifacts/. Pin exact copied inputs and source bytes into W1's launch manifest rather than trusting mutable cross-study paths.

| ID | Task input provenance | Obligation to operationalize independently | Existing execution limits (inner / outer / cleanup) |
|---|---|---|---|
| pool162 | Three selected pre-fix candidate methods and necessary helpers | Interruption of a waiting borrower must not consume capacity needed by later borrowing | W1 limits 30 / 60 / 30 seconds |
| grpc1859 | Identical repair-backported regression test on both production variants | Error in a large-message write must not strand send quota and prevent later progress | 110 / 120 / 30 seconds |
| k8s26980 | Identical repair-backported regression test on both production variants | A blocked notification send must not retain the listener lock needed by another actor | 60 / 90 / 30 seconds |
| istio17860 | Identical repair-backported regression test on both production variants | Restart waiting for liveness must permit epoch-exit processing to progress | 30 / 60 / 30 seconds |

These semantic descriptions are oracle-builder material. Measured packets contain source evidence, not this table or derived diagnoses.

## pool162 — Apache Commons Pool POOL-162

- Defective commit: `280c60ac3e918eb7fe8fb542847913bb5317cbc6`.
- Repaired commit: `674a6ba9877d2de7224306c83e7871e1eddeab93`.
- Candidate entry points: `TestGenericObjectPool.testWhenExhaustedBlock`, `TestGenericKeyedObjectPool.testWhenExhaustedGrow`, `TestStackObjectPool.testBorrowFromEmptyPoolWithNullFactory`.
- Pre-fix `src/test/org/apache/commons/pool/impl/TestGenericObjectPool.java` blob: `4008f1ee2b1cca71040feb1c14ee506701e70af9`.
- Withheld assessment reference: repair-added `testWhenExhaustedBlockInterupt` (upstream spelling). Do not include it, its patch, or an answer summary in method packets.
- Restore an identical pre-fix test package on both production versions. Resolve all other file identities, build dependencies and JDK explicitly. A modernized compatibility build must use the same changes on both variants and document differences from the historical environment. Do not require an unrelated legacy benchmark agent if the upstream pair can be coherently built without it.
- Fray or another controlled scheduler is optional only as a prequalified shared facility; no assumption of compatibility with this historical Java project. Freeze its availability before calibration. If unavailable, state that B1 has no controlled-scheduling component and narrow the claim accordingly.

## grpc1859 — grpc-go

- Preserved repaired checkout: `484b3ebb4ab56d3decc8240d599718bdbefcf7eb`; defective production reconstructed by its preserved reverse patch on that base. Resolve full parent identity from the source record; never expand an abbreviated hash by guessing.
- Known production blobs: client bad `717e4192ea13547ffe323613d3d4945c9c5a9b00`, fixed `56b434ef37fed92f87811d9d08e3c9c834cf9971`; server bad `5233d6f3db6bd29622f694a59befd50d9e6d7365`, fixed `24c2c7e18c48b007dd8a060cb4e09bfab1a55ebd`.
- Supplied `test/end2end_test.go` blob: `6a583182170323ec5b23d760d926c92d3816be18`; target `TestClientDoesntDeadlockWhileWritingErrornousLargeMessages` (upstream spelling).
- Existing test environment `tcp-clear-v1-balancer`; historical Go 1.13.15. Preserve the recorded dependency pins. Expired TLS certificates previously caused nonfocal failures; generic test timeouts must not count as quota witnesses.
- Oracle must bind error-path execution, quota/progress consequence, and diagnostic evidence. Existing C1 text matching is a starting point, not automatic qualification for changed tests.

## k8s26980 — Kubernetes

- Repaired checkout: `628af356b8c83f98ee3b50dfcf8b0250816a5581`; defective production from the recorded reverse patch. Historical Go 1.12.17.
- Supplied `pkg/controller/framework/processor_listener_test.go` blob: `ffd72d8fae243a1e221a574781a87ed2107aaf1a`; target `TestPopReleaseLock`.
- The supplied test does not establish that `pop` reached its blocked send before the competing locker succeeds. That is a source fact. The actual scheduling explanation for C1's zero failures remains unmeasured.
- Require a supported blocked-send/lock premise and progress consequence for a new witness. Test-side observation is permitted if it does not modify production semantics. Do not inject production hooks into v1 to force the claimed result.

## istio17860 — Istio

- Repaired checkout prefix `c6e91302`; resolve and record its full ID from the existing manifest. Defective production uses the recorded reverse patch. Historical Go 1.13.15.
- Supplied test blob: `09ea287d1f94319c7284f281838a579fdc98d442`; target `TestExitDuringWaitForLive`, package `pkg/envoy`.
- Preserve the same goautoneg compatibility replacement on both variants if reusing that restoration.
- Require evidence connecting restart/liveness waiting and delayed epoch-exit progress. Historical high visibility makes no-change a legitimate result, not an intervention failure.

## Qualification dossier required for every case

Record exact source tree hashes, all production and test differences, input availability class, build commands, toolchain/container digests, dependency locks, entry point, allowed test edits, timeout/cleanup behavior, processor profile, static extractor output, template applicability/bindings, oracle evidence requirements and fixtures. Mark unresolved facts explicitly.

Existing C1 image IDs do not establish availability now. Qualification is based on reconstruction and oracle specificity, not a requested failure count. If fewer than the required cases qualify, stop with NOT_READY; no roster expansion or rate-based salvage.
