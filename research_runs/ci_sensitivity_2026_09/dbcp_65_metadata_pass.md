# DBCP-65 — bounded metadata pass

## Scope and clock record

This artifact records only the approved bounded DBCP-65 metadata pass. No DBCP source or binary was restored, built, or executed; no qualification attempt was run; no harness or pipeline code was created or changed; and no unrelated candidate was inspected.

- Operational Q0 clock start / first post-amendment candidate-acquisition action: `2026-09-17T23:02:26.133312834Z`.
- Initial decision point after both answers became clear: `2026-09-17T23:03:56.830945026Z`.
- Exact acquisition-to-initial-decision wall-clock interval: `90.697633000` seconds.
- Initial artifact-write completion timestamp: `2026-09-17T23:05:36.502705119Z`.
- Exact start-to-initial-artifact-write-completion wall-clock interval: `190.369393000` seconds.
- Final metadata-verification stop: `2026-09-17T23:07:01.037184436Z`.
- Exact acquisition-to-verification-stop wall-clock interval: `274.903871602` seconds.
- Human metadata-hour charge: **UNKNOWN**. Agent/tool wall time is not equated to human metadata hours under `resource_ledger.md`.
- Applicable subcap: `min(1 human hour, remaining JaConTeBe allowance, remaining 12-hour Q0 metadata allowance)`; the two remaining allowances were already symbolically bounded because prior Task 3/4 human effort was not durably timed.
- Restoration/qualification compute charge: exactly `0` allocated vCPU-hours.

Evidence labels used below:

- **Observed evidence:** directly present in an authoritative Apache issue or imported Apache revision history, or directly visible in the previously identified reproducer source.
- **Source claim:** a reporter or maintainer statement that was not executed in this pass.
- **Inference:** the bounded-pass interpretation of that evidence against the frozen Q0 criteria.
- **Missing evidence:** information not supplied by the inspected records.

## Frozen focal obligation

The focal DBCP-65 obligation remains the one recorded in Task 4: concurrent eviction/validation and statement preparation or connection return must not acquire a DBCP connection/trace monitor and Commons Pool monitor in opposite orders and deadlock while eviction is active, especially with `testWhileIdle=true`.

The authoritative history exposes two manifestations within that obligation:

1. The original prepare-statement manifestation: a client holds `PoolingConnection` and waits for its keyed statement pool while the pool/evictor path holds the pool and waits for `PoolingConnection`.[1][7]
2. The later return/eviction manifestation: a client closes/returns a `PoolableConnection` while holding its monitor and waits for `GenericObjectPool`, while the evictor holds that pool and waits through `AbandonedTrace.addTrace` for the same connection monitor.[1][4][6]

## Question 1 — acceptable counterpart

### Result

**SUPPORTED_V_OK**

- Exact `V_ok`: `4bf62b339ef3a30dac10160da76905222063485b`.
- Exact parent: `c8034fa0290b3690e31e933402ee049af9aa39d0`.
- Imported authoritative SVN revision: `r672097`.
- Pair interpretation for the residual DBCP-65 manifestation: the parent remains the candidate defective side; the commit is the candidate acceptable side for the same return/evictor lock-order obligation. This is not an assertion that the entire revision is defect-free.

### Observed evidence

1. The nominal DBCP-65 fix is Apache commit `4ae50045738561c1c48c31bbad2ece90eaebffb8`, parent `ec3988c3bad400091ef48713dabfa38e665b434e`. It removes `synchronized` from two `PoolingConnection.prepareStatement` methods and explicitly names DBCP-65 and DBCP-202.[2]
2. DBCP-65 subsequently records that the bug still exists in 1.2.2 and gives a different but obligation-consistent lock cycle: eviction holds `GenericObjectPool` and waits in `AbandonedTrace.addTrace`, while connection return holds `PoolableConnection` and waits in `GenericObjectPool.returnObject`/`addObjectToPool`.[1]
3. DBCP-44 contains the same reported return/eviction stack. An Apache maintainer explicitly distinguishes it from DBCP-44’s original DriverManager deadlock while stating that the basic evictor/client contention is the same; the reporter then identifies the return/eviction case as DBCP-65.[3]
4. DBCP-270 records that exact return/evictor lock cycle and the `AbandonedTrace` synchronization defect. Its maintainer states that the applied patch also resolves the last deadlock reported in DBCP-44.[4]
5. Apache commit `4bf62b339ef3a30dac10160da76905222063485b` has sole parent `c8034fa0290b3690e31e933402ee049af9aa39d0`, identifies DBCP-270 and SVN `r672097`, and narrows `AbandonedTrace` synchronization from the connection object (`this`) to its internal trace list. That removes the connection-monitor edge shown in the residual DBCP-65 lock cycle.[5]
6. DBCP-281 is authoritatively titled as a “re-open of DBCP-65,” repeats the same residual stack, and is closed as a duplicate of DBCP-270. Its maintainer states that DBCP-270 was fixed in `r672097` by changing `AbandonedTrace#addTrace` to lock only the trace.[6]
7. DBCP-44 later records a maintainer assessment that the DBCP-270 `AbandonedTrace` synchronization-scope change should eliminate this second deadlock scenario.[3]
8. Apache repository comparison identifies the nominal DBCP-65 fix `4ae500...` as the merge base of `c8034fa...`, with the latter 101 commits ahead and zero behind. The immediate parent of the residual fix therefore already contains the nominal prepare-statement fix.[9]

### Inference

The linkage is sufficient to support `4bf62b...` as `V_ok` for the same frozen DBCP-65 obligation, not merely for an unrelated deadlock:

- DBCP-281 explicitly identifies itself as a reopened DBCP-65 and is authoritatively resolved as a duplicate of DBCP-270.[6]
- The residual DBCP-65/DBCP-281 stack and DBCP-270 stack have the same two lock edges and code paths.[1][4][6]
- The cumulative `V_ok` contains both the nominal prepare-statement synchronization removal and the later `AbandonedTrace` synchronization narrowing. Its immediate parent supplies the focused defective side for the residual manifestation.[2][5][9]

This also means DBCP-65’s residual manifestation and the separately carded DBCP-270 case are one upstream issue/fix episode for Q0 deduplication purposes; they cannot be counted as two independent episodes.

### Contradictory or limiting evidence

- DBCP-65 has post-closure reports that 1.2.2 still deadlocks, including a 2010 high-load report.[1] This contradicts treating release 1.2.2 or nominal revision `4ae500...` as `V_ok`; it does not contradict `r672097`, which was applied later on trunk for fix version 1.3.[4][5]
- The 2010 report supplies only the return-side stack excerpt, so it cannot establish a new lock cycle beyond the resolved DBCP-281/270 cycle.[1]
- No execution was performed. “Supported `V_ok`” is a metadata judgment; acceptable-counterpart witness validation remains a later qualification requirement.

## Question 2 — existing non-forcing protocol

### Result

**PLAUSIBLE_BUT_INCOMPLETE**

### Observed evidence and source claims

- The original DBCP-65 report describes a naturally occurring deployment deadlock, states that `testWhileIdle=true` increases its probability, supplies a thread dump, and says turning `testWhileIdle` off leaves a very small possibility.[1]
- A later DBCP-65 reporter supplies a natural configuration: DBCP 1.2.2, `minIdle=0`, `maxIdle=4`, `maxActive=8`, `testWhileIdle=true`, and `timeBetweenEvictionRunsMillis=15000`; the reporter says the deadlock occurred twice in one week in two applications after years without seeing it.[1]
- Another DBCP-65 report claims a web application under high load became stuck at connection return with DBCP 1.2.2.[1]
- DBCP-281 supplies an application stack involving Spring, Hibernate, JMS processing, and connection return, but no source package, input workload, launch command, reset procedure, or dependency lock.[6]
- DBCP-270 supplies the authentic lock-cycle dump and a production patch, but its authoritative issue has no executable reproducer attachment.[4]
- DBCP-44 does contain executable Java/test material and dependency details, but its attached `TestConcurrency` and standalone program target the distinct original DriverManager/`PoolableConnectionFactory.makeObject` lock cycle. Apache comments explicitly distinguish that first scenario from the later DBCP-65 return/evictor scenario. It therefore cannot be substituted as a protocol for this focal obligation.[3]
- The existing JaConTeBe `Dbcp65` kernel uses Mockito to force the expected path, and its shared script requests an external Java agent. It fails the non-forcing requirement.[8]

### Inference

Natural mixed manifestation is plausible: authoritative reports describe long periods without occurrence, two incidents in one week, and a high-load condition. The authentic product paths and several pool settings are identifiable.[1]

No existing source-supported protocol satisfies the full gate. The records do not provide one recoverable application/workload, exact dependency set, invocation, reset procedure, fixed condition distribution, and witness rule that can be restored without designing a new stress test. The only packaged DBCP-65 kernel deliberately controls the path. Historical frequency statements are evidence of natural occurrence, not an executable protocol.

### Missing evidence

- Complete source and immutable dependencies for either naturally failing application.
- A source-authored launch command and bounded workload for the DBCP-65 return/evictor manifestation.
- A reset recipe and fixed condition protocol suitable for repeated attempts.
- A non-Mockito, non-agent witness implementation tied to the focal lock cycle.
- Evidence that one frozen protocol can plausibly yield both passes and focal failures within the Q0 attempt budget.
- An identical protocol validated against `c8034fa...` and `4bf62b...`.

Designing a new stress test to fill these gaps is outside this pass and was not attempted.

## Final candidate disposition

**KEEP_UNRESOLVED**

DBCP-65 now has a metadata-supported acceptable counterpart for its residual focal manifestation, but it lacks an existing supported non-forcing execution protocol. It is therefore not restoration-eligible as a primary intermittent episode. The supported fix also overlaps DBCP-270 and must be deduplicated rather than counted as a second episode.

Conditional Task C should begin under the remaining deterministic source order and remaining symbolic resource limits. DBCP-65 must not be reopened again under this bounded sequence unless new external evidence is introduced by an explicitly authorized amendment.

## Sources

[1] https://issues.apache.org/jira/si/jira.issueviews:issue-xml/DBCP-65/DBCP-65.xml — ASF JIRA DBCP-65 XML
[2] https://github.com/apache/commons-dbcp/commit/4ae50045738561c1c48c31bbad2ece90eaebffb8 — nominal DBCP-65/DBCP-202 fix, imported SVN `r498524`
[3] https://issues.apache.org/jira/si/jira.issueviews:issue-xml/DBCP-44/DBCP-44.xml — ASF JIRA DBCP-44 XML and maintainer discussion distinguishing/linking the scenarios
[4] https://issues.apache.org/jira/si/jira.issueviews:issue-xml/DBCP-270/DBCP-270.xml — ASF JIRA DBCP-270 XML
[5] https://github.com/apache/commons-dbcp/commit/4bf62b339ef3a30dac10160da76905222063485b — DBCP-270 fix, imported SVN `r672097`
[6] https://issues.apache.org/jira/si/jira.issueviews:issue-xml/DBCP-281/DBCP-281.xml — authoritative reopen-of-DBCP-65 and duplicate-of-DBCP-270 record
[7] https://issues.apache.org/jira/si/jira.issueviews:issue-xml/DBCP-202/DBCP-202.xml — prepare-statement deadlock linked to nominal DBCP-65 fix
[8] https://github.com/ChopinLi-cp/JaConTeBe_TSVD — accessibility evidence for the controlled benchmark kernel only; not authoritative issue/fix provenance
[9] https://github.com/apache/commons-dbcp/compare/4ae50045738561c1c48c31bbad2ece90eaebffb8...c8034fa0290b3690e31e933402ee049af9aa39d0 — authoritative repository ancestry from nominal fix to residual-fix parent
