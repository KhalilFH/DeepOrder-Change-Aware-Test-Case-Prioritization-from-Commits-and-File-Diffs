# Task 5 restoration — etcd-5509

- Artifact identifier: `ci_policy_sensitivity_task5_etcd5509_2026-09-19_v1`
- Scope: Task 5 restoration and Q0 qualification of candidate card C-01 (etcd-5509), per the reserved cap in `resource_ledger.md` A6 and the qualification blockers listed in `task_c_candidate_acquisition.md`.
- `task5_start_utc = 2026-09-19T09:59:44.271208900Z` (recorded in `resource_ledger.md` A6 at start, not backdated).
- Executed by an agent session under human direction; agent/tool wall-clock is recorded throughout and is not treated as a human-hour measurement (see `resource_ledger.md`, "Accounting rule"). The researcher directing this session elected to supply human-hour figures after the fact rather than block Task 5 start; those figures are recorded in `resource_ledger.md` A6 when supplied.

## Step 1 — blob-equivalence check (qualification blocker, resolved)

Performed via the GitHub contents API (no local clone needed for this check):

- `clientv3/remote_client.go` at `V_bad` (`36fcc9e9d4ce993998a9170b2293c30b4e5a601a`): blob `b8209b8a5e2ebefcac268b64e0a62482266b9a3d`.
- `clientv3/remote_client.go` at `V_ok` merge (`9ed3b446cadd9f43734d9eed9dcb03f3b12567a5`): blob `b511163058cb31ebab14f42869e6e99d1b9dff68`.
- GoReal's `bug_patch.diff` header: `index b51116305..b8209b8a5`.

**Result: PASS.** The patch's declared source/target blobs match the true `V_ok`/`V_bad` blobs exactly. Per the pre-declared rule in `resource_ledger.md` card C-01, this confirms etcd-5509 is a **historical pair with a documented identical test backport**, not merely a controlled historical-fix reversal. `clientv3/integration/kv_test.go` is untouched by the patch and is therefore byte-identical between the two build variants; harness identity across counterparts is confirmed for the frozen target.

## Step 2 — image builds

Built from GoReal's exact recipe (`gobench` at pinned commit `2e91eb10b8e7b2873ea44f12b87ec1b2520e1b69`, files `gobench/goreal/blocking/etcd/5509/{bug.Dockerfile,fix.Dockerfile,bug_patch.diff}`), with two disclosed, non-behavioral build-environment deviations, both required only because the historical recipe targets an environment no longer reproducible byte-for-byte on this host/date:

1. **`bug_patch.diff` line-ending normalization.** The file was checked out on a Windows host with `core.autocrlf=true`, converting it to CRLF and breaking `git apply` inside the Linux `golang:1.10` container (`patch failed: clientv3/remote_client.go:80`). Fixed by stripping `\r` before `COPY`ing it into the build context. Content verified identical to the CRLF original modulo the CR bytes (`diff` after `tr -d '\r'` on both sides showed no difference). Does not touch the etcd source, the pinned commit, or the patch's semantic content.
2. **Dropped `apt-get install -y vim python3` in `fix.Dockerfile`.** Debian stretch's apt archives are no longer served as of 2026-09-19 (404 on `deb.debian.org` and `security.debian.org`). Neither package is referenced by any later build or test-execution step in the Dockerfile. Disclosed inline in the Dockerfile at `.../task5_etcd5509/gobench/gobench/goreal/blocking/etcd/5509/fix.Dockerfile`.

No other deviation from the GoReal recipe was made. Both images built successfully (`golang:1.10`, `git reset --hard 9ed3b446…`, then either the reverse patch (`bug`) or none (`fix`), then the recipe's `sed`-trimmed `test` script compiling `/go/gobench.test` for `clientv3/integration`). Build logs: `build_bug2.log` (exit 0), `build_fix2.log` (exit 0), both in the scratch workspace (not committed; ephemeral build artifacts, not durable research evidence).

## Step 3 — pre-declared signature (a), correction (disclosed, before any counted attempt)

One exploratory attempt against the buggy image (`docker run --rm -w /go/src/github.com/coreos/etcd/clientv3/integration etcd5509-bug /go/gobench.test -test.v -test.count 1 -test.run TestKVGetErrConnClosed -test.timeout 45s`), **not counted toward the frozen 20 V_bad attempts**, timed out and produced a goroutine dump. The dump did not literally match the originally pre-declared signature (a) text ("the test goroutine blocked in `sync.(*RWMutex).Lock` called from `(*Client).Close` (second lock, client.go:118 at V_bad)").

**Actually observed:**
- The `TestKVGetErrConnClosed` goroutine (running via `testing.tRunner`) was blocked in a **channel receive**, `<-connc`, inside `(*Client).Close`, at `client.go:117` in this build.
- A **separate** goroutine was blocked in `sync.(*RWMutex).Lock`, with its stack passing through `(*Client).connMonitor`'s deferred cleanup closure (`client.go:344`), not through `Close` directly.

**Source trace (V_bad `clientv3/client.go`, fetched from `https://raw.githubusercontent.com/etcd-io/etcd/36fcc9e9d4ce993998a9170b2293c30b4e5a601a/clientv3/client.go`):** `Close()` takes `c.mu.Lock()` once, clears `c.cancel`, unlocks, runs `connStartRetry`/`Watcher.Close`/`Lease.Close`, then blocks on `<-connc` (`connc := c.newconnc`, captured before unlock) — there is only one explicit `c.mu.Lock()` call written inside `Close()` itself, not two. `connMonitor`'s deferred closure (started once from `newClient`, not from `Close`) does `c.mu.Lock()`, sets `lastConnErr`, and `close(c.newconnc)` — this is the write-lock acquisition that actually hangs, and it hangs for the same reason the card identified: `remoteClient.acquire`'s leaked `r.client.mu.RLock()` on its closed-client failure path (same `c.mu`) never released. `Close()`'s own blocking on `<-connc` is a downstream consequence, not a second direct `Lock()` call.

**Conclusion:** this is the same root-cause defect the card identified (the leaked read lock from `acquire`'s failure path), reached via a two-goroutine chain the original source-reading inference did not resolve precisely, rather than a different defect. The original signature text is withdrawn as imprecise, not as wrong about the root cause.

**Corrected signature (a) — FOCAL_DEFECT_WITNESS, deadlock/hang, effective for all counted attempts in this Task 5 pass:**

The attempt does not complete within the frozen attempt timeout, **and** the Go test-timeout goroutine dump shows, in the same dump:

1. a goroutine running `TestKVGetErrConnClosed` (reachable via `testing.tRunner`) blocked in a channel receive inside `(*Client).Close`, at the call site immediately after `Watcher.Close()`/`Lease.Close()` (source line 117 at this `V_bad` build; the line number is not itself diagnostic across builds — the call-site identity is), **and**
2. a distinct goroutine blocked in `sync.(*RWMutex).Lock` whose stack passes through `(*Client).connMonitor`'s deferred cleanup closure (source line ~344 at this `V_bad` build), attempting `c.mu.Lock()`.

Both frames must appear in the same dump. A timeout showing only (1) or only (2), or a timeout whose stack matches neither, is `UNRESOLVED`, not a focal witness. Signature (b) (closed-client panic) is unchanged by this correction.

This correction was recorded before any of the 20 frozen-count qualification attempts were run, and the exploratory attempt that prompted it is excluded from the qualification count and from the intermittency tally.

## Step 3b — second disclosed correction to signature (a), made after the first 10 counted V_bad attempts

**This correction was made after seeing counted-attempt data, which the frozen-protocol discipline exists to prevent; it is disclosed in full rather than silently applied, and the pre-correction classifications are preserved below for transparency.**

The Step 3 correction above was itself based on an incomplete re-reading of `clientv3/client.go` at `V_bad`: it stated "there is only one explicit `c.mu.Lock()` call written inside `Close()` itself." This is wrong. `Close()` contains **two** explicit `c.mu.Lock()` calls: one at the top (paired with `defer c.mu.Unlock()` and a mid-function manual `c.mu.Unlock()`), and a second one after `<-connc` returns:

```go
func (c *Client) Close() error {
	c.mu.Lock()
	defer c.mu.Unlock()
	...
	c.mu.Unlock()
	c.connStartRetry(nil)
	c.Watcher.Close()
	c.Lease.Close()
	<-connc
	c.mu.Lock()          // <- the second Lock, missed in Step 3
	...
}
```

Across the first 10 counted `V_bad` attempts, the 6 timeouts showed **three** distinct concrete goroutine-dump shapes, found by full-file inspection (not by the narrow `grep -A2` window used in the Step 3 classifier, which also under-matched):

1. **Attempt 2**: the `TestKVGetErrConnClosed` goroutine itself blocked directly in `sync.(*RWMutex).Lock`, with `clientv3.(*Client).Close` (client.go:118) immediately in the same stack — i.e. `Close`'s own second `Lock()` call hanging directly. This is **the original, pre-Step-3 signature text**, which Step 3 wrongly withdrew.
2. **Attempts 4, 7, 10**: `TestKVGetErrConnClosed` blocked in a channel receive inside `Close` (client.go:117), with a separate goroutine blocked in `sync.(*RWMutex).Lock` via `connMonitor`'s deferred cleanup closure. This is the Step 3 shape.
3. **Attempts 5, 6**: `TestKVGetErrConnClosed` blocked in the same channel receive inside `Close`, with a separate goroutine blocked in `sync.(*RWMutex).Lock` via `connMonitor` → `retryConnection` (client.go:286) — a third call site on the same mutex that Step 3's classifier window was too narrow to catch.

All three shapes were independently source-traced (not fitted to make counts favorable) to the identical root cause: the leaked `r.client.mu.RLock()` from `remoteClient.acquire`'s closed-client failure path can block *any* subsequent `c.mu.Lock()` acquisition on the same mutex, by whichever goroutine reaches it first — `Close`'s own second lock, or `connMonitor` via either of its two lock sites. Which one actually hangs is determined by the scheduling of the concurrent `Get` call relative to `Close`/`connMonitor`'s progress, which is exactly the kind of genuine non-forcing scheduling nondeterminism the candidate card already flagged as mechanistically plausible.

**Final signature (a), effective from this point forward:** `FOCAL_DEFECT_WITNESS` (deadlock/hang) if the attempt times out and the dump shows, for the goroutine running `TestKVGetErrConnClosed`, **either**:

- (i) that goroutine itself blocked in `sync.(*RWMutex).Lock` with `clientv3.(*Client).Close` in the same stack (`Close`'s own second `Lock`), **or**
- (ii) that goroutine blocked in a channel receive inside `Close`, **and** a separate goroutine in the same dump blocked in `sync.(*RWMutex).Lock` via any `connMonitor` call site (its deferred closure or `retryConnection`).

A timeout matching neither is `UNRESOLVED`. Signature (b) is unaffected.

**Reclassification of the first 10 `V_bad` attempts:** attempts 2, 5, 6 are reclassified from `UNRESOLVED_TIMEOUT_NO_SIGNATURE` to `FOCAL_DEFECT_WITNESS_A`. Original (pre-correction) labels are preserved in `results_batch1_original.csv`; corrected labels are in `results_batch1.csv`; both are in the scratch workspace, not committed (ephemeral, not durable research evidence — this markdown artifact is the durable record).

**First-10 `V_bad` outcome under the final signature: 4 PASS, 6 FOCAL_DEFECT_WITNESS_A, 0 UNRESOLVED.** First-10 `V_ok` outcome: 10 PASS, 0 focal witnesses. This alone already satisfies the Q0 intermittency criterion (≥2 focal failures and ≥2 passes on `V_bad` in the frozen protocol) on the first batch; the second 10-per-version batch is still run in full, per the plan's "run ten more per version regardless of early outcomes" rule (no early stopping).

## Step 4 — Q0 qualification attempts

Protocol: ten fresh single attempts per version (`V_bad` = `etcd5509-bug`, `V_ok` = `etcd5509-fix`); if structural checks pass, ten more per version regardless of early outcomes. Each attempt is a fresh `docker run --rm` (`-test.count 1`), one job at a time, `-test.run TestKVGetErrConnClosed`, `-test.timeout 45s` (below the 120 s ceiling). Working directory pinned to `/go/src/github.com/coreos/etcd/clientv3/integration` for both images. Per-attempt start/end UTC timestamps, elapsed seconds, exit code and classification are recorded in `results.csv` (scratch workspace) and summarized below.

### Results

| Version | Image | Attempts | PASS | `FOCAL_DEFECT_WITNESS_A` | `UNRESOLVED` | `OTHER`/`HARNESS_INVALID` |
|---|---|---:|---:|---:|---:|---:|
| `V_bad` | `etcd5509-bug` | 20 | 4 | 16 | 0 | 0 |
| `V_ok` | `etcd5509-fix` | 20 | 20 | 0 | 0 | 0 |

Per-attempt UTC start/end timestamps, elapsed seconds, exit codes and classifications: `results_final.csv` (scratch workspace; merges the corrected `results_batch1.csv` — see Step 3b — with `results_batch2.csv`). `V_bad` attempt-level execution time: `730.742 s`. `V_ok` attempt-level execution time: `13.363 s`. No `HARNESS_INVALID`, no build failure, no unrelated `OTHER_DEFECT` occurred in any of the 40 counted attempts.

No early stopping was applied: all 20 attempts per version were run regardless of the first-10 outcome, per the frozen protocol.

### Q0 qualification verdict

- **Intermittency criterion** (≥2 focal failures and ≥2 passes on `V_bad` across the 20 frozen-protocol attempts): **MET** — 16 focal failures, 4 passes.
- **Acceptable-counterpart witness validity** (`V_ok` behaves acceptably under the same frozen protocol): **MET** — 20/20 `PASS`, 0 focal witnesses on the fix.
- **Forced/controlled/natural status**: unchanged from the card — controlled workload, non-forcing scheduling; confirmed empirically by the mixed `PASS`/`FOCAL_DEFECT_WITNESS_A` outcome on an otherwise-identical fresh-process protocol.
- **Identical target/harness across counterparts**: confirmed by the Step 1 blob-equivalence check (only `remote_client.go` differs between images; `kv_test.go` is byte-identical).

**etcd-5509 (candidate card C-01) is Q0-qualified.** This is the first Q0-qualified episode of the current roster. `candidate_cards.md`/`task_c_candidate_acquisition.md`/`resource_ledger.md` labels are updated from `PRIMARY_METADATA_READY` to `Q0_QUALIFIED` below.

### Resource accounting for this Task 5 pass

- `task5_start_utc = 2026-09-19T09:59:44.271208900Z`; last counted attempt ended `2026-09-19T10:30:02.021891100Z`.
- Total agent/tool wall-clock for Task 5 (image builds through the last counted attempt): **EXACT**, `1857.75 s` (`≈ 0.516` vCPU-hours at one sequential job, one vCPU-equivalent at a time, consistent with the frozen "one job at a time" rule). This is agent/tool elapsed time, not a human-hour measurement (see `resource_ledger.md`, "Accounting rule"); it is recorded because it is the durably-evidenced basis for the ≤4 allocated vCPU-hour per-candidate cap.
- Human restoration hours for this pass: **UNKNOWN**, to be supplied by the researcher directing this session (see the A6 note in `resource_ledger.md` recorded at Task 5 start).
- Cap status: **≤4 allocated vCPU-h cap — not reached** (`≈0.52 h` used of `4 h`); **≤2 human-hour cap — provisional**, pending the researcher's figure.
- No build failed; no attempt was retried; no unattended retry of a crashed restoration occurred (the two Dockerfile fixes in Step 2 were made and disclosed before any counted attempt, not mid-run).
