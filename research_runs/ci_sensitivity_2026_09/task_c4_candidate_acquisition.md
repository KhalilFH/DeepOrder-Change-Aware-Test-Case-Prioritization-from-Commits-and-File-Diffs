# Task C resumption (C4) — last primary slot after C-05 did not qualify

## Scope and stop

- **Authority:**
  - `task5_istio17860_restoration.md`: C-05 is `Q0_NOT_QUALIFIED`, which leaves the day-10 gate one qualified episode short, with grpc-go-2391 now `Q0_QUALIFIED`.
  - The Q0 protocol.
  - The researcher's sprint instruction of 2026-09-25.
- **This pass is metadata acquisition only.** Nothing was built or executed, and no qualification attempt ran. vCPU-hours: **EXACT, zero.**
- **Timing:**
  - The pass began after C-05's Task 5 ended (`2026-09-25T08:37:04.156Z`). Its exact start was not recorded.
  - It ended at `2026-09-25T08:40:22.131Z`, so it lasted at most **198 s** of agent/tool elapsed time.
- **Stop rule, as in C2/C3:** stop at the next defensible non-etcd `PRIMARY_METADATA_READY` candidate in deterministic order. **Only one primary roster entry remains (11 of 12 used)**, so this card is the roster's last primary slot.
- **Order and sources:** unchanged from C3. GoReal orders 27 onward at GoBench `2e91eb10…`, with upstream PRs, commits and blobs read through the GitHub REST API.

## Per-ID screening record

| Order | Entry | Upstream fix (authoritative) | Files changed upstream | Disposition | Reason |
|---|---|---|---|---|---|
| 27 | istio_18454 | PR #18454 "fix flaky TestProcessor_Publishing test", merged 2019-10-30 as `318d2ba92c…`; fixes istio#18258 | `galley/pkg/runtime/publish/strategy.go` +4/−1 (product), `processor_test.go` +8/−63 | `SCREENED_DETERMINISTIC_LEAD` | See **Reason for istio_18454** below the table. |
| 28 | kubernetes_1321 | PR #1321 "pkg/watch: fix potential deadlock", merged 2014-09-16 as `b3a52df56b…` | `pkg/watch/mux.go` +20/−8 (product), `mux_test.go` +22/−0 | `SCREENED_DETERMINISTIC_LEAD` | See **Reason for kubernetes_1321** below the table. |
| 29 | kubernetes_11298 | PR #11298 "Fix deadlocks and race conditions in mesos master election notifier", merged 2015-07-15 as `7bdb8a07b2…` | `contrib/mesos/pkg/election/master.go` +22/−29, `master_test.go` +19/−11 | `SCREENED_NOT_ISOLATABLE` (new disposition, defined here) | See **Reason for kubernetes_11298** below the table. |
| 30 | kubernetes_16851 | PR #16851 "MESOS: Avoid MockPodsListWatch deadlock …", merged 2015-11-05 | `contrib/mesos/pkg/scheduler/plugin_test.go` +37/−24 only | `SCREENED_TEST_ONLY_FIX` | The fix changes only a test mock. |
| 31 | kubernetes_25331 | PR #25331 "etcd3/watcher: fix goroutine leak if ctx is canceled", merged 2016-05-09 as `8a81000b71…` | `pkg/storage/etcd3/watcher.go` +6/−3 (product), `watcher_test.go` +26/−0 | `SCREENED_DETERMINISTIC_LEAD` | See **Reason for kubernetes_25331** below the table. |
| 32 | **kubernetes_26980** | PR #26980 "processor listener: fix locking in pop()", merge `628af356b8c83f98ee3b50dfcf8b0250816a5581` (first parent `98f0d22bcccbacaa0f5a6846b55ecfc6590b18bc`) | `pkg/controller/framework/shared_informer.go` +20/−11 (product), `processor_listener_test.go` +48/−0 (new) | **Carded C-06, `PRIMARY_METADATA_READY`** | Next defensible candidate. **Stop point, and the last primary roster slot.** |
| 33–40 | kubernetes_30872, kubernetes_38669, kubernetes_70277, moby_29733, moby_30408, serving_2137, syncthing_4829, syncthing_5795 | — | — | `NOT_SCREENED` | After the stop point. For the record only: the PR titles and file lists of 30872, 38669 and 70277 were read, but no disposition was made. |

- **Reason for istio_18454.**
  - **The product bug:** in `startTimer`, a reset receives `<-s.timer.C` whenever `Stop()` returns false. If that timer already fired and its value was consumed, the receive blocks forever.
  - **Why the fix's test always hits it:** the fix's test now waits for the first publish, so the timer has fired and been drained, before the Add event that triggers the reset. On the parent's product code that hangs structurally.
  - **GoReal's version is confounded as well:** its `V_bad` also reverts the test de-flake, mixing test non-determinism into the counterpart.
- **Reason for kubernetes_1321.**
  - **Forced by a hook:** the added test drives the interleaving through `testHookMuxDistribute`, a hook the fix adds to the *product* code. It makes the watcher call `Stop()` while `distribute` holds the lock, so the deadlock follows every time on the buggy code.
  - **Not a pure historical parent:** `V_bad` would also need that hook added to the parent.
- **Reason for kubernetes_11298.**
  - **Two defects in one fix:** the fix repairs two defects together, a `sync.Cond` deadlock and a lost-change-event race. It replaces the whole mechanism with a channel.
  - **The test targets the second defect too:** it was changed to fail on "0 changes".
  - **Consequence:** `V_bad` would carry both defects, and a failure could not be attributed to one of them. Plan §4.1 requires a historical pair with an *isolatable* focal change.
  - **Status:** this is a judgment that the researcher may overrule.
- **Reason for kubernetes_25331.** The added test makes `resultChan` and `errChan` unbuffered "to ensure ordering". At the parent, `run()` cancels and then blocks sending the error on a `resultChan` that nobody reads, so `wg.Wait()` hangs on every run.

## New candidate card C-06 — kubernetes 26980

- **Source tier:** 4, GoReal fallback (`kubernetes_26980`, order 32).
- **Classification:** `PRIMARY_METADATA_READY`. **Not Q0-qualified; intermittency unmeasured.**
- **Counterpart type:** historical pair with an isolatable focal change and an identical test backport. The upstream test is used unchanged. **GoReal's edited test is not used.**
- **Authoritative identity, observed:**
  - PR #26980 by `hongchaodeng`, "processor listener: fix locking in pop()". It has two PR commits: `308201acb0e1515dab33b015c05ca31e40662aa0` (the fix) and `d4eb48c0bb85bf8ceb4edce744971e0cc9dcf69a` ("add TestPopReleaseLock").
  - It was merged 2016-06-13 as merge commit `628af356b8c83f98ee3b50dfcf8b0250816a5581`, with first parent `98f0d22bcccbacaa0f5a6846b55ecfc6590b18bc`.
  - `compare 98f0d22b…628af356` touches exactly the PR's two files.
  - The PR body: "the lock in processorListener is used to guard pendingNotifications. But in pop, it also locks around on select chan. This will block the goroutine with lock acquired."
- **Candidate `V_bad`:** `98f0d22b…` product code plus the fix's new test file. **Candidate `V_ok`:** `628af356…`.
- **Blob-level counterpart check, observed:**
  - `pkg/controller/framework/shared_informer.go` is blob `ce9ddf2c7140ff2d9d9752ac8626cef1bb01a236` at the first parent and `c557bf97548a4e7054b05e0b158ba194b7dd59f2` at the merge.
  - GoReal's `bug_patch.diff` reverses it with `index c557bf97548..ce9ddf2c714`, which yields the parent's file byte for byte.
  - `processor_listener_test.go` is absent at the parent and is blob `ffd72d8fae243a1e221a574781a87ed2107aaf1a` at the merge.
  - **GoReal's patch also edits the test on `V_bad` only.** It replaces `t.Errorf("Timeout after %v", …)` with `debug.SetTraceback("all"); panic(…)`. Task 5 applies **only the `shared_informer.go` hunks**.
  - **Task 5 check:** `git hash-object` of `shared_informer.go` must be `ce9ddf2c…` in `V_bad` and `c557bf97…` in `V_ok`. `processor_listener_test.go` must be `ffd72d8f…` in **both**.
- **Focal behavioural obligation:** `processorListener.pop` must not hold `p.lock` while blocked on sending to `nextCh`. Another goroutine must be able to acquire `p.lock` while `pop` waits for a receiver.
- **Defect mechanism at `V_bad`, observed in source:**
  - `pop` takes `p.lock` at entry (`defer` unlock) and keeps it while it selects on `stopCh` or on the send `p.nextCh <- notification`.
  - With a pending notification and no receiver on the unbuffered `nextCh`, `pop` blocks forever while holding the lock.
- **Witness, observed:** the upstream `TestPopReleaseLock`, added by the fix in a new file. It:
  - calls `pl.add(1)`, then `go pl.pop(stopCh)`, then `go func(){ pl.lock.Lock(); close(resultCh) }()`;
  - waits for `resultCh` for up to `wait.ForeverTestTimeout` (30 s at the parent), and calls `t.Errorf("Timeout after 30s")` otherwise.
- **Target in GoReal:** GoReal names the same target (`testfunc: TestPopReleaseLock`, `workdir: ./pkg/controller/framework`, `golang:1.12`).
- **Why failure depends on timing (source reasoning, not measured):** the outcome depends on which of the two freshly started goroutines acquires `p.lock` first.
  - **`pop` first:** it takes the lock, finds the pending notification and blocks on the send while holding it, so the test fails at 30 s.
  - **The locker first:** it takes the lock and closes `resultCh`, so the test passes.

  Go's scheduler (`runnext` hand-off and work stealing across 16 Ps) makes either order possible, but the split is unknown and may be heavily skewed. C-05 is the cautionary precedent: a similar two-path race proved 20/0.
- **Forced/controlled/natural status, observed:** a controlled unit test (it sets up the listener directly), but not forced. There is no scheduler control, sleep, hook or lock instrumentation, and the interleaving is natural.
- **Pre-declared evaluator signatures,** frozen before any qualification attempt:
  - **(a) `FOCAL_DEFECT_WITNESS`, lock-held-while-blocked form:** `--- FAIL: TestPopReleaseLock` together with `Timeout after 30s`.
  - **Non-focal:** a Go test-timeout dump, a panic, build failure, a missing `=== RUN` line, or any other failure is `UNRESOLVED`/`HARNESS_INVALID` under the frozen categories.
  - **`V_ok` rule:** any (a) on `V_ok` makes the pair `UNRESOLVED` until a documented explanation exists.
- **Same target/harness plausibility, observed:** at the first parent, `shared_informer.go` has `newProcessListener`, `processorListener.add`/`pop`, `lock`, `cond`, `pendingNotifications` and `nextCh`. `pkg/util/wait.ForeverTestTimeout` (30 s) exists. So the new test should compile against the parent's product code. Task 5 confirms this by building.
- **Toolchain and dependencies, source claim:**
  - GoReal uses `golang:1.12`, GOPATH `/go/src/k8s.io/kubernetes`, a full clone plus reset, `apt install rsync` (unused by `go test`), and `go test ./pkg/controller/framework -c`.
  - The first parent vendors its dependencies (`vendor/`, with `Godeps/Godeps.json` present), so they are pinned in-tree.
  - **Recommended recipe:** a shallow fetch of the merge commit into the GOPATH location, GOPATH mode, and the same toolchain on both images. That is a disclosed deviation from GoReal's full clone and `rsync`.
- **Timing:**
  - A failing `V_bad` attempt ends about 30 s in; passes are sub-second.
  - The provisional `-test.timeout` is 60 s with a 90 s outer timeout, fixed by an uncounted timing run.
  - The worst-case counted cost is about 20 × 31 s for `V_bad`.
- **Qualification blockers:** the blob checks with the test unchanged; a successful build at the parent's product code; the timing run; the frozen `-test.run '^TestPopReleaseLock$'`; Q0's mixed `V_bad` outcomes; and a clean `V_ok` batch.

## Roster after C4

- **C-06 kubernetes-26980:** `PRIMARY_METADATA_READY`; historical pair with an identical test backport.
- **Primary roster: 12 of 12 used.** No further primary candidate can be carded this month. The two nuisance/control slots are still unused.
- **Per-project caps:** etcd 2/2, grpc-go 2/2, istio 1/2, kubernetes 1/2, commons-pool 2/2, commons-dbcp 2/2, log4j 2/2.
- **New uncarded stable-control leads,** by source reasoning: istio_18454, kubernetes_1321 (forced by a hook), kubernetes_25331.

## Decision recorded by this pass

**kubernetes-26980 (C-06) is the next defensible non-etcd candidate in deterministic order, and the last primary slot. Acquisition stops here.**

- **Task 5 needs separate authorisation.** Nothing here authorises it.
- **If C-06 qualifies before `2026-09-27T23:02:26Z`:** the day-10 gate's episode condition is met, with 4 episodes (etcd-5509, etcd-7492, grpc-go-2391, kubernetes-26980) across 3 projects.
- **If it does not qualify:** the roster is exhausted and the gate fails by the plan's rule (G1b: "No E2. Finish small feasibility report and trigger F1 where possible").
