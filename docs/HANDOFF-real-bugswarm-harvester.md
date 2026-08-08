# Handoff — build a REAL BugSwarm harvester for traccar

**For the next session.** Read `../CONTEXT.md` and `adr/0001`–`0004` first for the why. This is a **data-engineering prerequisite** that must finish before `NEXT-STEPS.md` Step 0.

## Goal

Replace the **synthetic** traccar dataset (`BugSwarm/BugSwarm@Traccar/traccar_traccar_high_failure_19pct_8735.csv`) with **real** per-test data. The existing harvester `BugSwarm/BugSwarm_harvester.py` fetches real *artifact-level* metadata but **fabricates every per-test row** (`_process_high_failure_artifact`, lines 221-361: invented test names, random verdicts, invented history, and `File{test_idx}.java` mappings that leak relevance). Do **not** reuse that method. We keep only its BugSwarm-enumeration parts.

## Hard constraint: limited local bandwidth

Cannot download 16 GB (TCP-CI) locally, and Docker artifact images are 1–4 GB **each** — so reproduction MUST happen in the **cloud (Kaggle/Colab)**. Only the final slim CSV (MBs) comes home. Never pull Docker images to the local machine.

## STEP 0 — Fail-fast viability check (do this FIRST, ~1 hour, tiny bandwidth)

BugSwarm is a set of isolated fail↔pass build pairs, not a continuous CI timeline. TCP needs a *sequence* of cycles for history features (E1/E2/E3, DIST) and the temporal split. **Verify traccar has enough before building anything:**

1. `filter_artifacts('{"repo": "traccar/traccar"}')` (metadata only — small).
2. Count artifacts; list `committed_at` / `trigger_sha` / `failed_job.job_id` / `passed_job.job_id`; look at the time spread and how many distinct commits.
3. **Decision gate:** if there are only a handful of disconnected pairs (no meaningful sequence), **STOP** — real traccar-via-BugSwarm can't support change-aware TCP. Pivot to fetching the **TCP-CI airavata** slice via the cloud instead (real CI timeline, already in the intended schema). Record the count in this file and hand back.

## STEP 1 — Real changed files (no Docker, tiny bandwidth)

For each artifact's `trigger_sha`: GitHub API `GET /repos/traccar/traccar/commits/{sha}` → `files[].filename`. Real repo-relative paths. This replaces the fabricated `File{idx}.java`. Cache to JSON.

## STEP 2 — Real per-test results (cloud, heavy — Docker)

For each viable artifact, in the cloud:
1. Reproduce with the BugSwarm CLI (`bugswarm run` / pull the image) for both failed and passed jobs.
2. Collect the JUnit/Surefire reports: `**/target/surefire-reports/TEST-*.xml` (and failsafe reports for IT).
3. Parse each `<testcase>` → real `classname#name`, `time` (duration), and status (`failure`/`error` ⇒ Verdict=1, else 0). This replaces the invented names/verdicts/durations.

## STEP 3 — History features (with the timeline caveat)

Order each test's results across artifacts by `committed_at` to build `LastResults` → E1/E2/E3, DIST, CHANGE_IN_STATUS. If the sequence is sparse (from Step 0), **document that honestly** — do not fabricate history to fill gaps. Sparse history is a finding, not a bug to paper over.

## STEP 4 — Emit a schema-compatible CSV

Match the schema the framework expects (`FINAL6/TCP-CI_schema.py` output): columns `Id, Name, Duration, CalcPrio, LastRun, LastResults, Verdict, Cycle, CommitMsg, FilesChanged, ...`. **Use `CommitMsg`/`FilesChanged`** (the real-schema names), not the synthetic file's `CommitMessage`/`LastFiles`. Export from the cloud; download only this CSV.

## STEP 5 — Anti-synthetic validation gate (BLOCKING)

Before trusting the output, assert:
- Test names are **real** traccar tests (e.g. `org.traccar.protocol.*DecoderTest`), NOT `EdgeTest005`-style counters.
- File paths are real traccar source paths.
- **No numeric test↔file leakage** (the test-name index must not equal its changed-file index).
- Run the Name-integrity / test↔diff overlap gate from `NEXT-STEPS.md` Step 1.

## Outcome

A real traccar CSV that becomes the **anchor** (replacing the synthetic one). Then proceed to `NEXT-STEPS.md` (T0 mechanism proof). If Step 0 failed the gate, the anchor is **airavata (TCP-CI)** instead — same T0 plan, different (real) data.

## Do NOT

- Reuse `_process_high_failure_artifact` (pure fabrication).
- Pull Docker images or the 16 GB dataset to the local machine.
- Fabricate any per-test field to hit a target failure rate (that is exactly what produced the synthetic mess).
