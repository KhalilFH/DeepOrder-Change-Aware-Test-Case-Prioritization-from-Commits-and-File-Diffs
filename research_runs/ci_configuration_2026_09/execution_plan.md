# C1 execution plan

## Material Passport

- Date: 2026-09-25; status: design frozen v1; implementation and run instructions **not executed**.
- This file separates inventory, artifact restoration, implementation, calibration, measured execution, analysis and interpretation.
- No C1 runner or analysis entry point exists yet. Names below describe future artifacts, not working commands.

## Phase 0: inventory without subject execution

Produce `readiness.md` using the six rows in [subject_register.md](subject_register.md).

Read-only starting commands from the repository root, when this task is started:

```powershell
git status --short
git rev-parse HEAD
docker version
docker info
docker image ls --no-trunc
```

Record observed runtime availability rather than assuming Docker is running. Inspect candidate image IDs individually and compare source records. Inspect host resources and existing processes without stopping unrelated work. Inventory missing archives, dependency metadata and oracle cards. Do not start Docker Desktop, pull images, build, launch tests or change host settings as part of this read-only task.

This design was prepared from repository records only; those runtime commands were not executed to assert C1 readiness.

## Phase 1: artifact preparation

Once preparation is authorized, work in a separate C1 scratch/output area, never in the old result folders. Reuse surviving immutable images where their counterpart evidence validates; otherwise rebuild equally pinned variants from the preserved recipes. Do not use mutable latest dependencies. Keep all build logs and failed reconstruction attempts.

Apply the dossier in the subject register. Existing verification scripts are read before use, because their subject coverage and reconstruction assumptions differ. Restore only the fixed six; an unavailable subject remains unavailable. Stop each pair after two active preparation hours or the total preparation cap, and record the limitation.

Check the CPU profile on non-subject helpers using the same runtime/toolchain where possible: inspect actual quota/period and visible CPU count, verify the explicit runtime parallelism and account for cgroup v1/v2. Quota is bandwidth, not affinity. Freeze the host identity, runtime, image IDs, profiles and exact target commands. If both profiles do not execute a supported workload, do not repair the problem by changing just one profile's timeouts or test.

Output `subject_manifest.json` and `environment_manifest.json`; use null with a reason for genuinely unknown historical facts, not invented values. Critical current image/command/profile identities must be known to launch.

## Phase 2: minimum implementation

Preferred implementation location after authorization: an isolated `c1_harness/` adapter plus study-local driver. Preserve `e1_harness/` and frozen E1 outputs. Reuse stable modules through explicit imports; do not copy an entire framework or build a generic orchestration platform.

| Existing component | Disposition | Required C1 seam |
|---|---|---|
| `e1_harness/policy.py` | KEEP | Same P1/P3/P3-retain semantics and prefix boundaries; test unchanged behavior. |
| `e1_harness/ledger.py` | KEEP / VALIDATE | Separate ledger per subject/profile, unique study IDs, verify chains and joins. Never concatenate profiles into colliding E1 identities. |
| `e1_harness/runner.py` | ADAPT externally | Existing manifest has no CPU settings. C1 needs enforced profiles, environment parameters, runtime inspection, matched scheduling and budget admission. A condition label alone changes nothing. |
| `e1_harness/oracle.py` | KEEP existing cards / ADAPT registry | Three cards exist; add grpc2391, istio17860 and k8s26980 from reviewed source records in the C1 layer. |
| `e1_harness/analysis.py` | REUSE primitives / ADAPT | Existing within-profile contrasts do not implement matched R/L analysis. Do not pool two independent E1 reports and call it a paired comparison. |
| Q0 recipes, manifests, logs | VALIDATE | Evidence inputs and reconstruction sources, not new observations. |
| T0, LRTS, historical prediction, APFD | FREEZE | No role in C1 execution or primary scoring. |
| Existing negative results | KEEP | No revisions to Q0, E1 or F1 conclusions. |

Required adapter behavior:

- Literal argument arrays, image IDs, profile parameters and command hashes enter the immutable manifest. Capture resulting container configuration before execution where necessary; avoid relying on inspection after a short-lived `--rm` container vanishes.
- Each attempt has study/subject/profile/variant/block/attempt/stage identity. One manifest/ledger per subject/profile avoids existing-key collisions. A separate matched-block ID joins R and L.
- One container at a time, fresh reset, specific-container cleanup after timeout, no stateful volumes, explicit host-load check. Never kill unrelated containers or processes.
- Full triple collection for measured cells; actual early stopping for direct policy checks. No automatic rerun on infrastructure failure. Log events rather than rewriting attempts.
- Budget reservation before blocks; wall-clock timeout and cleanup enforcement; no unbounded hanging driver. Cost totals include all stages and interrupted work.
- Support resuming only from recorded schedule state after a reviewed interruption. Do not repeat a committed attempt ID. A partly collected matched block remains incomplete for the primary analysis; mark its unrun cells missing and continue at the next scheduled block if authorized and valid.
- Keep measured, calibration, control and direct-check ledgers separate. Scheduling and oracle helpers cannot leak evaluator labels into policies.

## Phase 3: implementation checks, then fixed calibration

First run meaningful offline checks: policy truth tables including fail/pass prefixes; profile argument/inspection agreement; ledger uniqueness across profiles; censored/missing prefix decisions; matched-block joins; conservative bounds; resource admission; resume behavior; deterministic schedule regeneration; replay of old oracle logs and negative fixtures. Hash fixtures and source code.

Then, within the six-hour capacity budget for validation/calibration:

1. **Fixed smoke calibration:** one attempt per enrolled subject/profile/variant (24 attempts at six subjects). This checks target execution, capture and profile enforcement, not effect size. No pass/fail frequency criterion. No extra smoke attempts because a bug did not fail.
2. **Identity control:** use the first structurally ready subject's same acceptable image in both nominal version slots, three attempts per slot/profile (12 attempts). These observations must never support revision attribution. Failures are investigated, not automatically nuisance or an automatic reason to choose a different control.
3. **Direct policy checks:** first structurally ready subject, each profile x variant x P1/P3 once (eight traces; at most 24 primitive attempts). Check direct execution against reduction of its own recorded prefix, stopping rule and cleanup. Do not demand identical outcomes from separate stochastic executions. Flag that these checks are structural, not proof of counterfactual equality.
4. **Isolation/timeout checks:** four bounded non-empirical helper attempts, two/profile. The first container writes a marker and exits; the second fresh container checks that the marker is absent and then deliberately reaches the helper timeout so cleanup can be verified. Record both costs. A predeclared helper fixture is implementation validation, never product-defect evidence.

Helper profile probes also consume the stage budget; count them even when not part of these 64 maximum subject/control/helper attempts. If verification cannot finish inside the cap, stop before measured data. Preserve calibration results and oracle concerns; do not tune CPU quota, GOMAXPROCS, commands or sample size from them. A necessary amendment is written and reviewed before measurement, with the affected exploratory observations disclosed.

## Phase 4: launch freeze

The scientific design is already frozen by `DESIGN_FREEZE.sha256`. Create the distinct executable `launch_record.md` and `FREEZE.sha256` only after preparation and validation. Never treat the design checksum as evidence of runtime readiness. The launch record must contain:

- protocol/version and actual freeze time; researcher adoption/authorization reference;
- all enrolled/excluded subjects and reasons; exact source and executable identities;
- full host/profile manifests, code revision plus hashes of any uncommitted run code, versions/dependencies;
- materialized `schedule.csv`, exact commands and working directories, sample counts and family size;
- expected costs from observed durations, timeout ceiling, reserved stage caps and live budget guard;
- oracle validation coverage, unresolved risks and calibration/control/direct-check outcomes;
- literal run and analysis CLI commands that have actually been validated, not guessed flags;
- output location and byte-preservation mechanism. Hash raw bytes; verify line endings survive the intended Git checkout/export path.

Freeze the design checksum, immutable design files, accepted amendments, subject/environment manifests, schedule, run code and oracle source. `FREEZE.sha256` excludes itself and mutable records such as `research_record.md`, readiness updates, event/resource logs and attempt ledgers; the launch record states precisely what is frozen. Git commit is optional evidence, not required permission to run. Commit/push only when authorized for the relevant pass; this document-freeze pass is authorized, while the coding handoff does not automatically authorize publishing later implementation changes.

## Phase 5: measured execution

Execute the saved schedule for batch A, then run the integrity/cost gate before batch B. Keep any live console inspection to operational checks and predeclared validity alarms. Do not calculate comparative effects between batches to decide whether to continue.

The runner checks CPU configuration, subject identity, free capacity and absence of leftover study containers. An observer can monitor process status, elapsed time and recorded outputs without changing the experiment. Capture start/end times for each attempt and batch. Revalidate the environment after any restart. If identity changes, stop and record a deviation rather than mixing environments.

A hardware/daemon failure is a recorded interruption, not a reason to silently replace data. Resume from the next unrecorded scheduled block after integrity review. If the protocol gate fails, preserve the incomplete report.

## Phase 6: analysis and interpretation

Seal raw observations before classification; keep mechanical annotations and evidence-based adjudications separate. Run the frozen analysis, independent arithmetic verification and missingness bounds. Build the report specified in [analysis_plan.md](analysis_plan.md).

Only then apply the follow-up gate. A stronger finding requires fresh confirmation and credible nuisance controls if claiming a nuisance/sensitivity tradeoff. Ordinary paired methods being sufficient is an acceptable final conclusion.

## Minimal persistence contract

| Artifact | Required fields |
|---|---|
| Manifest | study ID, subject, counterpart type, revision/blob/test/dependency/image hashes, profile ID and enforced quota, runtime, literal argv, workdir, timeouts, oracle/code hashes |
| Attempt | unique identity, matched block, stage, scheduled/actual order, UTC start/end and availability time, monotonic elapsed seconds, exit/timeout/cleanup, stdout/stderr or content hashes, inspect/profile evidence, previous-record/hash, interruptions |
| Cost | stage, attempt/job, allocated-capacity basis, full elapsed/cleanup/gap, measured CPU or unknown, reserved/charged amount, host-reservation cost |
| Annotation | attempt hash, mechanical categories/signatures, oracle hash, later adjudication, rationale/evidence, adjudicator, annotation timestamp |
| Decision | policy, final status, warning, visible prefix IDs, suffix IDs, supported/unknown metrics and prefix cost |

Annotations may arrive later than the attempt; record both availability times. Never use future annotation as a policy input. Store build/image archives outside Git with durable checksums and retrieval locations; preserve small raw logs and tables under the new study root when suitable. Do not add a database, service or agent system.
