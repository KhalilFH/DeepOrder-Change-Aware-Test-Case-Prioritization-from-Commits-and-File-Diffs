# Task 5 restoration — etcd-7492

- Artifact identifier: `ci_policy_sensitivity_task5_etcd7492_2026-09-19_v1`
- Scope: Task 5 restoration and Q0 qualification of candidate card C-02 (etcd-7492), per the counterpart-type declaration and mandatory restricted-diff check in `task_c_candidate_acquisition.md` ("New candidate card C-02 — etcd-7492") and the reserved-cap conventions established for etcd-5509 in `resource_ledger.md` A6.
- **Counterpart type, as pre-declared and confirmed empirically below: controlled historical-fix reversal on one pinned base (`148c923c72c4aa9207173c03b775e2c0b8754067`) — NOT a historical pair.** This is reported separately from etcd-5509 (a historical pair with a documented identical test backport) in every summary below, per the card's explicit instruction.
- `task5_start_utc = 2026-09-19T10:55:26.855778800Z` (recorded at start, not backdated; Docker confirmed running, Linux containers, 16 host CPUs, before any other action).
- Executed by an agent session under human direction; agent/tool wall-clock is recorded throughout and is not treated as a human-hour measurement (see `resource_ledger.md`, "Accounting rule"). Human-hour figures are left `UNKNOWN, to be supplied by the researcher`, per that same convention.

## Step 1 — restricted-diff Task 5 check (mandatory gate, performed before any image was built)

Per the card's requirement, the defective variant's `auth/simple_token.go` must equal the historical parent's file plus *exactly* the declared `const`→`var` move and nothing else.

1. Fetched the three needed sources via raw GitHub (HTTP 200 each):
   - Historical parent `auth/simple_token.go` at `3a61fe596ba1eda2ae0900dfbb1f735ab574ab16` → local blob hash `5b608af92c732e9a840bf43d2e65c1372d62b5a2` (**matches** the card's declared historical-parent blob exactly).
   - Pinned base / `V_ok` `auth/simple_token.go` at `148c923c72c4aa9207173c03b775e2c0b8754067` → local blob hash `ff48c5140cbe103af6297990fd406a641d529631` (**matches** the card's declared `V_ok` blob exactly).
   - GoReal's `bug_patch.diff` (pinned `gobench` commit `2e91eb10b8e7b2873ea44f12b87ec1b2520e1b69`) — header `index ff48c5140..5b608af92`, 0 CR bytes found (no CRLF fix was needed for this file, unlike etcd-5509's `bug_patch.diff`; disclosed as a point of contrast, not assumed).
2. Reconstructed the defective variant locally: applied `bug_patch.diff` to the fetched `V_ok` file with `git apply` in a scratch repo with `core.autocrlf=false`/`core.eol=lf` forced (to avoid the Windows CRLF-on-checkout artifact that would otherwise contaminate the diff — this precaution changes no patch content, only how the reconstruction script stores it on disk). Patch applied cleanly (`git apply` exit 0, all 7 hunks applied, offsets only).
3. Diffed the reconstruction against the true historical-parent file:
   ```
   @@ -32,6 +32,10 @@
    const (
        letters                  = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        defaultSimpleTokenLength = 16
   +)
   +
   +// var for testing purposes
   +var (
        simpleTokenTTL           = 5 * time.Minute
        simpleTokenTTLResolution = 1 * time.Second
    )
   ```
   This is the **entire** diff — no other hunk. It is exactly the declared minimal source deviation (the four-line `const`→`var` block move, unchanged values). **Restricted-diff check: PASS.**
4. **Re-verified against the actual built `bug` image**, not only the local reconstruction (the card allows either; both were done here for extra rigor): after building `etcd7492-bug` (Step 2), extracted `/go/src/github.com/coreos/etcd/auth/simple_token.go` from a running container and diffed it against the local reconstruction from step 2 above. **Byte-identical (`diff` empty).** This confirms the gate result is not an artifact of the local reconstruction process but matches what Docker actually built.
5. Noted for the record (matches the card's disclosed provenance problem): the patch header's own `index ff48c5140..5b608af92` line names the historical-parent blob `5b608af92` as its target, but the actual reconstructed/built file's blob (`7aa8079477132dec7447507a310394b49fa8ef33`) is **not** that blob — confirming empirically, not just by inference, that "the header index line names the parent blob although its content does not restore it" (card, "Provenance problems"). The restricted-diff check above is what actually establishes fidelity, not the header.

**Gate result: PASS. Proceeding to build.**

## Step 2 — image builds

Built from GoReal's recipe (`gobench` at pinned commit `2e91eb10b8e7b2873ea44f12b87ec1b2520e1b69`, files `gobench/goreal/blocking/etcd/7492/{bug.Dockerfile,fix.Dockerfile,bug_patch.diff}`), with **one** disclosed, non-behavioral build-environment deviation:

1. **Dropped `apt-get update && apt-get install -y vim python3` from `fix.Dockerfile`.** Neither package is referenced by any later step in that Dockerfile (only two `sed` edits of the `test` script and `PKG=./auth PASSES='build unit' ./test`). Same class of deviation disclosed for etcd-5509's `fix.Dockerfile` in `task5_etcd5509_restoration.md` Step 2. `bug.Dockerfile` needed **no** deviation (no CRLF issue this time, no apt-get step present).

Both images (`golang:1.13`) built successfully with `docker build --no-cache`:

| Image | Start UTC | End UTC | Exit |
|---|---|---|---:|
| `etcd7492-bug` | `2026-09-19T10:58:09.488827400Z` | `2026-09-19T11:00:45.842556200Z` | `0` |
| `etcd7492-fix` | `2026-09-19T11:00:53.002659100Z` | `2026-09-19T11:01:49.631670700Z` | `0` |

Build logs (`build_bug.log`, `build_fix.log`, ephemeral scratch workspace, not committed) show `Running unit tests...` followed by successful image export for both. `/go/gobench.test` confirmed present (~14.7 MB) in both images by direct `docker run ... ls -la`.

## Step 3 — pre-declared signature verification (no correction needed)

Unlike etcd-5509 (which required two disclosed post-hoc corrections to its evaluator signature), the etcd-7492 card's pre-declared signature matched the first observed timeout dump exactly, with no reinterpretation. This is recorded plainly as a genuine outcome, not assumed in advance.

Chosen attempt timeout: **50 s** (below the 120 s ceiling; the card's own reasoning applies directly — `TestHammerSimpleAuthenticate` runs 50 users × 10 waves with a 10 ms simple-token TTL and 1 ms inter-wave sleep, so a non-hanging run completes in well under a second; 50 s leaves a wide margin while keeping each timed-out attempt's cost bounded, matching the suggested 45–60 s range). Held fixed for every attempt below, counted and uncounted alike.

**Exploratory attempts (not counted toward the frozen 20 `V_bad` / 20 `V_ok`):** 6 attempts against `etcd7492-bug` (1 initial + 5 more) and 1 against `etcd7492-fix`, run to sanity-check the harness and the signature before committing to the frozen protocol. 5 of the 6 bug attempts passed in ~0.7 s; the fix attempt passed in ~0.7 s; **1 of the 6 bug attempts (exploratory attempt 4) timed out** at 50 s (exit code 2). Its goroutine dump shows, in the same dump:

1. `goroutine 568 [chan send]`, blocked in `(*simpleTokenTTLKeeper).addSimpleToken` (`auth/simple_token.go:73`), called from `(*tokenSimple).assignSimpleTokenToUser` (`auth/simple_token.go:143`) — a send to `addSimpleTokenCh` from `assignSimpleTokenToUser`, exactly as pre-declared.
2. `goroutine 22 [semacquire]`, blocked in `sync.(*RWMutex).Lock` (`rwmutex.go:98`), called from `newDeleterFunc.func1` (`auth/simple_token.go:161`), called from `(*simpleTokenTTLKeeper).run` (`auth/simple_token.go:100`) — the `simpleTokenTTLKeeper.run` goroutine blocked in `RWMutex.Lock` via `deleteTokenFunc` (the closure `newDeleterFunc` returns *is* `deleteTokenFunc`), exactly as pre-declared.

Both required frames co-occur in this dump, matching the card's pre-declared signature **without modification**. **No correction to the signature was made or needed.** The exploratory attempts are excluded from the qualification count and from the intermittency tally, consistent with the etcd-5509 precedent's treatment of its own exploratory attempt.

## Step 4 — Q0 qualification attempts

Protocol: ten fresh single attempts per version (`V_bad` = `etcd7492-bug`, `V_ok` = `etcd7492-fix`), then ten more per version regardless of early outcome (20 total per version, no early stopping). Each attempt: fresh `docker run --rm` (`-test.count 1`), one job at a time (strictly sequential — no attempt overlapped another in wall-clock time), `-w /go/src/github.com/coreos/etcd/auth`, `-test.run TestHammerSimpleAuthenticate -test.timeout 50s`. Per-attempt UTC start/end, elapsed seconds, exit code and log are in `results.csv` (scratch workspace) and summarized below.

### Results

| Version | Image | Attempts | PASS | `FOCAL_DEFECT_WITNESS` | `UNRESOLVED` | `OTHER`/`HARNESS_INVALID` |
|---|---|---:|---:|---:|---:|---:|
| `V_bad` | `etcd7492-bug` | 20 | 18 | 2 | 0 | 0 |
| `V_ok` | `etcd7492-fix` | 20 | 20 | 0 | 0 | 0 |

`V_bad` timeouts: attempt 2 (batch 1, elapsed `50.492 s`, exit `2`) and attempt 11 (batch 2, elapsed `50.021 s`, exit `2`). Both goroutine dumps independently checked and both show, in the same dump, a `chan send` block in `(*tokenSimple).assignSimpleTokenToUser` → `(*simpleTokenTTLKeeper).addSimpleToken`, and the `simpleTokenTTLKeeper.run` goroutine blocked in `sync.(*RWMutex).Lock` via `newDeleterFunc.func1` (`deleteTokenFunc`) — matching the pre-declared signature exactly, same as the exploratory attempt in Step 3. Both classified `FOCAL_DEFECT_WITNESS`.

All 18 non-timeout `V_bad` attempts and all 20 `V_ok` attempts show `--- PASS: TestHammerSimpleAuthenticate` and overall `PASS` in their logs (verified by direct grep of every one of the 40 counted logs, not inferred from exit code alone). `V_bad` total attempt-level execution time: `112.883 s`. `V_ok` total attempt-level execution time: `13.439 s`. No `HARNESS_INVALID`, no build failure, no unrelated `OTHER_DEFECT`, and no backend/bolt setup failure occurred in any of the 40 counted attempts.

No early stopping was applied: all 20 attempts per version were run regardless of the first-10 outcome (first 10 `V_bad`: 1 timeout/focal witness, 9 pass — already sufficient to satisfy the intermittency criterion's failure half after the first batch, but the frozen protocol's second batch of 10 was run in full regardless, per the plan's "run ten more per version regardless of early outcomes" rule).

### Q0 qualification verdict

- **Intermittency criterion** (≥2 focal failures and ≥2 passes on `V_bad` across the 20 frozen-protocol attempts): **MET, at the minimum margin** — 2 focal failures, 18 passes. This is reported plainly: the criterion is met exactly at its lower bound (2 of 2 required focal failures), not with headroom. The observed focal-witness rate on `V_bad` in this run is `2/20 = 10%`, substantially lower than etcd-5509's `16/20 = 80%`; both are legitimate but qualitatively different intermittency profiles, consistent with the two cards' different counterpart types and different underlying race windows.
- **Acceptable-counterpart witness validity** (`V_ok` behaves acceptably under the same frozen protocol): **MET** — 20/20 `PASS`, 0 focal witnesses on the fix.
- **Forced/controlled/natural status**: unchanged from the card — controlled concurrent workload (50 users, 10 waves), non-forcing scheduling (no mock, no scheduler instrumentation, no synthetic fault injection); confirmed empirically by the mixed `PASS`/`FOCAL_DEFECT_WITNESS` outcome on an otherwise-identical fresh-process protocol.
- **Identical target/harness across counterparts, subject to the declared deviation**: confirmed by the Step 1 restricted-diff check (both against the local reconstruction and against the actual built image) — the only difference between `V_bad`'s `auth/simple_token.go` and the true historical parent's is the declared, non-behavioral `const`→`var` move. `auth/store_test.go` (containing `TestHammerSimpleAuthenticate`) is supplied identically to both images by the merge commit checkout plus (for `bug`) a patch that does not touch that file; not independently re-verified byte-for-byte in this pass beyond the patch's own file scope (the patch's diff header lists only `auth/simple_token.go` and `auth/store_test.go` as touched by the *original fix*; GoReal's reverse patch touches only `auth/simple_token.go`, so `store_test.go` is supplied by the merge checkout unmodified on both images by construction of the two Dockerfiles, which both reset to the same merge SHA before any patch is applied or withheld).
- **Counterpart-type discipline**: this result is **not** reported as a historical-pair qualification. It qualifies a *controlled historical-fix reversal on one pinned base*, exactly as the card requires, with the single declared source deviation disclosed and empirically bounded in Step 1.

**etcd-7492 (candidate card C-02) is Q0-qualified**, as a controlled historical-fix reversal (not a historical pair). This is the second Q0-qualified episode of the current roster, after etcd-5509.

## Resource accounting for this Task 5 pass

- `task5_start_utc = 2026-09-19T10:55:26.855778800Z`; last counted attempt (`V_ok` attempt 20) ended `2026-09-19T11:06:57.445310100Z`.
- Total agent/tool wall-clock for Task 5 (restricted-diff check, both image builds, all exploratory attempts, and all 40 counted attempts): **EXACT**, `690.590 s` (`≈ 0.1918` vCPU-hours at one sequential job, one vCPU-equivalent at a time, consistent with the frozen "one job at a time" rule and with how `task5_etcd5509_restoration.md` computed its own figure). This is agent/tool elapsed time, not a human-hour measurement (see `resource_ledger.md`, "Accounting rule").
- Human restoration hours for this pass: **UNKNOWN**, to be supplied by the researcher directing this session.
- Cap status: **≤4 allocated vCPU-h per-candidate cap — not reached** (`≈0.192 h` used of `4 h`). **≤2 human-hour cap — provisional**, pending the researcher's figure, per the same convention recorded for etcd-5509.
- Cumulative Q0 restoration/qualification vCPU-hours across both Task 5 passes to date: etcd-5509 `≈0.516 h` + etcd-7492 `≈0.192 h` = **`≈0.708 h`**, against the 20 allocated vCPU-h Q0 ceiling and the 40 allocated vCPU-h first-active-ten-day ceiling. Neither ceiling is approached; no stop was triggered.
- No build failed; no attempt was retried; no unattended retry of a crashed restoration occurred (the one Dockerfile deviation in Step 2 was made and disclosed before any counted attempt, not mid-run); no evaluator-signature correction was needed (contrast with etcd-5509, disclosed above in Step 3, not silently omitted).
- Operational-day placement: the Q0 operational clock started `2026-09-17T23:02:26.133312834Z` (`resource_ledger.md` A1). This Task 5 pass (`task5_start_utc = 2026-09-19T10:55:26.86Z`) falls inside the window `2026-09-18T23:02:26Z`–`2026-09-19T23:02:26Z`, i.e. **operational day 2**. The day-7 gate (two qualified development episodes, due `2026-09-24T23:02:26Z`) is therefore **met on operational day 2**, five days early: this is now the second Q0-qualified episode (etcd-5509, then etcd-7492).
