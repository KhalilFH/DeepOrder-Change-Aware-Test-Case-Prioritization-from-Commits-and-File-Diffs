# Conditional Task C candidate acquisition

## Revision record

- Original artifact written 2026-09-17 (file written `2026-09-17T23:33:58Z`).
- **Documentation repair applied 2026-09-19** following the Task C audit of 2026-09-18. The repair corrects provenance, labeling, counterpart-type, episode-accounting and decision-language defects identified by that audit (audit findings F1–F13). It adds no new candidate, restores nothing, runs nothing, and does not change `protocol.md`, `protocol_amendment_2026-09-17.md`, or the frozen `candidate_cards.md`. Where the original pass did not preserve a fact, this repair says so rather than reconstructing it.

## Scope and stop

This artifact records only the approved metadata-acquisition step. No candidate repository was restored, built, or executed; no qualification attempt or harness was run or implemented.

Acquisition started at `2026-09-17T23:10:59.517500913Z` and stopped at `2026-09-17T23:31:29.047893173Z`. Exact acquisition wall-clock interval: `1229.530393` seconds. This is agent/tool elapsed time, not a measured human-attention charge.

**Stop rule, corrected.** The original text described the stop as a "prospective `PRIMARY_METADATA_READY` gate". No such gate was pre-declared in `protocol.md`, the timing amendment, `resource_ledger.md`, or the DBCP-65 pass. The stop is therefore recorded as a **Task C decision**: acquisition was paused once two candidates reached `PRIMARY_METADATA_READY`, so that Task 5 (qualify the first candidate) could begin, consistent with the plan's Section 13 sequence (Task 4 "select the first two source-eligible cases", Task 5 "qualify the first candidate"). It is not a pre-registered gate and confers no authorization by itself. Consequences of pausing with two same-project candidates:

1. The plan's two-primary-episodes-per-project cap is saturated for etcd; no further etcd entry may be enrolled as primary.
2. E1's preference for two development episodes from different projects cannot be met from the present roster.
3. Gate G1b (four qualified episodes across at least two projects by operational day 10) requires acquisition to resume for a non-etcd project regardless of the etcd-5509 Task 5 outcome.

## Label vocabulary used in this artifact

The approved plan speaks of *qualified episodes*, *stable controls*, *nuisance/control candidates* and *excluded candidates*. Task 4 used `STABLE_ORACLE_CONTROL`, `UNRESOLVED`, `EXCLUDE` and the anticipated `PRIMARY_INTERMITTENT_CANDIDATE`. This artifact uses the following labels; none of them is a Q0 qualification outcome.

| Task C label | Meaning | Task 4 / plan equivalent |
|---|---|---|
| `PRIMARY_METADATA_READY` | Metadata sufficient to justify bounded Task 5 restoration on the primary (intermittent-defect) track: authoritative product-defect identity, exact counterparts with authoritative ancestry, explicit obligation and witness, an existing non-forcing procedure, bounded restoration path. **Not** Q0-qualified; intermittency is unmeasured. | Precedes the plan's "qualified episode"; the restoration-eligible state of a would-be `PRIMARY_INTERMITTENT_CANDIDATE` |
| `UNRESOLVED` | Real defect, but missing a supported acceptable counterpart and/or any existing non-forcing protocol; not restoration-eligible as primary. | Task 4 `UNRESOLVED` |
| `STABLE_CONTROL_ONLY` | Real defect with a supported pair but only a controlled/forced witness; usable only as a plan "stable defect retained as a named control". | Task 4 `STABLE_ORACLE_CONTROL` (rename only) |
| `EXCLUDE` | Retained in the roster for traceability; no acceptable counterpart or fix; consumes no restoration budget. | Task 4 `EXCLUDE` |

## Roster reconciliation before acquisition

**DBCP episode boundary, corrected.** The original text stated globally that "DBCP-65 and DBCP-270 are one historical defect/fix episode". That is overstated. The authoritative history shows two distinct defects under the DBCP-65 title:

- **DBCP-65a — prepareStatement synchronization deadlock.** Original DBCP-65 report; nominal fix Apache commit `4ae50045738561c1c48c31bbad2ece90eaebffb8` (SVN `r498524`, also cited by DBCP-202), sole parent `ec3988c3bad400091ef48713dabfa38e665b434e`, which removes `synchronized` from two `PoolingConnection.prepareStatement` methods. Task 4 Card 2's pair `ec3988c… → 4ae5004…` belongs to this defect. The JaConTeBe `Dbcp65` kernel (eviction path plus `PoolingConnection.prepareStatement` path) targets this manifestation and is Mockito-controlled. Status: **`UNRESOLVED`** — no non-forcing protocol exists; the pair is at most a stable-control lead and is not promoted here.
- **DBCP-65b / DBCP-270 / DBCP-281 — close/evict `AbandonedTrace` deadlock.** The residual manifestation reported against 1.2.2 in DBCP-65, re-filed as DBCP-281 ("re-open of DBCP-65", resolved *Duplicate* of DBCP-270), fixed by Apache commit `4bf62b339ef3a30dac10160da76905222063485b` (SVN `r672097`), sole parent `c8034fa0290b3690e31e933402ee049af9aa39d0`, which narrows `AbandonedTrace` synchronization to the trace list. This is one deduplicated episode under the plan's episode definition. Status: **`UNRESOLVED`** — supported pair, but no existing non-forcing protocol (see `dbcp_65_metadata_pass.md`, Question 2).

The two entries share the DBCP-65 issue title but have different `V_bad` hashes and different fixes; they are counted as two roster entries and neither is primary-ready. The frozen `candidate_cards.md` is not edited; this reconciliation supersedes its Card 2 pairing for roster-accounting purposes only.

The reconciled pre-Task-C card inventory therefore contained six distinct roster entries:

1. POOL-162 — `STABLE_CONTROL_ONLY`
2. DBCP-65a (prepareStatement, `ec3988c… → 4ae5004…`) — `UNRESOLVED`
3. DBCP-65b/270/281 (`AbandonedTrace`, `c8034fa… → 4bf62b3…`) — `UNRESOLVED`
4. POOL-146 — `STABLE_CONTROL_ONLY`
5. LOG4J-38137 — `UNRESOLVED`
6. LOG4J-41214 — `EXCLUDE`

**Slot-counting convention, declared.** The plan's roster ceiling is "at most 12 primary defect candidates plus two nuisance/control candidates". Every card above entered the roster as a primary product-defect candidate. A card that later functions only as a stable oracle control (POOL-162, POOL-146) **remains counted against the 12-primary ceiling and does not consume a nuisance/control slot**. The two nuisance/control slots are reserved for candidates acquired *as* nuisance or control subjects; they remain open because RQ1's nuisance-blocking measurement (`N`, `R`) requires at least one independently verified nuisance case, which the roster does not yet contain. Retained exclusions also count against the 12-primary ceiling, since the plan requires the whole roster and its exclusions to be kept. Under this convention the pre-acquisition roster used six of twelve primary entries and zero of two nuisance/control slots.

## Deterministic source-tier screening

### Tier 1 — JaConTeBe: exit recorded as a decision by judgment, not measured exhaustion

The plan's Tier 1 stop rule is a four-hour human metadata allowance. That allowance cannot be declared exhausted: Task 3, Task 4 and B human hours are `UNKNOWN` in the resource ledger. **Tier 1 was therefore exited by research judgment**, on these grounds:

- all six carded JaConTeBe kernels (POOL-162, DBCP-65, POOL-146, DBCP-270, LOG4J-38137, LOG4J-41214) are controlled reproducers (Mockito, staging sleeps, explicit interrupts, or an external Java agent), and the JaConTeBe paper reports 36 of 47 cases reproducing deterministically on every run;
- no case-specific evidence of unforced mixed manifestation was found for any carded Java lead;
- the bounded DBCP-65 pass (B) ended `KEEP_UNRESOLVED`.

**The remaining non-JDK JaConTeBe inventory was not exhaustively screened.** Never carded or screened: DBCP-271, DBCP-369, POOL-46, POOL-120, POOL-149, LOG4J-44032, LOG4J-50463, LOG4J-54325, DERBY-764, DERBY-4129, DERBY-5447, DERBY-5560, DERBY-5561, GROOVY-3495, GROOVY-4292, GROOVY-4736, GROOVY-5198, GROOVY-6068, GROOVY-6456, LUCENE-1544, LUCENE-2783 (21 IDs). Their status is `NOT_SCREENED`, not excluded. This is a selection limitation of the present cohort and must be reported as such.

**Language/harness selection (plan Section 5, Tier 4 rule: "Select Java or Go by day 7; do not build two new language harnesses in parallel").** Recorded here as an explicit research decision: **Go (GoReal) is selected as the single new-language harness for this month's Q0/E1 work.** Consequences: no Java subject is restored this month; POOL-162 and POOL-146 remain deferred stable-control leads (as the amendment already required for POOL-162); any later Java restoration needs a new budgeted decision. The decision was made on operational day 1 of the Q0 clock (clock start `2026-09-17T23:02:26Z`, see `resource_ledger.md`), within the day-7 limit.

### Tier 2 — matching archived Java CI

The BugSwarm metadata snapshot was screened for flaky Java artifacts whose classification records production-code changes. Nineteen entries had `classification.code = Yes` and `classification.test = No`; their archived fail/pass metadata did not by itself establish a causal defective/acceptable product pair, a focal product obligation, and candidate-specific natural intermittent manifestation.[1] The CI-Bench roster supplies reproducible BugSwarm artifact identifiers, but not the missing causal product-defect adjudication.[2]

No BugSwarm or CI-Bench row was promoted to a candidate card. In particular, no fail/pass build pair was treated as `V_bad`/`V_ok`, and no artifact-level flaky label was treated as product-defect truth.

**Traceability limitation (repair note).** The original pass did not record the identity (URL, commit, or hash) of the BugSwarm snapshot it screened, nor the nineteen artifact identifiers. No such snapshot exists in this repository (`BugSwarm/BugSwarm@Traccar/` holds only a Traccar execution CSV without `classification` fields). The count of nineteen is therefore an unverifiable statement of the original pass. Source [1] below points to the public BugSwarm dataset location; the exact snapshot is `NOT RECORDED`. Any future Tier 2 screening must record snapshot identity and per-artifact disposition.

### Tier 3 — IDoFT or equivalent issue/test-history leads

The IDoFT PR table was screened in repository order for accepted/developer-fixed and concurrency-related records. It records flaky-test repair proposals and statuses, but the inspected leads did not jointly provide an authoritative product fix, exact acceptable counterpart, and an existing non-forcing product-obligation protocol.[3]

No IDoFT row was promoted to a candidate card. Test-maintenance changes, retry changes, and unmerged repair proposals were not counted as product-defect fixes.

**Traceability limitation (repair note).** The original pass did not record the IDoFT commit or the individual rows inspected; per-row dispositions are `NOT RECORDED`. The original sentence "This exhausted the bounded Java acquisition path" is withdrawn: Tiers 2–3 were screened without promotion, and Tier 1 was exited by judgment as recorded above. Tier 4 was entered under the selection decision above.

### Tier 4 — GoReal fallback

GoBench reports 82 real-project concurrency bugs (GoReal) selected from merged fixes with detailed reproduction information and a test entry point; it reports reproducing each selected bug by running the bug-triggering test against buggy and fixed applications.[4] In the GoBench repository as read on 2026-09-18 (commit `2e91eb10b8e7b2873ea44f12b87ec1b2520e1b69`), GoReal is split into `configures/goreal/blocking.json` (40 entries) and `configures/goreal/nonblocking.json` (42 entries).[6] Its GoReal executor constructs native test-binary invocations (`/go/gobench.test -test.v -test.count N [-test.cpu C] [-test.failfast] -test.timeout T -test.run <TestFunc>`) and does not itself insert a scheduler controller into the subject.[7] The executor's default repeat mode is in-process `-test.count N` and it can run containers in parallel; Q0 must instead use fresh-process single attempts (`-test.count 1`), one job at a time, per the frozen protocol.

**Only `blocking.json` was screened. `nonblocking.json` was excluded** because its entries are data-race subjects, and the plan states that a data-race report alone does not satisfy the chosen behavioral-obligation requirement (an incorrect result, violated invariant, or diagnosed deadlock is required).

**Actual screening order (repair note).** The original text stated that "earlier CockroachDB and Moby entries" were not enrolled. That statement is inconsistent with every deterministic ordering of `blocking.json`: the file's own key order (and the alphabetical project order) is cockroach → etcd → grpc → hugo → istio → kubernetes → moby → serving → syncthing, so Moby entries are not "earlier" than etcd; in global numeric-issue order, grpc, kubernetes, serving and syncthing entries would also precede etcd-5509. The original pass did not preserve which cockroach or moby IDs were inspected or their individual reasons, and it did not record why etcd-6708 and etcd-7443 — which precede etcd-7492 in numeric order — were passed over. Those per-ID dispositions are `NOT RECORDED` and are **not reconstructed here**.

The ordering rule adopted prospectively from this repair onward is the plan's: source tier → project (alphabetical, as in the GoReal file order) → issue ID (numeric). Under that rule the Tier 4 roster position of the two enrolled cards is: cockroach entries first, then etcd-5509, etcd-6708, etcd-7443, etcd-7492, etcd-10492. **Appendix A** lists every `blocking.json` entry with its current disposition. Before any further Tier 4 enrolment, the ten cockroach entries and etcd-6708/etcd-7443 must be screened with recorded per-ID reasons; etcd entries can no longer be enrolled as primary because the per-project cap is saturated, so their screening serves ordering integrity only.

The two cards below are the two etcd entries that the original pass judged metadata-ready. Acquisition paused at that point (see "Scope and stop").

## New candidate card C-01 — etcd-5509

- **Source tier:** 4, GoReal fallback.
- **Classification:** `PRIMARY_METADATA_READY`.
- **Counterpart type (plan §4.1):** intended **historical pair with an isolatable focal change**, subject to the equivalence check below. If that check fails, the case may be reported only as a *controlled historical-fix reversal on one pinned base*, never as a historical pair.
- **Authoritative issue/source identity — observed:** etcd PR 5509, “clientv3: fix deadlock on Get with concurrent Close”, merged 2016-06-01 as `9ed3b446…`. The PR contains **two commits addressing two distinct failure modes**: (i) “clientv3: fix deadlock on Get with concurrent Close” and (ii) “clientv3: don't panic on Get if NewKV is created with a closed client”.[8] The maintainer's root-cause statement for (i): `r.acquire()` returned holding `r.client.mu.RLock()` on a failure path and leaked it, after which any `client.Close()` blocks forever waiting for the write lock.[8]
- **Correction of the original card (repair note).** The original card cited “a standalone reproducer” and “a maintainer statement that the problem was reproduced” as evidence for the deadlock. In the authoritative thread, the standalone reproducer was posted by a reviewer to show a *panic* on `Get` strictly after `Close` (failure mode ii), and the maintainer's “can repro … fixed the panic” refers to that panic, not to the deadlock.[8] **Neither is evidence that the deadlock was reproduced by upstream, and neither is used as such here.**
- **Affected version/revision — observed:** no affected release is inferred. The affected mainline revision is the first parent of the merge fix, `36fcc9e9d4ce993998a9170b2293c30b4e5a601a`.[9]
- **Candidate defective revision `V_bad`:** `36fcc9e9d4ce993998a9170b2293c30b4e5a601a`.
- **Candidate acceptable revision `V_ok`:** merge commit `9ed3b446cadd9f43734d9eed9dcb03f3b12567a5`, whose first parent is `V_bad`. The merge differs from `V_bad` in exactly two files: `clientv3/remote_client.go` (+7/−5, blob `b8209b8a5` → `b51116305`) and `clientv3/integration/kv_test.go` (+31/−10).[9]
- **Exact focal behavioral obligation:** `remoteClient.acquire` must not return while holding the client read lock, or report success, when the client is closed or has no connection; consequently a client `Get` concurrent with `Client.Close` must terminate (the test accepts successful completion or `ErrConnClosed`) and `Client.Close` must return.[8][9] The obligation covers both failure modes (i) and (ii) because both arise from the same `acquire` failure-path handling reversed by the same production patch; the two manifestations are nevertheless recorded with distinct signatures below.
- **Deadlock mechanism at `V_bad` — observed in source:** `Client.Close()` takes `c.mu.Lock()`, sets `c.cancel = nil`, releases the lock, performs shutdown work, then takes `c.mu.Lock()` a second time before returning (`clientv3/client.go` at `V_bad`, lines 104–123). A `Get` whose `acquire` runs between the release and the second lock observes `closed`, returns `ErrConnClosed` still holding `RLock`, and the second `Lock` blocks forever.[9][18] The hang therefore occurs inside `cli.Close()` on the test's main goroutine, *before* the test reaches its own 3-second `select`.
- **Pre-declared evaluator signatures (frozen before any qualification attempt):**
  - **(a) `FOCAL_DEFECT_WITNESS` — deadlock/hang:** the attempt does not complete within the frozen attempt timeout **and** the Go test-timeout goroutine dump (emitted by `-test.timeout`, `panic: test timed out after …`) shows the test goroutine blocked in `sync.(*RWMutex).Lock` called from `(*Client).Close` (second lock, `client.go:118` at `V_bad`), with `TestKVGetErrConnClosed` as the running test. A timeout without this stack evidence is `UNRESOLVED`, not a focal witness. The test's internal `kv.Get took too long` message is **not** expected for this mode and is not the operative witness.
  - **(b) `FOCAL_DEFECT_WITNESS` — closed-client / nil-connection panic:** the attempt terminates with a Go runtime panic (`nil pointer dereference` or equivalent) whose stack passes through `Get`/`acquire`/`remoteClient` on the closed client within `TestKVGetErrConnClosed`. This is a second focal manifestation of the same reversed patch. Recorded per attempt as a separate signature so that hang counts and panic counts are never merged.
  - Any other failure (cluster start-up failure, unrelated integration timeout, build error) is `OTHER_DEFECT`, `UNRESOLVED` or `HARNESS_INVALID` per the frozen categories. Q0's intermittency criterion (≥2 focal failures and ≥2 passes in 20 `V_bad` attempts) is evaluated on (a)+(b) combined, with the (a)/(b) split reported.
- **Available witness/reproducer — observed:** upstream `clientv3/integration::TestKVGetErrConnClosed` as modified by the merge. GoReal identifies that exact target (`testfunc: TestKVGetErrConnClosed`, `workdir: ./clientv3/integration`) and packages a focused integration-test binary.[6][8][10] The merge also adds `TestKVNewAfterClose` (failure mode ii); it is not part of the frozen target.
- **Forced/controlled/natural status — observed:** controlled concurrent workload, but non-forcing. The modified test starts one ordinary goroutine for `Get` and calls `Close` on the main goroutine; the Go scheduler determines the interleaving; there is no mocking, scheduler instrumentation, forced synchronization outcome, or synthetic fault injection.[9] The pre-merge version of the test contained an explicit ordering gate (`closed` channel) that ran `Get` only after `Close` returned; the merge removes that gate so the two operations genuinely race.[9]
- **Evidence for intermittency:** the deadlock requires `Get`'s `acquire` to fall inside the window between `Close`'s two lock acquisitions, so mixed manifestation is mechanistically plausible (inference from source). **No upstream reproduction of the deadlock, no pass/fail frequency, and no verified mixed count is published.** Q0 must establish the required two focal failures and two passes in 20 attempts under the frozen protocol.
- **Exact fix and parent — observed:** fix `9ed3b446cadd9f43734d9eed9dcb03f3b12567a5`; first parent `36fcc9e9d4ce993998a9170b2293c30b4e5a601a`.[9]
- **Same target/harness plausibility:** plausible with a frozen test-only backport (a *reconstructed test of a historical defect*, not replay of the original CI test). GoReal checks out the merge revision and applies its `bug_patch.diff`, which touches only `clientv3/remote_client.go`, to construct its buggy image, thereby retaining the same focused test on both variants.[10][11] **Equivalence check required in Task 5:** the reversed `clientv3/remote_client.go` must be byte-identical to that file at `V_bad` (git blob `b8209b8a5`, which is also the blob named in GoReal's patch header). If it is, the case is a historical pair with a documented identical test backport. If it is not, the case is reported only as a controlled historical-fix reversal with every deviation disclosed; it is not thereby a “synthetic mutant”, but it is never a historical pair.
- **Required historical toolchain/runtime — source claim:** Go 1.10 (`golang:1.10` image), a Linux Docker runtime, the historical etcd `test` script, and the `clientv3/integration` package.[6][10] **Harness modifications by GoReal that must be frozen and disclosed:** GoReal clones current `etcd-io/etcd` master into the historical `github.com/coreos/etcd` path, `git reset --hard` to the merge SHA, and edits the upstream `test` script by line number (`sed`) to compile the integration package to `/go/gobench.test`.[10] Q0 must pin the script hash after modification and run fresh-process single attempts (`-test.count 1`, `-test.run TestKVGetErrConnClosed`, `-test.timeout` below the 120-second attempt ceiling so that Go emits the goroutine dump).
- **Known restoration dependencies:** old pre-module etcd dependency resolution, a local single-member integration cluster created by the upstream test infrastructure, network access needed by the historical clone/build, and compatibility of the old Go image with the current container runtime.
- **Provenance problems:** the GoBench representation is a secondary benchmark and reconstructs the buggy production tree by reversing the authoritative fix; it is not authoritative provenance. The authoritative identity and counterpart pair come from etcd history.[8][9]
- **Qualification blockers:** perform the blob-equivalence check; freeze one identical test source on both revisions; confirm that target identity and timeout semantics are unchanged; apply signatures (a)/(b) against unrelated integration failures; and demonstrate natural mixed manifestation under the frozen Q0 reset/condition protocol.
- **Why metadata-ready (not Q0-qualified):** both exact counterparts have authoritative ancestry, the obligation and witnesses are explicit and pre-declared, and an existing non-forcing focused integration procedure has a bounded Go 1.10/Docker restoration path. Remaining questions are qualification questions rather than missing metadata. Intermittency is unmeasured.

## New candidate card C-02 — etcd-7492

- **Source tier:** 4, GoReal fallback.
- **Classification:** `PRIMARY_METADATA_READY`.
- **Counterpart type (plan §4.1): controlled historical-fix reversal on one pinned base.** The pinned base is the merge commit `148c923c72c4aa9207173c03b775e2c0b8754067`; the defective variant is that base with the authoritative production fix reversed **except for one declared non-behavioral source deviation** (below). **This counterpart is never described as a historical pair**, and it must be reported separately from historical-pair cases in every E1/E2 table. The original card's requirement that the buggy tree be byte-equivalent to the exact historical parent is withdrawn because it is infeasible (see “Same target/harness plausibility”).
- **Authoritative issue/source identity — observed:** etcd issue 7471, “Benchmarking is causing cluster to become unresponsive”, reports an etcd 3.1.0 three-node cluster with authentication enabled that became unresponsive under benchmark load; a later goroutine dump in the thread shows ~1,000 goroutines blocked in `auth.(*authStore).AuthInfoFromToken`. PR 7492, “auth: get rid of deadlocking channel passing scheme in simpleTokenTTL”, states “Fixes #7471” and was merged 2017-03-14 as `148c923c…`.[12][13][14]
- **Affected version/revision — observed / source claim:** the reporter identifies etcd 3.1.0. The mainline revision used as the historical reference for the defective state is the first parent of the merge, `3a61fe596ba1eda2ae0900dfbb1f735ab574ab16`.[12][14] The defective *variant actually executed* is the reversed pinned base, not this parent (see counterpart type).
- **Historical defective reference `V_bad` (reference only):** `3a61fe596ba1eda2ae0900dfbb1f735ab574ab16`.
- **Acceptable counterpart `V_ok`:** merge commit `148c923c72c4aa9207173c03b775e2c0b8754067`; its first parent is the reference above; the merge differs from it in exactly two files: `auth/simple_token.go` (+32/−31, blob `5b608af92` → `ff48c5140`) and `auth/store_test.go` (+49/−0).[14]
- **Exact focal behavioral obligation:** concurrent simple-token authentication and token expiration must complete without the `simpleTokensMu` / `addSimpleTokenCh` cycle (`assignSimpleTokenToUser`/`info` holding `simpleTokensMu` and blocked on a full channel while `run()`'s ticker branch is blocked acquiring `simpleTokensMu` inside `deleteTokenFunc`) making authentication or the cluster unresponsive.[12][13][16]
- **Pre-declared evaluator signature (frozen before any qualification attempt):** `FOCAL_DEFECT_WITNESS` requires that the attempt does not complete within the frozen attempt timeout **and** the Go test-timeout goroutine dump shows at least one goroutine blocked on a send to `addSimpleTokenCh`/`resetSimpleTokenCh`/`deleteSimpleTokenCh` (or in `simpleTokensMu` acquisition) from `tokenSimple.assignSimpleTokenToUser`/`info`/`invalidateUser`, together with the `simpleTokenTTLKeeper.run` goroutine blocked in `sync.(*Mutex).Lock`/`RWMutex.Lock` via `deleteTokenFunc`, within `TestHammerSimpleAuthenticate`. A timeout without that stack evidence, or a failure in backend/bolt setup, is `UNRESOLVED`/`OTHER_DEFECT`, not a focal witness.
- **Available witness/reproducer — observed:** upstream `auth::TestHammerSimpleAuthenticate`, added by the merge. It lowers `simpleTokenTTL`/`simpleTokenTTLResolution` to 10 ms, creates 50 users, and executes ten waves of concurrent `Authenticate`/`AuthInfoFromCtx` calls “to try to trigger races”, with a 1 ms sleep between waves.[15] GoReal identifies the same target (`testfunc: TestHammerSimpleAuthenticate`, `workdir: ./auth`), builds the `auth` package test binary, and its case README preserves the upstream description and a historical stack.[6][16][17]
- **Forced/controlled/natural status — observed:** controlled workload but non-forcing. The test changes a test-time TTL through package variables and supplies concurrent authentication load; it does not mock the product, control a scheduler, impose the expected interleaving, instrument locks, or inject a synthetic fault.[15] The failure-producing ordering remains a natural runtime scheduling outcome.
- **Evidence for intermittency — source claim:** the issue reporter states the benchmark “would occasionally complete successfully, but most of the time” the cluster became unresponsive — mixed manifestation at system level under the reporter's workload, not under the test.[12] The regression test says it tries to trigger races, and GoBench states that repeated native executions are needed for nondeterministic concurrency bugs.[4][15] No candidate-specific mixed count for the test is published; Q0 qualification remains mandatory.
- **Exact fix and parent — observed:** fix `148c923c72c4aa9207173c03b775e2c0b8754067`; first parent `3a61fe596ba1eda2ae0900dfbb1f735ab574ab16`.[14]
- **Same target/harness plausibility — corrected:** the merged test assigns to `simpleTokenTTL` and `simpleTokenTTLResolution`. At the historical parent these two identifiers are declared in a `const` block; the fix moves them into a `var` block (“var for testing purposes”).[14][19] **The identical test therefore cannot compile against a byte-identical parent**, so a historical pair with an identical test backport is impossible for this case. GoReal's `bug_patch.diff` accordingly reverses every production hunk of the fix *except* the `const → var` declaration change, which it retains as context.[17] **Declared minimal source deviation of the defective variant from the historical parent:** the four-line move of `simpleTokenTTL` and `simpleTokenTTLResolution` from `const` to `var` in `auth/simple_token.go`, with unchanged values (`5 * time.Minute`, `1 * time.Second`). This deviation changes no runtime behavior; it exists only to keep the frozen test compilable on both variants. **Task 5 check:** the defective variant's `auth/simple_token.go` must equal the historical parent's file *plus exactly that declaration move and nothing else* (diff restricted to that hunk); any other difference invalidates the variant. The benchmark patch itself is not treated as authoritative defect provenance.
- **Required historical toolchain/runtime — source claim:** Go 1.13 (`golang:1.13` image), a Linux Docker runtime, the historical etcd `test` script, and the `auth` package.[6][17] **Harness modifications by GoReal that must be frozen and disclosed:** clone of current `etcd-io/etcd` master into the historical `github.com/coreos/etcd` path, `git reset --hard` to the merge SHA, and two line-number `sed` edits of the upstream `test` script to compile the `auth` package to `/go/gobench.test` (`PKG=./auth PASSES='build unit' ./test`).[17] Q0 must pin the modified script hash and run fresh-process single attempts (`-test.count 1`, `-test.run TestHammerSimpleAuthenticate`, `-test.timeout` below the 120-second attempt ceiling).
- **Known restoration dependencies:** the historical `github.com/coreos/etcd` source path despite the current `etcd-io` repository identity, old vendored/pre-module dependencies, local bolt backend creation by `setupAuthStore` (temporary files that the reset recipe must remove), network access for image/build acquisition, and compatibility of the old Go image with the current container runtime.
- **Provenance problems:** repository-owner/path migration must not be mistaken for a different subject. GoBench is a secondary reproduction source and uses a reverse patch whose header index line names the parent blob although its content does not restore it; authoritative defect/fix identity comes from issue 7471, PR 7492, and the exact merge ancestry.[12][13][14][17]
- **Qualification blockers:** perform the restricted-diff check above; hold the backported test byte-identical across both variants; freeze TTL, CPU, reset and timeout conditions; apply the pre-declared signature against unrelated backend timeouts; and obtain Q0's required mixed defective-variant outcomes plus an acceptable-counterpart witness.
- **Why metadata-ready (not Q0-qualified):** authoritative exact ancestry, a precise product obligation, a focused upstream stress witness, source-supported condition dependence, and an existing non-forcing Go 1.13/Docker protocol are all present, with the counterpart type and its single declared deviation fixed in advance. Remaining uncertainty is empirical qualification, not an unbounded counterpart or protocol search. Intermittency is unmeasured.

## Reconciled roster after Task C

The candidate-card inventory now contains eight roster entries (eight cards; seven distinct upstream defect/fix episodes plus the DBCP-65a/65b split of the DBCP-65 title into its two defects):

| # | Entry | Tier | Pair (`V_bad` → `V_ok`) | Counterpart type | Label |
|---:|---|---:|---|---|---|
| 1 | DBCP-65a (prepareStatement) | 1 | `ec3988c…` → `4ae5004…` | historical pair (forced kernel only) | `UNRESOLVED` |
| 2 | DBCP-65b / DBCP-270 / DBCP-281 (`AbandonedTrace`) | 1 | `c8034fa…` → `4bf62b3…` | historical pair (no non-forcing protocol) | `UNRESOLVED` |
| 3 | LOG4J-38137 | 1 | `v1_2_13` → none | — | `UNRESOLVED` |
| 4 | LOG4J-41214 | 1 | `v1_2_13` → none | — | `EXCLUDE` |
| 5 | POOL-146 | 1 | `51ae45b…` → `1b80d34…` | historical pair | `STABLE_CONTROL_ONLY` |
| 6 | POOL-162 | 1 | `280c60a…` → `674a6ba…` | historical pair with identical test backport | `STABLE_CONTROL_ONLY` |
| 7 | etcd-5509 | 4 | `36fcc9e…` → `9ed3b44…` | historical pair, pending blob-equivalence check | `PRIMARY_METADATA_READY` |
| 8 | etcd-7492 | 4 | reference `3a61fe5…`; pinned base `148c923…` | controlled historical-fix reversal (declared `const → var` deviation) | `PRIMARY_METADATA_READY` |

Roster order above follows the plan's rule (tier → project alphabetical → issue ID). Task 4's card numbering (POOL-162 first) followed Task 3's recommendation and is preserved unchanged in the frozen `candidate_cards.md`; it does not govern E1 subject order.

Counts by label: `PRIMARY_METADATA_READY` 2 (etcd-5509, etcd-7492); `UNRESOLVED` 3 (DBCP-65a, DBCP-65b/270/281, LOG4J-38137); `STABLE_CONTROL_ONLY` 2 (POOL-146, POOL-162); `EXCLUDE` 1 (LOG4J-41214).

Ceiling accounting under the declared convention: **8 of 12 primary entries used; 4 remain. 0 of 2 nuisance/control slots used; 2 remain** and are reserved for a genuine verified-nuisance case and/or a deliberately acquired control. Per-project cap: etcd 2 of 2 (saturated); commons-pool 2 of 2 (both controls); commons-dbcp 2 of 2 (both unresolved); log4j 2 of 2 (unresolved/excluded). Any further primary enrolment must therefore come from a project not yet on the roster.

## Resource accounting

- Task C acquisition wall clock: **EXACT**, `1229.530393` seconds (agent/tool elapsed time).
- Task C human metadata effort: **UNKNOWN**; agent/tool elapsed time is not converted into human hours.
- Task 3, Task 4 and B human metadata effort: **UNKNOWN**, as recorded in the resource ledger.
- Restoration/qualification human effort in this task: **EXACT**, zero.
- Restoration/qualification allocated vCPU-hours in this task: **EXACT**, zero.
- Documentation repair of 2026-09-19: provenance work; human effort **UNKNOWN**; not charged as candidate acquisition; no compute.
- Remaining total Q0 metadata allowance: symbolically `12 human hours - supported cumulative Task 3/Task 4/B/Task C human metadata charge`; no numerical remainder is asserted.
- Remaining GoReal allowance: only the remainder of that same Q0 metadata cap and operational gate; no unsupported numerical remainder is asserted.
- Operational gate: the operational Q0 clock started at `2026-09-17T23:02:26.133312834Z` (B, recorded in `dbcp_65_metadata_pass.md`). Task C fell on operational day 1. Neither the day-7 nor the day-10 gate was reached by this metadata-only step.

## Task C decision

**Task 5 restoration of etcd-5509 is recommended pending completion of this documentation repair and a final consistency check.** etcd-5509 is the first `PRIMARY_METADATA_READY` entry in roster order and the only restoration-eligible primary-track candidate. This is a recommendation, not an authorization and not a qualification result; the authorization record is the ledger's decision entry of 2026-09-19. Task 5 must enforce the pre-declared signatures (a)/(b), the `remote_client.go` blob-equivalence check, the frozen target and timeout rules, fresh-process single attempts, and the per-candidate caps (≤2 human restoration hours, ≤4 allocated vCPU-hours) within the 20 vCPU-hour Q0 and 40 vCPU-hour first-ten-day ceilings.

Acquisition is paused, not closed: G1b requires resumption for a non-etcd project. Q0 no-go/fallback has not been reached.

## Appendix A — GoReal `blocking.json` screening record

Source: `gobench/configures/goreal/blocking.json` at GoBench commit `2e91eb10b8e7b2873ea44f12b87ec1b2520e1b69`, read 2026-09-18.[6] Order is the file's key order, which coincides with project-alphabetical order. Dispositions reflect what the durable record supports; nothing is reconstructed.

| Order | Entry | Test target | Disposition |
|---:|---|---|---|
| 1 | cockroach_1055 | `TestStopperQuiesce` | `NOT_CARDED` — original pass reported cockroach entries as not enrolled; per-ID reason `NOT RECORDED` |
| 2 | cockroach_1462 | `TestHeartbeatSingleGroup` | `NOT_CARDED` — per-ID reason `NOT RECORDED` |
| 3 | cockroach_17766 | `TestRangeLookupAsyncResolveIntent` | `NOT_CARDED` — per-ID reason `NOT RECORDED` |
| 4 | cockroach_24808 | `TestCompactorDeadlockOnStart` | `NOT_CARDED` — per-ID reason `NOT RECORDED` |
| 5 | cockroach_25456 | `TestConsistenctQueueErrorFromCheckConsistency` | `NOT_CARDED` — per-ID reason `NOT RECORDED` |
| 6 | cockroach_30452 | `TestReplicaIDChangePending` | `NOT_CARDED` — per-ID reason `NOT RECORDED` |
| 7 | cockroach_30479 | `TestGossipFirstRange` | `NOT_CARDED` — per-ID reason `NOT RECORDED` |
| 8 | cockroach_35073 | `TestOutboxUnblocksProducers` | `NOT_CARDED` — per-ID reason `NOT RECORDED` |
| 9 | cockroach_35931 | `TestFlowCancelPartiallyBlocked` | `NOT_CARDED` — per-ID reason `NOT RECORDED` |
| 10 | cockroach_36367 | `TestStoreRangeMergeInFlightTxns` | `NOT_CARDED` — per-ID reason `NOT RECORDED` |
| 11 | etcd_5509 | `TestKVGetErrConnClosed` | **Carded C-01**, `PRIMARY_METADATA_READY` |
| 12 | etcd_6708 | `TestHTTPClusterClientSyncPinLeaderEndpoint` | `SKIPPED` — precedes etcd_7492 in numeric order; no contemporaneous reason recorded; cannot now be enrolled as primary (etcd cap saturated) |
| 13 | etcd_7443 | `TestBalancerDoNotBlockOnClose` | `SKIPPED` — same as etcd_6708 |
| 14 | etcd_7492 | `TestHammerSimpleAuthenticate` | **Carded C-02**, `PRIMARY_METADATA_READY` |
| 15 | etcd_10492 | `TestLessorRenewWithCheckpointer` | `NOT_SCREENED` — after the pause point |
| 16–22 | grpc_649, grpc_795, grpc_1275, grpc_1424, grpc_1859, grpc_2391, grpc_3017 | (see file) | `NOT_SCREENED` — after the pause point |
| 23–24 | hugo_3251, hugo_5379 | (see file) | `NOT_SCREENED` |
| 25–27 | istio_16224, istio_17860, istio_18454 | (see file) | `NOT_SCREENED` |
| 28–35 | kubernetes_1321, kubernetes_11298, kubernetes_16851, kubernetes_25331, kubernetes_26980, kubernetes_30872, kubernetes_38669, kubernetes_70277 | (see file) | `NOT_SCREENED` |
| 36–37 | moby_29733, moby_30408 | `TestPluginAddHandler`, `TestPluginWaitBadPlugin` | Original pass reported Moby entries as inspected and not enrolled, contradicting the deterministic order; per-ID reason `NOT RECORDED`; treated as `NOT_SCREENED` for ordering purposes |
| 38 | serving_2137 | (see file) | `NOT_SCREENED` |
| 39–40 | syncthing_4829, syncthing_5795 | (see file) | `NOT_SCREENED` |

`nonblocking.json` (42 entries): `EXCLUDED_AS_SET` — data-race subjects; a data-race report alone does not satisfy the cohort's behavioral-obligation requirement.

## Sources

Authoritative upstream sources (issue/commit history) are listed first; secondary benchmark sources (GoBench/GoReal, BugSwarm, CI-Bench, IDoFT) are listed separately and are not treated as defect or revision provenance.

### Authoritative upstream sources

[8] https://github.com/etcd-io/etcd/pull/5509 — etcd PR 5509 “clientv3: fix deadlock on Get with concurrent Close” (two commits; reviewer panic reproducer; maintainer root-cause comment). API: https://api.github.com/repos/etcd-io/etcd/pulls/5509
[9] https://github.com/etcd-io/etcd/commit/9ed3b446cadd9f43734d9eed9dcb03f3b12567a5 — merge commit of PR 5509; parents `36fcc9e9d4ce993998a9170b2293c30b4e5a601a`, `a83051d0fc0e7ad06e8fea05ba150f6215b7ff80`; diff at `…/commit/9ed3b446cadd9f43734d9eed9dcb03f3b12567a5.diff`
[12] https://github.com/etcd-io/etcd/issues/7471 — etcd issue 7471 “Benchmarking is causing cluster to become unresponsive” (3.1.0, auth enabled; goroutine dump). API comments: https://api.github.com/repos/etcd-io/etcd/issues/7471/comments
[13] https://github.com/etcd-io/etcd/pull/7492 — etcd PR 7492 “auth: get rid of deadlocking channel passing scheme in simpleTokenTTL” (“Fixes #7471”)
[14] https://github.com/etcd-io/etcd/commit/148c923c72c4aa9207173c03b775e2c0b8754067 — merge commit of PR 7492; parents `3a61fe596ba1eda2ae0900dfbb1f735ab574ab16`, `44099321321f7c8c7e99ac134efa7d350b187975`; diff at `…/commit/148c923c72c4aa9207173c03b775e2c0b8754067.diff`
[15] `auth/store_test.go` hunk of [14] — `TestHammerSimpleAuthenticate` as merged
[18] https://raw.githubusercontent.com/etcd-io/etcd/36fcc9e9d4ce993998a9170b2293c30b4e5a601a/clientv3/client.go — `Client.Close` at `V_bad` (two lock acquisitions); companion `…/36fcc9e9d4ce993998a9170b2293c30b4e5a601a/clientv3/remote_client.go` — `acquire` at `V_bad`
[19] https://raw.githubusercontent.com/etcd-io/etcd/3a61fe596ba1eda2ae0900dfbb1f735ab574ab16/auth/simple_token.go — `const` declaration of `simpleTokenTTL`/`simpleTokenTTLResolution` at the etcd-7492 historical parent

DBCP episode-boundary sources (Apache JIRA / imported history) are those of `dbcp_65_metadata_pass.md` [1]–[9], in particular DBCP-281 (https://issues.apache.org/jira/si/jira.issueviews:issue-xml/DBCP-281/DBCP-281.xml — “re-open of DBCP-65”, resolved Duplicate of DBCP-270, fixed in `r672097`) and the two fix commits `4ae50045…` (`r498524`) and `4bf62b33…` (`r672097`).

### Secondary benchmark and dataset sources

[1] https://www.bugswarm.org/docs/introduction/what-is-bugswarm/ — BugSwarm dataset documentation (the plan's cited entry point). **Exact snapshot screened by the original pass: NOT RECORDED.**
[2] https://github.com/BugSwarm/CI-Bench — CI-Bench roster of BugSwarm artifact identifiers
[3] https://github.com/TestingResearchIllinois/idoft — IDoFT flaky-test dataset (test/PR records). **Commit and rows inspected by the original pass: NOT RECORDED.**
[4] https://lujie.ac.cn/files/papers/GoBench.pdf — GoBench primary paper (GoReal: 82 real bugs; reproduction by running the bug-triggering test on buggy and fixed versions)
[5] (not used)
[6] https://github.com/timmyyuan/gobench/blob/2e91eb10b8e7b2873ea44f12b87ec1b2520e1b69/gobench/configures/goreal/blocking.json — GoReal blocking configuration (40 entries; `testfunc`, `workdir`, `goversion`, `pull_sha`, build commands). `nonblocking.json` in the same directory (42 entries) was excluded as a set.
[7] https://github.com/timmyyuan/gobench/blob/2e91eb10b8e7b2873ea44f12b87ec1b2520e1b69/goreal_executor.go — GoReal executor (native `gobench.test` invocation with `-test.count`, `-test.cpu`, `-test.failfast`, `-test.timeout`, `-test.run`; parallel container mode)
[10] https://github.com/timmyyuan/gobench/blob/2e91eb10b8e7b2873ea44f12b87ec1b2520e1b69/gobench/goreal/blocking/etcd/5509/bug.Dockerfile — etcd-5509 buggy-image recipe (`golang:1.10`; reset to `9ed3b446…`; `git apply bug_patch.diff`; `sed` edits of `test`; `INTEGRATION=1 ./test`); companion `fix.Dockerfile`
[11] https://github.com/timmyyuan/gobench/blob/2e91eb10b8e7b2873ea44f12b87ec1b2520e1b69/gobench/goreal/blocking/etcd/5509/bug_patch.diff — etcd-5509 reverse patch (only `clientv3/remote_client.go`; header `index b51116305..b8209b8a5`)
[16] https://github.com/timmyyuan/gobench/blob/2e91eb10b8e7b2873ea44f12b87ec1b2520e1b69/gobench/goreal/blocking/etcd/7492/README.md — etcd-7492 case README (upstream description, historical stack)
[17] https://github.com/timmyyuan/gobench/blob/2e91eb10b8e7b2873ea44f12b87ec1b2520e1b69/gobench/goreal/blocking/etcd/7492/bug.Dockerfile and `…/7492/bug_patch.diff` — etcd-7492 buggy-image recipe (`golang:1.13`; reset to `148c923c…`; reverse patch retaining the `var` block; two `sed` edits of `test`; `PKG=./auth PASSES='build unit' ./test`)

## Post-Task-C addendum — 2026-09-19 (append-only; the sections above are the Task C record and are unchanged)

This artifact's scope is metadata acquisition only (see "Scope and stop" above); it does not itself restore, run, or qualify. Task 5 restoration of **card C-01 (etcd-5509)** was performed after this artifact was written. Recording the outcome here as a pointer, not a rewrite of the frozen Task C classification table (row 7) or the card's own `PRIMARY_METADATA_READY` fields above, which remain the Task C record as of 2026-09-19:

**etcd-5509 is now `Q0_QUALIFIED`** (blob-equivalence check passed; 20 fresh-process `V_bad` attempts → 16 `FOCAL_DEFECT_WITNESS_A` / 4 `PASS`; 20 `V_ok` attempts → 20/20 `PASS`). Full record, including two disclosed evaluator-signature corrections made during Task 5, is in `task5_etcd5509_restoration.md`. The authoritative post-Task-5 roster status is `resource_ledger.md` A4 (updated in place, per that file's own addendum convention) and A6 (Task 5 resource accounting). Card C-02 (etcd-7492) is unaffected and remains `PRIMARY_METADATA_READY`; its own Task 5 has not been performed.

## Post-Task-C addendum 2 — 2026-09-19 (append-only; pointer only)

Acquisition was **resumed** on 2026-09-19 (operational day 2) for a non-etcd project, per ledger A9 and the "Scope and stop" note above, and stopped at the first defensible non-etcd `PRIMARY_METADATA_READY` candidate in the tier → project → numeric-ID order: **grpc-go-1859, card C-03.** The per-ID reasons that Appendix A above records as `NOT RECORDED` for cockroach_1055–36367 and etcd_6708/7443 now exist (as screening dispositions, not cards) in `task_c2_candidate_acquisition.md`; Appendix A itself is not rewritten. Roster and accounting follow-up: `resource_ledger.md` Addendum v4 (A11, A4-addendum-2, A12, A13). Nothing was restored or executed in that pass.
