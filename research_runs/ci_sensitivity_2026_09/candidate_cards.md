# Task 4 — initial candidate cards

## Scope, ordering, and evidence rules

This artifact covers only Section 13 Task 4 of `docs/research/NEXT_RESEARCH_ACTION_PLAN.md`. No subject was restored or executed, no qualification attempt was run, and no harness was implemented. No command below is claimed to have been executed.

The first four cards follow the required order: POOL-162, DBCP-65, POOL-146, DBCP-270. Two Log4j cards follow because the approved source tier explicitly starts with Commons Pool, DBCP, and Log4j, identifies LOG4J-38137 as a seed, and sets an initial six-card target. LOG4J-41214 is the next Log4j issue in numeric order among the JaConTeBe inventory. This is source/roster ordering, not ranking by likely experimental effect.

Evidence labels:

- **Observed:** directly present in an authoritative upstream issue/history record or in the cited benchmark material.
- **Source claim:** an issue reporter, maintainer, or benchmark author’s claim not reproduced here.
- **Inference:** a Task 4 applicability judgment.
- **Missing:** not established by metadata inspection.

JaConTeBe’s paper and official SIR biography establish the benchmark identity.[12][13] The accessible `ChopinLi-cp/JaConTeBe_TSVD` repository is used only to inspect candidate reproducer code, scripts, packaged-version labels, and dependencies; it is not treated as authoritative defect or revision provenance.[14]

## Roster summary

| Order | Candidate | Exact candidate pair | Reproducer classification | Intermittency support | Expected role | Restoration disposition |
|---:|---|---|---|---|---|---|
| 1 | POOL-162 | `280c60ac3e918eb7fe8fb542847913bb5317cbc6` → `674a6ba9877d2de7224306c83e7871e1eddeab93` | Controlled interrupt/sleep sequence; benchmark script also requests an external Java agent | None for an unforced protocol | `STABLE_ORACLE_CONTROL` | Eligible as a control after dependencies are restored |
| 2 | DBCP-65 | `ec3988c3bad400091ef48713dabfa38e665b434e` → no supported `V_ok` | Mockito-controlled path; benchmark script also requests an external Java agent | Strong issue-report evidence for naturally rare/high-load deadlock, but not for the benchmark kernel | `UNRESOLVED` | Blocked: acceptable counterpart unresolved |
| 3 | POOL-146 | `51ae45b7462481c08fb53feaffc4d18ad4772074` → `1b80d343ca28618318e7c13760913ad91dca78c5` | Sleep/staged-thread controlled; benchmark script also requests an external Java agent | None | `STABLE_ORACLE_CONTROL` | Eligible as a control after dependencies are restored |
| 4 | DBCP-270 | `c8034fa0290b3690e31e933402ee049af9aa39d0` → `4bf62b339ef3a30dac10160da76905222063485b` | Mockito-controlled path; benchmark script also requests an external Java agent | None | `STABLE_ORACLE_CONTROL` | Eligible as a control after dependencies are restored |
| 5 | LOG4J-38137 | upstream tag `v1_2_13` (`2f10d668ef6f6ea725deaca8056e2ec1ec53f1d2`) → no supported `V_ok` | Stress-style kernel, but documented script requests an external Java agent | None specific to this case | `UNRESOLVED` | Blocked: authoritative issue inaccessible and exact fix/counterpart unresolved |
| 6 | LOG4J-41214 | upstream tag `v1_2_13` (`2f10d668ef6f6ea725deaca8056e2ec1ec53f1d2`) → no supported `V_ok` | Staged threads with a two-second ordering sleep; benchmark script also requests an external Java agent | None | `EXCLUDE` | Exclude from this Q0 queue: no acceptable counterpart; upstream lists it among outstanding high-complexity Log4j 1 bugs |

No card is qualified. No card currently satisfies the metadata needed for `PRIMARY_INTERMITTENT_CANDIDATE`: DBCP-65 has natural intermittency evidence but no acceptable counterpart, while the three supported Pool/DBCP pairs have only controlled reproducers and no case-specific evidence of unforced intermittency.

## Card 1 — POOL-162

- **Authoritative issue/source identity — observed:** ASF Commons Pool issue POOL-162, “When waiting threads are interrupted, pool can leak capacity,” type Bug, priority Major, closed as Fixed.[1]
- **Affected version/revision — observed:** the issue lists Pool 1.5, 1.5.1, 1.5.2, 1.5.3, and 1.5.4 as affected. Candidate defective revision is the immediate pre-fix parent below.[1][2]
- **Candidate `V_bad` — observed:** `280c60ac3e918eb7fe8fb542847913bb5317cbc6`, the sole parent of the focal fix commit.[2]
- **Candidate `V_ok` — observed as a focal-fix candidate, not qualified:** `674a6ba9877d2de7224306c83e7871e1eddeab93`, imported from ASF SVN revision `924479`. The issue discussion reviews that revision and the commit says it supplies the test and fix.[1][2]
- **Exact focal behavioral obligation:** after a thread waiting in `GenericObjectPool.borrowObject()` or `GenericKeyedObjectPool.borrowObject(key)` is interrupted, its abandoned allocation latch must not consume/leak pool capacity; returning the previously borrowed object must leave capacity available to a subsequent borrower rather than causing an indefinite wait or timeout.[1][2]
- **Available witness/reproducer — observed:** the upstream fix commit adds `TestGenericObjectPool.testWhenExhaustedBlockInterupt`, which exhausts a one-object pool, starts and interrupts a waiting borrower, returns the first object, and requires a second borrow to succeed. JaConTeBe provides an adapted `Test162` plus a waiting/deadlock monitor; its documented entry point is `jacontebe/pool/scripts/162.sh`.[2][14]
- **Forced/controlled versus natural — observed:** controlled. Both the upstream and benchmark tests deliberately exhaust the pool, sleep to stage the waiter, explicitly interrupt it, sleep again, then attempt another borrow. The mirror’s common script also invokes a user-local `asm-simple-project` Java agent. The interrupt is part of the real obligation, but this protocol intentionally creates the triggering state and is not evidence of ordinary CI intermittency.[2][14]
- **Intermittency evidence — missing:** neither the authoritative issue nor the inspected case material supplies case-specific pass/fail frequencies or identifies a non-forcing protocol that sometimes manifests and sometimes does not. Concurrency and sleeps alone are not intermittency evidence.
- **Exact fix commit and parent — observed:** fix `674a6ba9877d2de7224306c83e7871e1eddeab93`; parent `280c60ac3e918eb7fe8fb542847913bb5317cbc6`.[2]
- **Product-vs-test classification — observed:** combined product fix and test addition. The commit changes `GenericObjectPool`, `GenericKeyedObjectPool`, and `TestGenericObjectPool`; production handling removes an unserved interrupted latch or permits an already-served latch to continue.[2]
- **Identical target/harness plausibility — inference:** plausible through a disclosed identical backport of the added upstream test to `V_bad`, or by compiling one frozen external kernel against both revisions. The production API used by the test is unchanged in the focal commit. This would be a reconstructed test of a historical defect, not replay of an unchanged historical CI test. It remains unverified until Task 5 builds both sides.
- **Required historical toolchain/runtime — source claim:** JaConTeBe labels the reproduced environment Commons Pool 1.5 on JDK `1.6.0_33`. Its script expects Bash, `javac`/`java`, the JaConTeBe helper JAR, Commons Pool/Collections JARs, and an external Java agent at a user-local Maven path.[14]
- **Known restoration dependencies — observed:** Commons Pool source at both hashes; the identical test source; JDK 6-compatible compiler/runtime; JaConTeBe helper/reporting classes if its monitor is retained; Commons Pool and Commons Collections artifacts; and the referenced `asm-simple-project` agent, which is not present in the inspected mirror tree.[2][14]
- **Provenance problems:** upstream issue and fix history are authoritative, but the currently accessible benchmark copy has no documented custody chain from SIR. Its packaged Pool 1.5 JAR is release-level rather than the exact candidate parent, and must not substitute for the upstream hashes.[1][2][14]
- **Qualification blockers:** dependencies and old JDK are not restored; the identical backport has not been built on both revisions; monitor-to-obligation attribution and reset behavior are unverified; and no unforced intermittent protocol is documented.
- **Expected role:** `STABLE_ORACLE_CONTROL`. The metadata supports a real defect and focal pair, but only a controlled witness is presently available.

## Card 2 — DBCP-65

- **Authoritative issue/source identity — observed:** ASF Commons DBCP issue DBCP-65, “[dbcp] Deadlock when evicting dbcp objects (testWhileIdle=true),” type Bug, priority Major.[3]
- **Affected version/revision — observed/source claim:** the authoritative issue does not populate an affected-version field. JaConTeBe labels DBCP 1.2 as its defective library. The issue nominally assigns fix version 1.2.2, but later authoritative comments report the deadlock still in 1.2.2.[3][14]
- **Candidate `V_bad` — observed:** `ec3988c3bad400091ef48713dabfa38e665b434e`, the sole parent of nominal fix commit `4ae50045738561c1c48c31bbad2ece90eaebffb8`.[4]
- **Candidate `V_ok` — missing:** none. Commit `4ae50045738561c1c48c31bbad2ece90eaebffb8` cannot be used as `V_ok` for the broad evictor/connection lock-order obligation because later issue comments provide concrete 1.2.2 deadlock traces involving return/eviction and state that the bug persists.[3][4]
- **Exact focal behavioral obligation:** concurrent eviction/validation and statement preparation or connection return must not acquire the DBCP connection/trace monitor and Commons Pool monitor in opposite orders and deadlock when eviction is active, especially with `testWhileIdle=true`.[3]
- **Available witness/reproducer — observed:** the issue contains natural deployment thread dumps and configurations. JaConTeBe supplies `Dbcp65`, which starts an eviction path and a `PoolingConnection.prepareStatement` path, plus a deadlock monitor; its documented entry point is `jacontebe/dbcp/scripts/65.sh`.[3][14]
- **Forced/controlled versus natural — observed:** the issue reports potentially natural production/load manifestations. The JaConTeBe kernel is controlled: Mockito constructs the JDBC objects and explicitly ensures execution follows the expected deadlock path, while the common script requests the external Java agent.[3][14]
- **Intermittency evidence — source claim:** strong for the historical product behavior, not for the frozen benchmark kernel. The original report says there is a probability of deadlock, says disabling `testWhileIdle` leaves a very small possibility, and provides a deadlock dump. A later reporter observed it twice in one week after years without the issue in two applications. Another later report says a high-load application reaches the stuck state with “100% probability.” These reports support condition-dependent/rare natural manifestation; they do not establish the Q0 requirement of at least two passes and failures under one frozen protocol.[3]
- **Exact fix commit and parent — observed but not acceptable as final fix:** nominal fix `4ae50045738561c1c48c31bbad2ece90eaebffb8`; parent `ec3988c3bad400091ef48713dabfa38e665b434e`. The commit removes synchronization from two `PoolingConnection.prepareStatement` methods and names DBCP-65 and DBCP-202.[4]
- **Product-vs-test classification — observed:** production-only nominal fix; no test is added in that commit.[4]
- **Identical target/harness plausibility — inference:** plausible across the nominal parent/fix because the change removes method synchronization without changing the used API, but that pair does not provide a supported `V_ok`. A final obligation-satisfying fix must first be identified; only then can one frozen kernel be checked against both sides.
- **Required historical toolchain/runtime — source claim:** JaConTeBe labels DBCP 1.2 on JDK `1.6.0_33`. Its material expects Bash, `javac`/`java`, Commons DBCP 1.2, Commons Pool 1.2, Commons Collections 2.1, Mockito 1.9.5, JaConTeBe helper classes, and the external Java agent.[14]
- **Known restoration dependencies — observed:** exact DBCP and Pool source/binaries, old JDK compatibility, Mockito and helper/reporting JARs, the generated/helper `KeyGenerator` source, monitor logic, and the missing user-local agent.[14]
- **Provenance problems:** the upstream issue/nominal commit chain is authoritative, but issue closure and fix-version metadata conflict with later issue evidence. The mirror kernel and binaries have weak custody and cannot resolve the acceptable revision.[3][4][14]
- **Qualification blockers:** no defensible `V_ok`; the focal obligation may span DBCP-65, DBCP-44, and DBCP-270-era lock changes; the kernel is forced; the historical natural configurations depend on application/JDBC/load context; dependencies are unrestored.
- **Expected role:** `UNRESOLVED`. It is the strongest primary-intermittency lead in these six, but it cannot enter restoration qualification as a paired episode until the final focal fix and acceptable counterpart are traced.

## Card 3 — POOL-146

- **Authoritative issue/source identity — observed:** ASF Commons Pool issue POOL-146, “Thread deadlock issue in GenericKeyedObjectPool borrowObject(),” type Bug, priority Major, closed as Fixed.[5]
- **Affected version/revision — observed:** Pool 1.5 and 1.5.1 are listed as affected. The issue’s report contrasts problematic 1.5.1 behavior with 1.4, but that release comparison is not used to infer `V_ok`.[5]
- **Candidate `V_bad` — observed:** `51ae45b7462481c08fb53feaffc4d18ad4772074`, the sole parent of the focal production fix and a revision that already contains the final pre-fix form of the upstream regression test.[8][9]
- **Candidate `V_ok` — observed as a focal-fix candidate, not qualified:** `1b80d343ca28618318e7c13760913ad91dca78c5`.[9]
- **Exact focal behavioral obligation:** in a `GenericKeyedObjectPool` with per-key capacity, a waiter blocked because key A has reached `maxActive` must not prevent an immediately serviceable borrow for key B when total pool capacity remains available.[5][9]
- **Available witness/reproducer — observed:** upstream history adds `TestGenericKeyedObjectPool.testBlockedKeyDoesNotBlockPool`, updates it, and fixes its thread-start/timing error before the production fix.[8] JaConTeBe provides an adapted `Test146` and waiting monitor; its documented entry point is `jacontebe/pool/scripts/146.sh`.[14]
- **Forced/controlled versus natural — observed:** controlled. The test fixes limits, borrows key A, starts a second key-A borrower, sleeps one second to stage it, then borrows key B. The benchmark common script also requests the external Java agent.[8][14]
- **Intermittency evidence — missing:** no case-specific source establishes mixed pass/focal-failure outcomes under an unforced frozen protocol. The one-second staging sleep is control, not proof of intermittency.
- **Exact fix commit and parent — observed:** fix `1b80d343ca28618318e7c13760913ad91dca78c5`; parent `51ae45b7462481c08fb53feaffc4d18ad4772074`.[9]
- **Product-vs-test classification — observed:** the focal commit is production-only, changing `GenericKeyedObjectPool.allocate()` so allocation scans eligible queued latches rather than allowing an unsatisfied first key to block all allocation.[9]
  The regression test was created and corrected in the three preceding commits `e147ad5ab62e3379ea570d99ea90240039e0fc5b`, `9e74a87041a8a256412a4bb247d6e4a54d745528`, and `51ae45b7462481c08fb53feaffc4d18ad4772074`.[6][7][8]
- **Identical target/harness plausibility — observed/inference:** especially strong. The exact upstream test source already exists unchanged in both immediate sides of the production fix; no backport is needed. Task 5 must still verify that the same test selection and environment actually build and run on both hashes.[8][9]
- **Required historical toolchain/runtime — source claim:** JaConTeBe labels Commons Pool 1.5 and JDK `1.6.0_33`; upstream history preserves a pre-Java-5-compatible codebase. The benchmark material expects Bash, `javac`/`java`, Commons Pool/Collections and helper JARs, plus the external Java agent.[14]
- **Known restoration dependencies — observed:** exact upstream source hashes and their historical build dependencies; JDK 6-compatible tooling; the upstream test framework for the native test or JaConTeBe helper/monitor for the external kernel; and the missing agent if the benchmark script is used unchanged.[8][9][14]
- **Provenance problems:** issue and upstream test/fix history are strong.[5][9] The accessible benchmark mirror remains non-authoritative, and its Pool 1.5 JAR does not identify the exact immediate parent.[14]
- **Qualification blockers:** ancient build/dependencies are unrestored; target selection and timeout witness are unverified; the upstream test uses timing control; no unforced intermittency evidence exists.
- **Expected role:** `STABLE_ORACLE_CONTROL`.

## Card 4 — DBCP-270

- **Authoritative issue/source identity — observed:** ASF Commons DBCP issue DBCP-270, “Dead lock using the evictor,” type Bug, priority Critical, closed as Fixed.[10]
- **Affected version/revision — observed:** DBCP 1.2.2 is listed as affected. Candidate defective revision is the immediate parent below.[10][11]
- **Candidate `V_bad` — observed:** `c8034fa0290b3690e31e933402ee049af9aa39d0`, the sole parent of the focal fix.[11]
- **Candidate `V_ok` — observed as a focal-fix candidate, not qualified:** `4bf62b339ef3a30dac10160da76905222063485b`.[10][11]
- **Exact focal behavioral obligation:** concurrent evictor validation and connection return/close must not deadlock by holding the pool monitor while waiting for a `PoolableConnection`/`AbandonedTrace` monitor as the other thread holds that connection/trace monitor and waits for the pool.[10][11]
- **Available witness/reproducer — observed:** the issue supplies the lock-cycle thread dump and an attached patch description. JaConTeBe supplies `Dbcp270`, which starts `PoolableConnection.close()` and `GenericObjectPool.evict()` paths with a deadlock monitor; its documented entry point is `jacontebe/dbcp/scripts/270.sh`.[10][14]
- **Forced/controlled versus natural — observed:** the issue dump is from an application/Tomcat setting and is potentially natural. The benchmark kernel is controlled: Mockito stubs JDBC and pool factories “to make sure the program goes along the expected path leading to deadlock”; the common script also requests the external Java agent.[10][14]
- **Intermittency evidence — missing:** the issue proves an observed deadlock but supplies no frequency or same-protocol pass evidence. Concurrency alone does not establish intermittency.
- **Exact fix commit and parent — observed:** fix `4bf62b339ef3a30dac10160da76905222063485b`; parent `c8034fa0290b3690e31e933402ee049af9aa39d0`.[11]
- **Product-vs-test classification — observed:** production fix plus change log, no test. It narrows `AbandonedTrace` synchronization from `this` to the trace list and returns a copied trace list.[11]
- **Identical target/harness plausibility — inference:** plausible using one frozen external kernel because the focal API used by the kernel is unchanged across the immediate parent/fix. There is no upstream regression test in the focal commit, so the reconstructed external witness and its monitor must be disclosed and checked identically on both sides.
- **Required historical toolchain/runtime — source claim:** JaConTeBe labels DBCP 1.2 on JDK `1.6.0_33`, while the authoritative affected version is 1.2.2. The kernel expects Bash, `javac`/`java`, DBCP/Pool/Collections, Mockito 1.9.5, helper/reporting classes, and the external Java agent.[10][14]
- **Known restoration dependencies — observed:** exact DBCP source hashes; compatible Commons Pool/Collections; Mockito and JaConTeBe helper/monitor JARs; JDK 6-era compatibility; and the absent user-local agent.[11][14]
- **Provenance problems:** authoritative issue/fix history is strong, but the mirror labels its binary DBCP 1.2 rather than authoritative affected version 1.2.2 and lacks a custody chain. Exact-revision builds must replace packaged release binaries for pair qualification.[10][11][14]
- **Qualification blockers:** version mismatch between benchmark package and issue; old dependencies unrestored; controlled/mock reproducer; no native unforced frequency evidence; identical target and oracle not yet tested.
- **Expected role:** `STABLE_ORACLE_CONTROL`.

## Card 5 — LOG4J-38137

- **Authoritative issue/source identity — missing at inspection time:** the candidate points to ASF Bugzilla issue 38137, but both the browser and REST endpoint require authentication. The issue body/status therefore was not independently inspected.[15] JaConTeBe and its accessible mirror identify the case, but they are benchmark evidence, not authoritative upstream issue provenance.[12][14]
- **Affected version/revision — source claim plus upstream tag identity:** JaConTeBe labels Log4j 1.2.13 on JDK `1.6.0_33`. The authoritative repository’s `v1_2_13` tag resolves to `2f10d668ef6f6ea725deaca8056e2ec1ec53f1d2`; the issue-to-tag relation is presently supported by JaConTeBe rather than an accessible upstream issue record.[14][17]
- **Candidate `V_bad` — provisional:** `2f10d668ef6f6ea725deaca8056e2ec1ec53f1d2` (`v1_2_13`). It is not yet an authenticated issue-linked defective revision.[14][17]
- **Candidate `V_ok` — missing:** no later release is promoted to `V_ok`. Two nearby upstream commits alter `AsyncAppender` behavior—`4654df42766950b34b796d03849e4184ba069f13` for Bug 38982 and `4311600dc532367e57710ef90a8a55cc2a6ae244` for Bug 30106—but no inspected authoritative record links either one to Bug 38137’s exact obligation.[18][19]
- **Exact focal behavioral obligation — benchmark-supported, not yet upstream-authenticated:** concurrent producers and the `AsyncAppender` dispatcher must continue making progress when the bounded buffer fills; producers and consumer must not all wait indefinitely on the buffer monitor.[14]
- **Available witness/reproducer — observed in mirror:** `Test38137` starts ten producer threads, each appending 50 events through an `AsyncAppender`, joins them, and uses the JaConTeBe waiting monitor. Its documented entry point is `jacontebe/log4j/scripts/38137.sh`.[14]
- **Forced/controlled versus natural — mixed:** the Java workload is a stress-style reproducer without explicit Mockito or a staging sleep in the focal producer code, so a non-agent version might be potentially natural. The documented script is controlled because the shared runner requests the external Java agent; monitor and workload also deliberately fill the buffer.[14]
- **Intermittency evidence — missing:** no accessible case-specific source classifies this kernel among JaConTeBe’s deterministic/several-run groups, and no same-protocol frequency evidence was found.
- **Exact fix commit and parent — missing:** neither the Bug 38982 rewrite nor Bug 30106 dispatcher-self-deadlock guard can be assigned as the Bug 38137 fix without an authoritative linkage.[18][19]
- **Product-vs-test classification — unresolved:** the known nearby commits are production changes, but their relation to this issue is unproven.[18][19]
- **Identical target/harness plausibility — inference:** technically plausible across an eventual API-compatible fix pair, but scientifically unsupported until exact `V_bad`, fix, and `V_ok` are linked. The same mirror kernel cannot by itself supply provenance.
- **Required historical toolchain/runtime — source claim:** Log4j 1.2.13 and JDK `1.6.0_33`; Bash, `javac`/`java`, Log4j JAR, JaConTeBe helper/monitor JAR, and the external Java agent.[14]
- **Known restoration dependencies — observed:** exact upstream revision pair; Log4j’s old build dependencies if source builds are needed; helper/reporting classes; monitor; and the absent agent.[14][17]
- **Provenance problems:** inaccessible authoritative issue; no exact fix linkage; third-party mirror custody gap; packaged 1.2.13 JAR not proven identical to the upstream tag artifact in this task.
- **Qualification blockers:** authoritative issue fields unavailable; no supported `V_ok`; no exact fix/parent; no case-specific intermittency evidence; missing agent and unrestored historical runtime.
- **Expected role:** `UNRESOLVED`.

## Card 6 — LOG4J-41214

- **Authoritative issue/source identity — partially observed:** ASF Bugzilla issue 41214 is the referenced upstream identity, but the issue and REST endpoint require authentication.[16] The current authoritative Log4j 1 repository README independently lists issue 41214, “Deadlock with RollingFileAppender,” among high-complexity Log4j 1 bugs for which the EOL project will not invest in fixes.[17]
- **Affected version/revision — source claim plus upstream tag identity:** JaConTeBe labels Log4j 1.2.13; upstream tag `v1_2_13` resolves to `2f10d668ef6f6ea725deaca8056e2ec1ec53f1d2`.[14][17]
- **Candidate `V_bad` — provisional:** `2f10d668ef6f6ea725deaca8056e2ec1ec53f1d2` (`v1_2_13`), based on the benchmark’s version claim and upstream tag identity.[14][17]
- **Candidate `V_ok` — missing:** none. The authoritative repository’s EOL notice treats 41214 as outstanding; no later release is inferred acceptable.[17]
- **Exact focal behavioral obligation — benchmark-supported:** logging from a root-logger thread and from object/exception rendering paths must not invert locks between a logger/category and an appender, leaving both threads permanently blocked.[14]
- **Available witness/reproducer — observed in mirror:** a multi-class reproducer starts object and exception logging threads, sleeps two seconds so their rendering methods run before the root logger, starts the root-logger thread, joins it, and uses the JaConTeBe deadlock monitor. Its documented entry point is `jacontebe/log4j/scripts/41214.sh`.[14]
- **Forced/controlled versus natural — observed:** controlled. It explicitly orders thread phases with a two-second sleep and the shared script requests the external Java agent.[14]
- **Intermittency evidence — missing:** no source establishes mixed pass/failure behavior under one frozen non-forcing protocol.
- **Exact fix commit and parent — missing:** no focal fix was identified, consistent with the current upstream project’s listing of the issue among unresolved high-complexity/EOL work.[17]
- **Product-vs-test classification — missing:** no upstream production fix exists in the inspected evidence.
- **Identical target/harness plausibility — not currently meaningful:** one kernel could be frozen across two revisions, but no supported acceptable revision exists.
- **Required historical toolchain/runtime — source claim:** Log4j 1.2.13, JDK `1.6.0_33`, Bash, `javac`/`java`, Log4j, JaConTeBe helper/monitor classes, and the external Java agent.[14]
- **Known restoration dependencies — observed:** multi-package benchmark source, exact Log4j 1.2.13/tag artifact, helper/reporting JAR, monitor, old Java compatibility, and missing user-local agent.[14][17]
- **Provenance problems:** Bugzilla authentication wall; no fix provenance; mirror custody gap; benchmark version-to-upstream-hash link not independently authenticated by the issue.
- **Qualification blockers:** no acceptable counterpart or fix; controlled reproducer; no intermittency evidence; historical dependencies unavailable.
- **Expected role:** `EXCLUDE`. It is retained in the roster for traceability but should not consume the bounded restoration budget.

## Task 4 decision

### Candidates eligible for restoration

1. **POOL-162** — eligible only as a `STABLE_ORACLE_CONTROL`: authoritative defect, exact parent/fix pair, precise obligation, an upstream regression witness that can be identically backported, and known dependency gaps.
2. **POOL-146** — eligible only as a `STABLE_ORACLE_CONTROL`: authoritative defect, exact parent/fix pair, and the same upstream regression test already present on both immediate revisions.
3. **DBCP-270** — eligible only as a `STABLE_ORACLE_CONTROL`: authoritative defect and exact pair, with a plausibly identical external kernel; lower restoration priority because the witness is mock/agent-controlled and its packaged version disagrees with the issue’s affected version.

Eligibility here means metadata sufficient to justify bounded restoration inspection. It is not Q0 qualification and does not make any of these a primary intermittent episode.

### Blocked candidates

- **DBCP-65:** blocked because the nominal fix is contradicted by later issue reports, so there is no supported `V_ok`; the natural intermittency evidence cannot compensate for a missing acceptable counterpart.
- **LOG4J-38137:** blocked by inaccessible authoritative issue metadata, no supported fix/parent or `V_ok`, and no case-specific intermittency evidence.
- **LOG4J-41214:** excluded because no fix/acceptable counterpart is supported and upstream currently lists it among outstanding high-complexity Log4j 1 bugs under EOL.

### Task 5 first restoration candidate

**POOL-162.** It remains first by the approved source/evidence order. It satisfies the Q0 metadata gate for a bounded control restoration because the authoritative issue establishes the real product defect and affected versions; the exact immediate defective parent and focal fix are known; the obligation is independently interpretable; the fix commit includes a focused regression witness; the same witness can plausibly be held identical through a disclosed backport; and historical runtime/dependency/provenance gaps are explicit.[1][2] Its forced protocol and missing intermittency evidence preclude primary-cohort status unless a separate non-forcing protocol is later supported; Task 5 must not relabel it as intermittent.

## Sources

[1] https://issues.apache.org/jira/si/jira.issueviews:issue-xml/POOL-162/POOL-162.xml
[2] https://github.com/apache/commons-pool/commit/674a6ba9877d2de7224306c83e7871e1eddeab93
[3] https://issues.apache.org/jira/si/jira.issueviews:issue-xml/DBCP-65/DBCP-65.xml
[4] https://github.com/apache/commons-dbcp/commit/4ae50045738561c1c48c31bbad2ece90eaebffb8
[5] https://issues.apache.org/jira/si/jira.issueviews:issue-xml/POOL-146/POOL-146.xml
[6] https://github.com/apache/commons-pool/commit/e147ad5ab62e3379ea570d99ea90240039e0fc5b
[7] https://github.com/apache/commons-pool/commit/9e74a87041a8a256412a4bb247d6e4a54d745528
[8] https://github.com/apache/commons-pool/commit/51ae45b7462481c08fb53feaffc4d18ad4772074
[9] https://github.com/apache/commons-pool/commit/1b80d343ca28618318e7c13760913ad91dca78c5
[10] https://issues.apache.org/jira/si/jira.issueviews:issue-xml/DBCP-270/DBCP-270.xml
[11] https://github.com/apache/commons-dbcp/commit/4bf62b339ef3a30dac10160da76905222063485b
[12] https://mir.cs.illinois.edu/marinov/publications/LinETAL15JaConTeBe.pdf
[13] https://sir-public.github.io/SIR/JaConTeBe.html
[14] https://github.com/ChopinLi-cp/JaConTeBe_TSVD
[15] https://bz.apache.org/bugzilla/show_bug.cgi?id=38137
[16] https://bz.apache.org/bugzilla/show_bug.cgi?id=41214
[17] https://github.com/apache/logging-log4j1
[18] https://github.com/apache/logging-log4j1/commit/4311600dc532367e57710ef90a8a55cc2a6ae244
[19] https://github.com/apache/logging-log4j1/commit/4654df42766950b34b796d03849e4184ba069f13
