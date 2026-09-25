# Task 5 — restoration and Q0 qualification of card C-04 (grpc-go-2391)

## Result

| | `V_bad` (parent `39444b99` + fix test) | `V_ok` (squash-merge `ff2aa059`) |
|---|---:|---:|
| Attempts (frozen protocol, counted) | 20 | 20 |
| `FOCAL_DEFECT_WITNESS_A` | **18** | 0 |
| `PASS` | **2** (attempts 10 and 17) | 20 |
| `UNRESOLVED` / `HARNESS_INVALID` | 0 / 0 | 0 / 0 |

**Disposition: `Q0_QUALIFIED`** (historical pair with an identical test backport).

- **The criterion:** Q0 requires ≥2 focal failures **and** ≥2 passes on `V_bad` over the 20 counted attempts. This pair meets the passes requirement **exactly at the minimum**, the mirror image of etcd-7492, which met the focal requirement at its minimum.
- **`V_ok`:** clean, 20/20 `PASS`, with no `DeadlineExceeded` line in any log.
- **Qualification is selection, not a rate:** it establishes that the failure is measurably mixed under the frozen protocol. It does not estimate a population failure rate. 18/20 on this host is a high and imprecise rate.

## Authority and timing

- **Authority:** card C-04 (`task_c3_candidate_acquisition.md`), with Task 5 authorised by the researcher on 2026-09-25 for C-04 and then C-05.
- **Task 5 window:** `2026-09-25T08:18:58.909Z` → `08:28:59.352Z`, **600.4 s**.
- **Counted attempts:** `08:22:27.579Z` → `08:28:42.935Z`.
- **Operational day:** 8.

## Step 1 — counterpart verification: PASS

| Image | ID | `clientconn.go` | `test/end2end_test.go` | commit |
|---|---|---|---|---|
| `grpc2391-bug` | `sha256:cc6e5a69cd7a032623f39b04acc0e9f108d18cf22b4891fc629a413f152a92a2` | `e74f8e40…` (= parent `39444b99`) ✅ | `30d8a8c8…` ✅ | `ff2aa059` + GoReal patch |
| `grpc2391-fix` | `sha256:65a2902bbfce1dbc8afba7cd792dfeef134ad9aba2049ad65d333808b8906510` | `d0404313…` (= fix) ✅ | `30d8a8c8…` ✅ | `ff2aa059` |

- **Method:** blob IDs from `git hash-object` inside each image (`blob_check_{bug,fix}.txt`). They match the card's pre-declared values exactly.
- **What the patch does:** GoReal's `bug_patch.diff`, used unchanged, re-adds the three lines the fix removed and touches nothing else. The identical upstream test therefore compiled at the parent's product code.

## Step 2 — image builds: PASS, one disclosed deviation

- **Deviation from GoReal:**
  - **Module mode:** `GO111MODULE=on`, from the revision's own `go.mod`, in place of GoReal's unpinned GOPATH `go get -d` of dependency heads. For grpc-go-1859, that GOPATH approach failed on Go 1.13 and needed hand-pinned clones.
  - **Checkout:** a shallow fetch of the exact commit in place of a full clone and reset.
  - **Equal treatment:** both images are built identically apart from the bug patch.
- **Dependencies are reproducible:** `go list -m all` records 18 modules, all 2018-dated pins from the project's `go.mod` (for example `golang.org/x/net v0.0.0-20180826012351-8a410e7b638d`). The list is identical in both images (`dep_versions_{bug,fix}.txt`). **The A13/A19 dependency gap is closed for this candidate.**
- **Build time:** both builds exited 0, `08:19:08.488Z` → `08:19:39.560Z`.
- **Environment:** `golang:1.13`; this pass reconstructs neither the historical Travis matrix nor its Go versions, which is disclosed.

## Step 3 — uncounted exploratory runs

- **Command:** `-test.run '^TestGoAwayThenClose$' -test.timeout 60s`, in `timing/`.
- **`V_ok`:** 2/2 `PASS` (test time 0.01 s).
- **`V_bad`:** 5/5 failures, each ending about 20.0 s into the test with `end2end_test.go:7084: UnaryCall(_) = _, rpc error: code = DeadlineExceeded desc = context deadline exceeded; want _, nil`. That is **exactly the card's pre-declared signature (a); no correction was needed.** No leak report or timeout dump occurred.
- **What the runs decided:** the timeout, and a check of the classifier on all 7 logs. The protocol was not chosen by these outcomes, and the 5/5 was not used to decide whether to proceed.

## Step 4 — frozen protocol

`run/frozen_protocol.txt` was frozen at `2026-09-25T08:22:12Z`, before any counted attempt:

- **Images:** pinned by the IDs above.
- **Command:** `/go/gobench.test -test.v -test.count 1 -test.run '^TestGoAwayThenClose$' -test.timeout 60s` in `/go/src/google.golang.org/grpc/test`.
- **Limits:** a 90 s outer timeout (below the 120 s ceiling).
- **Reset and concurrency:** a fresh `docker run --rm` per attempt, strictly one job at a time.
- **Batches:** 10 `V_bad`, 10 `V_ok`, 10 `V_bad`, 10 `V_ok`, regardless of outcomes. `docker ps -a` was empty before and after.
- **Classifier:** `run/attempt.sh` applies only the pre-declared rules.

## Step 5 — counted qualification runs

- **Records:** `run/results.csv` holds all 40 rows, one log per attempt in `run/logs/`.
- **Durations:**
  - `V_bad` focal attempts took 19.59–19.87 s.
  - The two `V_bad` passes took 0.63 s and 0.61 s, each with test output `--- PASS: TestGoAwayThenClose (0.01s)`.
  - `V_ok` attempts took 0.57–0.68 s.
- **Cleanliness:** no leaked-goroutine report in any log.

## Accounting

- **Task 5 wall clock:** **EXACT**, 600.4 s ≈ **0.1668** allocated vCPU-h (Q0 convention, one vCPU-equivalent per sequential job, as in ledger A14).
- **Counted attempts:** 369.0 s ≈ 0.1025 h.
- **Cap:** ≤4 allocated vCPU-h per candidate, not reached (4.2% used).
- **Human restoration hours:** **UNKNOWN**; this was an agent-executed pass.
- **Artifacts:** `task5_artifacts/grpc2391/`, about 127 KB: recipes (the GoReal original and as-built), build logs, blob checks, dependency lists, exploratory logs, the frozen protocol, the attempt script, the results ledger and 40 raw attempt logs. They were written into the repository as the pass ran (ledger A18). The images themselves are not preserved.

## What was deliberately not done

- No attempts beyond the pre-declared 20 per version.
- No change to the command, timeout or environment after the exploratory runs.
- No relabelling.
- GoReal's GOPATH recipe was not used, for the reproducibility reason in Step 2. That was decided before any run.
