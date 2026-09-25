# Task C resumption (C3) — two further non-etcd primary candidates for the day-10 gate

## Scope and stop

- **Authority:**
  - Ledger A15: the day-10 gate is not met and "would require two further qualified non-etcd episodes".
  - The Q0 protocol: roster ceiling, deterministic source order and per-candidate caps.
  - The researcher's instruction of 2026-09-25: a rule-following qualification sprint toward the gate.
- **This pass is metadata acquisition only.**
  - Nothing was restored, built or executed. No qualification attempt ran and no harness code was written.
  - Restoration/qualification vCPU-hours in this pass: **EXACT, zero.**
- **Timing:**
  - Acquisition started at `2026-09-25T08:06:08.831036600Z`.
  - Per-ID screening stopped at `2026-09-25T08:12:12.479262400Z`: **363.648 s** of agent/tool elapsed time.
  - Byte-level and compile-plausibility checks for the two cards ran until `2026-09-25T08:13:35.878364700Z`.
  - Operational day 8 (the A1 clock started `2026-09-17T23:02:26Z`).
  - Day-10 gate: `2026-09-27T23:02:26Z`.
- **Stop rule, the researcher's instruction for this pass:** stop at the second defensible non-etcd `PRIMARY_METADATA_READY` candidate in deterministic order. Two are the minimum that could still meet the gate. This is not a pre-registered protocol gate, and it does not authorise Task 5.

## Order and method

- **Order:** unchanged from C2. Tier 4 (GoReal, the language decision in ledger A5.1), then project in GoReal's `blocking.json` order, then numeric issue ID. The pass resumes at order 21, where C2 stopped.
- **Sources:**
  - `gobench/configures/goreal/blocking.json` and `gobench/goreal/blocking/<project>/<id>/{README.md,bug.Dockerfile,fix.Dockerfile,bug_patch.diff}` at GoBench commit `2e91eb10b8e7b2873ea44f12b87ec1b2520e1b69` (the same pin as Task C, C2 and Task 5).
  - Read through the GitHub REST API and raw.githubusercontent.com, because a `git clone` into the scratch workspace failed on this host's long path.
  - Upstream PRs, commits and file blobs read through the GitHub REST API.
- **Labels:** the C2 vocabulary. A new disposition is needed only because grpc-go reaches its per-project cap in this pass.

## Per-ID screening record

| Order | Entry | Upstream fix (authoritative) | Files changed upstream | Disposition | Reason |
|---|---|---|---|---|---|
| 21 | **grpc_2391** | PR #2391 "internal: fix GO_AWAY deadlock", squash-merged 2018-10-19 as `ff2aa05958775030998dbe2f9bccbe2af324adf4`, sole parent `39444b99c097c9f53536ad8f16cd9f0288c7f695`; on `master` | `clientconn.go` +0/−3 (product), `test/end2end_test.go` +109/−0 (test added) | **Carded C-04, `PRIMARY_METADATA_READY`** | First defensible candidate in this pass. Fills grpc-go's second primary slot (2/2). |
| 22 | grpc_3017 | PR #3017 "grpclb: fix deadlock in grpclb connection cache", merged 2019-09-10 as `ac35b67779…` | `balancer/grpclb/grpclb_util.go` +1/−1 (product), `grpclb_util_test.go` +43/−0 | `SCREENED_INELIGIBLE_PROJECT_CAP` | grpc-go is saturated at 2/2 once C-04 is carded. By source reasoning it would also be a `SCREENED_DETERMINISTIC_LEAD`: the added test runs 1,000 remove/re-add iterations against a 1 ns removal timer, and the unlock-less early return fires whenever the re-add wins the mutex, so a deadlock within one run is near-certain. Retained as a stable-control lead. |
| 23 | hugo_3251 | PR #3251 "tplimpl: Fix deadlock in getJSON", merged 2017-03-31 as `79b34c2f1e…`; fixes #3211 | `tpl/tplimpl/template_resources.go` +8/−1 (product), `template_resources_test.go` +43/−0 | `SCREENED_DETERMINISTIC_LEAD` | At the parent, `URLLock` acquires the per-URL mutex while holding the map lock, and releasing the URL needs the map lock: an AB-BA cycle. The added `TestScpGetRemoteParallel` runs 50 goroutines × 10 fetches of one URL, so two overlapping holders, and hence the deadlock, are expected in every run. |
| 24 | hugo_5379 | PR #5379 "hugolib: Fix deadlock when content building times out", merged 2018-10-30 as `729593c842…`, sole parent `e65268f2c2…`; fixes #5375 | `hugolib/page.go` +9/−2 (product), `hugo_sites_build_errors_test.go` +30/−0 | `SCREENED_DETERMINISTIC_LEAD` | The added `TestSiteBuildTimeout` makes each of 99 pages render a shortcode that reads every other page's `.WordCount`. The content loop is circular by construction, so the 5 ms timeout always fires. At the parent, the rendering goroutine keeps `contentInitMu` after the timeout while it waits on another page, so a lock cycle forms structurally rather than by chance. This is a source-reasoning judgment, not a measurement. |
| 25 | istio_16224 | PR #16224 "Fix memory monitor test deadlock", merged 2019-08-13 | `pilot/pkg/config/memory/monitor_test.go` +4/−3 only | `SCREENED_TEST_ONLY_FIX` | Test-code-only change; no product fix. |
| 26 | **istio_17860** | PR #17860 "Fix deadlock in envoy restart logic.", merged 2019-10-15 as `c6e9130227497ab064dd571a1409236d17aa2ef3`, sole parent `7a9a996f6641024298e6010c6f1d7e87a83a48dc`; on `master` | `pkg/envoy/agent.go` +50/−28 (product), `pkg/envoy/agent_test.go` +55/−0 (test added) | **Carded C-05, `PRIMARY_METADATA_READY`** | Second defensible candidate. **Stop point.** Fills istio's first primary slot (1/2). |
| 27–40 | istio_18454, kubernetes_1321, kubernetes_11298, kubernetes_16851, kubernetes_25331, kubernetes_26980, kubernetes_30872, kubernetes_38669, kubernetes_70277, moby_29733, moby_30408, serving_2137, syncthing_4829, syncthing_5795 | — | — | `NOT_SCREENED` | After the stop point. For the record only, not a ranking: istio_18454's PR title and file list were read. Its fix bundles a product change (`publish/strategy.go` +4/−1) with de-flaking the same test (`processor_test.go` +8/−63), and GoReal's `V_bad` reverts both, which would be a confounded counterpart. The GoReal README descriptions of the rest were read in bulk but not dispositioned. |

## New candidate card C-04 — grpc-go 2391

- **Source tier:** 4, GoReal fallback (`grpc_2391`, order 21).
- **Classification:** `PRIMARY_METADATA_READY`. **Not Q0-qualified; intermittency unmeasured.**
- **Counterpart type (plan §4.1):** historical pair with an isolatable focal change and an identical test backport, confirmed at the blob level below.
- **Authoritative identity, observed:**
  - PR #2391, "internal: fix GO_AWAY deadlock", squash-merged 2018-10-19T21:11:21Z as `ff2aa05958775030998dbe2f9bccbe2af324adf4`, with sole parent `39444b99c097c9f53536ad8f16cd9f0288c7f695`.
  - The PR body: "A deadlock can occur when a GO_AWAY is followed by a connection closure … onClose needlessly closes the current ac.transport: if a GO_AWAY already occured, and the transport was already reset, then the later closure (of the original address) sets ac.transport - which is now healthy - to nil. The manifestation of this problem is that picker_wrapper spins forever trying to use a READY connection whose ac.transport is nil."
- **Candidate `V_bad`:** `39444b99…` plus the identical backport of the fix's test addition. **Candidate `V_ok`:** `ff2aa059…`.
- **Blob-level counterpart check, observed:**
  - `clientconn.go` is blob `e74f8e40ea3c697b5479cf020a97a82c5cabb897` at the parent and `d04043137a7ed5bfa5fe9df401e064e693573569` at the fix.
  - GoReal's `bug_patch.diff` (`index d0404313..e74f8e40`) re-adds exactly the three removed lines and touches no other file. Applied to the fix tree, it therefore yields the parent's `clientconn.go` byte for byte.
  - `test/end2end_test.go` is blob `30d8a8c8d0516165b46723900e72de61e7e242ce` at the fix, and must be identical in both images.
  - **Task 5 check:** in the built images, `git hash-object clientconn.go` must be `e74f8e40…` in `V_bad` and `d0404313…` in `V_ok`, and `test/end2end_test.go` must be `30d8a8c8…` in both.
- **Focal behavioural obligation:** after a GO_AWAY on connection 1 and the subsequent closure of that connection, the client must keep using the healthy replacement transport. Each of the test's ten subsequent `UnaryCall`s must complete without error within the test's 20 s context.
- **Defect mechanism at `V_bad`, observed in source:**
  - In `addrConn.createTransport`, the `allowedToReset` branch sets `ac.transport = nil` under `ac.mu` before `oneReset.Do(...)`.
  - If the GO_AWAY path has already reset the connection to a healthy new transport, the old connection's closure nils that healthy transport.
  - `oneReset` has already fired, so nothing re-creates it, and the picker spins on a READY `addrConn` with a nil transport.
- **Witness, observed:** the upstream `test::TestGoAwayThenClose`, added by the fix. The test:
  - starts two servers on loopback TCP (`WithInsecure`, **no TLS**, so the grpc-go-1859 expired-certificate problem does not apply);
  - opens a long-lived stream on connection 1, sends GO_AWAY via `s1.GracefulStop()`, and waits for the *server-side* `Accept` of connection 2;
  - stops `s1`, expects the stream to die, then issues ten `UnaryCall`s that must succeed;
  - runs `leakcheck.Check(t)` at the end.
- **Target in GoReal:** GoReal names the same target (`testfunc: TestGoAwayThenClose`, `workdir: ./test`, `go test ./test -c`).
- **Why failure depends on timing (source reasoning, not measured):** the test waits on the server's `Accept` of connection 2, not on the client having installed the new transport in `ac.transport`. Whether the old connection's closure runs before or after that installation decides the outcome:
  - **before:** the nil write is harmless and the test passes;
  - **after:** the healthy transport is lost and the calls spin until the 20 s context expires.

  No mixed count is published. Q0 must measure it, and a 20/20 failure result would make this a stable control, not a primary episode.
- **Forced/controlled/natural status, observed:** a controlled sequence, not forced. The test orders protocol events (GO_AWAY, then closure) through public server APIs. It does not mock the transport, control the scheduler, instrument locks or insert sleeps.
- **Pre-declared evaluator signatures,** frozen before any qualification attempt:
  - **(a) `FOCAL_DEFECT_WITNESS`, spin form:** the test fails with a `UnaryCall(_) = _, … ; want _, nil` line whose error carries `code = DeadlineExceeded`. A call issued after the old connection's closure did not complete within the test's 20 s context.
  - **Anything else is not focal:** a `FullDuplexCall` failure, "expected the stream to die, but got a successful Recv", a listen or server start-up failure, a `leakcheck` report *without* an (a) line, or a `UnaryCall` error with any other code. These are `UNRESOLVED`/`HARNESS_INVALID` under the frozen categories.
  - Exploratory runs may show that the spin also surfaces as a test-timeout dump. Any refinement of (a) must be recorded before the first counted attempt, as etcd-5509's corrections were.
  - **`V_ok` rule:** any (a) on `V_ok` makes the pair `UNRESOLVED` until a documented explanation exists (Q0 protocol).
- **Same target/harness plausibility, observed:**
  - The test hunk's new import `google.golang.org/grpc/internal/grpcsync` exists at the parent (package history from 2018-07-30), as do `resolver/manual.GenerateAndRegisterManualResolver`, the `funcServer` type with `unaryCall`/`fullDuplexCall` fields, and the `leakcheck`, `resolver/manual` and `net` imports of `end2end_test.go`.
  - `listenWithNotifyingListener` and `notifyingListener` are defined inside the hunk itself.
  - So the identical test should compile at the parent. Task 5 confirms this by building.
- **Toolchain and dependencies, source claim:**
  - GoReal's recipe: `golang:1.13`, GOPATH layout at `/go/src/google.golang.org/grpc`, and unpinned `go get -d` of eight packages. That is the pattern that failed for grpc-go-1859 (current heads need a newer Go).
  - **The parent has a `go.mod`** (grpc-go adopted modules before 2018-10), with no `vendor/vendor.json` or `Gopkg.toml`.
  - **Recommended for Task 5:** build both images in module mode (`GO111MODULE=on`) from each revision's own `go.mod`, which pins the dependency versions. This is a disclosed deviation from GoReal's GOPATH recipe, adopted for reproducibility (ledger A13/A19). If module resolution fails, fall back to 1859's pinned dated clones and disclose.
- **Timing:**
  - A failing `V_bad` attempt is expected to take about 20 s (the test context) plus `leakcheck` grace.
  - The provisional `-test.timeout` is 60 s with a 75 s runner timeout, under the 120 s ceiling.
  - An uncounted timing run fixes both before the first counted attempt.
- **Qualification blockers:** the blob checks; a successful build of the identical test at the parent; the timing run; the frozen `-test.run '^TestGoAwayThenClose$'`, timeout, working directory and reset (fresh `docker run --rm` per attempt); Q0's mixed `V_bad` outcomes (≥2 focal, ≥2 pass in 20); and a clean `V_ok` batch.

## New candidate card C-05 — istio 17860

- **Source tier:** 4, GoReal fallback (`istio_17860`, order 26).
- **Classification:** `PRIMARY_METADATA_READY`. **Not Q0-qualified; intermittency unmeasured.**
- **Counterpart type:** historical pair with an isolatable focal change and an identical test backport. The upstream test must be used unchanged, **not GoReal's edited version** (see below).
- **Authoritative identity, observed:**
  - PR #17860, "Fix deadlock in envoy restart logic.", by `nmittler`. It was squash-merged 2019-10-15T02:11:20Z as `c6e9130227497ab064dd571a1409236d17aa2ef3`, with sole parent `7a9a996f6641024298e6010c6f1d7e87a83a48dc`.
  - The PR body is the unfilled template, and no issue is linked. The obligation is therefore derived from the diff and the added test, which is a provenance limitation.
- **Candidate `V_bad`:** `7a9a996f…` plus the identical backport of the fix's test addition. **Candidate `V_ok`:** `c6e91302…`.
- **Blob-level counterpart check, observed:**
  - `pkg/envoy/agent.go` is blob `f6644419ad8c…` at the parent and `638578e33415…` at the fix.
  - GoReal's `bug_patch.diff` reverts `agent.go` with `index 638578e33..f6644419a`, which yields the parent's file byte for byte.
  - `pkg/envoy/agent_test.go` is blob `09ea287d1f94…` at the fix.
  - **GoReal's patch also edits the test on `V_bad` only.** Its test hunk replaces `t.Fatalf("timed out waiting for epoch 1 to start")` with `debug.SetTraceback("all"); panic(...)`, which is instrumentation for its own detector. Using it would give the two versions different tests, against Q0's "same target/harness across counterparts". **Task 5 applies only the `agent.go` hunks.**
  - **Task 5 check:** `git hash-object pkg/envoy/agent.go` must be `f6644419ad8c…` in `V_bad` and `638578e33415…` in `V_ok`, and `pkg/envoy/agent_test.go` must be `09ea287d1f94…` in **both**.
- **Focal behavioural obligation:** while a hot restart waits for the previous Envoy epoch to go live, the agent must still process that epoch's exit. A second `Restart` must not stall the exit handler for the full 20 s live-wait. When epoch 0 exits during the wait, epoch 1 must start within the test's 5 s bound.
- **Defect mechanism at `V_bad`, observed in source:**
  - `Restart` takes `a.mu` for its whole body, including `waitUntilLive()`, which polls `IsLive()` for up to 20 s.
  - `Run`'s exit-status handler needs `a.mu` to delete the exited epoch.
  - If the second `Restart` holds `a.mu` when epoch 0's exit status arrives, the exit cannot be processed until the 20 s wait times out.
- **Witness, observed:** the upstream `pkg/envoy::TestExitDuringWaitForLive`, added by the fix. It uses a fake proxy that never goes live:
  - `Restart("config1")`, then `go Restart("config2")`, then it immediately makes epoch 0 exit;
  - it fails with `t.Fatalf("timed out waiting for epoch 1 to start")` if epoch 1 has not started within 5 s;
  - it then asserts with Gomega `BeTemporally("~", …, 1s)` that epoch 1 started promptly.
- **Target in GoReal:** GoReal names the same target (`testfunc: TestExitDuringWaitForLive`, `workdir: ./pkg/envoy`, `go test ./pkg/envoy -c`).
- **Why failure depends on timing (source reasoning, not measured):** the outcome depends on whether the `go a.Restart("config2")` goroutine acquires `a.mu` before `Run` receives epoch 0's exit status through the chain start → `runWait` → `statusCh`:
  - **exit handler first:** it deletes epoch 0, the second `Restart` finds no active epoch, and the test passes;
  - **`Restart` first:** it holds `a.mu` for 20 s and the test fails at 5 s.

  The `Restart` path has fewer goroutine hand-offs, so the failure rate may be high. It may even be near-deterministic, which Q0 would show as fewer than 2 passes in 20.
- **Forced/controlled/natural status, observed:** a controlled unit test with a fake proxy (`TestProxy` with scripted `run`/`live`), which is the project's own upstream harness. It does not mock the agent's locking, control the scheduler or insert sleeps in the product path. The interleaving is natural.
- **Pre-declared evaluator signatures,** frozen before any qualification attempt:
  - **(a) `FOCAL_DEFECT_WITNESS`, stalled-exit form:** `--- FAIL: TestExitDuringWaitForLive` together with `timed out waiting for epoch 1 to start`.
  - **Non-focal:** a Gomega `BeTemporally` failure, where epoch 1 started but outside the 1 s threshold, is `UNRESOLVED` on either version. The test author flags this assertion's own flake risk ("Should (hopefully) be enough to avoid flakes").
  - **Also non-focal:** build or module failure, a missing `=== RUN` line, or any other failure is `UNRESOLVED`/`HARNESS_INVALID` under the frozen categories.
  - **`V_ok` rule:** any (a) on `V_ok` makes the pair `UNRESOLVED` until a documented explanation exists. `BeTemporally` failures on `V_ok` are reported separately and are not focal.
- **Same target/harness plausibility, observed:**
  - At the parent, `agent.go` has the same `NewAgent(proxy Proxy, terminationDrainDuration time.Duration)`, `Agent.Restart`/`Run` and `Proxy.IsLive()` API that the test uses.
  - `TestProxy` and the Gomega imports are defined in the (fix-version) test file itself.
  - The test's only new import is `errors`, so the identical test should compile at the parent. Task 5 confirms this by building.
- **Toolchain and dependencies, source claim:**
  - GoReal: `golang:1.13`, module mode, and one `go.mod` edit applied to both images: `replace bitbucket.org/ww/goautoneg => github.com/munnerz/goautoneg …`, because the Bitbucket host no longer serves it.
  - The parent's `go.mod` declares `go 1.12` and has a `go.sum`, so dependency versions are pinned by the project.
  - The `replace` line is a disclosed, identical-on-both-versions environment deviation. Task 5 records whether it is still needed.
- **Timing:**
  - A failing `V_bad` attempt is expected to end about 5 s after start. A passing one ends in about 1 s plus Gomega bookkeeping.
  - The provisional `-test.timeout` is 30 s with a 45 s runner timeout, fixed by an uncounted timing run.
- **Qualification blockers:** the blob checks with the upstream test unchanged; a successful build at the parent; the timing run; the frozen `-test.run '^TestExitDuringWaitForLive$'`, timeout, working directory and reset; Q0's mixed `V_bad` outcomes; and a clean `V_ok` batch.

## Reconciled roster after C3

C2's roster table is not edited. Rows 1–9 stand as updated by ledger A4-addendum-3 (grpc-go-1859 → `Q0_NOT_QUALIFIED`).

| # | Entry | Tier | Pair (`V_bad` → `V_ok`) | Counterpart type | Label |
|---:|---|---:|---|---|---|
| 10 | **grpc-go-2391** | 4 | `39444b9…` (+ identical test backport) → `ff2aa05…` | historical pair with identical test backport | **`PRIMARY_METADATA_READY`** |
| 11 | **istio-17860** | 4 | `7a9a996…` (+ identical test backport) → `c6e9130…` | historical pair with identical test backport | **`PRIMARY_METADATA_READY`** |

- **Roster use:** **11 of 12 primary entries used; 1 remains. 0 of 2 nuisance/control slots are used.** E1's AMENDMENTS §7–§8 ran grpc1859 as an E1 control, not as a roster control entry.
- **Per-project caps:** etcd 2/2, **grpc-go 2/2**, **istio 1/2**, commons-pool 2/2, commons-dbcp 2/2, log4j 2/2.
- **New uncarded stable-control leads,** by source reasoning: grpc_3017, hugo_3251, hugo_5379. They consume no slot.

## Resource accounting

- **Screening wall clock, EXACT:** 363.648 s of agent/tool elapsed time. Card checks ran until 08:13:35.878Z.
- **Human metadata effort:** **UNKNOWN.** The researcher's own time is not recorded, per the ledger's accounting rule.
- **Restoration/qualification human effort and allocated vCPU-hours:** **EXACT, zero.**
- **Network:** GitHub REST API and raw.githubusercontent.com reads only. One failed `git clone` of GoBench wrote nothing. Nothing was written outside this repository's `research_runs/` directory and the session scratch workspace.

## Decision recorded by this pass

**grpc-go-2391 (C-04) and istio-17860 (C-05) are the next two defensible non-etcd `PRIMARY_METADATA_READY` candidates in deterministic order, and acquisition stops here as instructed.**

- **Not an authorisation:** each needs a separately authorised Task 5 (≤2 human restoration hours and ≤4 allocated vCPU-hours per candidate, within the 20 / 40 vCPU-hour ceilings).
- **What the gate still needs:** it stays **not met**. Meeting it requires **both** Task 5 passes to qualify before `2026-09-27T23:02:26Z`, which would give 4 episodes across 3 projects (etcd, grpc-go, istio).
- **If either fails:** order resumes at istio_18454 for istio's second slot, or at kubernetes_1321, with one primary roster entry left.

## Sources

1. grpc-go PR #2391 — https://github.com/grpc/grpc-go/pull/2391 ; commit `ff2aa05958775030998dbe2f9bccbe2af324adf4` and parent `39444b99c097c9f53536ad8f16cd9f0288c7f695`.
2. grpc-go PR #3017 — https://github.com/grpc/grpc-go/pull/3017 ; commit `ac35b67779b9802189d5c0bcfc25d84ce7ba36a1`.
3. hugo PR #3251 — https://github.com/gohugoio/hugo/pull/3251 ; commit `79b34c2f1e0ba91ff5f4f879dc42eddfd82cc563`.
4. hugo PR #5379 — https://github.com/gohugoio/hugo/pull/5379 ; commit `729593c842794eaf7127050953a5c2256d332051`, parent `e65268f2c2dd5ac54681d3266564901d99ed3ea3`.
5. istio PR #16224 — https://github.com/istio/istio/pull/16224 .
6. istio PR #17860 — https://github.com/istio/istio/pull/17860 ; commit `c6e9130227497ab064dd571a1409236d17aa2ef3` and parent `7a9a996f6641024298e6010c6f1d7e87a83a48dc`.
7. istio PR #18454 — https://github.com/istio/istio/pull/18454 (title, body and file list only).
8. GoBench at `2e91eb10b8e7b2873ea44f12b87ec1b2520e1b69` — https://github.com/timmyyuan/gobench — `gobench/configures/goreal/blocking.json`; `gobench/goreal/blocking/{grpc,hugo,istio}/<id>/`.
