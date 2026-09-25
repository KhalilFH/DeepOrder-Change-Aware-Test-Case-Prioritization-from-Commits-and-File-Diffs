# Task 5 — restoration and Q0 qualification of card C-06 (kubernetes-26980)

## Result

| | `V_bad` (first parent `98f0d22b` + unchanged fix test) | `V_ok` (merge `628af356`) |
|---|---:|---:|
| Attempts (frozen protocol, counted) | 20 | 20 |
| `FOCAL_DEFECT_WITNESS_A` | **0** | 0 |
| `PASS` | **20** | 20 |
| `UNRESOLVED` / `HARNESS_INVALID` | 0 / 0 | 0 / 0 |

**Disposition: `Q0_NOT_QUALIFIED`** (primary track).

- **Why not qualified:** Q0 requires ≥2 focal failures **and** ≥2 passes on `V_bad` over the 20 counted attempts. There were no focal failures.
- **The mirror image of C-05:** istio-17860 failed on every attempt; this pair passed on every attempt. Both are threshold failures in opposite directions.
- **The counterpart is valid:** blob checks pass, so `V_bad` really carries the parent's lock-holding `pop()` (Step 1). What did not happen under this protocol is the interleaving that exposes it.
- **Not a proof that the defect cannot manifest:** 0 focal in 20 (plus 0 in 5 exploratory) does not show the failing interleaving is impossible. The card pre-declared that the split "is unknown and may be heavily skewed".
- **No rescue:** no attempts beyond the 20, no change to the command or environment, and no relabelling.
- **No secondary role is proposed.** Under this protocol the defect never manifested, so the pair cannot serve as the B2 stable-defect control either (contrast istio-17860).

## Authority and timing

- **Authority:** card C-06 (`task_c4_candidate_acquisition.md`), with Task 5 authorised by the researcher on 2026-09-25 ("run C-06 Task 5"), after PR #5 was merged.
- **Task 5 window:** `2026-09-25T09:01:48.403Z` → `09:07:34.530Z`, **346.1 s**.
- **Counted attempts:** `09:06:51.519Z` → `09:07:22.371Z`.
- **Operational day:** 8.

## Step 1 — counterpart verification: PASS

| Image | ID | `shared_informer.go` | `processor_listener_test.go` | `Godeps/Godeps.json` | commit |
|---|---|---|---|---|---|
| `k8s26980-bug` | `sha256:8a215c592956b0f99ff977285822ffcbc3116d1ff7fab1da692b0e67d28bafaf` | `ce9ddf2c7140…` (= first parent `98f0d22b`) ✅ | `ffd72d8fae24…` ✅ | `980fd6aca303…` | `628af356` + product-only patch |
| `k8s26980-fix` | `sha256:6c93e46a3848354353a72d545dc782257d620432c07d3497ded117476f75d5d4` | `c557bf97548a…` (= merge) ✅ | `ffd72d8fae24…` ✅ | `980fd6aca303…` | `628af356` |

- **Method:** blob IDs from `git hash-object` inside each image (`blob_check_{bug,fix}.txt`). They match the card's pre-declared values exactly.
- **Patch used:** only the `shared_informer.go` hunk of GoReal's `bug_patch.diff` (`recipe/as_built/bug_patch.diff`). GoReal's `V_bad`-only test edit, which replaces `t.Errorf("Timeout after %v", …)` with `debug.SetTraceback("all"); panic(…)`, is **not** applied, as the card required. The test file is therefore identical on both images.
- **Scope of the pair:** the card observed that `compare 98f0d22b…628af356` touches exactly these two files, so `V_bad` equals the first parent plus the fix's new test file.

## Step 2 — image builds: PASS, one disclosed deviation

- **Deviation from GoReal:**
  - **Checkout:** a shallow fetch of the exact merge commit into the GOPATH location, in place of a full clone and reset.
  - **Packages:** GoReal's `apt install rsync` (bug image) and `rsync vim python3` (fix image) are dropped on both images; none is used by `go test`.
  - **Equal treatment:** both images are built identically apart from the bug patch.
- **Toolchain:** `golang:1.12` (`go1.12.17`), as in GoReal, with `GO111MODULE=off` (GOPATH mode). This pass reconstructs neither the 2016 CI environment nor its Go version, which is disclosed.
- **Dependencies are pinned in-tree:** the revision vendors its dependencies under `vendor/`, and `Godeps/Godeps.json` is the same blob (`980fd6ac…`) in both images. No dependency is resolved at build time, so the A13/A19 dependency gap does not arise for this candidate.
- **Build times:** fix `09:02:47.556Z` → `09:05:34.280Z`, bug `09:05:41.482Z` → `09:05:53.801Z` (the bug build reused the cached fetch layer). Both exited 0 on the first attempt.

## Step 3 — uncounted exploratory runs

- **Command:** `-test.run '^TestPopReleaseLock$' -test.timeout 60s`, the card's provisional values, with logs in `timing/`.
- **`V_ok`:** 2/2 `--- PASS: TestPopReleaseLock (0.00s)`, at about 0.6 s per attempt.
- **`V_bad`:** 5/5 `--- PASS: TestPopReleaseLock (0.00s)`, at about 0.6 s per attempt. **No focal witness occurred**, so signature (a) could not be checked against an observed failure. It stays exactly as the card pre-declared it.
- **Container:** 16 CPUs visible (`timing/container_env.txt`), so GOMAXPROCS is 16 by default.
- **Decision taken after these runs:** keep the card's command, timeout and default scheduler environment unchanged. Adding `-test.cpu`, a GOMAXPROCS change, load or stress because `V_bad` kept passing would be forcing, or selection on the observed outcome (the C-03 and C-05 precedents).

## Step 4 — frozen protocol

`run/frozen_protocol.txt` was frozen at `2026-09-25T09:06:43Z`, before any counted attempt:

- **Images:** pinned by the IDs above.
- **Command:** `/go/gobench.test -test.v -test.count 1 -test.run '^TestPopReleaseLock$' -test.timeout 60s` in `/go/src/k8s.io/kubernetes/pkg/controller/framework`.
- **Limits:** a 90 s outer timeout (below the 120 s ceiling).
- **Reset and concurrency:** a fresh `docker run --rm` per attempt, strictly one job at a time.
- **Batches:** 10 `V_bad`, 10 `V_ok`, 10 `V_bad`, 10 `V_ok`, regardless of outcomes. `docker ps -a` was empty before and after.
- **Classifier:** `run/attempt.sh` applies only the pre-declared rules.

## Step 5 — counted qualification runs

- **Records:** `run/results.csv` holds all 40 rows, one log per attempt in `run/logs/`.
- **`V_bad`:** 20/20 `--- PASS: TestPopReleaseLock (0.00s)`, exit 0, at 0.567–0.675 s per attempt.
- **`V_ok`:** 20/20 `--- PASS: TestPopReleaseLock (0.00s)`, exit 0, at 0.523–0.653 s per attempt.
- **No log** contains `--- FAIL`, `Timeout after`, a panic or a test-timeout dump.

## Interpretation (not measured)

- **Hypothesis for the skew:** the test starts `go pl.pop(stopCh)` and then the locker goroutine, then blocks in `select`. In Go's scheduler, the most recently started goroutine usually sits in the current P's `runnext` slot and runs first when the starting goroutine blocks. The locker would then take `p.lock` before `pop` does, and the test passes. `pop` wins only if another P steals it first, which was evidently rare on this host.
- **This is source reasoning, not an observation.** No scheduler trace was taken, and none would change the verdict.

## Consequence for the day-10 gate (for the ledger to record)

- C-06 was the **last primary roster slot (12/12)**. With it `Q0_NOT_QUALIFIED`, qualified episodes stay at **three across two projects** (etcd-5509, etcd-7492, grpc-go-2391).
- No primary candidate remains that could provide the fourth episode before `2026-09-27T23:02:26Z`. Under the plan as written, the day-10 gate's episode condition cannot be met, and **G1b applies**: no E2; finish the small feasibility report and trigger F1 where possible.
- This record makes no gate decision. That belongs to the ledger and the researcher.

## Accounting

- **Task 5 wall clock:** **EXACT**, 346.1 s ≈ **0.0961** allocated vCPU-h (Q0 convention, one vCPU-equivalent per sequential job, as in ledger A14).
- **Counted attempts:** span 30.9 s; attempt-sum 24.7 s.
- **Cap:** ≤4 allocated vCPU-h per candidate, not reached (2.4 % used).
- **Human restoration hours:** **UNKNOWN**; this was an agent-executed pass.
- **Artifacts:** `task5_artifacts/k8s26980/`, about 135 KB. It holds the recipes (the GoReal original and as-built), build logs, blob checks, exploratory logs, the container environment, the frozen protocol, the attempt script, the results ledger and 40 raw attempt logs. They were written into the repository as the pass ran (ledger A18). The images themselves are not preserved.

## What was deliberately not done

- No attempts beyond the pre-declared 20 per version.
- No change to the command, timeout or environment after the exploratory runs, although all five exploratory `V_bad` runs passed.
- No `-test.cpu`, GOMAXPROCS, CPU-pinning, load or stress setting, and no scheduler trace.
- No switch to GoReal's instrumented (`panic`) test.
- No relabelling.
