# Task 5 restoration and Q0 qualification — grpc-go-1859 (card C-03)

- Record identifier: `ci_policy_sensitivity_task5_grpc1859_2026-09-22_v1`.
- Repository baseline at start: `8777c3de04649cb9e4499e85940604828b8e3531`, branch `research/revival-2026` (plus the uncommitted C2 artifacts).
- `task5_start_utc = 2026-09-22T17:44:33.746614400Z`; `task5_end_utc = 2026-09-22T18:00:14.143628200Z`.
- Operational Q0 day **5** (clock start `2026-09-17T23:02:26Z`).
- Card: `task_c2_candidate_acquisition.md`, "New candidate card C-03". Counterpart type pre-declared as **historical pair with identical test backport**.

## Q0 VERDICT: NOT QUALIFIED — intermittency criterion not met

| | `V_bad` (`grpc1859-bug`) | `V_ok` (`grpc1859-fix`) |
|---|---|---|
| Attempts (frozen protocol, counted) | 20 | 20 |
| `PASS` | **19** | **20** |
| `FOCAL_DEFECT_WITNESS_A` | **1** | 0 |
| `FOCAL_DEFECT_WITNESS_B` | 0 | 0 |
| `UNRESOLVED` / `OTHER` / `HARNESS_INVALID` | 0 | 0 |

Q0 requires **at least two focal failures and at least two passes** among 20 `V_bad` attempts at the frozen protocol. Observed: **1 focal failure**. The criterion fails by one witness.

**Disposition: `Q0_NOT_QUALIFIED` on the primary track.** The episode is *not* enrolled as a qualified primary episode and does not count toward the day-10 gate. No rescue was attempted: no additional attempts were run after the pre-declared 20, the frozen environment was not changed after seeing counted outcomes, and no outcome was relabelled. See "What was deliberately not done" below.

This is a **threshold** failure, not a demonstration that the test is deterministic. The observed `V_bad` stream is literally mixed (1 fail, 19 pass) and the `V_ok` stream is clean; the defect mechanism reproduced and was correctly attributed. The measured rate is simply too low for the protocol's power bar at n=20.

## Step 1 — blob-equivalence check: **PASS**

The strongest result of this pass, and stronger than either etcd case.

Reconstruction: fetched the three merge-revision files, applied GoReal's `bug_patch.diff` in a scratch git repo with `core.autocrlf=false` / `core.eol=lf`, and hashed the result.

| File | Reconstructed `V_bad` | Authoritative historical parent `6c48c7f5…` | Match |
|---|---|---|---|
| `transport/http2_client.go` | `717e4192ea13547ffe323613d3d4945c9c5a9b00` | `717e4192ea13547ffe323613d3d4945c9c5a9b00` | ✅ |
| `transport/http2_server.go` | `5233d6f3db6bd29622f694a59befd50d9e6d7365` | `5233d6f3db6bd29622f694a59befd50d9e6d7365` | ✅ |
| `test/end2end_test.go` | `6a583182170323ec5b23d760d926c92d3816be18` | (merge blob, unchanged — the identical test backport) | ✅ |

`git diff` of the reconstruction against the merge is exactly the four removed production lines (two comments, two `t.sendQuotaPool.add(tq)` statements) across the two transport files, and nothing else. **The counterpart is a genuine historical pair with an identical test backport** — the card's fallback to "controlled historical-fix reversal" was not needed.

Re-verified **inside the built images** (the card's pre-declared Task 5 check):

| Image | `http2_client.go` | `http2_server.go` | `end2end_test.go` |
|---|---|---|---|
| `grpc1859-bug` | `717e4192…` ✅ | `5233d6f3…` ✅ | `6a583182…` ✅ |
| `grpc1859-fix` | `56b434ef…` ✅ | `24c2c7e1…` ✅ | `6a583182…` ✅ |

Mechanism sanity check: the string `Add the acquired quota back to transport` occurs 0 times in each transport file in the bug image and 1 time in each in the fix image. The two test binaries have coincidentally identical byte size (14,610,125) but different SHA-256 — noted because size alone would have been a misleading check.

**CRLF finding (disclosed).** The Windows checkout of GoBench stored `bug_patch.diff` with CRLF line endings (26 CR bytes, sha256 `6e9042a7…`), and `git apply` rejected it. The authoritative repo blob is pure LF (`bb72cba21a09c731ae0189e15fe3283df6ca2e98`, sha256 `36595003…`, 0 CR), confirmed identical to the GitHub raw file at the pinned commit. All work used the LF blob. This is a local checkout artifact, not a content change — the same class of problem the etcd-5509 pass recorded.

## Step 2 — image builds: **PASS, with two disclosed deviations**

Base recipe: `gobench/goreal/blocking/grpc/1859/{bug,fix}.Dockerfile` at pinned GoBench commit `2e91eb10b8e7b2873ea44f12b87ec1b2520e1b69`.

**Deviation 1 — dropped an unused `apt-get install -y vim python3` step from `fix.Dockerfile`** (unreferenced by later steps; present only in the fix recipe, so removing it makes the two recipes symmetric). Same precedent as the etcd-7492 pass.

**Deviation 2 — replaced GoReal's unpinned dependency step with identical pinned clones in both images.** This was **forced, not chosen**: the recipe's `go get -v -d` of master heads fails on `golang:1.13` with `package embed: unrecognized import path "embed"` (current `golang/protobuf` master depends on `google.golang.org/protobuf`, which requires Go 1.16+). The card pre-declared this contingency ("if a current dependency head no longer compiles against 2018 grpc-go, pin to a dated commit and disclose it"). Each dependency is pinned to its **last commit on or before 2018-02-13**, the subject's merge date — which is *more* faithful to the historical environment than master heads:

| Package | Repository | Commit | Date |
|---|---|---|---|
| `github.com/golang/glog` | golang/glog | `23def4e6c14b4da8ac2ed8007337bc5eb5007998` | 2016-01-26 |
| `github.com/golang/protobuf` | golang/protobuf | `e6af52bec88380a7a18ecc0977fa4312370a970b` | 2018-02-07 |
| `golang.org/x/net` | golang/net | `f5dfe339be1d06f81b22525fe34671ee7d2c8904` | 2018-02-08 |
| `google.golang.org/genproto` | googleapis/go-genproto | `2b5a72b8730b0b16380010cfe5286c42108d88e7` | 2018-02-06 |
| `golang.org/x/text` | golang/text | `4e4a3210bb54bb31f6ab2cdca2edcc0b50c420c1` | 2018-02-08 |

`golang.org/x/text` is not in GoReal's list; it was added because `x/net/idna` requires it and the original `go get` would have pulled it transitively. The resolved commits were recorded **inside each image** at `/go/dep_versions.txt` and verified byte-identical between the two images, closing the reproducibility gap flagged in ledger A13. Both builds exited 0; `/go/gobench.test` present in both.

## Step 3 — uncounted exploratory runs, and the expired-certificate finding

These runs are **not counted** toward the 20+20 and are reported in full because they determined the frozen protocol.

**First timing runs (`-test.timeout 110s`, all environments): both versions timed out at 110 s.** Diagnosis from the goroutine dumps: only 7 goroutines, **zero** `quotaPool.get` frames, and the test goroutine blocked at `end2end_test.go:6017` → `te.clientConn()` → `grpc.Dial` → `WaitForStateChange`. The frame arguments identify a 19-character environment name — `tcp-tls-v1-balancer`.

**Root cause: the repository's test certificates have expired.** Inside the image, `testdata/ca.pem` is valid `2014-11-11` → **`2024-11-08`** and `testdata/server1.pem` `2015-11-04` → **`2025-11-01`**. Today is 2026-09-22. Every TLS environment therefore fails certificate validation and blocks in `Dial` until the test timeout.

Two consequences worth recording:

1. **This is a wall-clock artifact of running a 2018 test in 2026, affecting both versions identically.** It is not a property of either revision, and under the frozen categories it is `HARNESS_INVALID`, never a focal witness.
2. **The pre-declared signatures did their job.** A naive frozen run would have produced 20/20 timeouts on *both* versions — superficially a dramatic "deterministic failure" — yet signature (b) requires `quotaPool.get` frames under `http2Client/Server.Write`, which were absent, so the outcome would have been correctly classified `UNRESOLVED` rather than a defect witness. This is direct evidence that the protocol's insistence on stack-level signatures, rather than exit status, is load-bearing.

**Resolution — environment restriction via the test's own upstream flag.** The frozen test source defines `-only_env` (declared at `end2end_test.go:407`, upstream, unmodified). Restricting to a clear-text environment avoids the expired certificates without touching the subject, the test source, or any product behaviour, and applies identically to both versions. Of the six `allEnv` entries, four use TLS (`tcp-tls-v1-balancer`, `tcp-tls`, `handler-tls`, `no-balancer`) and two are clear (`tcp-clear-v1-balancer`, `tcp-clear`).

Exploratory probes after the restriction (uncounted):

| Image | Environment | n | PASS | FAIL |
|---|---|---:|---:|---:|
| `grpc1859-bug` | `tcp-clear-v1-balancer` | 10 | 9 | **1** |
| `grpc1859-bug` | `tcp-clear` | 10 | 8 | **2** |
| `grpc1859-fix` | `tcp-clear-v1-balancer` | 5 | 5 | 0 |

All three exploratory failures matched **pre-declared signature (a)** verbatim — `rpc error: code = DeadlineExceeded …, want code: ResourceExhausted`, with a test duration of ~10.1 s (the call deadline). **No signature correction was required**, in contrast to etcd-5509, which needed two.

## Step 4 — frozen protocol

Frozen after the exploratory runs and **before any counted attempt**:

```
image_bad   = grpc1859-bug     image_ok = grpc1859-fix
workdir     = /go/src/google.golang.org/grpc/test
command     = /go/gobench.test -test.v -test.count 1
              -test.run '^TestClientDoesntDeadlockWhileWritingErrornousLargeMessages$'
              -test.timeout 110s -only_env tcp-clear-v1-balancer
reset       = fresh `docker run --rm` per attempt; nothing persists between attempts
concurrency = strictly one job at a time
batches     = 10 per version, then 10 more per version regardless of early outcomes
```

**Environment choice is a declared integrity point.** `tcp-clear-v1-balancer` was selected as the **first clear-text entry in the upstream `allEnv` list order** (`tcpClearEnv`). The other clear environment, `tcp-clear`, showed the *higher* exploratory failure rate (2/10 vs 1/10) and was deliberately **not** chosen, because selecting the environment by observed failure rate is precisely what the plan forbids ("Do not rank by newly measured policy losses"). The consequence — a lower-rate environment, and therefore a harder intermittency bar — is accepted and is a plausible contributor to the verdict below.

`-test.timeout 110s` sits under the plan's 120 s attempt ceiling. Observed attempt durations: passes ~0.8 s, the focal failure 10.49 s. The ceiling was never approached, so the card's "cannot complete inside the ceiling" blocker did not materialise once the certificate issue was understood.

## Step 5 — counted qualification runs

40 attempts, strictly sequential, per-attempt UTC start/end, elapsed, exit code, classification and full log preserved in the scratch workspace (`run/results.csv`, `run/logs/*.log`; not committed).

`V_bad`: attempts 1, 2, 4–20 `PASS`; **attempt 3 `FOCAL_DEFECT_WITNESS_A`** (10.49 s; ten `DeadlineExceeded … want code: ResourceExhausted` lines at `end2end_test.go:6035`). `V_ok`: 20/20 `PASS` (0.79–0.88 s).

Batch 2 was executed in full after batch 1 had already produced its single witness, as the protocol requires ("regardless of whether early outcomes look favorable").

Classification audit: every one of the 40 logs was re-checked mechanically for a `PASS` marker co-occurring with a `FAIL` marker; **0 inconsistencies**.

**Acceptable-counterpart result:** 20/20 clean on `V_ok`. This is supportive reproduction evidence, not proof of zero defect probability. Notably, **the counterpart-validity caveat recorded on card C-03 did not reproduce**: the post-merge Travis hang of the fixed test (issue #1850, comment of 2018-02-14) produced no analogue here — no `V_ok` attempt exhibited signature (a) or (b). That caveat is neither confirmed nor refuted by 20 attempts in a single environment on one host; it remains recorded.

## What was deliberately not done

Each of these would have changed the verdict and each is forbidden or compromising:

- **Not** run further `V_bad` attempts beyond the pre-declared 20 to reach a second witness. The batch size was frozen in advance; extending it after seeing 1/20 is sampling to a foregone conclusion.
- **Not** re-run on `tcp-clear`, the environment with the higher exploratory rate. Switching environments after a disappointing counted result is selection on observed loss.
- **Not** run with multiple environments, a longer deadline, added load, or `-test.cpu` tuning to raise the rate. All would be forcing.
- **Not** relabelled the 19 passes or reinterpreted the single witness.
- **Not** treated the earlier all-environment timeouts as focal witnesses, which would have produced a spurious 20/20 "qualification" on the strength of an expired certificate.

## Resource accounting

| Item | Value | Basis |
|---|---|---|
| Task 5 wall clock (start → end) | **EXACT**, `940.4 s` ≈ `0.2612` allocated vCPU-h | recorded timestamps, one sequential job at a time |
| of which the 40 counted attempts | **EXACT**, `60.8 s` ≈ `0.0169` h | `counted_start_utc` → `counted_end_utc` |
| Per-candidate cap (≤4 allocated vCPU-h) | **not reached** — 6.5 % used | above |
| Per-candidate human-hour cap (≤2 h) | **provisional**; human effort **UNKNOWN** | same convention as ledger A6/A8 |
| Cumulative Q0 restoration/qualification | **≈0.969 h** of the 20 h Q0 ceiling and the 40 h first-ten-day ceiling | 0.708 prior + 0.261 |
| Stop triggered by a cap | none | no cap approached |

Artifacts: images `grpc1859-bug` / `grpc1859-fix` (1.73 GB each, retained locally); build logs, dependency manifests, `frozen_protocol.txt`, `results.csv` and 40 attempt logs in the ephemeral scratch workspace.

## Roster and gate consequences

- **grpc-go-1859: `Q0_NOT_QUALIFIED`** (primary track). The roster entry remains; it is not a qualified episode.
- Qualified episodes remain **two, both etcd** (etcd-5509, etcd-7492). etcd's per-project primary cap is saturated.
- **Day-10 gate** (four qualified episodes across ≥2 projects by `2026-09-27T23:02:26Z`): now requires **two** further qualified non-etcd episodes within five days, from a roster that has 3 free primary slots and no remaining metadata-ready candidate. On the evidence of this pass and the C2 screening, that is unlikely.
- **G1b consequence, stated plainly:** if the gate is missed, the plan's declared path is "No E2. Finish small feasibility report and trigger F1 where possible." Nothing in this pass authorises widening the defect definition, raising a cap, or re-running this candidate under a different environment to manufacture a qualification.

## Options for the researcher (not taken here)

1. **Accept the no-go and move to the E1/F1 path.** Two qualified etcd episodes already satisfy the day-7 gate, so E1 (calibration on two episodes) remains executable regardless; the day-10/E2 gate is what is at risk.
2. **A separately budgeted amendment** re-running C-03 on `tcp-clear`, explicitly labelled as development-only and selection-biased. This would *not* produce a clean qualification and must never be reported as one.
3. **Retain C-03 as a named non-primary case.** The mechanism reproduced, the counterpart is the cleanest historical pair in the roster, and the episode is cheap (0.26 vCPU-h end to end). It is a legitimate *demonstration* subject even though it fails the intermittency bar.
4. **Resume acquisition** at `grpc_2391`, then `grpc_3017` (both `NOT_SCREENED`), which is the deterministic next position. The C2 screening's prior is that most remaining grpc entries are deterministic.

Option 1 is the honest reading of the evidence. Option 3 is compatible with it.

## Threats and limits

- **One host, one environment, n=20.** The rate estimate is very imprecise: 1/20 with exploratory data suggesting roughly 5–10 %. A different host, core count, or environment could easily cross the ≥2/20 bar. This pass establishes that *this* protocol on *this* host did not.
- **Environment restriction narrows the workload** from five executed environments to one, reducing the number of racing calls per attempt by roughly 5× and therefore the per-attempt failure probability. The restriction was unavoidable (expired certificates) but it is a real limit on comparability with the historical CI.
- **Go 1.13 and 2018-dated dependencies** are not the historical CI environment (Travis ran Go 1.6–1.9 with `make test`). Disclosed, identical across both versions.
- **The expired-certificate problem generalises.** Any GoReal/BugSwarm-style Java or Go subject whose tests exercise TLS with committed test certificates will exhibit the same class of failure when restored years later. This is worth carrying into any future artifact-qualification work as a standing screening question, and it is a genuine, reusable finding of this pass independent of the verdict.
