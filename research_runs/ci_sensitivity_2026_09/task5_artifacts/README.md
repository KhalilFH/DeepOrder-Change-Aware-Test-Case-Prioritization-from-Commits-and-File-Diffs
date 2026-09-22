# Task 5 execution artifacts — salvaged 2026-09-22

Build recipes, frozen protocols, runner scripts, per-attempt ledgers and raw
attempt logs for all three Q0 restoration/qualification passes.

| Candidate | Q0 verdict | Files | Size |
|---|---|---:|---:|
| `etcd5509/` | `Q0_QUALIFIED` (16 focal / 4 pass on `V_bad`) | 62 | ~450 KB |
| `etcd7492/` | `Q0_QUALIFIED` (2 focal / 18 pass on `V_bad`) | 62 | ~585 KB |
| `grpc1859/` | `Q0_NOT_QUALIFIED` (1 focal / 19 pass on `V_bad`) | 93 | ~40 KB |

`MANIFEST.csv` lists all 221 files with size and a SHA-256 prefix.

## Layout

```
<candidate>/
  recipe/
    goreal_original/   pristine GoBench blobs at pinned commit 2e91eb1
    as_built/          the recipe actually executed, plus its build context
  attempts/ , *.csv    per-attempt ledgers
  *.log                build output and raw per-attempt logs
DEVIATIONS.md          every original-vs-as-built difference, explained
rebuild.sh             rebuilds a pair and verifies the recorded source blobs
MANIFEST.csv           every file with size, SHA-256 prefix and source directory
```

Rebuild a subject pair with:

```bash
research_runs/ci_sensitivity_2026_09/task5_artifacts/rebuild.sh grpc1859
```

`recipe/as_built/*.Dockerfile` is reconstructed from each image's layer history
(`docker history --no-trunc`), so it records the executed steps faithfully but
is not a byte copy of the file fed to `docker build`. Where that literal file
also survives it is kept as `*.Dockerfile.literal`.

## Why this directory did not exist until now

**It should have from the first Task 5 pass.** The etcd-5509 and etcd-7492
records both state that their results lived in an "ephemeral scratch workspace,
not committed", and the grpc-go-1859 record inherited that habit. The
consequence was that three qualification verdicts — including the two episodes
that satisfy the day-7 gate and are E1's subjects — rested on evidence that
existed only in session-scoped temporary directories, which are wiped without
warning. The durable record held the summary tables, and nothing an independent
reader could check them against.

This is the same class of defect the ledger already flags twice: A7 records that
the Task C BugSwarm snapshot identity and IDoFT commit "were not recorded; those
screenings are not reproducible from the durable record", and A13 recorded the
unpinned dependency versions as an open gap. Those entries named the problem for
*metadata* passes; the same problem was quietly present for every *execution*
pass, and was not named.

`AGENTS.md` says "Large datasets, generated artifacts, credentials, and local
agent/runtime state stay out of Git." That correctly excludes the Docker images
(1.73 GB each) and the GoBench clone. It does not cover build recipes, frozen
protocols, runner scripts or attempt ledgers: those are small text inputs and
primary evidence, not bulk generated output. Treating them as scratch was a
misreading.

The recovery was luck, not design: the two earlier sessions' temporary
directories happened to survive. Had they been cleaned, the etcd evidence would
have been unrecoverable and both qualified episodes would have rested on their
summary tables alone.

## Standing rule this implies

Every future execution pass writes its recipes, frozen protocol, runner, and
per-attempt ledger **into the repository as it runs**, not afterwards from
scratch. Raw logs follow when their total stays in the low megabytes, as here.

## Contents per candidate

- `recipe/goreal_original/` and `recipe/as_built/` — the pristine upstream
  recipe and the one actually executed. `DEVIATIONS.md` explains every
  difference; `rebuild.sh` rebuilds from the as-built set.
- `frozen_protocol.txt` (grpc1859) — the execution protocol frozen before any
  counted attempt.
- `run_attempts.sh`, `run_batch.sh`, `attempt.sh` — the runners.
- `results*.csv` — the per-attempt ledger: version, attempt number, UTC start
  and end, elapsed seconds, exit code, classification.
- `*.log` — raw build output and per-attempt stdout/stderr, including the
  goroutine dumps that the evaluator signatures were adjudicated against.

Two files preserve superseded states deliberately:

- `etcd5509/recipe/goreal_original/bug_patch.diff.orig_crlf` — the CRLF-contaminated Windows
  checkout of the patch, kept beside the LF version that was actually applied.
- `etcd5509/attempts/results_batch1_original.csv` — the batch-1 ledger before
  the two disclosed evaluator-signature corrections described in
  `task5_etcd5509_restoration.md`, kept beside the corrected ledger.

For grpc-go-1859 both patch fetch paths are kept at the top level
(`bug_patch_raw.diff` from GitHub, `bug_patch_blob.diff` from the pinned repo
blob; byte-identical, 0 CR), together with the CRLF finding recorded in that
pass's Step 1.

The etcd-5509 pass edited its Dockerfiles in place inside the GoBench clone, so
the files first salvaged as its "originals" were the edited ones. They have been
replaced with the authoritative pinned blobs and preserved as
`as_built/*.Dockerfile.literal`; see `DEVIATIONS.md`.

## What is still not durably recorded

- The Docker images themselves. Rebuildable from the recipes here, but the
  rebuild is not bit-reproducible: the base `golang:1.13` image tag and the
  `git clone` of each subject resolve at build time. For grpc-go-1859 the
  dependency commits are pinned and were also captured inside the images at
  `/go/dep_versions.txt`; for the two etcd passes the dependency state is
  whatever their recipes resolved at build time and was not recorded.
- Human hours for every pass, which remain `UNKNOWN` per the ledger's
  accounting rule.
