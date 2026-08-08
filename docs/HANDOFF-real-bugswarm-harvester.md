# Handoff — build a REAL BugSwarm harvester for traccar

**For the next session.** Read `../CONTEXT.md` and `adr/0001`–`0004` first for the why. This is a **data-engineering prerequisite** that must finish before `NEXT-STEPS.md` Step 0.

---

## ⛔ STEP 0 RESULT (2026-08-08): GATE FAILED — do NOT build the harvester; pivot to airavata (TCP-CI)

STEP 0 was run against the live BugSwarm REST API (metadata only, no token, no Docker; ~2 requests). **The viability gate failed decisively.** Real-traccar-via-BugSwarm cannot support change-aware TCP. Steps 1–5 below are **abandoned** — do not build them for traccar.

**Evidence (reproducible):**
- Script: [`../BugSwarm/step0_viability.py`](../BugSwarm/step0_viability.py) — hits `http://www.api.bugswarm.org/v1/artifacts?where={"repo":"traccar/traccar"}` (HTTP only; the API is unauthenticated ≤20 req/min).
- Full run log: [`../BugSwarm/step0_viability_report.txt`](../BugSwarm/step0_viability_report.txt)
- Raw metadata (80 artifacts): [`../BugSwarm/traccar_bugswarm_metadata.json`](../BugSwarm/traccar_bugswarm_metadata.json)

**The numbers:**
| Metric | Value |
|---|---|
| Total BugSwarm artifacts for `traccar/traccar` | **80** (all distinct commits) |
| Time span | 2015-05-04 → 2026-06-02 (**11 years**) |
| Artifacts with ANY per-test failure data (`num_tests_failed>0`) | **35 / 80** |
| The other 45 | compile/build/"code" failures — tests never ran (`num_tests_run=0`) → zero per-test data |
| Usable artifacts with **exactly 1** failing test | **30 / 35** |
| Usable artifacts with >1 failing test | 5 (counts: 2, 3, 75, 146, 196) |
| Largest gap between consecutive usable artifacts | **1934 days (5.3 yrs)**; 6 gaps > 180 days |

**Why this fails the gate (four independent blockers):**
1. **Isolated pairs, not a timeline.** BugSwarm gives 80 disconnected fail↔pass build pairs. History features (E1/E2/E3, DIST, CHANGE_IN_STATUS) need each test's *ordered outcomes across consecutive cycles*; BugSwarm captures only the single failing snapshot per pair, so per-test history is not reconstructable without the full suite runs *between* pairs (which BugSwarm does not have).
2. **Degenerate within-cycle ranking.** 30/35 usable cycles have exactly **one** failing test. Per-cycle APFD — the metric T0 must move — is near-trivial when there is one fault and nothing to order against it.
3. **No coherent temporal split.** An 11-year span with a 5.3-year hole (and 6 gaps > 180 days) has no continuous CI train/test boundary.
4. **Only 35/80 have per-test data at all**; and reproducing even those 35 = 35 Docker images (1–4 GB each, ~35–140 GB in the cloud) to yield mostly single-fault, disconnected cycles — unacceptable ROI.

**Decision → PIVOT.** Anchor becomes **airavata (TCP-CI)** — a real continuous CI timeline already in the intended schema (`Id, Name, Duration, LastRun, LastResults, Verdict, Cycle, CommitMsg, FilesChanged, ...`). Same T0 plan (`NEXT-STEPS.md`), different (real) data. This is the fallback the handoff and `NEXT-STEPS.md` Step 0 already anticipated. Note: the synthetic `traccar_..._19pct_8735.csv` stays as a **unit-test fixture only**, never for results.

**Next session's first move:** get the TCP-CI airavata slice into the schema (cloud, then download only the slim CSV), then run `NEXT-STEPS.md` Step 1 (name-integrity gate) → Step 2 (history-only per-cycle APFD baseline) → Step 3 (add T0 path-token relevance).

The original harvester plan is kept below **for the record only** — it is not the path forward.

---

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
